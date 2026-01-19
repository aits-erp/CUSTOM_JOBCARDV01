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
    # ON SUBMIT → APPLY CUMULATIVE LOGIC
    # --------------------------------------------------
    # def on_submit(self):
    #     super().on_submit()
    #     self.db_set("process_loss_qty", 0, update_modified=False)
    #     self.update_cumulative_completed_qty()

    # # --------------------------------------------------
    # # ✅ FIXED CUMULATIVE QTY LOGIC
    # # --------------------------------------------------
    # def update_cumulative_completed_qty(self):
    #     """
    #     Operation-wise cumulative completed qty
    #     """

    #     if not self.work_order or not self.operation:
    #         return

    #     wo = frappe.get_doc("Work Order", self.work_order)

    #     # Find current operation row
    #     current_op = None
    #     for op in wo.operations:
    #         if op.operation == self.operation:
    #             current_op = op
    #             break

    #     if not current_op:
    #         return

    #     current_seq = flt(current_op.sequence_id)

    #     # ✅ CORRECT FIELD
    #     current_qty = flt(self.total_completed_qty or 0)

    #     # Sum previous operations
    #     previous_total = 0
    #     for op in wo.operations:
    #         if flt(op.sequence_id) < current_seq:
    #             previous_total += flt(op.completed_qty or 0)

    #     cumulative_qty = previous_total + current_qty

    #     # Update only this operation row
    #     current_op.completed_qty = cumulative_qty

    #     wo.save(ignore_permissions=True)
