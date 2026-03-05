import frappe


@frappe.whitelist()
def apply_quality_template_to_stock_entry(docname):

    if not docname:
        frappe.throw("Stock Entry name is required")

    from chemical_mfg.chemical_mfg.overrides.stock_entry import CustomStockEntry

    se = frappe.get_doc("Stock Entry", docname)

    custom_se = CustomStockEntry(se.doctype, se.name)
    custom_se.apply_quality_template()

    se.save()

    return {"message": "Quality Template applied to Stock Entry"}