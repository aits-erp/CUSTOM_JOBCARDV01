import frappe


def validate_job_card_sequence(doc, method):

    # run only when completing job
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
        fields=["name", "sequence_id", "status"]
    )

    for jc in previous_cards:
        if jc.status != "Completed":
            frappe.throw(
                f"Job Card {jc.name} with Sequence {jc.sequence_id} must be completed before completing Sequence {doc.sequence_id}"
            )