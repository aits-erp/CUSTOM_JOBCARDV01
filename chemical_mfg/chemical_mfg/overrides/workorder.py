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
    # OPERATION STATUS (your logic – kept)
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
    # 🔴 MOST IMPORTANT OVERRIDE
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
