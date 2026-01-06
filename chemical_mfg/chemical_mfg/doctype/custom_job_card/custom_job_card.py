import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CustomJobCard(Document):

    def validate(self):
        """
        Calculate RM qty for this stage
        """
        # rm_stage_qty is user-entered or calculated externally
        self.rm_stage_qty = flt(self.rm_stage_qty or 0)

    def on_submit(self):
        """
        Calculate cumulative qty based on previous operations
        """
        if not self.work_order or not self.sequence_id:
            return

        previous_total = frappe.db.sql(
            """
            SELECT
                COALESCE(SUM(rm_stage_qty), 0)
            FROM
                `tabCustom Job Card`
            WHERE
                work_order = %s
                AND docstatus = 1
                AND sequence_id < %s
            """,
            (self.work_order, self.sequence_id),
        )[0][0]

        self.cumulative_qty = flt(previous_total) + flt(self.rm_stage_qty)

        self.db_set(
            "cumulative_qty",
            self.cumulative_qty,
            update_modified=False
        )

        self.db_set(
            "status",
            "Completed",
            update_modified=False
        )
