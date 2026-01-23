import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class CustomJobCard(JobCard):

    # --------------------------------------------------
    # DISABLE STANDARD VALIDATIONS (AS REQUIRED)
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
    def validate(self):
        # keep standard ERPNext validate
        super().validate()

        # always force process loss to zero
        self.process_loss_qty = 0

    # --------------------------------------------------
    # ONLY FIX STATUS (NO EXTRA LOGIC)
    # --------------------------------------------------
    def on_submit(self):
        # keep standard submit flow
        super().on_submit()

        # ❌ DO NOT db_set inside submit (causes refresh error)
        # just update in memory
        self.process_loss_qty = 0

        # update status safely
        self.update_job_card_status()

    # --------------------------------------------------
    # STATUS FIX (MINIMAL & SAFE)
    # --------------------------------------------------
    def update_job_card_status(self):
        completed = flt(self.total_completed_qty or 0)
        planned = flt(self.for_quantity or 0)

        if planned > 0 and completed >= planned:
            # ❌ do not use db_set here
            self.status = "Completed"
