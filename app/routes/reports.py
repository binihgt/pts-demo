from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from app.utils.decorators import manager_or_ceo_required
from app.services.report_service import ReportService

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@manager_or_ceo_required
def index():
    """Reports overview and download page."""
    return render_template("reports/index.html")


@reports_bp.route("/download", methods=["GET"])
@manager_or_ceo_required
def download():
    """Generate and download Excel report for selected date range."""
    start_date = request.args.get("start_date", "").strip() or None
    end_date = request.args.get("end_date", "").strip() or None

    try:
        buffer, filename = ReportService.generate_excel_report(
            start_date=start_date,
            end_date=end_date
        )
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        flash(f"Failed to generate report: {str(e)}", "danger")
        return redirect(url_for("reports.index"))
