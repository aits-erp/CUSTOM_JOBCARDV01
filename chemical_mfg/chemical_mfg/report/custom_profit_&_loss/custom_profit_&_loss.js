// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Custom Profit & Loss"] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions("Custom Profit & Loss", 10);

frappe.query_reports["Custom Profit & Loss"]["filters"].push(
	{
		fieldname: "selected_view",
		label: __("Select View"),
		fieldtype: "Select",
		options: [
			{ value: "Report", label: __("Report View") },
			{ value: "Growth", label: __("Growth View") },
			{ value: "Margin", label: __("Margin View") },
		],
		default: "Report",
		reqd: 1,
	},
	{
		fieldname: "accumulated_values",
		label: __("Accumulated Values"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "include_default_book_entries",
		label: __("Include Default FB Entries"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "show_zero_values",
		label: __("Show zero values"),
		fieldtype: "Check",
	},
	{
		fieldname: "show_group_accounts",
		label: __("Show Group Accounts"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "only_gl_accounts",
		label: __("Only GL Accounts (Exclude Groups)"),
		fieldtype: "Check",
		default: 0,
		depends_on: "eval:doc.show_group_accounts",
		description: __("When checked, only leaf-level GL accounts will be shown (no group/subgroup totals)"),
	}
);