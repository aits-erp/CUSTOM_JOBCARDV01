# import frappe
# from frappe.utils import flt


# def execute(filters=None):
#     if not filters or not filters.get("work_order"):
#         return get_columns(), []

#     work_order = filters.get("work_order")
#     data = []

#     grand_planned_map = {}
#     grand_consumed_map = {}

#     # ---------------------------------
#     # Planned grouped by operation
#     # ---------------------------------
#     planned_by_op = {}

#     wo_items = frappe.get_all(
#         "Work Order Item",
#         filters={"parent": work_order},
#         fields=["item_code", "required_qty", "operation"]
#     )

#     for row in wo_items:
#         op = row.operation or "No Operation"

#         planned_by_op.setdefault(op, {})
#         planned_by_op[op][row.item_code] = (
#             planned_by_op[op].get(row.item_code, 0) + flt(row.required_qty)
#         )

#         grand_planned_map[row.item_code] = (
#             grand_planned_map.get(row.item_code, 0) + flt(row.required_qty)
#         )

#     # ---------------------------------
#     # Job Cards
#     # ---------------------------------
#     job_cards = frappe.get_all(
#         "Job Card",
#         filters={"work_order": work_order},
#         fields=["name", "operation", "sequence_id"],
#         order_by="sequence_id asc"
#     )

#     # ---------------------------------
#     # Operation loop
#     # ---------------------------------
#     for jc in job_cards:

#         op_name = jc.operation

#         # ✅ Operation header row (blank numbers)
#         data.append({
#             "operation": op_name,
#             "planned_qty": None,
#             "consumed_qty": None,
#             "difference": None,
#             "new_item": None
#         })

#         planned = planned_by_op.get(op_name, {})
#         actual = {}

#         se_items = frappe.db.sql("""
#             SELECT sed.item_code,
#                    SUM(sed.qty) AS qty
#             FROM `tabStock Entry` se
#             JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
#             WHERE se.job_card = %s
#             AND se.docstatus = 1
#             AND se.stock_entry_type IN (
#                 'Material Transfer for Manufacture',
#                 'Material Consumption for Manufacture'
#             )
#             AND IFNULL(sed.is_finished_item,0) = 0
#             GROUP BY sed.item_code
#         """, jc.name, as_dict=1)

#         for row in se_items:
#             actual[row.item_code] = flt(row.qty)

#             grand_consumed_map[row.item_code] = (
#                 grand_consumed_map.get(row.item_code, 0) + flt(row.qty)
#             )

#         all_items = set(planned.keys()) | set(actual.keys())

#         for item in sorted(all_items):
#             p = flt(planned.get(item))
#             c = flt(actual.get(item))
#             d = c - p

#             data.append({
#                 "operation": "",
#                 "item_code": item,
#                 "planned_qty": p,
#                 "consumed_qty": c,
#                 "difference": d,
#                 "new_item": "Yes" if p == 0 and c > 0 else "No"
#             })

#     # ---------------------------------
#     # TOTAL
#     # ---------------------------------
#     total_planned = sum(grand_planned_map.values())
#     total_consumed = sum(grand_consumed_map.values())

#     data.append({
#         "operation": "TOTAL",
#         "planned_qty": total_planned,
#         "consumed_qty": total_consumed,
#         "difference": total_consumed - total_planned,
#         "new_item": None,
#         "is_total_row": 1
#     })

#     return get_columns(), data


# def get_columns():
#     return [
#         {"label": "Operation", "fieldname": "operation", "width": 200},
#         {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
#         {"label": "Planned Qty", "fieldname": "planned_qty", "fieldtype": "Float", "width": 120},
#         {"label": "Consumed Qty", "fieldname": "consumed_qty", "fieldtype": "Float", "width": 120},
#         {"label": "Difference", "fieldname": "difference", "fieldtype": "Float", "width": 120},
#         {"label": "New Item?", "fieldname": "new_item", "width": 100},
#     ]

import frappe
from frappe.utils import flt


def execute(filters=None):
    if not filters or not filters.get("work_order"):
        return get_columns(), []

    work_order = filters.get("work_order")
    data = []

    grand_planned_map = {}
    grand_consumed_map = {}

    # ---------------------------------
    # Planned grouped by operation
    # ---------------------------------
    planned_by_op = {}

    wo_items = frappe.get_all(
        "Work Order Item",
        filters={"parent": work_order},
        fields=["item_code", "required_qty", "operation"]
    )

    for row in wo_items:
        op = row.operation or "No Operation"

        planned_by_op.setdefault(op, {})
        planned_by_op[op][row.item_code] = (
            planned_by_op[op].get(row.item_code, 0) + flt(row.required_qty)
        )

        grand_planned_map[row.item_code] = (
            grand_planned_map.get(row.item_code, 0) + flt(row.required_qty)
        )

    # ---------------------------------
    # Job Cards
    # ---------------------------------
    job_cards = frappe.get_all(
        "Job Card",
        filters={"work_order": work_order},
        fields=["name", "operation", "sequence_id"],
        order_by="sequence_id asc"
    )

    # ---------------------------------
    # Operation loop
    # ---------------------------------
    for jc in job_cards:

        op_name = jc.operation

        op_total_planned = 0
        op_total_consumed = 0

        # Operation header
        data.append({
            "operation": op_name,
            "planned_qty": None,
            "consumed_qty": None,
            "difference": None,
            "new_item": None
        })

        planned = planned_by_op.get(op_name, {})
        actual = {}

        se_items = frappe.db.sql("""
            SELECT sed.item_code,
                   SUM(sed.qty) AS qty
            FROM `tabStock Entry` se
            JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
            WHERE se.job_card = %s
            AND se.docstatus = 1
            AND se.stock_entry_type IN (
                'Material Transfer for Manufacture',
                'Material Consumption for Manufacture'
            )
            AND IFNULL(sed.is_finished_item,0) = 0
            GROUP BY sed.item_code
        """, jc.name, as_dict=1)

        for row in se_items:
            actual[row.item_code] = flt(row.qty)
            grand_consumed_map[row.item_code] = (
                grand_consumed_map.get(row.item_code, 0) + flt(row.qty)
            )

        all_items = set(planned.keys()) | set(actual.keys())

        for item in sorted(all_items):
            p = flt(planned.get(item))
            c = flt(actual.get(item))
            d = c - p

            op_total_planned += p
            op_total_consumed += c

            data.append({
                "operation": "",
                "item_code": item,
                "planned_qty": p,
                "consumed_qty": c,
                "difference": d,
                "new_item": "Yes" if p == 0 and c > 0 else "No"
            })

        # ✅ Operation subtotal row
        data.append({
            "operation": f"{op_name} TOTAL",
            "planned_qty": op_total_planned,
            "consumed_qty": op_total_consumed,
            "difference": op_total_consumed - op_total_planned,
            "new_item": None,
            "is_total_row": 1
        })

    # ---------------------------------
    # GRAND TOTAL
    # ---------------------------------
    total_planned = sum(grand_planned_map.values())
    total_consumed = sum(grand_consumed_map.values())

    data.append({
        "operation": "GRAND TOTAL",
        "planned_qty": total_planned,
        "consumed_qty": total_consumed,
        "difference": total_consumed - total_planned,
        "new_item": None,
        "is_total_row": 1
    })

    return get_columns(), data


def get_columns():
    return [
        {"label": "Operation", "fieldname": "operation", "width": 200},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": "Planned Qty", "fieldname": "planned_qty", "fieldtype": "Float", "width": 120},
        {"label": "Consumed Qty", "fieldname": "consumed_qty", "fieldtype": "Float", "width": 120},
        {"label": "Difference", "fieldname": "difference", "fieldtype": "Float", "width": 120},
        {"label": "New Item?", "fieldname": "new_item", "width": 100},
    ]
