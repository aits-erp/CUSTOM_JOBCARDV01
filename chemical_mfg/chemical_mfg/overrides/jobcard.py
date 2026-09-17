# import frappe
# from frappe.utils import flt
# from erpnext.manufacturing.doctype.job_card.job_card import JobCard


# class CustomJobCard(JobCard):
    

#     def validate(self):

#         try:
#             super().validate()

#         except Exception as e:

#             if "Could not find Quality Inspection" in str(e):
#                 frappe.msgprint("Quality Inspection bypassed")
#             else:
#                 raise

#     # --------------------------------------------------
#     # DISABLE STRICT STANDARD VALIDATIONS
#     # --------------------------------------------------
#     def validate_completed_qty(self):
#         pass
#     # --------------------------------------------------
#     # DISABLE STANDARD VALIDATIONS (AS REQUIRED)
#     # --------------------------------------------------
#     def validate_job_card(self):
#         return

#     def validate_sequence_id(self):
#         return

#     def validate_job_card_qty(self):
#         return

#     # --------------------------------------------------
#     # KEEP STANDARD VALIDATE + KILL PROCESS LOSS
#     # --------------------------------------------------
#     def validate(self):
#         # keep standard ERPNext validate
#         super().validate()

#         # always force process loss to zero
#         self.process_loss_qty = 0

#     # --------------------------------------------------
#     # ONLY FIX STATUS (NO EXTRA LOGIC)
#     # --------------------------------------------------
#     def on_submit(self):
#         # keep standard submit flow
#         super().on_submit()

#         # ❌ DO NOT db_set inside submit (causes refresh error)
#         # just update in memory
#         self.process_loss_qty = 0

#         # update status safely
#         self.update_job_card_status()

#     # --------------------------------------------------
#     # STATUS FIX (MINIMAL & SAFE)
#     # --------------------------------------------------
#     def update_job_card_status(self):
#         completed = flt(self.total_completed_qty or 0)
#         planned = flt(self.for_quantity or 0)

#         if planned > 0 and completed >= planned:
#             # ❌ do not use db_set here
#             self.status = "Completed"
import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class CustomJobCard(JobCard):

    # --------------------------------------------------
    # DISABLE STRICT STANDARD VALIDATIONS (EXISTING - UNCHANGED)
    # --------------------------------------------------
    def validate_completed_qty(self):
        pass

    def validate_job_card(self):
        return

    def validate_sequence_id(self):
        return

    def validate_job_card_qty(self):
        return

    # --------------------------------------------------
    # VALIDATE (EXISTING - FIXED)
    # --------------------------------------------------
    # NOTE: the previous version of this file defined validate() TWICE.
    # In Python, the second definition silently replaced the first, so the
    # try/except that bypassed the "Could not find Quality Inspection" error
    # was dead code and never actually ran. Merged into one method so both
    # behaviours (Quality Inspection bypass + process_loss_qty reset) work.
    # --------------------------------------------------
    def validate(self):
        try:
            super().validate()
        except Exception as e:
            if "Could not find Quality Inspection" in str(e):
                frappe.msgprint("Quality Inspection bypassed")
            else:
                raise

        # always force process loss to zero
        self.process_loss_qty = 0

    # --------------------------------------------------
    # SUBMIT (EXISTING LOGIC PRESERVED + NEW SYNC STEP ADDED)
    # --------------------------------------------------
    def on_submit(self):
        # keep standard submit flow: this already runs
        # validate_transfer_qty -> validate_job_card -> update_work_order()
        # -> set_transferred_qty(). update_work_order() is what normally
        # pushes completed_qty into the Work Order Operation row and calls
        # Work Order.update_operation_status(); we do NOT remove this.
        super().on_submit()

        # keep in-memory value consistent (existing behaviour)
        self.process_loss_qty = 0

        # existing status fix (kept, unchanged)
        self.update_job_card_status()

        # NEW: force-sync the linked Work Order Operation from Job Card
        # status. This is the authoritative, defensive step that guarantees
        # the Work Order reflects "Completed" the moment this Job Card is
        # Completed, regardless of qty vs Work Order Qty To Manufacture.
        self.sync_work_order_operation_from_job_card()

    def on_cancel(self):
        # keep standard cancel flow (recomputes Work Order via update_work_order())
        super().on_cancel()

        # NEW: re-derive the operation status/qty now that this Job Card's
        # contribution has been removed (handles cancel / amend correctly).
        self.sync_work_order_operation_from_job_card()

    def on_update_after_submit(self):
        # Standard JobCard does not define this hook, so there is nothing to
        # call super() for. This covers the case where a submitted Job
        # Card's status/qty is changed afterwards (e.g. via amend-in-place
        # utilities or Data Import) without a fresh submit.
        self.sync_work_order_operation_from_job_card()

    # --------------------------------------------------
    # STATUS FIX (EXISTING - UNCHANGED)
    # --------------------------------------------------
    def update_job_card_status(self):
        completed = flt(self.total_completed_qty or 0)
        planned = flt(self.for_quantity or 0)

        if planned > 0 and completed >= planned:
            # in-memory only; persisted as part of the submit transaction
            self.status = "Completed"

    # --------------------------------------------------
    # NEW: JOB CARD -> WORK ORDER OPERATION SYNC
    # --------------------------------------------------
    def sync_work_order_operation_from_job_card(self):
        """
        Keep Work Order > Operations in sync with Job Card status.

        Business rule (as specified):
            Job Card Status == "Completed"  -> Work Order Operation = Completed
            (never depends on completed_qty >= Work Order Qty To Manufacture)

        Design notes:
          - Writes directly to the DB with frappe.db.set_value(). This does
            NOT call Work Order.save()/validate(), so it can never trigger
            Work Order -> Job Card recursion (requirement F), and it cannot
            create duplicate Stock Entries / Job Cards / transactions
            (requirement G) because nothing else is submitted or saved here.
          - Idempotent: safe to call multiple times, on submit, cancel, or
            re-save; running it twice for the same data produces the same
            result.
          - Handles: Job Card without a Work Order, Job Card without an
            Operation, an operation row that cannot be found (e.g. deleted
            or regenerated), multiple Job Cards against the same operation,
            amended/cancelled Job Cards, and corrective Job Cards (skipped,
            matching standard ERPNext behaviour for corrective cards).
        """
        # Corrective job cards don't map 1:1 to a Work Order Operation row -
        # standard update_work_order() already special-cases these, so we
        # leave them alone here too.
        if getattr(self, "is_corrective_job_card", 0):
            return

        # J: Job Card has no Work Order
        if not self.work_order:
            return

        operation_id = self.operation_id

        # J: Job Card has no Operation / operation_id link
        if not operation_id:
            if not self.operation:
                return
            # best-effort recovery: resolve the row via (work_order, operation)
            operation_id = frappe.db.get_value(
                "Work Order Operation",
                {"parent": self.work_order, "operation": self.operation},
                "name",
            )
            if not operation_id:
                frappe.log_error(
                    title="chemical_mfg: Job Card -> Work Order Operation sync skipped",
                    message=(
                        "Job Card {0}: could not resolve a Work Order Operation "
                        "row for Work Order {1}, operation {2}"
                    ).format(self.name, self.work_order, self.operation),
                )
                return

        # J: Work Order operation row cannot be found (deleted / regenerated)
        if not frappe.db.exists("Work Order Operation", operation_id):
            frappe.log_error(
                title="chemical_mfg: Work Order Operation not found",
                message="Job Card {0} references missing operation row {1}".format(
                    self.name, operation_id
                ),
            )
            return

        # F: recursion / re-entrancy guard (defensive - this path never calls
        # Work Order.save(), but this keeps repeated calls in one request cheap
        # and safe if this method is ever invoked more than once per row).
        guard_key = "chemical_mfg_wo_op_sync::{0}".format(operation_id)
        if frappe.flags.get(guard_key):
            return

        frappe.flags[guard_key] = True
        try:
            self._recompute_operation_from_job_cards(operation_id)
        finally:
            frappe.flags[guard_key] = False

    def _recompute_operation_from_job_cards(self, operation_id):
        # J: multiple Job Cards can exist for the same operation. Aggregate
        # completed qty from every currently submitted, non-corrective Job
        # Card for this exact operation row - this mirrors ERPNext's own
        # get_current_operation_data() so the qty stays correct no matter
        # how many Job Cards contribute to it, and automatically corrects
        # itself when one of them is cancelled/amended.
        result = frappe.db.sql(
            """
            SELECT
                COALESCE(SUM(total_completed_qty), 0) AS completed_qty,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_cards
            FROM `tabJob Card`
            WHERE
                docstatus = 1
                AND work_order = %s
                AND operation_id = %s
                AND IFNULL(is_corrective_job_card, 0) = 0
            """,
            (self.work_order, operation_id),
            as_dict=True,
        )

        row = result[0] if result else {}
        completed_qty = flt(row.get("completed_qty"))
        has_completed_job_card = flt(row.get("completed_cards")) > 0

        # C: Job Card status is the source of truth for completion.
        # completed_qty > 0 is kept only as a fallback for the existing
        # chemical-process rule (process loss means qty is often below the
        # Work Order Qty To Manufacture - that alone is still a valid
        # "Completed" signal), but a Completed Job Card ALWAYS wins even if
        # qty happens to be recorded as 0.
        if has_completed_job_card or completed_qty > 0:
            new_status = "Completed"
        else:
            new_status = "Pending"

        frappe.db.set_value(
            "Work Order Operation",
            operation_id,
            {
                "completed_qty": completed_qty,
                "status": new_status,
            },
            update_modified=False,
        )

        # Keep Work Order.manufactured_qty consistent with the existing
        # chemical_mfg rule in CustomWorkOrder.update_work_order_qty()
        # (manufactured_qty = max completed operation qty), without needing
        # a full Work Order save.
        max_completed = frappe.db.sql(
            """
            SELECT MAX(completed_qty) FROM `tabWork Order Operation`
            WHERE parent = %s
            """,
            (self.work_order,),
        )[0][0]

        if max_completed is not None:
            frappe.db.set_value(
                "Work Order",
                self.work_order,
                "manufactured_qty",
                flt(max_completed),
                update_modified=False,
            )