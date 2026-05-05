# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	compute_growth_view_data,
	compute_margin_view_data,
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)


def execute(filters=None):
	if not filters:
		filters = frappe._dict()
	
	# Set default fiscal year if not provided
	if not filters.get("from_fiscal_year") and not filters.get("to_fiscal_year"):
		current_fiscal_year = frappe.db.get_value(
			"Fiscal Year",
			{"is_default": 1},
			"name"
		)
		if not current_fiscal_year:
			current_fiscal_year = frappe.db.get_value(
				"Fiscal Year",
				{},
				"name"
			)
		if current_fiscal_year:
			filters.from_fiscal_year = current_fiscal_year
			filters.to_fiscal_year = current_fiscal_year

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	if not period_list:
		return [], [], None, None, None, None

	filters.period_start_date = period_list[0]["year_start_date"]

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	# Get Income data
	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	# Get Expense data
	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	# Ensure they are lists
	income = income or []
	expense = expense or []

	# Filter out group accounts if only_gl_accounts is checked
	if filters.get("only_gl_accounts"):
		income = [row for row in income if not row.get("is_group")]
		expense = [row for row in expense if not row.get("is_group")]

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency, filters=filters
	)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss and not filters.get("only_gl_accounts"):
		data.append(net_profit_loss)

	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

	chart = get_chart_data(filters, columns, income, expense, net_profit_loss, currency)

	report_summary, primitive_summary = get_report_summary(
		period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	if filters.get("selected_view") == "Margin":
		compute_margin_view_data(data, period_list, filters.accumulated_values)

	return columns, data, None, chart, report_summary, primitive_summary


def get_report_summary(
	period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False
):
	if not filters:
		filters = frappe._dict()
	
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0

	# Ensure they are lists
	income = income or []
	expense = expense or []

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	if filters.accumulated_values:
		# when 'accumulated_values' is enabled, periods have running balance.
		# so, last period will have the net amount.
		key = period_list[-1].key
		if income:
			# Find the total row
			income_total = None
			for row in reversed(income):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					income_total = row
					break
			if not income_total and len(income) > 0:
				income_total = income[-1]
			if income_total:
				net_income = income_total.get(key, 0.0)
		if expense:
			expense_total = None
			for row in reversed(expense):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					expense_total = row
					break
			if not expense_total and len(expense) > 0:
				expense_total = expense[-1]
			if expense_total:
				net_expense = expense_total.get(key, 0.0)
		if net_profit_loss and not filters.get("only_gl_accounts"):
			net_profit = net_profit_loss.get(key, 0.0)
	else:
		for period in period_list:
			key = period if consolidated else period.key
			if income:
				income_total = None
				for row in reversed(income):
					if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
						income_total = row
						break
				if not income_total and len(income) > 0:
					income_total = income[-1]
				if income_total:
					net_income += income_total.get(key, 0.0)
			if expense:
				expense_total = None
				for row in reversed(expense):
					if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
						expense_total = row
						break
				if not expense_total and len(expense) > 0:
					expense_total = expense[-1]
				if expense_total:
					net_expense += expense_total.get(key, 0.0)
			if net_profit_loss and not filters.get("only_gl_accounts"):
				net_profit += net_profit_loss.get(key, 0.0)

	if len(period_list) == 1 and periodicity == "Yearly":
		profit_label = _("Profit This Year")
		income_label = _("Total Income This Year")
		expense_label = _("Total Expense This Year")
	else:
		profit_label = _("Net Profit")
		income_label = _("Total Income")
		expense_label = _("Total Expense")

	report_summary_items = [
		{"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
	]
	
	if not filters.get("only_gl_accounts"):
		report_summary_items.append({
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		})
	
	return report_summary_items, net_profit


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False, filters=None):
	if not filters:
		filters = frappe._dict()
	
	total = 0
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False
	
	# Ensure they are lists
	income = income or []
	expense = expense or []
	
	# Find total rows
	income_total = None
	expense_total = None
	
	if income:
		for row in reversed(income):
			if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
				income_total = row
				break
		if not income_total and len(income) > 0:
			income_total = income[-1]
	
	if expense:
		for row in reversed(expense):
			if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
				expense_total = row
				break
		if not expense_total and len(expense) > 0:
			expense_total = expense[-1]

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income_total.get(key, 0.0), 3) if income_total else 0
		total_expense = flt(expense_total.get(key, 0.0), 3) if expense_total else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value and not filters.get("only_gl_accounts"):
		return net_profit_loss
	
	return None


def get_chart_data(filters, columns, income, expense, net_profit_loss, currency):
	if not filters:
		filters = frappe._dict()
	
	labels = [d.get("label") for d in columns[4:]]

	income_data, expense_data, net_profit = [], [], []
	
	# Ensure they are lists
	income = income or []
	expense = expense or []
	
	# Find total rows
	income_total = None
	expense_total = None
	
	if income:
		for row in reversed(income):
			if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
				income_total = row
				break
		if not income_total and len(income) > 0:
			income_total = income[-1]
	
	if expense:
		for row in reversed(expense):
			if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
				expense_total = row
				break
		if not expense_total and len(expense) > 0:
			expense_total = expense[-1]

	for p in columns[4:]:
		if income and income_total:
			income_data.append(income_total.get(p.get("fieldname"), 0.0))
		if expense and expense_total:
			expense_data.append(expense_total.get(p.get("fieldname"), 0.0))
		if net_profit_loss and not filters.get("only_gl_accounts"):
			net_profit.append(net_profit_loss.get(p.get("fieldname"), 0.0))

	datasets = []
	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit and not filters.get("only_gl_accounts"):
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"
	chart["options"] = "currency"
	chart["currency"] = currency

	return chart