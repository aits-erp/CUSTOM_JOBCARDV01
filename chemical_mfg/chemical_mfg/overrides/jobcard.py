# from erpnext.manufacturing.doctype.job_card.job_card import JobCard

# class CustomJobCard(JobCard):

#     def validate_job_card(self):
#         """
#         🚫 Disable:
#         Total Completed Qty == For Quantity validation
#         (Chemical / process manufacturing)
#         """
#         return

#     def validate_sequence_id(self):
#         """
#         🚫 Disable previous operation completed qty comparison
#         """
#         return

#     def validate_job_card_qty(self):
#         """
#         🚫 Disable Job Card qty vs Work Order qty limit
#         """
#         return

from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class CustomJobCard(JobCard):

    # ---------------------------------------------
    # KEEP YOUR EXISTING LOGIC
    # ---------------------------------------------
    def validate_job_card(self):
        return

    def validate_sequence_id(self):
        return

    def validate_job_card_qty(self):
        return

    # ---------------------------------------------
    # 🔴 MISSING PART (CRITICAL)
    # ---------------------------------------------
    def validate(self):
        super().validate()

        # 🚫 Kill process loss at source
        self.process_loss_qty = 0

    def on_submit(self):
        super().on_submit()

        # 🔒 Force remove loss AFTER ERPNext logic
        self.db_set("process_loss_qty", 0, update_modified=False)

