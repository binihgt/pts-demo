import io
from datetime import datetime, timezone
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.models.sale import Sale
from app.models.payment import Payment
from app.models.user import User


class ReportService:
    """Service to generate professional, styled multi-sheet Excel workbooks."""

    # Brand styling constants
    COLOR_HEADER_BG = "1E3A8A"       # Deep Navy
    COLOR_HEADER_TEXT = "FFFFFF"     # White
    COLOR_ACCENT_BG = "F1F5F9"       # Light Slate
    COLOR_TOTAL_BG = "E2E8F0"        # Medium Slate
    COLOR_BORDER = "CBD5E1"          # Slate border

    @classmethod
    def generate_excel_report(
        cls,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[io.BytesIO, str]:
        """
        Generate a complete business workbook with Summary, Sales, and Payments sheets.
        Applies auto-fitting columns, formatted headers, and currency formatting.
        """
        # Parse date range
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError:
                pass

        # Helper to ensure UTC
        def ensure_dt(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        # Query Sales and filter by date range
        sales_query = Sale.query.order_by(Sale.created_at.desc()).all()
        if start_dt:
            sales_query = [s for s in sales_query if ensure_dt(s.created_at) >= start_dt]
        if end_dt:
            sales_query = [s for s in sales_query if ensure_dt(s.created_at) <= end_dt]

        # Query Payments and filter by date range
        payments_query = Payment.query.order_by(Payment.created_at.desc()).all()
        if start_dt:
            payments_query = [p for p in payments_query if ensure_dt(p.created_at) >= start_dt]
        if end_dt:
            payments_query = [p for p in payments_query if ensure_dt(p.created_at) <= end_dt]

        # Create Workbook
        wb = openpyxl.Workbook()

        # Styles
        thin_border = Border(
            left=Side(style="thin", color=cls.COLOR_BORDER),
            right=Side(style="thin", color=cls.COLOR_BORDER),
            top=Side(style="thin", color=cls.COLOR_BORDER),
            bottom=Side(style="thin", color=cls.COLOR_BORDER)
        )
        double_bottom_border = Border(
            left=Side(style="thin", color=cls.COLOR_BORDER),
            right=Side(style="thin", color=cls.COLOR_BORDER),
            top=Side(style="thin", color=cls.COLOR_BORDER),
            bottom=Side(style="double", color="000000")
        )
        header_fill = PatternFill(start_color=cls.COLOR_HEADER_BG, end_color=cls.COLOR_HEADER_BG, fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color=cls.COLOR_HEADER_TEXT)
        bold_font = Font(name="Calibri", size=11, bold=True)
        title_font = Font(name="Calibri", size=16, bold=True, color=cls.COLOR_HEADER_BG)
        section_font = Font(name="Calibri", size=13, bold=True)
        total_fill = PatternFill(start_color=cls.COLOR_TOTAL_BG, end_color=cls.COLOR_TOTAL_BG, fill_type="solid")

        # -----------------------------------------------------------------
        # Sheet 1: Summary Sheet
        # -----------------------------------------------------------------
        ws_summary = wb.active
        ws_summary.title = "Summary"
        ws_summary.views.sheetView[0].showGridLines = True
        ws_summary.row_dimensions[1].height = 36

        from app.utils.formatting import format_eat_datetime
        from app.services.sales_service import SalesService

        # Report Header
        ws_summary["A1"] = "PTS Demo - Business Executive Report"
        ws_summary["A1"].font = title_font
        ws_summary["A2"] = f"Generated: {format_eat_datetime(datetime.now(timezone.utc))} (EAT)"
        ws_summary["A2"].font = Font(italic=True, color="64748B")

        filter_text = "All Time"
        if start_date and end_date:
            filter_text = f"{start_date} to {end_date}"
        elif start_date:
            filter_text = f"From {start_date}"
        elif end_date:
            filter_text = f"Until {end_date}"
        ws_summary["A3"] = f"Date Filter: {filter_text}"
        ws_summary["A3"].font = Font(bold=True, color="334155")

        # Key Metrics Table
        ws_summary["A5"] = "Executive Key Performance Indicators"
        ws_summary["A5"].font = section_font
        ws_summary.row_dimensions[5].height = 24
        ws_summary.row_dimensions[6].height = 22

        if not start_dt and not end_dt:
            # Use unified single source of truth
            company_totals = SalesService.get_company_totals()
            total_sales_count = len(sales_query)
            total_sales_amount = company_totals["all_time_sales_total"]
            total_payments_amount = company_totals["all_time_collected_total"]
            total_unpaid_amount = company_totals["total_outstanding"]
        else:
            total_sales_count = len(sales_query)
            total_sales_amount = round(sum(s.total for s in sales_query), 2)
            total_payments_amount = round(sum(p.amount for p in payments_query), 2)
            total_unpaid_amount = round(sum(s.balance for s in sales_query), 2)

        collection_rate = (total_payments_amount / total_sales_amount * 100) if total_sales_amount > 0 else 0.0

        kpis = [
            ("Total Sales Transactions", total_sales_count, "#,##0"),
            ("Total Sales Revenue (ETB)", total_sales_amount, "#,##0.00"),
            ("Total Payments Collected (ETB)", total_payments_amount, "#,##0.00"),
            ("Outstanding Unpaid Balance (ETB)", total_unpaid_amount, "#,##0.00"),
            ("Collection Rate", collection_rate / 100.0, "0.0%"),
        ]

        ws_summary["A6"] = "Metric"
        ws_summary["B6"] = "Value"
        ws_summary["A6"].font = header_font
        ws_summary["A6"].fill = header_fill
        ws_summary["B6"].font = header_font
        ws_summary["B6"].fill = header_fill

        curr_row = 7
        for label, val, num_fmt in kpis:
            c1 = ws_summary.cell(row=curr_row, column=1, value=label)
            c2 = ws_summary.cell(row=curr_row, column=2, value=val)
            c1.border = thin_border
            c2.border = thin_border
            c2.number_format = num_fmt
            c2.alignment = Alignment(horizontal="right")
            curr_row += 1

        # Payment Methods Breakdown Table
        curr_row += 2
        ws_summary.cell(row=curr_row, column=1, value="Collections by Payment Method").font = section_font
        curr_row += 1

        ws_summary.cell(row=curr_row, column=1, value="Method").font = header_font
        ws_summary.cell(row=curr_row, column=1).fill = header_fill
        ws_summary.cell(row=curr_row, column=2, value="Transactions").font = header_font
        ws_summary.cell(row=curr_row, column=2).fill = header_fill
        ws_summary.cell(row=curr_row, column=3, value="Total Collected (ETB)").font = header_font
        ws_summary.cell(row=curr_row, column=3).fill = header_fill
        curr_row += 1

        for method_name, method_key in [("Telebirr", Payment.METHOD_TELEBIRR), ("Bank Transfer / CBE", Payment.METHOD_BANK), ("Cash", Payment.METHOD_CASH)]:
            method_payments = [p for p in payments_query if p.method == method_key]
            m_count = len(method_payments)
            m_sum = sum(p.amount for p in method_payments)

            r1 = ws_summary.cell(row=curr_row, column=1, value=method_name)
            r2 = ws_summary.cell(row=curr_row, column=2, value=m_count)
            r3 = ws_summary.cell(row=curr_row, column=3, value=m_sum)
            for cell in (r1, r2, r3):
                cell.border = thin_border
            r2.number_format = "#,##0"
            r3.number_format = "#,##0.00"
            curr_row += 1

        # Top Sales Performers
        curr_row += 2
        ws_summary.cell(row=curr_row, column=1, value="Top Sales Employees").font = section_font
        curr_row += 1

        ws_summary.cell(row=curr_row, column=1, value="Employee Name").font = header_font
        ws_summary.cell(row=curr_row, column=1).fill = header_fill
        ws_summary.cell(row=curr_row, column=2, value="Sales Count").font = header_font
        ws_summary.cell(row=curr_row, column=2).fill = header_fill
        ws_summary.cell(row=curr_row, column=3, value="Total Revenue (ETB)").font = header_font
        ws_summary.cell(row=curr_row, column=3).fill = header_fill
        curr_row += 1

        # Aggregate sales per employee
        emp_totals = {}
        for s in sales_query:
            emp_name = s.employee.name if s.employee else "Unknown"
            if emp_name not in emp_totals:
                emp_totals[emp_name] = {"count": 0, "total": 0.0}
            emp_totals[emp_name]["count"] += 1
            emp_totals[emp_name]["total"] += s.total

        sorted_emps = sorted(emp_totals.items(), key=lambda x: x[1]["total"], reverse=True)
        for emp_name, data in sorted_emps[:5]:
            e1 = ws_summary.cell(row=curr_row, column=1, value=emp_name)
            e2 = ws_summary.cell(row=curr_row, column=2, value=data["count"])
            e3 = ws_summary.cell(row=curr_row, column=3, value=data["total"])
            for cell in (e1, e2, e3):
                cell.border = thin_border
            e2.number_format = "#,##0"
            e3.number_format = "#,##0.00"
            curr_row += 1

        # -----------------------------------------------------------------
        # Sheet 2: Sales Sheet
        # -----------------------------------------------------------------
        ws_sales = wb.create_sheet(title="Sales")
        ws_sales.views.sheetView[0].showGridLines = True
        ws_sales.freeze_panes = "A2"

        sales_headers = [
            "Invoice #",
            "Date & Time (EAT)",
            "Employee",
            "Customer",
            "Customer Phone",
            "Item Description",
            "Quantity",
            "Unit Price (ETB)",
            "Total (ETB)",
            "Amount Paid (ETB)",
            "Balance Due (ETB)",
            "Status",
        ]

        for col_idx, header in enumerate(sales_headers, start=1):
            cell = ws_sales.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws_sales.row_dimensions[1].height = 26

        row_idx = 2
        for s in sales_query:
            ws_sales.cell(row=row_idx, column=1, value=s.id).alignment = Alignment(horizontal="center")
            ws_sales.cell(row=row_idx, column=2, value=format_eat_datetime(s.created_at))
            ws_sales.cell(row=row_idx, column=3, value=s.employee.name if s.employee else "-")
            ws_sales.cell(row=row_idx, column=4, value=s.customer.name if s.customer else "Walk-in")
            ws_sales.cell(row=row_idx, column=5, value=s.customer.phone if s.customer and s.customer.phone else "-")
            ws_sales.cell(row=row_idx, column=6, value=s.item)

            c_qty = ws_sales.cell(row=row_idx, column=7, value=s.quantity)
            c_qty.number_format = "#,##0"

            c_price = ws_sales.cell(row=row_idx, column=8, value=s.unit_price)
            c_price.number_format = "#,##0.00"

            c_total = ws_sales.cell(row=row_idx, column=9, value=s.total)
            c_total.number_format = "#,##0.00"

            c_paid = ws_sales.cell(row=row_idx, column=10, value=s.total_paid)
            c_paid.number_format = "#,##0.00"

            c_bal = ws_sales.cell(row=row_idx, column=11, value=s.balance)
            c_bal.number_format = "#,##0.00"

            c_status = ws_sales.cell(row=row_idx, column=12, value=s.payment_status.title())
            c_status.alignment = Alignment(horizontal="center")

            for col_idx in range(1, 13):
                ws_sales.cell(row=row_idx, column=col_idx).border = thin_border

            row_idx += 1

        # Totals Row for Sales using live Excel formulas
        if sales_query:
            ws_sales.cell(row=row_idx, column=6, value="TOTALS:").font = bold_font
            ws_sales.cell(row=row_idx, column=6).alignment = Alignment(horizontal="right")

            last_data_row = row_idx - 1
            t_qty = ws_sales.cell(row=row_idx, column=7, value=f"=SUM(G2:G{last_data_row})")
            t_qty.number_format = "#,##0"
            t_qty.font = bold_font

            t_total = ws_sales.cell(row=row_idx, column=9, value=f"=SUM(I2:I{last_data_row})")
            t_total.number_format = "#,##0.00"
            t_total.font = bold_font

            t_paid = ws_sales.cell(row=row_idx, column=10, value=f"=SUM(J2:J{last_data_row})")
            t_paid.number_format = "#,##0.00"
            t_paid.font = bold_font

            t_bal = ws_sales.cell(row=row_idx, column=11, value=f"=SUM(K2:K{last_data_row})")
            t_bal.number_format = "#,##0.00"
            t_bal.font = bold_font

            for col_idx in range(1, 13):
                c = ws_sales.cell(row=row_idx, column=col_idx)
                c.fill = total_fill
                c.border = double_bottom_border

        # -----------------------------------------------------------------
        # Sheet 3: Payments Sheet
        # -----------------------------------------------------------------
        ws_payments = wb.create_sheet(title="Payments")
        ws_payments.views.sheetView[0].showGridLines = True
        ws_payments.freeze_panes = "A2"

        payments_headers = [
            "Receipt #",
            "Date & Time (EAT)",
            "Invoice #",
            "Item",
            "Customer",
            "Amount (ETB)",
            "Payment Method",
        ]

        for col_idx, header in enumerate(payments_headers, start=1):
            cell = ws_payments.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
        ws_payments.row_dimensions[1].height = 26

        p_row_idx = 2
        for p in payments_query:
            ws_payments.cell(row=p_row_idx, column=1, value=f"PAY-{p.id}").alignment = Alignment(horizontal="center")
            ws_payments.cell(row=p_row_idx, column=2, value=format_eat_datetime(p.created_at))
            ws_payments.cell(row=p_row_idx, column=3, value=p.sale_id).alignment = Alignment(horizontal="center")
            ws_payments.cell(row=p_row_idx, column=4, value=p.sale.item if p.sale else "-")
            ws_payments.cell(row=p_row_idx, column=5, value=p.sale.customer.name if p.sale and p.sale.customer else "Walk-in")

            c_amt = ws_payments.cell(row=p_row_idx, column=6, value=p.amount)
            c_amt.number_format = "#,##0.00"

            c_method = ws_payments.cell(row=p_row_idx, column=7, value=p.method.title())
            c_method.alignment = Alignment(horizontal="center")

            for col_idx in range(1, 8):
                ws_payments.cell(row=p_row_idx, column=col_idx).border = thin_border

            p_row_idx += 1

        # Totals Row for Payments using live Excel formula
        if payments_query:
            ws_payments.cell(row=p_row_idx, column=5, value="TOTAL COLLECTED:").font = bold_font
            ws_payments.cell(row=p_row_idx, column=5).alignment = Alignment(horizontal="right")

            last_p_row = p_row_idx - 1
            t_p_amt = ws_payments.cell(row=p_row_idx, column=6, value=f"=SUM(F2:F{last_p_row})")
            t_p_amt.number_format = "#,##0.00"
            t_p_amt.font = bold_font

            for col_idx in range(1, 8):
                c = ws_payments.cell(row=p_row_idx, column=col_idx)
                c.fill = total_fill
                c.border = double_bottom_border

        # -----------------------------------------------------------------
        # Auto-fit Column Widths across all sheets (including Payment Method)
        # -----------------------------------------------------------------
        for ws in (ws_summary, ws_sales, ws_payments):
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value is not None:
                        val_str = str(cell.value)
                        # Normalize formula representations for sizing
                        if val_str.startswith("="):
                            val_str = "123,456.78"
                        max_len = max(max_len, len(val_str))
                # Generous padding ensuring no truncation
                ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

        # Write to in-memory bytes buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        filename = f"pts_report_{timestamp_str}.xlsx"

        return buffer, filename
