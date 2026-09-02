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
#     # VALIDATE — Final safety net so items are never merged
#     # --------------------------------------------------
#     # Runs on every save. If required_items has fewer rows than
#     # bom.items, something merged them somewhere in the flow —
#     # rebuild directly from bom.items.
#     # --------------------------------------------------
#     def validate(self):
#         super().validate()

#         if self.bom_no and flt(self.qty):
#             try:
#                 bom = frappe.get_doc("BOM", self.bom_no)
#                 bom_rows = len(bom.get("items") or [])
#                 wo_rows = len(self.get("required_items") or [])

#                 if wo_rows < bom_rows:
#                     self._rebuild_required_items_from_bom(bom)
#             except Exception:
#                 frappe.log_error(
#                     title="CustomWorkOrder.validate: rebuild check failed",
#                     message=frappe.get_traceback(),
#                 )

#     # --------------------------------------------------
#     # KEEP SAME ITEM AS SEPARATE ROWS PER OPERATION
#     # --------------------------------------------------
#     # Standard ERPNext v15 merges BOM items by item_code alone,
#     # so an item used in two different operations becomes a single
#     # required_items row and only one operation survives. This
#     # override rebuilds directly from bom.items, one WO row per
#     # BOM row.
#     # --------------------------------------------------
#     def set_required_items(self, reset_only_qty=False, reset_source_warehouse=False, *args, **kwargs):
#         if not self.bom_no or not flt(self.qty):
#             if not reset_only_qty:
#                 self.set("required_items", [])
#             return

#         bom = frappe.get_doc("BOM", self.bom_no)
#         bom_qty = flt(bom.quantity) or 1.0
#         wo_qty = flt(self.qty)

#         # Fast path: keep rows, only rescale qty
#         if reset_only_qty and self.get("required_items"):
#             bom_by_key = {}
#             for b in bom.get("items") or []:
#                 key = (b.item_code, b.operation or "")
#                 bom_by_key.setdefault(key, []).append(b)

#             used = {}
#             for row in self.get("required_items"):
#                 key = (row.item_code, row.operation or "")
#                 candidates = bom_by_key.get(key) or []
#                 idx = used.get(key, 0)
#                 bom_row = candidates[idx] if idx < len(candidates) else (candidates[0] if candidates else None)
#                 used[key] = idx + 1

#                 if not bom_row:
#                     continue

#                 new_qty = (flt(bom_row.qty) / bom_qty) * wo_qty
#                 row.required_qty = new_qty
#                 row.rate = bom_row.rate
#                 row.amount = flt(bom_row.rate) * new_qty
#                 if reset_source_warehouse:
#                     row.source_warehouse = bom_row.source_warehouse or self.source_warehouse
#             return

#         # Full rebuild
#         self._rebuild_required_items_from_bom(bom)

#     # --------------------------------------------------
#     # INTERCEPT BOM SELECTION FROM NEW WORK ORDER FORM
#     # --------------------------------------------------
#     # Called when the user picks/changes bom_no on a fresh Work
#     # Order form. Standard ERPNext merges here — we rebuild fresh.
#     # --------------------------------------------------
#     @frappe.whitelist()
#     def get_items_and_operations_from_bom(self):
#         if not self.bom_no or not flt(self.qty):
#             return {}

#         bom = frappe.get_doc("BOM", self.bom_no)
#         self._rebuild_required_items_from_bom(bom)

#         # Return in the shape ERPNext callers expect
#         result = {}
#         for row in self.get("required_items") or []:
#             key = (row.item_code, row.operation or "")
#             result[key] = frappe._dict({
#                 "item_code": row.item_code,
#                 "item_name": row.item_name,
#                 "description": row.description,
#                 "operation": row.operation,
#                 "qty": row.required_qty,
#                 "uom": row.uom,
#                 "stock_uom": row.stock_uom,
#                 "conversion_factor": row.conversion_factor,
#                 "source_warehouse": row.source_warehouse,
#                 "allow_alternative_item": row.allow_alternative_item,
#                 "include_item_in_manufacturing": row.include_item_in_manufacturing,
#                 "rate": row.rate,
#                 "amount": row.amount,
#                 "idx": row.idx,
#             })
#         return result

#     # --------------------------------------------------
#     # SHARED HELPER — the actual rebuild logic
#     # --------------------------------------------------
#     def _rebuild_required_items_from_bom(self, bom):
#         """Wipe required_items and rebuild one row per BOM item row."""
#         bom_qty = flt(bom.quantity) or 1.0
#         wo_qty = flt(self.qty)

#         self.set("required_items", [])
#         for bom_row in bom.get("items") or []:
#             required_qty = (flt(bom_row.qty) / bom_qty) * wo_qty
#             self.append("required_items", {
#                 "item_code": bom_row.item_code,
#                 "item_name": bom_row.item_name,
#                 "description": bom_row.description,
#                 "operation": bom_row.operation,
#                 "required_qty": required_qty,
#                 "uom": bom_row.uom,
#                 "stock_uom": bom_row.stock_uom,
#                 "conversion_factor": bom_row.conversion_factor or 1,
#                 "source_warehouse": bom_row.source_warehouse or self.source_warehouse,
#                 "allow_alternative_item": bom_row.allow_alternative_item,
#                 "include_item_in_manufacturing": bom_row.include_item_in_manufacturing,
#                 "rate": bom_row.rate,
#                 "amount": flt(bom_row.rate) * required_qty,
#             })

#     # --------------------------------------------------
#     # MANUFACTURED QTY / PROCESS LOSS
#     # --------------------------------------------------
#     def update_work_order_qty(self):
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
    # OPERATION STATUS (CHEMICAL LOGIC)
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
    def set_required_items(self, reset_only_qty=False, **kwargs):
        """
        Chemical mfg override of ERPNext's set_required_items.

        Behaviour:
          - GROUP BY (item_code, operation) — never merges rows across operations
          - Same item + same operation IS combined into one row (per spec)
          - Idempotent: always rebuilt from BOM, never patched from existing rows,
            so N saves produce the same table as 1 save
          - Handles both reset_only_qty=True and False on the same rebuild path,
            because the standard reset_only_qty branch in ERPNext uses
            get_bom_items_as_dict() which merges by item_code only — the exact
            behaviour we must avoid
          - Accepts **kwargs so future ERPNext signatures (e.g. reset_source_warehouse)
            do not raise TypeError

        Why we do NOT delegate to the parent:
          ERPNext's set_required_items calls
              get_bom_items_as_dict(bom_no, company, qty, fetch_exploded)
          which does `GROUP BY item_code, stock_uom` in SQL and then aggregates
          again in Python keyed only on item_code. That is what causes
          "Item ABC in Operation A + Item ABC in Operation B" to collapse into
          a single ABC row after save. We bypass that function entirely and
          build the required_items table directly from bom.items.
        """
        if not self.bom_no or not self.qty:
            # nothing to build against — leave table alone
            return

        bom = frappe.get_doc("BOM", self.bom_no)
        bom_qty = flt(bom.quantity) or 1.0
        wo_qty = flt(self.qty)
        scale = wo_qty / bom_qty

        # 1) Aggregate BOM rows by (item_code, operation)
        #    - preserves ordering so the UI is stable across saves
        #    - sums qty when the same item + same operation appears twice
        grouped = {}
        order = []
        for item in bom.items:
            key = (item.item_code, item.operation or "")
            if key not in grouped:
                order.append(key)
                grouped[key] = {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "description": item.description,
                    "operation": item.operation,
                    "uom": item.uom,
                    "stock_uom": item.stock_uom,
                    "conversion_factor": item.conversion_factor or 1,
                    "source_warehouse": item.source_warehouse or self.source_warehouse,
                    "allow_alternative_item": item.allow_alternative_item,
                    "include_item_in_manufacturing": item.include_item_in_manufacturing,
                    "rate": item.rate,
                    "qty": 0.0,
                }
            grouped[key]["qty"] += flt(item.qty)

        # 2) ALWAYS rebuild from the aggregated dict.
        #    This is what makes save + re-save idempotent, and what stops
        #    ERPNext's reset_only_qty branch from re-merging our rows.
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

        # 3) Preserve ERPNext's default of populating availability columns.
        #    Wrapped in try/except so a bin-lookup failure never blocks Save.
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
