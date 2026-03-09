import frappe
from frappe.utils import flt


def update_job_card_quantities(doc):

    if not doc.work_order:
        return

    # ----------------------------------
    # RM TOTAL QTY (current job card)
    # ----------------------------------
    rm_total = frappe.db.sql("""
        SELECT SUM(sed.qty)
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed
        ON sed.parent = se.name
        WHERE se.job_card = %s
        AND se.docstatus = 1
        AND IFNULL(sed.is_finished_item,0) = 0
    """, doc.name)

    doc.custom_rm_total_quantity = flt(rm_total[0][0]) if rm_total else 0

    # ----------------------------------
    # PREVIOUS COMPLETED QTY
    # ----------------------------------
    prev_job_card = frappe.db.sql("""
        SELECT name
        FROM `tabJob Card`
        WHERE work_order = %s
        AND sequence_id < %s
        AND status = 'Completed'
        ORDER BY sequence_id DESC
        LIMIT 1
    """, (doc.work_order, doc.sequence_id), as_dict=1)

    prev_qty = 0

    if prev_job_card:
        prev_qty_data = frappe.db.sql("""
            SELECT SUM(sed.qty)
            FROM `tabStock Entry` se
            JOIN `tabStock Entry Detail` sed
            ON sed.parent = se.name
            WHERE se.job_card = %s
            AND se.docstatus = 1
            AND IFNULL(sed.is_finished_item,0) = 0
        """, prev_job_card[0].name)

        prev_qty = flt(prev_qty_data[0][0]) if prev_qty_data else 0

    doc.custom_previous_completed_qty = prev_qty

    # ----------------------------------
    # TOTAL STAGE COMPLETED QTY
    # ----------------------------------
    doc.custom_total_stage_completed_quantity = (
        flt(doc.custom_previous_completed_qty)
        + flt(doc.custom_rm_total_quantity)
    )