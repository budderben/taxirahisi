from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
import datetime
import io
import csv
from database import (
    SessionLocal, User, Taxpayer, Business, Association, AssociationMember, AssociationPayout,
    CommunityProject, TaxAssessment, TaxBand, TaxRule, Payment, DigitalReceipt, Complaint,
    ComplaintResponse, AuditLog, Region, District, Market, BusinessCategory, Registration
)
from auth import login_required, roles_required, log_audit_event

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@roles_required('super_admin', 'tra_admin', 'revenue_officer', 'auditor')
def dashboard():
    db = SessionLocal()
    try:
        # Aggregated real platform metrics
        total_taxpayers = db.query(Taxpayer).count()
        total_associations = db.query(Association).count()
        active_associations = db.query(Association).filter(Association.status == "Active").count()

        payments = db.query(Payment).all()
        total_collected = sum(p.amount for p in payments if p.status == "SUCCESSFUL")
        pending_payments_count = sum(1 for p in payments if p.status == "PENDING")

        assessments = db.query(TaxAssessment).all()
        total_assessed = sum(a.total_tax_liability for a in assessments)
        outstanding_balance = max(0.0, total_assessed - total_collected)

        compliant_count = db.query(Taxpayer).filter(Taxpayer.compliance_status.in_(["COMPLIANT", "GRACE_PERIOD"])).count()
        compliance_rate = round((compliant_count / total_taxpayers * 100), 1) if total_taxpayers > 0 else 100.0

        pending_complaints = db.query(Complaint).filter(Complaint.status.in_(["Submitted", "Under Review"])).count()
        pending_payouts = db.query(AssociationPayout).filter(AssociationPayout.status == "Pending Approval").count()

        # Regional collection summary
        regions = db.query(Region).all()
        regional_stats = []
        for r in regions:
            r_taxpayers = db.query(Taxpayer).filter(Taxpayer.region_id == r.id).all()
            r_tp_ids = [t.id for t in r_taxpayers]
            r_collected = sum(p.amount for p in payments if p.taxpayer_id in r_tp_ids and p.status == "SUCCESSFUL") if r_tp_ids else 0.0
            regional_stats.append({
                "region_name": r.name,
                "taxpayers_count": len(r_taxpayers),
                "total_collected": r_collected
            })

        recent_payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(6).all()
        recent_taxpayers = db.query(Taxpayer).order_by(Taxpayer.created_at.desc()).limit(6).all()

        return render_template('admin/dashboard.html',
                               total_taxpayers=total_taxpayers,
                               total_associations=total_associations,
                               active_associations=active_associations,
                               total_collected=total_collected,
                               outstanding_balance=outstanding_balance,
                               compliance_rate=compliance_rate,
                               pending_complaints=pending_complaints,
                               pending_payouts=pending_payouts,
                               regional_stats=regional_stats,
                               recent_payments=recent_payments,
                               recent_taxpayers=recent_taxpayers)
    finally:
        db.close()

@admin_bp.route('/taxpayers')
@login_required
@roles_required('super_admin', 'tra_admin', 'revenue_officer', 'auditor')
def taxpayers():
    db = SessionLocal()
    try:
        search = request.args.get('search', '').strip()
        region_filter = request.args.get('region')
        status_filter = request.args.get('status')

        query = db.query(Taxpayer)
        if search:
            query = query.filter(
                (Taxpayer.full_name.ilike(f"%{search}%")) |
                (Taxpayer.tin.ilike(f"%{search}%")) |
                (Taxpayer.phone_number.ilike(f"%{search}%"))
            )
        if region_filter:
            query = query.filter(Taxpayer.region_id == int(region_filter))
        if status_filter:
            query = query.filter(Taxpayer.compliance_status == status_filter)

        taxpayers_list = query.order_by(Taxpayer.created_at.desc()).all()
        regions = db.query(Region).all()

        return render_template('admin/taxpayers.html',
                               taxpayers=taxpayers_list,
                               regions=regions,
                               search=search,
                               current_region=region_filter,
                               current_status=status_filter)
    finally:
        db.close()

@admin_bp.route('/taxpayers/<int:taxpayer_id>/toggle-status', methods=['POST'])
@login_required
@roles_required('super_admin', 'tra_admin')
def toggle_taxpayer_status(taxpayer_id):
    db = SessionLocal()
    try:
        taxpayer = db.query(Taxpayer).filter(Taxpayer.id == taxpayer_id).first()
        if taxpayer and taxpayer.user:
            taxpayer.user.is_active = not taxpayer.user.is_active
            action_name = "REACTIVATE" if taxpayer.user.is_active else "SUSPEND"
            db.commit()

            log_audit_event(
                actor_username=session.get('username'),
                action=f"TAXPAYER_{action_name}",
                entity_type="TAXPAYER",
                entity_id=str(taxpayer.id),
                details=f"User {taxpayer.full_name} status toggled to is_active={taxpayer.user.is_active}"
            )
            flash(f"Hali ya mlipakodi {taxpayer.full_name} imebadilishwa kuwa: {'Hai (Active)' if taxpayer.user.is_active else 'Imesimamishwa (Suspended)'}.", "info")
        return redirect(url_for('admin.taxpayers'))
    finally:
        db.close()

@admin_bp.route('/tax-rules', methods=['GET', 'POST'])
@login_required
@roles_required('super_admin', 'tra_admin')
def tax_rules():
    db = SessionLocal()
    try:
        if request.method == 'POST':
            band_id = int(request.form.get('band_id'))
            fixed_tax = float(request.form.get('fixed_tax', 0))
            reason = request.form.get('reason', '').strip()

            band = db.query(TaxBand).filter(TaxBand.id == band_id).first()
            if band:
                old_val = f"Fixed: TZS {band.fixed_tax_amount:,.0f}"
                band.fixed_tax_amount = fixed_tax
                new_val = f"Fixed: TZS {fixed_tax:,.0f}"

                rule_log = TaxRule(
                    rule_code=f"RULE-BAND-{band.band_number}-{datetime.datetime.now().strftime('%y%m%d')}",
                    title=f"Mabadiliko ya Kiwango cha Kodi - {band.name}",
                    description=reason or "Marekebisho ya viwango kwa mujibu wa mwongozo wa TRA.",
                    previous_value=old_val,
                    current_value=new_val,
                    approved_by=session.get('username'),
                    status="APPROVED"
                )
                db.add(rule_log)
                db.commit()

                log_audit_event(
                    actor_username=session.get('username'),
                    action="TAX_RULE_UPDATED",
                    entity_type="TAX_BAND",
                    entity_id=str(band.id),
                    details=f"Band {band.band_number}: {old_val} -> {new_val}. Reason: {reason}"
                )
                flash(f"Kiwango cha {band.name} kimesasishwa kwa mafanikio.", "success")
                return redirect(url_for('admin.tax_rules'))

        bands = db.query(TaxBand).order_by(TaxBand.band_number.asc()).all()
        rules_history = db.query(TaxRule).order_by(TaxRule.effective_date.desc()).all()
        return render_template('admin/tax_rules.html', bands=bands, rules_history=rules_history)
    finally:
        db.close()

@admin_bp.route('/payments')
@login_required
@roles_required('super_admin', 'tra_admin', 'revenue_officer', 'auditor')
def payments():
    db = SessionLocal()
    try:
        payments_list = db.query(Payment).order_by(Payment.created_at.desc()).all()
        total_successful = sum(p.amount for p in payments_list if p.status == "SUCCESSFUL")
        return render_template('admin/payments.html', payments=payments_list, total_successful=total_successful)
    finally:
        db.close()

@admin_bp.route('/compliance')
@login_required
@roles_required('super_admin', 'tra_admin', 'revenue_officer', 'auditor')
def compliance():
    db = SessionLocal()
    try:
        # Smart compliance risk scoring
        taxpayers = db.query(Taxpayer).all()
        risk_traders = []
        for t in taxpayers:
            unpaid_assessments = [a for a in t.assessments if a.balance_due > 0]
            overdue_amount = sum(a.balance_due for a in unpaid_assessments)
            failed_payments = [p for p in t.payments if p.status == "FAILED"]

            risk_level = "LOW"
            if overdue_amount > 200000 or len(failed_payments) >= 3:
                risk_level = "HIGH"
            elif overdue_amount > 50000 or len(failed_payments) >= 1:
                risk_level = "MEDIUM"

            if overdue_amount > 0 or risk_level in ["MEDIUM", "HIGH"]:
                risk_traders.append({
                    "taxpayer": t,
                    "overdue_amount": overdue_amount,
                    "failed_count": len(failed_payments),
                    "risk_level": risk_level,
                    "recommended_action": "Kumbusho la SMS kupitia mfumo" if risk_level == "LOW" else "Kutembelewa na Afisa Kodi / Chama"
                })

        return render_template('admin/compliance.html', risk_traders=risk_traders)
    finally:
        db.close()

@admin_bp.route('/associations')
@login_required
@roles_required('super_admin', 'tra_admin')
def associations():
    db = SessionLocal()
    try:
        associations_list = db.query(Association).all()
        payouts_list = db.query(AssociationPayout).order_by(AssociationPayout.created_at.desc()).all()
        return render_template('admin/associations.html', associations=associations_list, payouts=payouts_list)
    finally:
        db.close()

@admin_bp.route('/payouts/<int:payout_id>/action', methods=['POST'])
@login_required
@roles_required('super_admin', 'tra_admin')
def payout_action(payout_id):
    db = SessionLocal()
    try:
        action = request.form.get('action') # APPROVE, WITHHOLD, REJECT
        payout = db.query(AssociationPayout).filter(AssociationPayout.id == payout_id).first()

        if payout:
            if action == 'APPROVE':
                payout.status = "Disbursed"
                payout.approved_by = session.get('username')
                payout.approved_at = datetime.datetime.utcnow()
                flash(f"Gawio la TZS {payout.amount:,.0f} kwa {payout.association.name} limethibitishwa na kutumwa.", "success")
            elif action == 'WITHHOLD':
                payout.status = "Withheld"
                flash(f"Gawio la {payout.association.name} limesimamishwa kwa uchunguzi.", "warning")
            elif action == 'REJECT':
                payout.status = "Rejected"
                flash(f"Ombi la gawio limekataliwa.", "danger")

            db.commit()
            log_audit_event(
                actor_username=session.get('username'),
                action=f"PAYOUT_{action}",
                entity_type="ASSOCIATION_PAYOUT",
                entity_id=str(payout.id),
                details=f"Amount: TZS {payout.amount:,.0f}, Status: {payout.status}"
            )
        return redirect(url_for('admin.associations'))
    finally:
        db.close()

@admin_bp.route('/complaints', methods=['GET', 'POST'])
@login_required
@roles_required('super_admin', 'tra_admin', 'revenue_officer')
def complaints():
    db = SessionLocal()
    try:
        if request.method == 'POST':
            complaint_id = int(request.form.get('complaint_id'))
            response_msg = request.form.get('response')
            new_status = request.form.get('status', 'Resolved')

            complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
            if complaint:
                complaint.status = new_status
                complaint.resolution_notes = response_msg
                complaint.assigned_officer = session.get('full_name')
                complaint.updated_at = datetime.datetime.utcnow()

                resp = ComplaintResponse(
                    complaint_id=complaint.id,
                    author_name=session.get('full_name', 'TRA Officer'),
                    author_role=session.get('user_role', 'Revenue Officer'),
                    message=response_msg
                )
                db.add(resp)
                db.commit()

                log_audit_event(
                    actor_username=session.get('username'),
                    action="COMPLAINT_RESOLVED",
                    entity_type="COMPLAINT",
                    entity_id=str(complaint.id),
                    details=f"Status: {new_status}, Response: {response_msg}"
                )
                flash(f"Tiketi {complaint.ticket_number} imesasishwa: {new_status}.", "success")
                return redirect(url_for('admin.complaints'))

        complaints_list = db.query(Complaint).order_by(Complaint.created_at.desc()).all()
        return render_template('admin/complaints.html', complaints=complaints_list)
    finally:
        db.close()

@admin_bp.route('/reports')
@login_required
@roles_required('super_admin', 'tra_admin', 'revenue_officer', 'auditor')
def reports():
    db = SessionLocal()
    try:
        export_format = request.args.get('format')
        report_type = request.args.get('type', 'collections')

        if export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)

            if report_type == 'collections':
                writer.writerow(['Tarehe', 'Control Number', 'Mlipaji', 'TIN', 'Kiasi (TZS)', 'Mtandao', 'Hali'])
                payments = db.query(Payment).all()
                for p in payments:
                    writer.writerow([
                        p.payment_date.strftime('%Y-%m-%d %H:%M') if p.payment_date else '',
                        p.control_number,
                        p.taxpayer.full_name if p.taxpayer else '',
                        p.taxpayer.tin if p.taxpayer else '',
                        p.amount,
                        p.provider.name if p.provider else '',
                        p.status
                    ])
                filename = f"TaxRahisi_Ripoti_Mapato_{datetime.date.today()}.csv"

            elif report_type == 'taxpayers':
                writer.writerow(['TIN', 'Jina Kamili', 'Simu', 'NIDA', 'Mkoa', 'Biashara', 'Hali ya Kodi'])
                taxpayers = db.query(Taxpayer).all()
                for t in taxpayers:
                    biz = t.businesses[0].name if t.businesses else ''
                    writer.writerow([t.tin, t.full_name, t.phone_number, t.nida_number, t.region.name if t.region else '', biz, t.compliance_status])
                filename = f"TaxRahisi_Ripoti_Walipakodi_{datetime.date.today()}.csv"

            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment;filename={filename}"}
            )

        return render_template('admin/reports.html')
    finally:
        db.close()

@admin_bp.route('/audit-logs')
@login_required
@roles_required('super_admin', 'tra_admin', 'auditor')
def audit_logs():
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
        return render_template('admin/audit_logs.html', logs=logs)
    finally:
        db.close()
