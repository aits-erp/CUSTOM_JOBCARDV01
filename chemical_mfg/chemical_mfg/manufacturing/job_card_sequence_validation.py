import frappe

def validate_job_card_sequence(doc, method):

    if doc.status != "Completed":
        return

    if not doc.sequence_id or not doc.work_order:
        return

    previous_cards = frappe.get_all(
        "Job Card",
        filters={
            "work_order": doc.work_order,
            "sequence_id": ["<", doc.sequence_id]
        },
        fields=["name", "sequence_id", "status"],
        order_by="sequence_id asc"
    )

    for jc in previous_cards:
        if jc.status != "Completed":
            frappe.throw(
                f"Job Card <b>{jc.name}</b> with Sequence <b>{jc.sequence_id}</b> must be completed before completing Sequence <b>{doc.sequence_id}</b>"
            )