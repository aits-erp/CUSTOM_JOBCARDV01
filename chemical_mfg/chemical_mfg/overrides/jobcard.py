import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class CustomJobCard(JobCard):

    # --------------------------------------------------
    # DISABLE STANDARD VALIDATIONS (AS REQUESTED)
    # --------------------------------------------------
    def validate_job_card(self):
        return

    def validate_sequence_id(self):
        return

    def validate_job_card_qty(self):
        return

    # --------------------------------------------------
    # KEEP STANDARD VALIDATE + KILL PROCESS LOSS
    # --------------------------------------------------
    def validate(self):
        super().validate()
        self.process_loss_qty = 0

    # --------------------------------------------------
    # ON SUBMIT – CORE FIXES
    # --------------------------------------------------
    def on_submit(self):
        super().on_submit()

        # 🔒 Always kill process loss
        self.db_set("process_loss_qty", 0, update_modified=False)

        # ✅ Apply cumulative operation qty logic
        self.update_cumulative_completed_qty()

        # ✅ FIX: Ensure Job Card gets Completed
        self.update_job_card_status()

    # --------------------------------------------------
    # CUMULATIVE COMPLETED QTY (SEQUENCE-WISE)
    # --------------------------------------------------
    def update_cumulative_completed_qty(self):
        """
        Example:
        Seq 1 = 10
        Seq 2 = 10 → becomes 20
        Seq 3 = 5  → becomes 25
        """

        if not self.work_order or not self.operation:
            return

        wo = frappe.get_doc("Work Order", self.work_order)

        current_op = None
        for op in wo.operations:
            if op.operation == self.operation:
                current_op = op
                break

        if not current_op:
            return

        current_seq = flt(current_op.sequence_id)

        # ✅ Job Card correct field
        current_qty = flt(self.total_completed_qty or 0)

        previous_total = 0
        for op in wo.operations:
            if flt(op.sequence_id) < current_seq:
                previous_total += flt(op.completed_qty or 0)

        cumulative_qty = previous_total + current_qty

        current_op.completed_qty = cumulative_qty
        wo.save(ignore_permissions=True)

    # --------------------------------------------------
    # 🔥 FORCE JOB CARD STATUS
    # --------------------------------------------------
    def update_job_card_status(self):
        """
        ERPNext does NOT auto-complete Job Card.
        We must do it manually.
        """

        completed = flt(self.total_completed_qty or 0)
        planned = flt(self.for_quantity or 0)

        if planned > 0 and completed >= planned:
            self.db_set("status", "Completed", update_modified=False)
