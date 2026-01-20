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
    def validate(self):
        super().validate()
        self.process_loss_qty = 0

    # --------------------------------------------------
    # ONLY FIX STATUS (NO OTHER LOGIC)
    # --------------------------------------------------
    def on_submit(self):
        super().on_submit()

        # Always keep process loss zero
        self.db_set("process_loss_qty", 0, update_modified=False)

        # ✅ FIX: Force status update
        self.update_job_card_status()

    # --------------------------------------------------
    # STATUS FIX (MINIMAL)
    # --------------------------------------------------
    def update_job_card_status(self):
        completed = flt(self.total_completed_qty or 0)
        planned = flt(self.for_quantity or 0)

        if planned > 0 and completed >= planned:
            self.db_set("status", "Completed", update_modified=False)
