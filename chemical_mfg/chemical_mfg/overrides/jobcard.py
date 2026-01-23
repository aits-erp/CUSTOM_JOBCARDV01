import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class CustomJobCard(JobCard):

    # --------------------------------------------------
    # DISABLE STANDARD VALIDATIONS (AS YOU WANT)
    # --------------------------------------------------
    def validate_job_card(self):
        return

    def validate_sequence_id(self):
        return

    def validate_job_card_qty(self):
        return

    # --------------------------------------------------
    # KEEP STANDARD VALIDATE + KILL PROCESS LOSS
    # --------------------------------------------------
    