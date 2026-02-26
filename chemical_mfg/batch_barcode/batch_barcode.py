import frappe
import barcode
from barcode.writer import ImageWriter

def generate_batch_barcode(doc, method):

    if doc.custom_batch_barcode:
        return

    barcode_value = f"{doc.item}|{doc.name}|{doc.expiry_date or ''}"

    code128 = barcode.get('code128', barcode_value, writer=ImageWriter())

    file_name = doc.name.replace("/", "-")

    file_path = frappe.get_site_path("public", "files", file_name)

    filename = code128.save(file_path)

    with open(filename, "rb") as f:
        content = f.read()

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name + ".png",
        "content": content,
        "is_private": 0
    })

    file_doc.save(ignore_permissions=True)

    frappe.db.set_value("Batch", doc.name, "custom_batch_barcode", file_doc.file_url)
    frappe.db.set_value("Batch", doc.name, "custom_barcode_text", barcode_value)
