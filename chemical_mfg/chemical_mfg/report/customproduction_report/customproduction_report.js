frappe.query_reports["CustomProduction report"] = {
    filters: [
        {
            fieldname: "work_order",
            label: "Work Order",
            fieldtype: "Link",
            options: "Work Order",
            reqd: 1
        }
    ]
};
