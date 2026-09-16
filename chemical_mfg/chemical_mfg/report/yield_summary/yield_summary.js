frappe.query_reports["Yield Summary"] = {
    filters: [
        {
            fieldname: "work_order",
            label: __("Work Order"),
            fieldtype: "Link",
            options: "Work Order",
            reqd: 1
        }
    ]
};