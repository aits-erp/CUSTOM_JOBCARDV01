import frappe

def execute(filters=None):
    if not filters or not filters.get("work_order"):
        return get_columns(), []

    work_order = filters.get("work_order")

    planned = {}
    actual = {}

    # ----------------------------
    # Planned Qty (Work Order Item)
    # ----------------------------
    wo_items = frappe.get_all(
        "Work Order Item",
        filters={"parent": work_order},
        fields=["item_code", "required_qty"]
    )

    for row in wo_items:
        planned[row.item_code] = row.required_qty

    # ----------------------------
    # Actual Qty (Stock Entry)
    # ----------------------------
    stock_entries = frappe.get_all(
        "Stock Entry",
        filters={
            "work_order": work_order,
            "docstatus": 1
        },
        pluck="name"
    )

    for se in stock_entries:
        se_items = frappe.get_all(
            "Stock Entry Detail",
            filters={"parent": se},
            fields=["item_code", "qty"]
        )
        for row in se_items:
            actual[row.item_code] = actual.get(row.item_code, 0) + row.qty

    # ----------------------------
    # Merge & Compare
    # ----------------------------
    data = []
    all_items = set(planned.keys()) | set(actual.keys())

    for item in sorted(all_items):
        planned_qty = planned.get(item, 0)
        consumed_qty = actual.get(item, 0)
        difference = consumed_qty - planned_qty

        new_item = "Yes" if planned_qty == 0 and consumed_qty > 0 else "No"

        data.append([
            item,
            planned_qty,
            consumed_qty,
            difference,
            new_item
        ])

    return get_columns(), data


def get_columns():
    return [
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 220
        },
        {
            "label": "Planned Qty",
            "fieldname": "planned_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": "Consumed Qty",
            "fieldname": "consumed_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": "Difference",
            "fieldname": "difference",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": "New Item?",
            "fieldname": "new_item",
            "fieldtype": "Data",
            "width": 100
        }
    ]
