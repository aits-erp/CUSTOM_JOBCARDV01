# import frappe
# from frappe.utils import flt
# from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder


# class CustomWorkOrder(WorkOrder):

#     # --------------------------------------------------
#     # DISABLE STRICT STANDARD VALIDATIONS
#     # --------------------------------------------------
#     def validate_completed_qty(self):
#         pass

#     def validate_qty_to_produce_against_completed_qty(self):
#         pass

#     def validate_qty_to_produce(self):
#         pass

#     # --------------------------------------------------
#     # VALIDATE — extended hook
#     # --------------------------------------------------
#     # Runs on every save (both create and re-save). Two jobs:
#     #
#     # 1) Recompute operation statuses using the chemical rule.
#     #    Standard ERPNext only calls update_operation_status() from
#     #    Job Card submit/cancel — never from WO save. Calling it here
#     #    means an existing WO with stale "Work in Progress" statuses
#     #    self-heals the moment anyone re-saves it.
#     #
#     # 2) Required-items backstop. If for any reason required_items
#     #    has fewer rows than the BOM has distinct (item, operation)
#     #    pairs (i.e. something merged them), rebuild from the BOM.
#     # --------------------------------------------------
#     def validate(self):
#         super().validate()

#         # (1) Recompute operation statuses
#         try:
#             self.update_operation_status()
#         except Exception:
#             frappe.log_error(
#                 title="CustomWorkOrder.validate: update_operation_status failed",
#                 message=frappe.get_traceback(),
#             )

#         # (2) Required-items backstop
#         if self.bom_no and flt(self.qty):
#             try:
#                 bom = frappe.get_doc("BOM", self.bom_no)
#                 bom_keys = set(
#                     (b.item_code, b.operation or "") for b in (bom.get("items") or [])
#                 )
#                 if len(self.get("required_items") or []) < len(bom_keys):
#                     self._rebuild_required_items_from_bom(bom)
#             except Exception:
#                 frappe.log_error(
#                     title="CustomWorkOrder.validate: required-items rebuild failed",
#                     message=frappe.get_traceback(),
#                 )

#     # --------------------------------------------------
#     # OPERATION STATUS (CHEMICAL LOGIC)
#     # --------------------------------------------------
#     # In chemical / process manufacturing an operation output is often
#     # LESS than the WO Qty To Manufacture because of intentional
#     # process loss. Standard ERPNext treats any qty < WO qty as
#     # "Work in Progress", which is wrong for this business.
#     # Rule:
#     #   completed_qty > 0  → Completed
#     #   completed_qty == 0 → Pending
#     # --------------------------------------------------
#     def update_operation_status(self):
#         # Chemical-process rule, extended to also honor Job Card status
#         # directly (kept consistent with
#         # CustomJobCard.sync_work_order_operation_from_job_card in
#         # jobcard.py, so a manual Work Order re-save can never disagree
#         # with what Job Card submission just set):
#         #   - a Completed Job Card exists for this operation -> Completed
#         #   - completed_qty > 0 (process-loss-aware, existing rule) -> Completed
#         #   - otherwise -> Pending
#         for d in self.get("operations") or []:
#             has_completed_job_card = False
#             if d.name and not self.is_new():
#                 has_completed_job_card = bool(
#                     frappe.db.exists(
#                         "Job Card",
#                         {
#                             "work_order": self.name,
#                             "operation_id": d.name,
#                             "docstatus": 1,
#                             "status": "Completed",
#                             "is_corrective_job_card": 0,
#                         },
#                     )
#                 )

#             if has_completed_job_card or flt(d.completed_qty) > 0:
#                 d.status = "Completed"
#             else:
#                 d.status = "Pending"

#     # --------------------------------------------------
#     # REQUIRED ITEMS (GROUP BY item_code + operation)
#     # --------------------------------------------------
#     # Standard ERPNext uses get_bom_items_as_dict() which groups by
#     # item_code alone — that is what merges rows across operations.
#     # We bypass that entirely and rebuild from bom.items directly,
#     # keyed on (item_code, operation).
#     #   - same item + different operations => separate rows
#     #   - same item + same operation      => quantities summed
#     #   - idempotent: N saves == 1 save
#     #   - **kwargs accepted for future ERPNext signatures
#     # --------------------------------------------------
#     def set_required_items(self, reset_only_qty=False, **kwargs):
#         if not self.bom_no or not self.qty:
#             return

#         bom = frappe.get_doc("BOM", self.bom_no)
#         self._rebuild_required_items_from_bom(bom)

#     # --------------------------------------------------
#     # INTERCEPT BOM SELECTION FROM THE NEW WORK ORDER FORM
#     # --------------------------------------------------
#     # Called by ERPNext when the user picks a BOM on a fresh Work
#     # Order form and from make_work_order() at creation. Overriding
#     # here guarantees no merge happens on that entry path either.
#     # --------------------------------------------------
#     @frappe.whitelist()
#     def get_items_and_operations_from_bom(self):
#         if not self.bom_no or not flt(self.qty):
#             return {}

#         bom = frappe.get_doc("BOM", self.bom_no)
#         self._rebuild_required_items_from_bom(bom)
#         self.set_work_order_operations()

#         try:
#             from erpnext.manufacturing.doctype.work_order.work_order import (
#                 check_if_scrap_warehouse_mandatory,
#             )
#             return check_if_scrap_warehouse_mandatory(self.bom_no)
#         except Exception:
#             return {}

#     # --------------------------------------------------
#     # SHARED REBUILD HELPER (required items)
#     # --------------------------------------------------
#     def _rebuild_required_items_from_bom(self, bom):
#         bom_qty = flt(bom.quantity) or 1.0
#         wo_qty = flt(self.qty)
#         scale = wo_qty / bom_qty

#         # 1) Aggregate BOM rows by (item_code, operation)
#         grouped = {}
#         order = []
#         for b in bom.get("items") or []:
#             key = (b.item_code, b.operation or "")
#             if key not in grouped:
#                 order.append(key)
#                 grouped[key] = {
#                     "item_code": b.item_code,
#                     "item_name": b.item_name,
#                     "description": b.description,
#                     "operation": b.operation,
#                     "uom": b.uom,
#                     "stock_uom": b.stock_uom,
#                     "conversion_factor": b.conversion_factor or 1,
#                     "source_warehouse": b.source_warehouse or self.source_warehouse,
#                     "allow_alternative_item": b.allow_alternative_item,
#                     "include_item_in_manufacturing": b.include_item_in_manufacturing,
#                     "rate": b.rate,
#                     "qty": 0.0,
#                 }
#             grouped[key]["qty"] += flt(b.qty)

#         # 2) Full rebuild — idempotent
#         self.set("required_items", [])
#         for key in order:
#             row = grouped[key]
#             req_qty = flt(row["qty"]) * scale
#             self.append("required_items", {
#                 "item_code": row["item_code"],
#                 "item_name": row["item_name"],
#                 "description": row["description"],
#                 "operation": row["operation"],
#                 "required_qty": req_qty,
#                 "uom": row["uom"],
#                 "stock_uom": row["stock_uom"],
#                 "conversion_factor": row["conversion_factor"],
#                 "source_warehouse": row["source_warehouse"],
#                 "allow_alternative_item": row["allow_alternative_item"],
#                 "include_item_in_manufacturing": row["include_item_in_manufacturing"],
#                 "rate": row["rate"],
#                 "amount": flt(row["rate"]) * req_qty,
#             })

#         # 3) Populate availability columns (best-effort)
#         try:
#             self.set_available_qty()
#         except Exception:
#             pass

#     # --------------------------------------------------
#     # MANUFACTURED QTY / PROCESS LOSS  (unchanged)
#     # --------------------------------------------------
#     def update_work_order_qty(self):
#         """
#         - Kill process loss
#         - Manufactured Qty = max completed operation qty
#         """
#         super().update_work_order_qty()
#         self.process_loss_qty = 0

#         if self.operations:
#             self.manufactured_qty = max(
#                 flt(op.completed_qty) for op in self.operations
#             )
#         else:
#             self.manufactured_qty = flt(self.qty_completed)

import frappe
from frappe.utils import flt

from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder


class CustomWorkOrder(WorkOrder):

    # ==========================================================
    # DISABLE STRICT STANDARD VALIDATIONS
    # ==========================================================

    def validate_completed_qty(self):
        pass

    def validate_qty_to_produce_against_completed_qty(self):
        pass

    def validate_qty_to_produce(self):
        pass

    # ==========================================================
    # VALIDATE
    # ==========================================================

    def validate(self):
        """
        Custom Work Order validation.

        Main purposes:

        1. Update operation status according to chemical
           manufacturing logic.

        2. ALWAYS rebuild Required Items from BOM using:

               item_code + operation

           This prevents the same raw material from being
           merged when it is used in multiple operations.

        Example:

            R1101 -> BATCHING
            R1101 -> HOMOGENIZING
            R1101 -> FINALIZING

        These remain 3 separate rows.
        """

        # Run standard ERPNext validations first
        super().validate()

        # ------------------------------------------------------
        # 1. UPDATE OPERATION STATUS
        # ------------------------------------------------------

        try:
            self.update_operation_status()

        except Exception:
            frappe.log_error(
                title="CustomWorkOrder.validate: update_operation_status failed",
                message=frappe.get_traceback(),
            )

        # ------------------------------------------------------
        # 2. ALWAYS REBUILD REQUIRED ITEMS FROM BOM
        # ------------------------------------------------------

        if self.bom_no and flt(self.qty):

            try:
                bom = frappe.get_doc("BOM", self.bom_no)

                # IMPORTANT:
                # Do NOT compare only row counts.
                #
                # Always rebuild from BOM using:
                #
                #     item_code + operation
                #
                self._rebuild_required_items_from_bom(bom)

            except Exception:

                frappe.log_error(
                    title="CustomWorkOrder.validate: required-items rebuild failed",
                    message=frappe.get_traceback(),
                )

                # Do not silently continue.
                # If BOM rebuilding fails, Work Order should
                # show the actual error instead of saving
                # incorrect Required Items.
                raise

    # ==========================================================
    # OPERATION STATUS
    # ==========================================================

    def update_operation_status(self):
        """
        Chemical manufacturing operation status logic.

        Rules:

            Completed Job Card exists
                    OR
            completed_qty > 0

                    =>
                Completed

            Otherwise
                    =>
                Pending

        This allows process loss.

        Example:

            Work Order Qty       = 1000 KG
            Operation Completed  = 950 KG

        Standard logic may consider this incomplete.

        Our chemical logic considers it Completed because
        completed_qty > 0.
        """

        for operation in self.get("operations") or []:

            has_completed_job_card = False

            # Existing Work Order only
            if operation.name and not self.is_new():

                has_completed_job_card = bool(
                    frappe.db.exists(
                        "Job Card",
                        {
                            "work_order": self.name,
                            "operation_id": operation.name,
                            "docstatus": 1,
                            "status": "Completed",
                            "is_corrective_job_card": 0,
                        },
                    )
                )

            # --------------------------------------------------
            # COMPLETED
            # --------------------------------------------------

            if (
                has_completed_job_card
                or flt(operation.completed_qty) > 0
            ):
                operation.status = "Completed"

            # --------------------------------------------------
            # PENDING
            # --------------------------------------------------

            else:
                operation.status = "Pending"

    # ==========================================================
    # REQUIRED ITEMS
    # ==========================================================

    def set_required_items(self, reset_only_qty=False, **kwargs):
        """
        Override ERPNext standard Required Items generation.

        Standard ERPNext can group BOM items by item code.

        We need:

            item_code + operation

        as the unique combination.

        Therefore:

            R1101 + BATCHING
            R1101 + HOMOGENIZING
            R1101 + FINALIZING

        are separate Required Item rows.
        """

        if not self.bom_no or not flt(self.qty):
            return

        bom = frappe.get_doc("BOM", self.bom_no)

        self._rebuild_required_items_from_bom(bom)

    # ==========================================================
    # BOM SELECTION
    # ==========================================================

    @frappe.whitelist()
    def get_items_and_operations_from_bom(self):
        """
        Called when BOM is selected in Work Order.

        Handles:

            New Work Order
                ↓
            Production Item
                ↓
            BOM
                ↓
            Required Items
                +
            Operations
        """

        if not self.bom_no or not flt(self.qty):
            return {}

        bom = frappe.get_doc("BOM", self.bom_no)

        # ------------------------------------------------------
        # REQUIRED ITEMS
        # ------------------------------------------------------

        self._rebuild_required_items_from_bom(bom)

        # ------------------------------------------------------
        # OPERATIONS
        # ------------------------------------------------------

        self.set_work_order_operations()

        # ------------------------------------------------------
        # SCRAP WAREHOUSE CHECK
        # ------------------------------------------------------

        try:

            from erpnext.manufacturing.doctype.work_order.work_order import (
                check_if_scrap_warehouse_mandatory,
            )

            return check_if_scrap_warehouse_mandatory(self.bom_no)

        except Exception:

            return {}

    # ==========================================================
    # REBUILD REQUIRED ITEMS FROM BOM
    # ==========================================================

    def _rebuild_required_items_from_bom(self, bom):
        """
        Rebuild Work Order Required Items directly from BOM.

        IMPORTANT LOGIC:

            key = (item_code, operation)

        Therefore:

            Same Item
            +
            Different Operation

            =

            Different Work Order rows.

        Example BOM:

            R1101   BATCHING       50 KG
            R1101   HOMOGENIZING   20 KG
            R1101   FINALIZING     10 KG

        Work Order:

            R1101   BATCHING       50 KG
            R1101   HOMOGENIZING   20 KG
            R1101   FINALIZING     10 KG

        They are NOT merged into:

            R1101   80 KG
        """

        # ------------------------------------------------------
        # BOM QUANTITY
        # ------------------------------------------------------

        bom_qty = flt(bom.quantity) or 1.0

        # ------------------------------------------------------
        # WORK ORDER QUANTITY
        # ------------------------------------------------------

        wo_qty = flt(self.qty)

        # ------------------------------------------------------
        # QUANTITY SCALE
        # ------------------------------------------------------

        scale = wo_qty / bom_qty

        # ------------------------------------------------------
        # GROUP BOM ITEMS
        # ------------------------------------------------------

        grouped = {}

        # Preserve BOM row order
        order = []

        for bom_row in bom.get("items") or []:

            item_code = bom_row.item_code
            operation = bom_row.operation or ""

            # --------------------------------------------------
            # CRITICAL KEY
            # --------------------------------------------------
            #
            # DO NOT use only item_code.
            #
            # Use:
            #
            #     item_code + operation
            #
            # --------------------------------------------------

            key = (
                item_code,
                operation,
            )

            # --------------------------------------------------
            # FIRST OCCURRENCE
            # --------------------------------------------------

            if key not in grouped:

                order.append(key)

                grouped[key] = {

                    "item_code": item_code,

                    "item_name": bom_row.item_name,

                    "description": bom_row.description,

                    "operation": bom_row.operation,

                    "uom": bom_row.uom,

                    "stock_uom": bom_row.stock_uom,

                    "conversion_factor":
                        bom_row.conversion_factor or 1,

                    "source_warehouse":
                        bom_row.source_warehouse
                        or self.source_warehouse,

                    "allow_alternative_item":
                        bom_row.allow_alternative_item,

                    "include_item_in_manufacturing":
                        bom_row.include_item_in_manufacturing,

                    "rate": bom_row.rate,

                    "qty": 0.0,
                }

            # --------------------------------------------------
            # ADD QUANTITY
            # --------------------------------------------------

            grouped[key]["qty"] += flt(bom_row.qty)

        # ======================================================
        # CLEAR EXISTING REQUIRED ITEMS
        # ======================================================

        self.set("required_items", [])

        # ======================================================
        # CREATE REQUIRED ITEMS
        # ======================================================

        for key in order:

            row = grouped[key]

            # --------------------------------------------------
            # SCALE BOM QTY TO WORK ORDER QTY
            # --------------------------------------------------

            required_qty = flt(row["qty"]) * scale

            # --------------------------------------------------
            # APPEND WORK ORDER ITEM
            # --------------------------------------------------

            self.append(
                "required_items",
                {
                    "item_code": row["item_code"],

                    "item_name": row["item_name"],

                    "description": row["description"],

                    # VERY IMPORTANT
                    "operation": row["operation"],

                    "required_qty": required_qty,

                    "uom": row["uom"],

                    "stock_uom": row["stock_uom"],

                    "conversion_factor":
                        row["conversion_factor"],

                    "source_warehouse":
                        row["source_warehouse"],

                    "allow_alternative_item":
                        row["allow_alternative_item"],

                    "include_item_in_manufacturing":
                        row["include_item_in_manufacturing"],

                    "rate": row["rate"],

                    "amount":
                        flt(row["rate"]) * required_qty,
                },
            )

        # ======================================================
        # UPDATE AVAILABLE QTY
        # ======================================================

        try:

            self.set_available_qty()

        except Exception:

            # Availability is only a helper.
            # Do not prevent Work Order creation if this
            # calculation fails.
            pass

    # ==========================================================
    # MANUFACTURED QTY / PROCESS LOSS
    # ==========================================================

    def update_work_order_qty(self):
        """
        Chemical manufacturing logic.

        Process loss is not treated as pending production.

        Example:

            WO Qty = 1000 KG

            BATCHING completed = 1000 KG
            HOMOGENIZING completed = 980 KG
            FINALIZING completed = 970 KG

        Manufactured Qty = MAX operation completed qty

                           = 1000 KG

        Process Loss = 0

        """

        # Run ERPNext standard logic first
        super().update_work_order_qty()

        # ------------------------------------------------------
        # Disable standard process loss
        # ------------------------------------------------------

        self.process_loss_qty = 0

        # ------------------------------------------------------
        # Calculate Manufactured Qty
        # ------------------------------------------------------

        if self.get("operations"):

            self.manufactured_qty = max(
                flt(operation.completed_qty)
                for operation in self.get("operations") or []
            )

        else:

            self.manufactured_qty = flt(
                self.qty_completed
            )