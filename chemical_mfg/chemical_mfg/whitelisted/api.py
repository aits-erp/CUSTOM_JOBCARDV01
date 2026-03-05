import json
import frappe
from erpnext.manufacturing.doctype.work_order.work_order import make_work_order as erp_make_work_order


@frappe.whitelist()
def custom_make_work_order(item=None, bom_no=None, qty=1, variant_items=None, use_multi_level_bom=0, **kwargs):
    """
    Override of:
      erpnext.manufacturing.doctype.work_order.work_order.make_work_order

    ERPNext v15.98.1 signature (from your request):
      make_work_order(bom_no, item, qty=1, variant_items='[]', use_multi_level_bom=0, ...)

    Goal:
      Auto-fill Work Order Operation.custom_quality_template from BOM Operation.custom_quality_template.
    """

    if not bom_no:
        frappe.throw("bom_no is required")
    if not item:
        # fallback derive item from BOM
        item = frappe.db.get_value("BOM", bom_no, "item")
    if not item:
        frappe.throw("item is required")

    # Normalize variant_items (UI sends "[]", sometimes list/None)
    if variant_items is None:
        variant_items = "[]"
    if isinstance(variant_items, (list, dict)):
        variant_items = json.dumps(variant_items)

    # 1) Call ERPNext original method ONLY with supported params
    doc = erp_make_work_order(
        bom_no=bom_no,
        item=item,
        qty=qty,
        variant_items=variant_items,
        use_multi_level_bom=use_multi_level_bom,
    )

    # 2) Build map from BOM operations: operation -> custom_quality_template
    bom = frappe.get_doc("BOM", bom_no)
    bom_map = {
        r.operation: r.custom_quality_template
        for r in (bom.get("operations") or [])
        if r.operation
    }

    # 3) Apply to Work Order operations
    for row in (doc.get("operations") or []):
        if row.operation and row.operation in bom_map:
            row.custom_quality_template = bom_map[row.operation]

    return doc