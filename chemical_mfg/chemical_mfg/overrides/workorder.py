import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder

class CustomWorkOrder(WorkOrder):

    def validate_completed_qty(self):
        return

    def validate_qty_to_produce_against_completed_qty(self):
        return

    def validate_qty_to_produce(self):
        return

    def update_operation_status(self):
        """
        Chemical / process manufacturing:
        - No qty equality enforcement
        - Status only depends on whether something is completed
        """
        for d in self.get("operations"):
            if flt(d.completed_qty) > 0 or flt(d.process_loss_qty) > 0:
                d.status = "Completed"
            else:
                d.status = "Pending"
