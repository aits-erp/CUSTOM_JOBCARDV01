import frappe
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class ChemicalJobCard(JobCard):
    """
    Minimal override for chemical manufacturing:
    - Keeps standard ERPNext behavior
    - Removes qty / sequence validations only
    """

    # ❌ Block operation sequence qty validation
    def validate_previous_operation_completed_qty(self):
        pass

    # ❌ Block completed qty == for qty validation
    def validate_completed_qty(self):
        pass

    # ❌ Block sequence-based qty comparison
    def validate_sequence_id(self):
        pass

# import frappe
# from erpnext.manufacturing.doctype.job_card.job_card import JobCard

# class CustomJobCard(JobCard):

#     # 🚫 REMOVE ALL QTY LIMITS
#     def validate_job_card_qty(self):
#         """
#         Disable job card qty vs work order qty validation
#         (UNLIMITED production allowed)
#         """
#         return

#     def validate_sequence_id(self):
#         """
#         Disable previous operation completed qty validation
#         """
#         return
