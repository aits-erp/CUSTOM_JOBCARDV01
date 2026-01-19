# import frappe
# from frappe.utils import flt
# from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder


# class CustomWorkOrder(WorkOrder):

#     # --------------------------------------------------
#     # DISABLE STANDARD VALIDATIONS
#     # --------------------------------------------------
#     def validate_completed_qty(self):
#         pass

#     def validate_qty_to_produce_against_completed_qty(self):
#         pass

#     def validate_qty_to_produce(self):
#         pass

#     # --------------------------------------------------
#     # OPERATION STATUS (your logic – kept)
#     # --------------------------------------------------
#     def update_operation_status(self):
#         """
#         Chemical / process manufacturing:
#         - No qty equality enforcement
#         - Status only depends on whether something is completed
#         """
#         for d in self.get("operations"):
#             if flt(d.completed_qty) > 0:
#                 d.status = "Completed"
#             else:
#                 d.status = "Pending"

#     # --------------------------------------------------
#     # 🔴 MOST IMPORTANT OVERRIDE
#     # --------------------------------------------------
#     def update_work_order_qty(self):
#         """
#         CORE FIX:
#         - Kill process loss completely
#         - Manufactured Qty = max completed qty of operations
#         """

#         # Call ERPNext logic first (keeps stock/accounting safe)
#         super().update_work_order_qty()

#         # 🚫 Disable process loss forever
#         self.process_loss_qty = 0

#         # ✅ Manufactured Qty = actual production
#         if self.operations:
#             self.manufactured_qty = max(
#                 flt(d.completed_qty) for d in self.operations
#             )
#         else:
#             self.manufactured_qty = flt(self.qty_completed)

import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder


class CustomWorkOrder(WorkOrder):

    # --------------------------------------------------
    # DISABLE STANDARD VALIDATIONS
    # --------------------------------------------------
    def validate_completed_qty(self):
        pass

    def validate_qty_to_produce_against_completed_qty(self):
        pass

    def validate_qty_to_produce(self):
        pass

    # --------------------------------------------------
    # OPERATION STATUS
    # --------------------------------------------------
    def update_operation_status(self):
        """
        Chemical / process manufacturing:
        Status depends only on completed qty
        """
        for d in self.get("operations") or []:
            if flt(d.completed_qty) > 0:
                d.status = "Completed"
            else:
                d.status = "Pending"

    # --------------------------------------------------
    # REQUIRED ITEMS (ERPNext v15 SAFE)
    # --------------------------------------------------
    def set_required_items(self, reset_only_qty=False):
        """
        ERPNext v15 SAFE override

        - Same item in different operations is NOT merged
        - When reset_only_qty=True, rows are preserved
        """

        # Called by ERPNext many times – be defensive
        if reset_only_qty:
            for d in self.get("required_items") or []:
                d.required_qty = flt(d.required_qty)
            return

        # Full rebuild only when BOM is set
        self.set("required_items", [])

        if not self.bom_no:
            return

        try:
            bom = frappe.get_doc("BOM", self.bom_no)
        except frappe.DoesNotExistError:
            return

        for bom_item in bom.items or []:
            self.append("required_items", {
                "item_code": bom_item.item_code,
                "description": bom_item.description,
                "required_qty": flt(bom_item.qty) * flt(self.qty),
                "uom": bom_item.uom,
                "stock_uom": bom_item.stock_uom,
                "conversion_factor": bom_item.conversion_factor or 1,
                "source_warehouse": (
                    bom_item.source_warehouse
                    or self.source_warehouse
                ),
                "operation": bom_item.operation,
                "allow_alternative_item": 0,
                "include_item_in_manufacturing": 1,
            })

    # --------------------------------------------------
    # MANUFACTURED QTY / PROCESS LOSS
    # --------------------------------------------------
    def update_work_order_qty(self):
        """
        - Disable process loss
        - Manufactured qty = max completed qty
        """

        # Let ERPNext do its internal calculations first
        super().update_work_order_qty()

        # Kill process loss
        self.process_loss_qty = 0

        if self.operations:
            self.manufactured_qty = max(
                flt(d.completed_qty) for d in self.operations
            )
        else:
            self.manufactured_qty = flt(self.qty_completed)
