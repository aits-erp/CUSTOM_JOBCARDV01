import frappe
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class CustomJobCard(JobCard):

    # ❌ Disable timestamp conflict
    def check_if_latest(self):
        return

    # ❌ Disable all validations
    def validate(self):
        return

    def before_submit(self):
        return

    def on_submit(self):
        return

    def on_update(self):
        return

    # ❌ Kill internal logic
    def validate_job_card(self):
        return

    def validate_sequence_id(self):
        return

    def validate_job_card_qty(self):
        return

    def validate_time_logs(self):
        return

    def validate_process_loss(self):
        return

    def validate_operations(self):
        return

    def set_status(self):
        return

    def update_job_card_status(self):
        return
