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

        Required Items are always rebuilt from the selected BOM,
        one Required Item row per BOM item row - never grouped,
        merged, or summed. See _rebuild_required_items_from_bom.

        Example:

            R1101 -> BATCHING
            R1101 -> HOMOGENIZING
            R1101 -> FINALIZING

        These remain separate rows. Likewise, duplicate
        item_code + operation combinations within the same BOM
        (e.g. the same raw material listed twice under FINALIZING)
        remain separate rows too.
        """

        # Run standard ERPNext validation first
        super().validate()

        # ------------------------------------------------------
        # UPDATE OPERATION STATUS
        # ------------------------------------------------------

        try:
            self.update_operation_status()

        except Exception:
            frappe.log_error(
                title="CustomWorkOrder: Operation Status Error",
                message=frappe.get_traceback(),
            )

        # ------------------------------------------------------
        # REBUILD REQUIRED ITEMS
        # ------------------------------------------------------

        if self.bom_no and flt(self.qty):

            try:
                bom = frappe.get_doc(
                    "BOM",
                    self.bom_no
                )

                self._rebuild_required_items_from_bom(
                    bom
                )

            except Exception:

                frappe.log_error(
                    title="CustomWorkOrder: Required Items Error",
                    message=frappe.get_traceback(),
                )

                raise

    # ==========================================================
    # OPERATION STATUS
    # ==========================================================

    def update_operation_status(self):
        """
        Chemical manufacturing rule:

            completed_qty > 0
                OR
            Completed Job Card exists

                =>
            Completed

        Otherwise:

            Pending
        """

        for operation in self.get("operations") or []:

            has_completed_job_card = False

            # --------------------------------------------------
            # CHECK EXISTING JOB CARD
            # --------------------------------------------------

            if (
                operation.name
                and not self.is_new()
            ):

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
    # SET REQUIRED ITEMS
    # ==========================================================

    def set_required_items(
        self,
        reset_only_qty=False,
        **kwargs
    ):
        """
        Override standard ERPNext Required Items generation.

        Standard ERPNext (get_bom_items_as_dict) groups BOM rows
        by item_code alone, merging/losing rows. We bypass that
        entirely: every BOM item row becomes exactly one Required
        Item row, carrying that row's own operation, never merged
        with any other row - not even a duplicate item_code +
        operation row.
        """

        if not self.bom_no:
            return

        if not flt(self.qty):
            return

        bom = frappe.get_doc(
            "BOM",
            self.bom_no
        )

        self._rebuild_required_items_from_bom(
            bom
        )

    # ==========================================================
    # GET ITEMS AND OPERATIONS FROM BOM
    # ==========================================================

    @frappe.whitelist()
    def get_items_and_operations_from_bom(self):
        """
        Handles:

            New Work Order
                ↓
            Production Item
                ↓
            BOM
                ↓
            Work Order Operations
                ↓
            Required Items
        """

        if not self.bom_no:
            return {}

        if not flt(self.qty):
            return {}

        # ------------------------------------------------------
        # GET BOM
        # ------------------------------------------------------

        bom = frappe.get_doc(
            "BOM",
            self.bom_no
        )

        # ------------------------------------------------------
        # IMPORTANT:
        #
        # CREATE WORK ORDER OPERATIONS FIRST
        # ------------------------------------------------------

        self.set_work_order_operations()

        # ------------------------------------------------------
        # THEN CREATE REQUIRED ITEMS
        # ------------------------------------------------------

        self._rebuild_required_items_from_bom(
            bom
        )

        # ------------------------------------------------------
        # STANDARD SCRAP WAREHOUSE CHECK
        # ------------------------------------------------------

        try:

            from erpnext.manufacturing.doctype.work_order.work_order import (
                check_if_scrap_warehouse_mandatory,
            )

            return check_if_scrap_warehouse_mandatory(
                self.bom_no
            )

        except Exception:

            return {}

    # ==========================================================
    # REBUILD REQUIRED ITEMS FROM BOM
    # ==========================================================

    def _rebuild_required_items_from_bom(
        self,
        bom
    ):
        """
        Build Required Items directly from BOM.

        IMPORTANT:

        Every BOM item row becomes exactly one Required Item
        row, in BOM row order, carrying that row's own operation.
        Rows are NEVER grouped, merged, or summed - not even when
        item_code + operation repeats across multiple BOM rows.

        Example BOM:

            R1101 -> BATCHING       50 KG
            R1101 -> HOMOGENIZING   20 KG
            R1101 -> FINALIZING     10 KG

            S6014 -> FINALIZING      3.0 KG
            S6014 -> FINALIZING      0.7 KG
            S6014 -> FINALIZING      3.0 KG

        Result: 6 separate Required Item rows (scaled by
        work_order_qty / bom_qty), in the same order - S6014
        stays as three separate FINALIZING rows, NOT one row
        summed to 6.7 KG.
        """

        # ======================================================
        # QUANTITY CALCULATION
        # ======================================================

        bom_qty = flt(
            bom.quantity
        ) or 1.0

        work_order_qty = flt(
            self.qty
        )

        if not work_order_qty:
            self.set(
                "required_items",
                []
            )
            return

        scale = (
            work_order_qty
            / bom_qty
        )

        # ======================================================
        # GROUP BOM ITEMS
        # ======================================================

        grouped = {}

        order = []

        for bom_item in (
            bom.get("items") or []
        ):

            item_code = (
                bom_item.item_code
            )

            operation = (
                bom_item.operation
                or ""
            )

            # --------------------------------------------------
            # CRITICAL KEY
            # --------------------------------------------------
            #
            # bom_item.idx makes this key unique per BOM row.
            #
            # Every BOM item row becomes exactly one Required
            # Item row - never merged, never summed. Even when
            # the same item_code + operation repeats multiple
            # times in the BOM (e.g. the same raw material added
            # twice under the same operation), each occurrence
            # stays a separate row.
            # --------------------------------------------------

            key = (
                item_code,
                operation,
                bom_item.idx,
            )

            if key not in grouped:

                order.append(
                    key
                )

                grouped[key] = {

                    "item_code":
                        item_code,

                    "item_name":
                        bom_item.item_name,

                    "description":
                        bom_item.description,

                    "operation":
                        operation,

                    "uom":
                        bom_item.uom,

                    "stock_uom":
                        bom_item.stock_uom,

                    "conversion_factor":
                        bom_item.conversion_factor
                        or 1,

                    "source_warehouse":
                        bom_item.source_warehouse
                        or self.source_warehouse,

                    "allow_alternative_item":
                        bom_item.allow_alternative_item,

                    "include_item_in_manufacturing":
                        bom_item.include_item_in_manufacturing,

                    "rate":
                        flt(bom_item.rate),

                    "qty":
                        0.0,
                }

            # --------------------------------------------------
            # ADD BOM QUANTITY
            # --------------------------------------------------

            grouped[key]["qty"] += flt(
                bom_item.qty
            )

        # ======================================================
        # PRESERVE EXISTING TRANSFERRED QTY
        # ======================================================

        existing_transferred = {}

        for old_row in (
            self.get("required_items") or []
        ):

            old_key = (
                old_row.item_code,
                old_row.operation or "",
                old_row.idx,
            )

            existing_transferred[
                old_key
            ] = flt(
                old_row.transferred_qty
            )

        # ======================================================
        # CLEAR REQUIRED ITEMS
        # ======================================================

        self.set(
            "required_items",
            []
        )

        # ======================================================
        # CREATE REQUIRED ITEMS
        # ======================================================

        for key in order:

            row = grouped[key]

            required_qty = (
                flt(row["qty"])
                * scale
            )

            transferred_qty = (
                existing_transferred.get(
                    key,
                    0
                )
            )

            # --------------------------------------------------
            # APPEND
            # --------------------------------------------------

            self.append(
                "required_items",
                {

                    "item_code":
                        row["item_code"],

                    "item_name":
                        row["item_name"],

                    "description":
                        row["description"],

                    # IMPORTANT
                    "operation":
                        row["operation"],

                    "required_qty":
                        required_qty,

                    "transferred_qty":
                        transferred_qty,

                    "uom":
                        row["uom"],

                    "stock_uom":
                        row["stock_uom"],

                    "conversion_factor":
                        row["conversion_factor"],

                    "source_warehouse":
                        row["source_warehouse"],

                    "allow_alternative_item":
                        row["allow_alternative_item"],

                    "include_item_in_manufacturing":
                        row[
                            "include_item_in_manufacturing"
                        ],

                    "rate":
                        row["rate"],

                    "amount":
                        (
                            flt(row["rate"])
                            * required_qty
                        ),
                }
            )

        # ======================================================
        # AVAILABLE QTY
        # ======================================================

        try:

            self.set_available_qty()

        except Exception:

            # Availability calculation should not
            # prevent Work Order creation.
            pass

    # ==========================================================
    # MANUFACTURED QTY / PROCESS LOSS
    # ==========================================================

    def update_work_order_qty(self):
        """
        Chemical manufacturing logic.

        Process loss is disabled.

        Manufactured Qty is the maximum completed quantity
        across all operations.
        """

        # Run standard ERPNext calculation
        super().update_work_order_qty()

        # ------------------------------------------------------
        # DISABLE PROCESS LOSS
        # ------------------------------------------------------

        self.process_loss_qty = 0

        # ------------------------------------------------------
        # MANUFACTURED QTY
        # ------------------------------------------------------

        if self.get("operations"):

            completed_quantities = [
                flt(
                    operation.completed_qty
                )
                for operation
                in self.get("operations")
                or []
            ]

            self.manufactured_qty = max(
                completed_quantities
            )

        else:

            self.manufactured_qty = flt(
                self.qty_completed
            )