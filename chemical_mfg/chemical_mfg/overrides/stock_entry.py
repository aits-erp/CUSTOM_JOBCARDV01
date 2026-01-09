import frappe


def update_consumed_qty(doc, method):
    if doc.stock_entry_type != "Material Consumption for Manufacture":
        return

    if not doc.work_order or not doc.total_qty:
        return

    consumed = frappe.db.get_value(
        "Work Order",
        doc.work_order,
        "custom_consumed_qty_total"
    ) or 0

    frappe.db.set_value(
        "Work Order",
        doc.work_order,
        "custom_consumed_qty_total",
        consumed + doc.total_qty
    )


def rollback_consumed_qty(doc, method):
    if doc.stock_entry_type != "Material Consumption for Manufacture":
        return

    if not doc.work_order or not doc.total_qty:
        return

    consumed = frappe.db.get_value(
        "Work Order",
        doc.work_order,
        "custom_consumed_qty_total"
    ) or 0

    frappe.db.set_value(
        "Work Order",
        doc.work_order,
        "custom_consumed_qty_total",
        max(consumed - doc.total_qty, 0)
    )
