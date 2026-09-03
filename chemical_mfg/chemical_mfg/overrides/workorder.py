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
#     # OPERATION STATUS (CHEMICAL LOGIC)
#     # --------------------------------------------------
#     def update_operation_status(self):
#         for d in self.get("operations") or []:
#             if flt(d.completed_qty) > 0:
#                 d.status = "Completed"
#             else:
#                 d.status = "Pending"

#     # --------------------------------------------------
#     # REQUIRED ITEMS (GROUP BY item_code + operation)
#     # --------------------------------------------------
#     def set_required_items(self, reset_only_qty=False, **kwargs):
#         """
#         Chemical mfg override of ERPNext's set_required_items.

#         Behaviour:
#           - GROUP BY (item_code, operation) — never merges rows across operations
#           - Same item + same operation IS combined into one row (per spec)
#           - Idempotent: always rebuilt from BOM, never patched from existing rows,
#             so N saves produce the same table as 1 save
#           - Handles both reset_only_qty=True and False on the same rebuild path,
#             because the standard reset_only_qty branch in ERPNext uses
#             get_bom_items_as_dict() which merges by item_code only — the exact
#             behaviour we must avoid
#           - Accepts **kwargs so future ERPNext signatures (e.g. reset_source_warehouse)
#             do not raise TypeError

#         Why we do NOT delegate to the parent:
#           ERPNext's set_required_items calls
#               get_bom_items_as_dict(bom_no, company, qty, fetch_exploded)
#           which does `GROUP BY item_code, stock_uom` in SQL and then aggregates
#           again in Python keyed only on item_code. That is what causes
#           "Item ABC in Operation A + Item ABC in Operation B" to collapse into
#           a single ABC row after save. We bypass that function entirely and
#           build the required_items table directly from bom.items.
#         """
#         if not self.bom_no or not self.qty:
#             # nothing to build against — leave table alone
#             return

#         bom = frappe.get_doc("BOM", self.bom_no)
#         bom_qty = flt(bom.quantity) or 1.0
#         wo_qty = flt(self.qty)
#         scale = wo_qty / bom_qty

#         # 1) Aggregate BOM rows by (item_code, operation)
#         #    - preserves ordering so the UI is stable across saves
#         #    - sums qty when the same item + same operation appears twice
#         grouped = {}
#         order = []
#         for item in bom.items:
#             key = (item.item_code, item.operation or "")
#             if key not in grouped:
#                 order.append(key)
#                 grouped[key] = {
#                     "item_code": item.item_code,
#                     "item_name": item.item_name,
#                     "description": item.description,
#                     "operation": item.operation,
#                     "uom": item.uom,
#                     "stock_uom": item.stock_uom,
#                     "conversion_factor": item.conversion_factor or 1,
#                     "source_warehouse": item.source_warehouse or self.source_warehouse,
#                     "allow_alternative_item": item.allow_alternative_item,
#                     "include_item_in_manufacturing": item.include_item_in_manufacturing,
#                     "rate": item.rate,
#                     "qty": 0.0,
#                 }
#             grouped[key]["qty"] += flt(item.qty)

#         # 2) ALWAYS rebuild from the aggregated dict.
#         #    This is what makes save + re-save idempotent, and what stops
#         #    ERPNext's reset_only_qty branch from re-merging our rows.
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

#         # 3) Preserve ERPNext's default of populating availability columns.
#         #    Wrapped in try/except so a bin-lookup failure never blocks Save.
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

    # --------------------------------------------------
    # DISABLE STRICT STANDARD VALIDATIONS
    # --------------------------------------------------
    def validate_completed_qty(self):
        pass

    def validate_qty_to_produce_against_completed_qty(self):
        pass

    def validate_qty_to_produce(self):
        pass

    # --------------------------------------------------
    # VALIDATE — extended hook
    # --------------------------------------------------
    # Runs on every save (both create and re-save). Two jobs:
    #
    # 1) Recompute operation statuses using the chemical rule.
    #    Standard ERPNext only calls update_operation_status() from
    #    Job Card submit/cancel — never from WO save. Calling it here
    #    means an existing WO with stale "Work in Progress" statuses
    #    self-heals the moment anyone re-saves it.
    #
    # 2) Required-items backstop. If for any reason required_items
    #    has fewer rows than the BOM has distinct (item, operation)
    #    pairs (i.e. something merged them), rebuild from the BOM.
    # --------------------------------------------------
    def validate(self):
        super().validate()

        # (1) Recompute operation statuses
        try:
            self.update_operation_status()
        except Exception:
            frappe.log_error(
                title="CustomWorkOrder.validate: update_operation_status failed",
                message=frappe.get_traceback(),
            )

        # (2) Required-items backstop
        if self.bom_no and flt(self.qty):
            try:
                bom = frappe.get_doc("BOM", self.bom_no)
                bom_keys = set(
                    (b.item_code, b.operation or "") for b in (bom.get("items") or [])
                )
                if len(self.get("required_items") or []) < len(bom_keys):
                    self._rebuild_required_items_from_bom(bom)
            except Exception:
                frappe.log_error(
                    title="CustomWorkOrder.validate: required-items rebuild failed",
                    message=frappe.get_traceback(),
                )

    # --------------------------------------------------
    # OPERATION STATUS (CHEMICAL LOGIC)
    # --------------------------------------------------
    # In chemical / process manufacturing an operation output is often
    # LESS than the WO Qty To Manufacture because of intentional
    # process loss. Standard ERPNext treats any qty < WO qty as
    # "Work in Progress", which is wrong for this business.
    # Rule:
    #   completed_qty > 0  → Completed
    #   completed_qty == 0 → Pending
    # --------------------------------------------------
    def update_operation_status(self):
        for d in self.get("operations") or []:
            if flt(d.completed_qty) > 0:
                d.status = "Completed"
            else:
                d.status = "Pending"

    # --------------------------------------------------
    # REQUIRED ITEMS (GROUP BY item_code + operation)
    # --------------------------------------------------
    # Standard ERPNext uses get_bom_items_as_dict() which groups by
    # item_code alone — that is what merges rows across operations.
    # We bypass that entirely and rebuild from bom.items directly,
    # keyed on (item_code, operation).
    #   - same item + different operations => separate rows
    #   - same item + same operation      => quantities summed
    #   - idempotent: N saves == 1 save
    #   - **kwargs accepted for future ERPNext signatures
    # --------------------------------------------------
    def set_required_items(self, reset_only_qty=False, **kwargs):
        if not self.bom_no or not self.qty:
            return

        bom = frappe.get_doc("BOM", self.bom_no)
        self._rebuild_required_items_from_bom(bom)

    # --------------------------------------------------
    # INTERCEPT BOM SELECTION FROM THE NEW WORK ORDER FORM
    # --------------------------------------------------
    # Called by ERPNext when the user picks a BOM on a fresh Work
    # Order form and from make_work_order() at creation. Overriding
    # here guarantees no merge happens on that entry path either.
    # --------------------------------------------------
    @frappe.whitelist()
    def get_items_and_operations_from_bom(self):
        if not self.bom_no or not flt(self.qty):
            return {}

        bom = frappe.get_doc("BOM", self.bom_no)
        self._rebuild_required_items_from_bom(bom)
        self.set_work_order_operations()

        try:
            from erpnext.manufacturing.doctype.work_order.work_order import (
                check_if_scrap_warehouse_mandatory,
            )
            return check_if_scrap_warehouse_mandatory(self.bom_no)
        except Exception:
            return {}

    # --------------------------------------------------
    # SHARED REBUILD HELPER (required items)
    # --------------------------------------------------
    def _rebuild_required_items_from_bom(self, bom):
        bom_qty = flt(bom.quantity) or 1.0
        wo_qty = flt(self.qty)
        scale = wo_qty / bom_qty

        # 1) Aggregate BOM rows by (item_code, operation)
        grouped = {}
        order = []
        for b in bom.get("items") or []:
            key = (b.item_code, b.operation or "")
            if key not in grouped:
                order.append(key)
                grouped[key] = {
                    "item_code": b.item_code,
                    "item_name": b.item_name,
                    "description": b.description,
                    "operation": b.operation,
                    "uom": b.uom,
                    "stock_uom": b.stock_uom,
                    "conversion_factor": b.conversion_factor or 1,
                    "source_warehouse": b.source_warehouse or self.source_warehouse,
                    "allow_alternative_item": b.allow_alternative_item,
                    "include_item_in_manufacturing": b.include_item_in_manufacturing,
                    "rate": b.rate,
                    "qty": 0.0,
                }
            grouped[key]["qty"] += flt(b.qty)

        # 2) Full rebuild — idempotent
        self.set("required_items", [])
        for key in order:
            row = grouped[key]
            req_qty = flt(row["qty"]) * scale
            self.append("required_items", {
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "description": row["description"],
                "operation": row["operation"],
                "required_qty": req_qty,
                "uom": row["uom"],
                "stock_uom": row["stock_uom"],
                "conversion_factor": row["conversion_factor"],
                "source_warehouse": row["source_warehouse"],
                "allow_alternative_item": row["allow_alternative_item"],
                "include_item_in_manufacturing": row["include_item_in_manufacturing"],
                "rate": row["rate"],
                "amount": flt(row["rate"]) * req_qty,
            })

        # 3) Populate availability columns (best-effort)
        try:
            self.set_available_qty()
        except Exception:
            pass

    # --------------------------------------------------
    # MANUFACTURED QTY / PROCESS LOSS  (unchanged)
    # --------------------------------------------------
    def update_work_order_qty(self):
        """
        - Kill process loss
        - Manufactured Qty = max completed operation qty
        """
        super().update_work_order_qty()
        self.process_loss_qty = 0

        if self.operations:
            self.manufactured_qty = max(
                flt(op.completed_qty) for op in self.operations
            )
        else:
            self.manufactured_qty = flt(self.qty_completed)
