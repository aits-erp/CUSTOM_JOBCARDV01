import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from chemical_mfg.chemical_mfg.whitelisted.yield_methods import update_work_order_yield


def execute():
    create_custom_fields(
        {
            "Work Order": [
                {
                    "fieldname": "custom_gross_yield",
                    "label": "Custom Gross Yield",
                    "fieldtype": "Percent",
                    "insert_after": "produced_qty",
                    "read_only": 1,
                    "no_copy": 1,
                    "allow_on_submit": 1,
                },
                {
                    "fieldname": "custom_net_yield",
                    "label": "Custom Net Yield",
                    "fieldtype": "Percent",
                    "insert_after": "custom_gross_yield",
                    "read_only": 1,
                    "no_copy": 1,
                    "allow_on_submit": 1,
                },
            ]
        }
    )

    # backfill existing Work Orders
    for name in frappe.get_all("Work Order", filters={"docstatus": 1}, pluck="name"):
        update_work_order_yield(name)
