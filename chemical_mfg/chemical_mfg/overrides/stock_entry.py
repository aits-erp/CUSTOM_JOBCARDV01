import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


class CustomStockEntry(StockEntry):

    def on_submit(self):
        super().on_submit()

        if (
            self.stock_entry_type == "Material Consumption for Manufacture"
            and self.work_order
            and self.total_qty
        ):
            consumed = frappe.db.get_value(
                "Work Order",
                self.work_order,
                "custom_consumed_qty_total"
            ) or 0

            frappe.db.set_value(
                "Work Order",
                self.work_order,
                "custom_consumed_qty_total",
                consumed + self.total_qty
            )
