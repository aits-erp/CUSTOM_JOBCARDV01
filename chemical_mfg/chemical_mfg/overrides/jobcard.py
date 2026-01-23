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
    # 🔥 CRITICAL FIX: ensure _action exists on insert
    # --------------------------------------------------
    def before_insert(self):
        # Frappe expects this during _validate_links
        self._action = "insert"

    # --------------------------------------------------
    # Fix wrong status string
    # --------------------------------------------------
    def validate(self):
        if self.status == "Complete":
            self.status = "Completed"

    # --------------------------------------------------
    # ❌ Disable ALL qty validations (only these)
    # --------------------------------------------------
    def validate_previous_operation_completed_qty(self):
        return

    def validate_completed_qty(self):
        return

    def validate_qty(self):
        return

    # --------------------------------------------------
    # Safe submit (NO db_set here)
    # --------------------------------------------------
    def on_submit(self):
        self.status = "Completed"
        return