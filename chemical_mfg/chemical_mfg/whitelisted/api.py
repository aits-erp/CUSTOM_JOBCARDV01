# # import json
# # import frappe
# # from erpnext.manufacturing.doctype.work_order.work_order import make_work_order as erp_make_work_order


# # @frappe.whitelist()
# # def custom_make_work_order(item=None, bom_no=None, qty=1, variant_items=None, use_multi_level_bom=0, **kwargs):
# #     """
# #     Override of:
# #       erpnext.manufacturing.doctype.work_order.work_order.make_work_order

# #     ERPNext v15.98.1 signature (from your request):
# #       make_work_order(bom_no, item, qty=1, variant_items='[]', use_multi_level_bom=0, ...)

# #     Goal:
# #       Auto-fill Work Order Operation.custom_quality_template from BOM Operation.custom_quality_template.
# #     """

# #     if not bom_no:
# #         frappe.throw("bom_no is required")
# #     if not item:
# #         # fallback derive item from BOM
# #         item = frappe.db.get_value("BOM", bom_no, "item")
# #     if not item:
# #         frappe.throw("item is required")

# #     # Normalize variant_items (UI sends "[]", sometimes list/None)
# #     if variant_items is None:
# #         variant_items = "[]"
# #     if isinstance(variant_items, (list, dict)):
# #         variant_items = json.dumps(variant_items)

# #     # 1) Call ERPNext original method ONLY with supported params
# #     doc = erp_make_work_order(
# #         bom_no=bom_no,
# #         item=item,
# #         qty=qty,
# #         variant_items=variant_items,
# #         use_multi_level_bom=use_multi_level_bom,
# #     )

# #     # 2) Build map from BOM operations: operation -> custom_quality_template
# #     bom = frappe.get_doc("BOM", bom_no)
# #     bom_map = {
# #         r.operation: r.custom_quality_template
# #         for r in (bom.get("operations") or [])
# #         if r.operation
# #     }

# #     # 3) Apply to Work Order operations
# #     for row in (doc.get("operations") or []):
# #         if row.operation and row.operation in bom_map:
# #             row.custom_quality_template = bom_map[row.operation]

# #     return doc

# import json
# import frappe
# from frappe.utils import flt
# from erpnext.manufacturing.doctype.work_order.work_order import make_work_order as erp_make_work_order


# @frappe.whitelist()
# def custom_make_work_order(item=None, bom_no=None, qty=1, variant_items=None, use_multi_level_bom=0, **kwargs):
#     """
#     Override of:
#       erpnext.manufacturing.doctype.work_order.work_order.make_work_order

#     ERPNext v15.98.1 signature:
#       make_work_order(bom_no, item, qty=1, variant_items='[]', use_multi_level_bom=0, ...)

#     Goals:
#       1. Auto-fill Work Order Operation.custom_quality_template from BOM Operation.custom_quality_template.
#       2. Rebuild required_items from BOM rows directly so the SAME item used in
#          two different operations stays as TWO separate rows (v15 merges by item_code).
#     """
#     if not bom_no:
#         frappe.throw("bom_no is required")
#     if not item:
#         item = frappe.db.get_value("BOM", bom_no, "item")
#     if not item:
#         frappe.throw("item is required")

#     # Normalize variant_items (UI sends "[]", sometimes list/None)
#     if variant_items is None:
#         variant_items = "[]"
#     if isinstance(variant_items, (list, dict)):
#         variant_items = json.dumps(variant_items)

#     # 1) Call ERPNext original method
#     doc = erp_make_work_order(
#         bom_no=bom_no,
#         item=item,
#         qty=qty,
#         variant_items=variant_items,
#         use_multi_level_bom=use_multi_level_bom,
#     )

#     # 2) SAFETY NET: rebuild required_items directly from BOM rows,
#     # so items are NOT merged across different operations.
#     try:
#         if doc.get("bom_no") and flt(doc.get("qty")):
#             bom = frappe.get_doc("BOM", doc.bom_no)
#             bom_qty = flt(bom.quantity) or 1.0
#             wo_qty = flt(doc.qty)

#             doc.set("required_items", [])
#             for bom_row in bom.get("items") or []:
#                 required_qty = (flt(bom_row.qty) / bom_qty) * wo_qty
#                 doc.append("required_items", {
#                     "item_code": bom_row.item_code,
#                     "item_name": bom_row.item_name,
#                     "description": bom_row.description,
#                     "operation": bom_row.operation,
#                     "required_qty": required_qty,
#                     "uom": bom_row.uom,
#                     "stock_uom": bom_row.stock_uom,
#                     "conversion_factor": bom_row.conversion_factor or 1,
#                     "source_warehouse": bom_row.source_warehouse or doc.source_warehouse,
#                     "allow_alternative_item": bom_row.allow_alternative_item,
#                     "include_item_in_manufacturing": bom_row.include_item_in_manufacturing,
#                     "rate": bom_row.rate,
#                     "amount": flt(bom_row.rate) * required_qty,
#                 })
#     except Exception:
#         frappe.log_error(
#             title="custom_make_work_order: required_items rebuild failed",
#             message=frappe.get_traceback(),
#         )

#     # 3) Copy custom_quality_template from BOM operations to Work Order operations
#     bom = frappe.get_doc("BOM", bom_no)
#     bom_map = {
#         r.operation: r.custom_quality_template
#         for r in (bom.get("operations") or [])
#         if r.operation
#     }
#     for row in (doc.get("operations") or []):
#         if row.operation and row.operation in bom_map:
#             row.custom_quality_template = bom_map[row.operation]

#     return doc

import json
import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.work_order.work_order import make_work_order as erp_make_work_order


@frappe.whitelist()
def custom_make_work_order(item=None, bom_no=None, qty=1, variant_items=None, use_multi_level_bom=0, **kwargs):
    if not bom_no:
        frappe.throw("bom_no is required")
    if not item:
        item = frappe.db.get_value("BOM", bom_no, "item")
    if not item:
        frappe.throw("item is required")

    if variant_items is None:
        variant_items = "[]"
    if isinstance(variant_items, (list, dict)):
        variant_items = json.dumps(variant_items)

    doc = erp_make_work_order(
        bom_no=bom_no,
        item=item,
        qty=qty,
        variant_items=variant_items,
        use_multi_level_bom=use_multi_level_bom,
    )

    # Safety net for BOM → Create → Work Order path
    try:
        if doc.get("bom_no") and flt(doc.get("qty")):
            bom = frappe.get_doc("BOM", doc.bom_no)
            bom_qty = flt(bom.quantity) or 1.0
            wo_qty = flt(doc.qty)

            doc.set("required_items", [])
            for bom_row in bom.get("items") or []:
                required_qty = (flt(bom_row.qty) / bom_qty) * wo_qty
                doc.append("required_items", {
                    "item_code": bom_row.item_code,
                    "item_name": bom_row.item_name,
                    "description": bom_row.description,
                    "operation": bom_row.operation,
                    "required_qty": required_qty,
                    "uom": bom_row.uom,
                    "stock_uom": bom_row.stock_uom,
                    "conversion_factor": bom_row.conversion_factor or 1,
                    "source_warehouse": bom_row.source_warehouse or doc.source_warehouse,
                    "allow_alternative_item": bom_row.allow_alternative_item,
                    "include_item_in_manufacturing": bom_row.include_item_in_manufacturing,
                    "rate": bom_row.rate,
                    "amount": flt(bom_row.rate) * required_qty,
                })
    except Exception:
        frappe.log_error(
            title="custom_make_work_order: required_items rebuild failed",
            message=frappe.get_traceback(),
        )

    # Copy custom_quality_template from BOM operations to WO operations
    bom = frappe.get_doc("BOM", bom_no)
    bom_map = {
        r.operation: r.custom_quality_template
        for r in (bom.get("operations") or [])
        if r.operation
    }
    for row in (doc.get("operations") or []):
        if row.operation and row.operation in bom_map:
            row.custom_quality_template = bom_map[row.operation]

    return doc
