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
    # REQUIRED ITEMS (DO NOT MERGE BY ITEM CODE)
    # --------------------------------------------------
    def set_required_items(self, reset_only_qty=False):
        """
        - Same item allowed in multiple operations
        - Qty scales correctly with Planned Qty
        - Safe for ERPNext v15
        """

        if reset_only_qty:
            return

        self.set("required_items", [])

        if not self.bom_no or not self.qty:
            return

        bom = frappe.get_doc("BOM", self.bom_no)
        bom_qty = flt(bom.quantity) or 1

        for item in bom.items:
            self.append("required_items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "operation": item.operation,
                "required_qty": (flt(item.qty) / bom_qty) * flt(self.qty),
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor or 1,
                "source_warehouse": item.source_warehouse or self.source_warehouse,
                "allow_alternative_item": item.allow_alternative_item,
                "include_item_in_manufacturing": 1,
                "rate": item.rate,
                "amount": flt(item.rate) * ((flt(item.qty) / bom_qty) * flt(self.qty)),
            })

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
