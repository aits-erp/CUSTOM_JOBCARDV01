import frappe

def apply_quality_template_from_bom(doc, method=None, *args, **kwargs):
    """before_save hook: copy custom_quality_template from BOM operations to Work Order operations"""
    if not getattr(doc, "bom_no", None):
        return

    if not getattr(doc, "operations", None):
        return

    bom = frappe.get_doc("BOM", doc.bom_no)
    if not getattr(bom, "operations", None):
        return

    # map BOM ops by operation name
    bom_map = {op.operation: op for op in bom.operations if op.operation}

    for wo_op in doc.operations:
        bom_op = bom_map.get(wo_op.operation)
        if bom_op:
            wo_op.custom_quality_template = bom_op.custom_quality_template