import frappe


def validate_job_card_sequence(doc, method=None):
    # Auto-created job cards on Work Order submit should pass through untouched.
    if getattr(doc, "docstatus", 0) != 1 and getattr(doc, "status", None) != "Completed":
        return

    if not getattr(doc, "sequence_id", None) or not getattr(doc, "work_order", None):
        return

    previous_cards = frappe.get_all(
        "Job Card",
        filters={
            "work_order": doc.work_order,
            "sequence_id": ["<", doc.sequence_id],
            "docstatus": ["!=", 2],
        },
        fields=["name", "sequence_id", "status", "docstatus"],
    )

    for jc in previous_cards:
        if jc.docstatus == 2:
            continue

        if jc.status != "Completed":
            frappe.throw(
                f"Job Card {jc.name} with Sequence {jc.sequence_id} "
                f"must be completed before completing Sequence {doc.sequence_id}"
            )

# # import frappe


# # def validate_job_card_sequence(doc, method):

# #     # run only when completing job
# #     if doc.status != "Completed":
# #         return

# #     if not doc.sequence_id or not doc.work_order:
# #         return

# #     previous_cards = frappe.get_all(
# #         "Job Card",
# #         filters={
# #             "work_order": doc.work_order,
# #             "sequence_id": ["<", doc.sequence_id]
# #         },
# #         fields=["name", "sequence_id", "status"]
# #     )

# #     for jc in previous_cards:
# #         if jc.status != "Completed":
# #             frappe.throw(
# #                 f"Job Card {jc.name} with Sequence {jc.sequence_id} must be completed before completing Sequence {doc.sequence_id}"
# #             )

# import frappe


# def validate_job_card_sequence(doc, method):

#     # Run only when completing Job Card
#     if doc.status != "Completed":
#         return

#     if not doc.sequence_id or not doc.work_order:
#         return

#     previous_cards = frappe.get_all(
#         "Job Card",
#         filters={
#             "work_order": doc.work_order,
#             "sequence_id": ["<", doc.sequence_id],
#             "docstatus": ["!=", 2]   # Ignore Cancelled Job Cards
#         },
#         fields=["name", "sequence_id", "status", "docstatus"]
#     )

#     for jc in previous_cards:

#         # Skip cancelled records
#         if jc.docstatus == 2:
#             continue

#         if jc.status != "Completed":
#             frappe.throw(
#                 f"Job Card {jc.name} with Sequence {jc.sequence_id} "
#                 f"must be completed before completing Sequence {doc.sequence_id}"
#             )