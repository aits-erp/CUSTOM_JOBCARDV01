import frappe

from chemical_mfg.chemical_mfg.report.yield_summary.yield_summary import execute


def update_work_order_yield(work_order):
    """Store the Yield Summary report's gross / net yield on the Work Order."""
    if not work_order or not frappe.db.exists("Work Order", work_order):
        return

    _, data = execute({"work_order": work_order})

    if not data:
        return

    summary = data[0]

    frappe.db.set_value(
        "Work Order",
        work_order,
        {
            "custom_gross_yield": summary.get("gross_yield") or 0,
            "custom_net_yield": summary.get("net_yield") or 0,
        },
        update_modified=False,
    )


def update_yield_from_doc(doc, method=None):
    """doc_events hook for Stock Entry and Job Card."""
    work_order = doc.get("work_order")

    if not work_order:
        return

    try:
        update_work_order_yield(work_order)
    except Exception:
        # never block a stock entry / job card because of the yield figure
        frappe.log_error(
            title=f"Yield update failed for {work_order}",
            message=frappe.get_traceback(),
        )
