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
    # DISABLE STANDARD VALIDATIONS (your existing logic)
    # --------------------------------------------------
    def validate_completed_qty(self):
        pass

    def validate_qty_to_produce_against_completed_qty(self):
        pass

    def validate_qty_to_produce(self):
        pass

    # --------------------------------------------------
    # OPERATION STATUS (your existing logic)
    # --------------------------------------------------
    def update_operation_status(self):
        """
        Chemical / process manufacturing:
        - No qty equality enforcement
        - Status only depends on whether something is completed
        """
        for d in self.get("operations"):
            if flt(d.completed_qty) > 0:
                d.status = "Completed"
            else:
                d.status = "Pending"

    # --------------------------------------------------
    # 🔴 REQUIRED ITEMS (THIS FIXES R1106 MERGING)
    # --------------------------------------------------
    def set_required_items(self):
        """
        CORE FIX:
        - Do NOT merge same item across operations
        - One BOM row = one Required Item row
        """

        self.set("required_items", [])

        if not self.bom_no:
            return

        bom = frappe.get_doc("BOM", self.bom_no)

        for bom_item in bom.items:
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
    # MANUFACTURED QTY / PROCESS LOSS (your existing logic)
    # --------------------------------------------------
    def update_work_order_qty(self):
        """
        CORE FIX:
        - Kill process loss completely
        - Manufactured Qty = max completed qty of operations
        """

        # Call ERPNext logic first (keeps stock/accounting safe)
        super().update_work_order_qty()

        # 🚫 Disable process loss forever
        self.process_loss_qty = 0

        # ✅ Manufactured Qty = actual production
        if self.operations:
            self.manufactured_qty = max(
                flt(d.completed_qty) for d in self.operations
            )
        else:
            self.manufactured_qty = flt(self.qty_completed)
