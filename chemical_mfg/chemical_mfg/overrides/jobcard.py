import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard


class CustomJobCard(JobCard):

    # ---------------------------------------------
    # KEEP YOUR EXISTING LOGIC (UNCHANGED)
    # ---------------------------------------------
    def validate_job_card(self):
        return

    def validate_sequence_id(self):
        return

    def validate_job_card_qty(self):
        return

    # ---------------------------------------------
    # KEEP EXISTING VALIDATE
    # ---------------------------------------------
    def validate(self):
        super().validate()

        # 🚫 Kill process loss at source
        self.process_loss_qty = 0

    # ---------------------------------------------
    # ADD CUMULATIVE QTY LOGIC
    # ---------------------------------------------
    def on_submit(self):
        # Let ERPNext do its standard submit work
        super().on_submit()

        # 🔒 Force remove loss AFTER ERPNext logic
        self.db_set("process_loss_qty", 0, update_modified=False)

        # ➕ Apply cumulative completed qty logic
        self.update_cumulative_completed_qty()

    # ---------------------------------------------
    # INTERNAL METHOD
    # ---------------------------------------------
    def update_cumulative_completed_qty(self):
        """
        Make completed_qty cumulative based on operation sequence
        """

        if not self.work_order or not self.operation:
            return

        wo = frappe.get_doc("Work Order", self.work_order)

        current_op = None
        for op in wo.operations or []:
            if op.operation == self.operation:
                current_op = op
                break

        if not current_op:
            return

        current_seq = flt(current_op.sequence_id)
        current_qty = flt(self.completed_qty)

        # Sum completed qty of all previous operations
        previous_total = 0
        for op in wo.operations or []:
            if flt(op.sequence_id) < current_seq:
                previous_total += flt(op.completed_qty)

        cumulative_qty = previous_total + current_qty

        # Update only the current operation row
        current_op.completed_qty = cumulative_qty

        wo.save(ignore_permissions=True)
