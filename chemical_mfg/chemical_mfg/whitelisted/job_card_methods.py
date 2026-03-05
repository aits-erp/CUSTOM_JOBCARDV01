import frappe

def apply_quality_template_from_work_order(doc, method=None):
    """
    Fetch custom_quality_template from Work Order Operation
    and set it in Job Card field quality_inspection_template
    """

    if not doc.work_order:
        return

    if not doc.operation:
        return

    wo = frappe.get_doc("Work Order", doc.work_order)

    for op in wo.operations:
        if op.operation == doc.operation:
            doc.quality_inspection_template = op.custom_quality_template
            break