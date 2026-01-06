# import frappe
# from erpnext.manufacturing.doctype.job_card.job_card import JobCard


# class ChemicalJobCard(JobCard):
#     """
#     Minimal override for chemical manufacturing:
#     - Keeps standard ERPNext behavior
#     - Removes qty / sequence validations only
#     """

#     # ❌ Block operation sequence qty validation
#     def validate_previous_operation_completed_qty(self):
#         pass

#     # ❌ Block completed qty == for qty validation
#     def validate_completed_qty(self):
#         pass

#     # ❌ Block sequence-based qty comparison
#     def validate_sequence_id(self):
#         pass


from erpnext.manufacturing.doctype.job_card.job_card import JobCard

class CustomJobCard(JobCard):

    def validate_job_card(self):
        """
        🚫 Disable:
        Total Completed Qty == For Quantity validation
        (Chemical / process manufacturing)
        """
        return

    def validate_sequence_id(self):
        """
        🚫 Disable previous operation completed qty comparison
        """
        return

    def validate_job_card_qty(self):
        """
        🚫 Disable Job Card qty vs Work Order qty limit
        """
        return
