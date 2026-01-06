import frappe
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder

class CustomWorkOrder(WorkOrder):

    def validate_production_qty(self):
        """
        Disable produced_qty <= planned_qty validation
        Allows UNLIMITED overproduction
        """
        return
