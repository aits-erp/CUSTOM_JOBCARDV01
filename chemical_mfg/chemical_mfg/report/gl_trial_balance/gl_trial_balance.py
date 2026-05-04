import frappe
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("company"):
        frappe.throw("Company is required")

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required")

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": "Account Code", "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 200},
        {"label": "Account Name", "fieldname": "account_name", "fieldtype": "Data", "width": 200},
        {"label": "Opening Balance", "fieldname": "opening", "fieldtype": "Currency", "width": 150},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 150},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 150},
        {"label": "Closing Balance", "fieldname": "closing", "fieldtype": "Currency", "width": 150},
    ]


def get_data(filters):
    # Opening Balance (before from_date)
    opening = frappe.db.sql("""
        SELECT
            gle.account,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND gle.posting_date < %(from_date)s
            AND acc.is_group = 0
        GROUP BY gle.account
    """, filters, as_dict=1)

    opening_map = {d.account: flt(d.balance) for d in opening}

    # Period Data
    data = frappe.db.sql("""
        SELECT
            gle.account,
            acc.account_name,
            SUM(gle.debit) AS debit,
            SUM(gle.credit) AS credit
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND acc.is_group = 0
        GROUP BY gle.account, acc.account_name
        ORDER BY gle.account
    """, filters, as_dict=1)

    result = []

    for d in data:
        opening_balance = opening_map.get(d.account, 0)
        closing = opening_balance + (flt(d.debit) - flt(d.credit))

        result.append({
            "account": d.account,
            "account_name": d.account_name,
            "opening": opening_balance,
            "debit": flt(d.debit),
            "credit": flt(d.credit),
            "closing": closing
        })

    return result