import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard

# class CustomJobCard(JobCard):

#     def validate(self):
#         # Fix wrong status string safely
#         if self.status == "Complete":
#             self.status = "Completed"

#     # ❌ Disable ALL quantity validations
#     def validate_previous_operation_completed_qty(self):
#         return

#     def validate_completed_qty(self):
#         return

#     def validate_qty(self):
#         return

#     # ❌ Disable submit-time qty enforcement
#     def on_submit(self):
#         """
#         Skip:
#         - total_completed_qty == for_quantity
#         - previous operation qty checks
#         """

#         # ✅ ONLY set value in memory
#         self.status = "Completed"

#         # ❌ DO NOT call db_set here
#         return


class CustomJobCard(JobCard):

    # --------------------------------------------------
    # 🔥 STOP "Document modified" error
    # --------------------------------------------------
    def check_if_latest(self):
        # Disable optimistic locking for Job Card
        return

    # --------------------------------------------------
    # Fix wrong status value
    # --------------------------------------------------
    def validate(self):
        if self.status == "Complete":
            self.status = "Completed"

    # --------------------------------------------------
    # Disable qty validations
    # --------------------------------------------------
    def validate_previous_operation_completed_qty(self):
        return

    def validate_completed_qty(self):
        return

    def validate_qty(self):
        return

    # --------------------------------------------------
    # Safe submit
    # --------------------------------------------------
    def on_submit(self):
        self.status = "Completed"
        return