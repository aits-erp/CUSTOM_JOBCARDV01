import frappe
from frappe.utils import flt


def execute(filters=None):

    filters = filters or {}

    work_order = filters.get("work_order")

    if not work_order:
        return get_columns(), []


    # ============================================================
    # WORK ORDER
    # ============================================================

    wo = frappe.get_doc("Work Order", work_order)

    production_item = wo.production_item
    production_item_name = frappe.db.get_value(
        "Item",
        production_item,
        "item_name"
    ) or production_item

    stock_uom = wo.stock_uom or ""


    # ============================================================
    # VARIABLES
    # ============================================================

    rm_input = 0.0
    blending_fg_input = 0.0
    packing_material = 0.0

    operation_data = []

    grand_planned = 0.0
    grand_consumed = 0.0


    # ============================================================
    # WORK ORDER PLANNED ITEMS
    # ============================================================

    planned_by_operation = {}

    wo_items = frappe.get_all(
        "Work Order Item",
        filters={
            "parent": work_order
        },
        fields=[
            "item_code",
            "item_name",
            "required_qty",
            "operation",
            "stock_uom"
        ]
    )

    for row in wo_items:

        operation = row.operation or "No Operation"

        operation_key = operation.strip().lower()

        if operation_key not in planned_by_operation:
            planned_by_operation[operation_key] = {}

        if row.item_code not in planned_by_operation[operation_key]:
            planned_by_operation[operation_key][row.item_code] = {
                "item_name": row.item_name,
                "qty": 0.0,
                "uom": row.stock_uom or stock_uom
            }

        planned_by_operation[operation_key][row.item_code]["qty"] += flt(
            row.required_qty
        )

        grand_planned += flt(row.required_qty)


    # ============================================================
    # JOB CARDS
    # ============================================================

    job_cards = frappe.get_all(
        "Job Card",
        filters={
            "work_order": work_order,
            "docstatus": ["<", 2]
        },
        fields=[
            "name",
            "operation",
            "sequence_id",
            "workstation",
            "actual_start_date",
            "actual_end_date",
            "total_time_in_mins"
        ],
        order_by="sequence_id asc, creation asc"
    )


    # ============================================================
    # PROCESS EACH JOB CARD
    # ============================================================

    for jc in job_cards:

        operation = jc.operation or "No Operation"
        operation_key = operation.strip().lower()

        planned = planned_by_operation.get(
            operation_key,
            {}
        )

        actual = {}

        # --------------------------------------------------------
        # STOCK ENTRIES FOR JOB CARD
        # --------------------------------------------------------

        stock_entries = frappe.get_all(
            "Stock Entry",
            filters={
                "job_card": jc.name,
                "docstatus": 1,
                "stock_entry_type": [
                    "in",
                    [
                        "Material Transfer for Manufacture",
                        "Material Consumption for Manufacture"
                    ]
                ]
            },
            fields=[
                "name"
            ]
        )


        # --------------------------------------------------------
        # CONSUMPTION
        # --------------------------------------------------------

        for se_row in stock_entries:

            stock_entry_items = frappe.get_all(
                "Stock Entry Detail",
                filters={
                    "parent": se_row.name,
                    "is_finished_item": 0
                },
                fields=[
                    "item_code",
                    "item_name",
                    "qty",
                    "uom"
                ]
            )

            for sed in stock_entry_items:

                item_code = sed.item_code
                qty = flt(sed.qty)

                if item_code not in actual:
                    actual[item_code] = {
                        "item_name": sed.item_name,
                        "qty": 0.0,
                        "uom": sed.uom or stock_uom
                    }

                actual[item_code]["qty"] += qty

                grand_consumed += qty


        # --------------------------------------------------------
        # YIELD CLASSIFICATION
        # --------------------------------------------------------

        for item_code, values in actual.items():

            qty = flt(values["qty"])

            item_default_bom = frappe.db.get_value(
                "Item",
                item_code,
                "default_bom"
            )

            # ----------------------------------------------------
            # BLENDING
            # ----------------------------------------------------

            if "blend" in operation_key:

                # Existing FG / manufactured item consumed in
                # blending is treated as Blending FG Input.
                #
                # Raw materials consumed in blending remain RM.

                if (
                    item_code == production_item
                    or item_default_bom
                ):
                    blending_fg_input += qty
                else:
                    rm_input += qty

            # ----------------------------------------------------
            # PACKING / FILTRATION
            # ----------------------------------------------------

            elif (
                "pack" in operation_key
                or "filtration" in operation_key
            ):

                packing_material += qty

            # ----------------------------------------------------
            # OTHER OPERATIONS
            # ----------------------------------------------------

            else:

                rm_input += qty


        # ========================================================
        # OPERATION REPORT ROWS
        # ========================================================

        operation_data.append({
            "operation": operation,
            "job_card": jc.name,
            "workstation": jc.workstation,
            "planned": planned,
            "actual": actual
        })


    # ============================================================
    # PRODUCTION
    # ============================================================

    net_production = flt(wo.produced_qty)


    # ============================================================
    # YIELD CALCULATION
    # ============================================================

    # FG Manufactured = New FG + Blending FG
    fg_manufactured = (
        net_production
        + blending_fg_input
    )


    # Total Input = RM + Blending FG
    total_input = (
        rm_input
        + blending_fg_input
    )


    # Gross Yield
    if total_input:
        gross_yield = (
            fg_manufactured
            / total_input
        ) * 100
    else:
        gross_yield = 0


    # Net Yield
    if rm_input:
        net_yield = (
            net_production
            / rm_input
        ) * 100
    else:
        net_yield = 0


    # ============================================================
    # REPORT DATA
    # ============================================================

    data = []


    # ============================================================
    # HEADER / SUMMARY
    # ============================================================

    data.append({
        "row_type": "summary",
        "operation": "YIELD SUMMARY",
        "item_code": production_item,
        "item_name": production_item_name,
        "planned_qty": flt(wo.qty),
        "rm_input": rm_input,
        "blending_fg_input": blending_fg_input,
        "total_input": total_input,
        "net_production": net_production,
        "fg_manufactured": fg_manufactured,
        "packing_material": packing_material,
        "gross_yield": gross_yield,
        "net_yield": net_yield
    })


    # ============================================================
    # OPERATION DETAILS
    # ============================================================

    for op in operation_data:

        operation = op["operation"]

        planned = op["planned"]
        actual = op["actual"]

        all_items = set(planned.keys()) | set(actual.keys())

        for item_code in sorted(all_items):

            p = planned.get(item_code, {})
            a = actual.get(item_code, {})

            planned_qty = flt(
                p.get("qty", 0)
            )

            actual_qty = flt(
                a.get("qty", 0)
            )

            difference = (
                actual_qty
                - planned_qty
            )

            data.append({
                "row_type": "detail",
                "operation": operation,
                "job_card": op["job_card"],
                "workstation": op["workstation"],
                "item_code": item_code,
                "item_name": (
                    a.get("item_name")
                    or p.get("item_name")
                ),
                "planned_qty": planned_qty,
                "consumed_qty": actual_qty,
                "difference": difference,
                "new_item": (
                    "Yes"
                    if planned_qty == 0 and actual_qty > 0
                    else "No"
                )
            })


        # Operation total

        operation_planned = sum(
            flt(x.get("qty", 0))
            for x in planned.values()
        )

        operation_consumed = sum(
            flt(x.get("qty", 0))
            for x in actual.values()
        )

        data.append({
            "row_type": "operation_total",
            "operation": f"{operation} TOTAL",
            "planned_qty": operation_planned,
            "consumed_qty": operation_consumed,
            "difference": (
                operation_consumed
                - operation_planned
            )
        })


    # ============================================================
    # GRAND TOTAL
    # ============================================================

    data.append({
        "row_type": "grand_total",
        "operation": "GRAND TOTAL",
        "planned_qty": grand_planned,
        "consumed_qty": grand_consumed,
        "difference": (
            grand_consumed
            - grand_planned
        )
    })


    return get_columns(), data


# ================================================================
# COLUMNS
# ================================================================

def get_columns():

    return [

        {
            "label": "Type",
            "fieldname": "row_type",
            "fieldtype": "Data",
            "hidden": 1
        },

        {
            "label": "Operation",
            "fieldname": "operation",
            "fieldtype": "Data",
            "width": 180
        },

        {
            "label": "Job Card",
            "fieldname": "job_card",
            "fieldtype": "Link",
            "options": "Job Card",
            "width": 160
        },

        {
            "label": "Workstation",
            "fieldname": "workstation",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 180
        },

        {
            "label": "Item Name",
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 200
        },

        {
            "label": "Planned Qty",
            "fieldname": "planned_qty",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Consumed Qty",
            "fieldname": "consumed_qty",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Difference",
            "fieldname": "difference",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "New Item?",
            "fieldname": "new_item",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": "RM Input",
            "fieldname": "rm_input",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Blending FG Input",
            "fieldname": "blending_fg_input",
            "fieldtype": "Float",
            "width": 140
        },

        {
            "label": "Total Input",
            "fieldname": "total_input",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Net Production",
            "fieldname": "net_production",
            "fieldtype": "Float",
            "width": 130
        },

        {
            "label": "FG Manufactured",
            "fieldname": "fg_manufactured",
            "fieldtype": "Float",
            "width": 130
        },

        {
            "label": "Packing Material",
            "fieldname": "packing_material",
            "fieldtype": "Float",
            "width": 130
        },

        {
            "label": "Gross Yield %",
            "fieldname": "gross_yield",
            "fieldtype": "Percent",
            "width": 120
        },

        {
            "label": "Net Yield %",
            "fieldname": "net_yield",
            "fieldtype": "Percent",
            "width": 120
        }
    ]