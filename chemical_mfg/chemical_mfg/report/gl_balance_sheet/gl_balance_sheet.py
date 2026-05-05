# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from erpnext.accounts.report.financial_statements import (
	compute_growth_view_data,
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
		# Get current fiscal year
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

	# Get data
	asset = get_data(
		filters.company,
		"Asset",
		"Debit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	liability = get_data(
		filters.company,
		"Liability",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	equity = get_data(
		filters.company,
		"Equity",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	# Ensure they are lists
	asset = asset or []
	liability = liability or []
	equity = equity or []

	# Filter out group accounts if only_gl_accounts is checked
	if filters.get("only_gl_accounts"):
		asset = [row for row in asset if not row.get("is_group")]
		liability = [row for row in liability if not row.get("is_group")]
		equity = [row for row in equity if not row.get("is_group")]

	provisional_profit_loss, total_credit = get_provisional_profit_loss(
		asset, liability, equity, period_list, filters.company, currency, filters=filters
	)

	message, opening_balance = check_opening_balance(asset, liability, equity)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])
	
	# Only add unclosed fiscal years entry if not showing only GL accounts
	if opening_balance and round(opening_balance, 2) != 0 and not filters.get("only_gl_accounts"):
		unclosed = {
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		for period in period_list:
			unclosed[period.key] = opening_balance
			if provisional_profit_loss:
				provisional_profit_loss[period.key] = provisional_profit_loss.get(period.key, 0) - opening_balance

		unclosed["total"] = opening_balance
		data.append(unclosed)

	if provisional_profit_loss and not filters.get("only_gl_accounts"):
		data.append(provisional_profit_loss)
	if total_credit and not filters.get("only_gl_accounts"):
		data.append(total_credit)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, company=filters.company
	)

	chart = get_chart_data(filters, columns, asset, liability, equity, currency)

	report_summary, primitive_summary = get_report_summary(
		period_list, asset, liability, equity, provisional_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	return columns, data, message, chart, report_summary, primitive_summary


def get_provisional_profit_loss(
	asset, liability, equity, period_list, company, currency=None, consolidated=False, filters=None
):
	if not filters:
		filters = frappe._dict()
	
	provisional_profit_loss = {}
	total_row = {}
	
	# Ensure all are lists
	asset = asset or []
	liability = liability or []
	equity = equity or []
	
	if asset and not filters.get("only_gl_accounts"):
		total = total_row_total = 0
		currency = currency or frappe.get_cached_value("Company", company, "default_currency")
		total_row = {
			"account_name": "'" + _("Total (Credit)") + "'",
			"account": "'" + _("Total (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		has_value = False

		# Find the total row (usually the last row or row with "Total" in name)
		asset_last_row = None
		liability_last_row = None
		equity_last_row = None
		
		# Find asset total row
		if asset:
			for row in reversed(asset):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					asset_last_row = row
					break
			if not asset_last_row and len(asset) > 0:
				asset_last_row = asset[-1] if asset else None
		
		# Find liability total row    
		if liability:
			for row in reversed(liability):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					liability_last_row = row
					break
			if not liability_last_row and len(liability) > 0:
				liability_last_row = liability[-1] if liability else None
		
		# Find equity total row    
		if equity:
			for row in reversed(equity):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					equity_last_row = row
					break
			if not equity_last_row and len(equity) > 0:
				equity_last_row = equity[-1] if equity else None

		for period in period_list:
			key = period if consolidated else period.key
			total_assets = flt(asset_last_row.get(key)) if asset_last_row else 0.0
			effective_liability = 0.00

			if liability_last_row:
				effective_liability += flt(liability_last_row.get(key))
			if equity_last_row:
				effective_liability += flt(equity_last_row.get(key))

			provisional_profit_loss[key] = total_assets - effective_liability
			if total_row is not None:
				total_row[key] = provisional_profit_loss[key] + effective_liability

			if provisional_profit_loss[key]:
				has_value = True

			total += flt(provisional_profit_loss[key])
			provisional_profit_loss["total"] = total

			if total_row is not None:
				total_row_total += flt(total_row[key])
				total_row["total"] = total_row_total

		if has_value:
			provisional_profit_loss.update(
				{
					"account_name": "'" + _("Provisional Profit / Loss (Credit)") + "'",
					"account": "'" + _("Provisional Profit / Loss (Credit)") + "'",
					"warn_if_negative": True,
					"currency": currency,
				}
			)

	return provisional_profit_loss, total_row


def check_opening_balance(asset, liability, equity):
	# Check if previous year balance sheet closed
	opening_balance = 0
	float_precision = cint(frappe.db.get_default("float_precision")) or 2
	
	# Ensure all are lists
	asset = asset or []
	liability = liability or []
	equity = equity or []
	
	if asset and len(asset) > 0 and asset[-1] is not None:
		opening_balance = flt(asset[-1].get("opening_balance", 0), float_precision)
	if liability and len(liability) > 0 and liability[-1] is not None:
		opening_balance -= flt(liability[-1].get("opening_balance", 0), float_precision)
	if equity and len(equity) > 0 and equity[-1] is not None:
		opening_balance -= flt(equity[-1].get("opening_balance", 0), float_precision)

	opening_balance = flt(opening_balance, float_precision)
	if opening_balance:
		return _("Previous Financial Year is not closed"), opening_balance
	return None, None


def get_report_summary(
	period_list,
	asset,
	liability,
	equity,
	provisional_profit_loss,
	currency,
	filters,
	consolidated=False,
):
	if not filters:
		filters = frappe._dict()
	
	net_asset, net_liability, net_equity, net_provisional_profit_loss = 0.0, 0.0, 0.0, 0.0

	# Ensure all are lists
	asset = asset or []
	liability = liability or []
	equity = equity or []

	if filters.get("accumulated_values"):
		period_list = [period_list[-1]]

	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for period in period_list:
		key = period if consolidated else period.key
		
		# Calculate asset total
		if asset:
			asset_total = None
			for row in reversed(asset):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					asset_total = row
					break
			if not asset_total and len(asset) > 0:
				asset_total = asset[-1]
			if asset_total:
				net_asset += asset_total.get(key, 0.0)
		
		# Calculate liability total        
		if liability:
			liability_total = None
			for row in reversed(liability):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					liability_total = row
					break
			if not liability_total and len(liability) > 0:
				liability_total = liability[-1]
			if liability_total:
				net_liability += liability_total.get(key, 0.0)
		
		# Calculate equity total        
		if equity:
			equity_total = None
			for row in reversed(equity):
				if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
					equity_total = row
					break
			if not equity_total and len(equity) > 0:
				equity_total = equity[-1]
			if equity_total:
				net_equity += equity_total.get(key, 0.0)
		
		# Calculate provisional profit/loss
		if provisional_profit_loss and not filters.get("only_gl_accounts"):
			net_provisional_profit_loss += provisional_profit_loss.get(key, 0.0)

	report_summary_items = [
		{"value": net_asset, "label": _("Total Asset"), "datatype": "Currency", "currency": currency},
		{
			"value": net_liability,
			"label": _("Total Liability"),
			"datatype": "Currency",
			"currency": currency,
		},
		{"value": net_equity, "label": _("Total Equity"), "datatype": "Currency", "currency": currency},
	]
	
	if not filters.get("only_gl_accounts"):
		report_summary_items.append({
			"value": net_provisional_profit_loss,
			"label": _("Provisional Profit / Loss (Credit)"),
			"indicator": "Green" if net_provisional_profit_loss > 0 else "Red",
			"datatype": "Currency",
			"currency": currency,
		})
	
	return report_summary_items, (net_asset - net_liability + net_equity)


def get_chart_data(filters, columns, asset, liability, equity, currency):
	if not filters:
		filters = frappe._dict()
	
	labels = [d.get("label") for d in columns[2:]]

	asset_data, liability_data, equity_data = [], [], []

	# Ensure all are lists
	asset = asset or []
	liability = liability or []
	equity = equity or []

	# Find total rows
	asset_total = None
	liability_total = None
	equity_total = None
	
	if asset:
		for row in reversed(asset):
			if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
				asset_total = row
				break
		if not asset_total and len(asset) > 0:
			asset_total = asset[-1]
	
	if liability:
		for row in reversed(liability):
			if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
				liability_total = row
				break
		if not liability_total and len(liability) > 0:
			liability_total = liability[-1]
	
	if equity:
		for row in reversed(equity):
			if row.get("account_name") and ("Total" in str(row.get("account_name", "")) or not row.get("parent_account")):
				equity_total = row
				break
		if not equity_total and len(equity) > 0:
			equity_total = equity[-1]

	for p in columns[2:]:
		if asset and asset_total:
			asset_data.append(asset_total.get(p.get("fieldname"), 0.0))
		if liability and liability_total:
			liability_data.append(liability_total.get(p.get("fieldname"), 0.0))
		if equity and equity_total:
			equity_data.append(equity_total.get(p.get("fieldname"), 0.0))

	datasets = []
	if asset_data:
		datasets.append({"name": _("Assets"), "values": asset_data})
	if liability_data:
		datasets.append({"name": _("Liabilities"), "values": liability_data})
	if equity_data:
		datasets.append({"name": _("Equity"), "values": equity_data})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"
	chart["options"] = "currency"
	chart["currency"] = currency

	return chart