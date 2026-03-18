import frappe

@frappe.whitelist()
def fix_quality_inspection(docname):

    doc = frappe.get_doc("Quality Inspection", docname)

    overall_status = "Accepted"
    valid_rows_found = False

    for row in doc.readings:

        # RESET status first 🔥
        row.status = ""

        # ---------- NUMERIC ----------
        if row.numeric:

            readings = [
                row.reading_1, row.reading_2, row.reading_3, row.reading_4,
                row.reading_5, row.reading_6, row.reading_7, row.reading_8,
                row.reading_9, row.reading_10
            ]

            readings = [r for r in readings if r not in [None, ""]]

            if not readings:
                continue

            valid_rows_found = True

            readings = [float(r) for r in readings]
            avg = sum(readings) / len(readings)

            min_val = float(row.min_value or 0)
            max_val = float(row.max_value or 0)

            if min_val <= avg <= max_val:
                row.status = "Accepted"
            else:
                row.status = "Rejected"
                overall_status = "Rejected"

        # ---------- MANUAL ----------
        else:
            if not row.value:
                continue

            valid_rows_found = True
            row.status = "Accepted"

    # ---------- FINAL STATUS ----------
    if not valid_rows_found:
        doc.status = "Rejected"
    else:
        doc.status = overall_status

    # 🔥 FORCE SAVE + DB UPDATE
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)

    frappe.db.commit()

    return "QC Updated Successfully"