# # import frappe
# # from frappe.utils import flt
# # from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder


# # class CustomWorkOrder(WorkOrder):

# #     # --------------------------------------------------
# #     # DISABLE STANDARD VALIDATIONS
# #     # --------------------------------------------------
# #     def validate_completed_qty(self):
# #         pass

# #     def validate_qty_to_produce_against_completed_qty(self):
# #         pass

# #     def validate_qty_to_produce(self):
# #         pass

# #     # --------------------------------------------------
# #     # OPERATION STATUS (your logic – kept)
# #     # --------------------------------------------------
# #     def update_operation_status(self):
# #         """
# #         Chemical / process manufacturing:
# #         - No qty equality enforcement
# #         - Status only depends on whether something is completed
# #         """
# #         for d in self.get("operations"):
# #             if flt(d.completed_qty) > 0:
# #                 d.status = "Completed"
# #             else:
# #                 d.status = "Pending"

# #     # --------------------------------------------------
# #     # 🔴 MOST IMPORTANT OVERRIDE
# #     # --------------------------------------------------
# #     def update_work_order_qty(self):
# #         """
# #         CORE FIX:
# #         - Kill process loss completely
# #         - Manufactured Qty = max completed qty of operations
# #         """

# #         # Call ERPNext logic first (keeps stock/accounting safe)
# #         super().update_work_order_qty()

# #         # 🚫 Disable process loss forever
# #         self.process_loss_qty = 0

# #         # ✅ Manufactured Qty = actual production
# #         if self.operations:
# #             self.manufactured_qty = max(
# #                 flt(d.completed_qty) for d in self.operations
# #             )
# #         else:
# #             self.manufactured_qty = flt(self.qty_completed)

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
#     # REQUIRED ITEMS (DO NOT MERGE BY ITEM CODE)
#     # --------------------------------------------------
#     def set_required_items(self, reset_only_qty=False):
#         """
#         - Same item allowed in multiple operations
#         - Qty scales correctly with Planned Qty
#         - Safe for ERPNext v15
#         """

#         if reset_only_qty:
#             return

#         self.set("required_items", [])

#         if not self.bom_no or not self.qty:
#             return

#         bom = frappe.get_doc("BOM", self.bom_no)
#         bom_qty = flt(bom.quantity) or 1

#         for item in bom.items:
#             self.append("required_items", {
#                 "item_code": item.item_code,
#                 "item_name": item.item_name,
#                 "description": item.description,
#                 "operation": item.operation,
#                 "required_qty": (flt(item.qty) / bom_qty) * flt(self.qty),
#                 "uom": item.uom,
#                 "stock_uom": item.stock_uom,
#                 "conversion_factor": item.conversion_factor or 1,
#                 "source_warehouse": item.source_warehouse or self.source_warehouse,
#                 "allow_alternative_item": item.allow_alternative_item,
#                 "include_item_in_manufacturing": 1,
#                 "rate": item.rate,
#                 "amount": flt(item.rate) * ((flt(item.qty) / bom_qty) * flt(self.qty)),
#             })

#     # --------------------------------------------------
#     # MANUFACTURED QTY / PROCESS LOSS
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
    # OPERATION STATUS (CHEMICAL LOGIC)
    # --------------------------------------------------
    def update_operation_status(self):
        for d in self.get("operations") or []:
            if flt(d.completed_qty) > 0:
                d.status = "Completed"
            else:
                d.status = "Pending"

    # --------------------------------------------------
    # KEEP SAME ITEM AS SEPARATE ROWS PER OPERATION
    # --------------------------------------------------
    # Standard ERPNext v15 merges BOM items by item_code alone in
    # get_items_and_operations_from_bom(), so an item used in two
    # different operations becomes a single required_items row and
    # only one operation survives. Here we rebuild required_items
    # directly from bom.items so every BOM row produces its own
    # Work Order row.
    # --------------------------------------------------
    def set_required_items(self, reset_only_qty=False, reset_source_warehouse=False, *args, **kwargs):
        """
        - Never merge same item across different operations
        - reset_only_qty=True  -> keep rows, only rescale qty
        - reset_only_qty=False -> full rebuild (one row per BOM row)
        - *args/**kwargs future-proofs against extra ERPNext parameters
        """
        if not self.bom_no or not flt(self.qty):
            if not reset_only_qty:
                self.set("required_items", [])
            return

        bom = frappe.get_doc("BOM", self.bom_no)
        bom_qty = flt(bom.quantity) or 1.0
        wo_qty = flt(self.qty)

        # ------- Fast path: only rescale existing rows -------
        if reset_only_qty and self.get("required_items"):
            bom_by_key = {}
            for b in bom.get("items") or []:
                key = (b.item_code, b.operation or "")
                bom_by_key.setdefault(key, []).append(b)

            used = {}
            for row in self.get("required_items"):
                key = (row.item_code, row.operation or "")
                candidates = bom_by_key.get(key) or []
                idx = used.get(key, 0)
                bom_row = candidates[idx] if idx < len(candidates) else (candidates[0] if candidates else None)
                used[key] = idx + 1

                if not bom_row:
                    continue

                new_qty = (flt(bom_row.qty) / bom_qty) * wo_qty
                row.required_qty = new_qty
                row.rate = bom_row.rate
                row.amount = flt(bom_row.rate) * new_qty
                if reset_source_warehouse:
                    row.source_warehouse = bom_row.source_warehouse or self.source_warehouse
            return

        # ------- Full rebuild: one WO row per BOM row -------
        self.set("required_items", [])
        for bom_row in bom.get("items") or []:
            required_qty = (flt(bom_row.qty) / bom_qty) * wo_qty
            self.append("required_items", {
                "item_code": bom_row.item_code,
                "item_name": bom_row.item_name,
                "description": bom_row.description,
                "operation": bom_row.operation,
                "required_qty": required_qty,
                "uom": bom_row.uom,
                "stock_uom": bom_row.stock_uom,
                "conversion_factor": bom_row.conversion_factor or 1,
                "source_warehouse": bom_row.source_warehouse or self.source_warehouse,
                "allow_alternative_item": bom_row.allow_alternative_item,
                "include_item_in_manufacturing": bom_row.include_item_in_manufacturing,
                "rate": bom_row.rate,
                "amount": flt(bom_row.rate) * required_qty,
            })

    # --------------------------------------------------
    # OVERRIDE THE OTHER ENTRY POINT TOO
    # --------------------------------------------------
    # v15's mapper / RequiredItemsService may call this directly
    # when the Work Order is being created from BOM. Delegate to
    # our set_required_items so merging never happens here either.
    # --------------------------------------------------
    @frappe.whitelist()
    def get_items_and_operations_from_bom(self):
        self.set_required_items(reset_only_qty=False)
        result = {}
        for row in self.get("required_items") or []:
            key = (row.item_code, row.operation or "")
            result[key] = frappe._dict({
                "item_code": row.item_code,
                "item_name": row.item_name,
                "description": row.description,
                "operation": row.operation,
                "qty": row.required_qty,
                "uom": row.uom,
                "stock_uom": row.stock_uom,
                "conversion_factor": row.conversion_factor,
                "source_warehouse": row.source_warehouse,
                "allow_alternative_item": row.allow_alternative_item,
                "include_item_in_manufacturing": row.include_item_in_manufacturing,
                "rate": row.rate,
                "amount": row.amount,
                "idx": row.idx,
            })
        return result

    # --------------------------------------------------
    # MANUFACTURED QTY / PROCESS LOSS
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
