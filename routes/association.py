from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import datetime
from database import (
    SessionLocal, User, Association, AssociationMember, Taxpayer, Business, Payment,
    RevenueSharingCalculation, AssociationPayout, CommunityProject, TaxPeriod, AuditLog
)
from auth import login_required, roles_required, log_audit_event

association_bp = Blueprint('association', __name__, url_prefix='/association')

@association_bp.route('/dashboard')
@login_required
@roles_required('association_admin', 'super_admin', 'tra_admin')
def dashboard():
    db = SessionLocal()
    try:
        # Get current association
        user_id = session.get('user_id')
        user = db.query(User).filter(User.id == user_id).first()

        # If association_admin, match association; if super_admin, take first or requested
        assoc_id = request.args.get('id')
        if assoc_id:
            association = db.query(Association).filter(Association.id == int(assoc_id)).first()
        else:
            association = db.query(Association).first()

        if not association:
            flash("Chama hakikupatikana.", "warning")
            return redirect(url_for('public.index'))

        members = db.query(AssociationMember).filter(AssociationMember.association_id == association.id).all()
        member_taxpayer_ids = [m.taxpayer_id for m in members]

        # Calculate collections from members
        member_payments = db.query(Payment).filter(
            Payment.taxpayer_id.in_(member_taxpayer_ids),
            Payment.status == "SUCCESSFUL"
        ).all() if member_taxpayer_ids else []

        total_collected = sum(p.amount for p in member_payments)
        eligible_revenue_share = total_collected * (association.revenue_share_pct / 100.0)

        # Count compliance
        taxpayers = db.query(Taxpayer).filter(Taxpayer.id.in_(member_taxpayer_ids)).all() if member_taxpayer_ids else []
        compliant_count = sum(1 for t in taxpayers if t.compliance_status in ["COMPLIANT", "GRACE_PERIOD"])
        non_compliant_count = len(taxpayers) - compliant_count

        projects = db.query(CommunityProject).filter(CommunityProject.association_id == association.id).all()
        payouts = db.query(AssociationPayout).filter(AssociationPayout.association_id == association.id).all()

        return render_template('association/dashboard.html',
                               association=association,
                               members_count=len(members),
                               compliant_count=compliant_count,
                               non_compliant_count=non_compliant_count,
                               total_collected=total_collected,
                               eligible_revenue_share=eligible_revenue_share,
                               projects=projects,
                               payouts=payouts)
    finally:
        db.close()

@association_bp.route('/members')
@login_required
@roles_required('association_admin', 'super_admin', 'tra_admin')
def members():
    db = SessionLocal()
    try:
        association = db.query(Association).first()
        members_query = db.query(AssociationMember).filter(AssociationMember.association_id == association.id).all()

        # Build privacy-safe member list (no full NIDA revealed)
        members_list = []
        for m in members_query:
            t = m.taxpayer
            biz = t.businesses[0] if t.businesses else None
            members_list.append({
                "membership_number": m.membership_number,
                "full_name": t.full_name,
                "tin": t.tin,
                "phone": t.phone_number,
                "business_name": biz.name if biz else "-",
                "business_category": biz.category.name if biz and biz.category else "-",
                "compliance_status": t.compliance_status,
                "joined_date": m.joined_date
            })

        return render_template('association/members.html', association=association, members=members_list)
    finally:
        db.close()

@association_bp.route('/revenue-sharing', methods=['GET', 'POST'])
@login_required
@roles_required('association_admin', 'super_admin', 'tra_admin')
def revenue_sharing():
    db = SessionLocal()
    try:
        association = db.query(Association).first()
        members = db.query(AssociationMember).filter(AssociationMember.association_id == association.id).all()
        taxpayer_ids = [m.taxpayer_id for m in members]

        payments = db.query(Payment).filter(
            Payment.taxpayer_id.in_(taxpayer_ids),
            Payment.status == "SUCCESSFUL"
        ).all() if taxpayer_ids else []

        total_collected = sum(p.amount for p in payments)
        share_pct = association.revenue_share_pct
        calculated_share = total_collected * (share_pct / 100.0)

        payouts = db.query(AssociationPayout).filter(AssociationPayout.association_id == association.id).order_by(AssociationPayout.created_at.desc()).all()
        total_disbursed = sum(p.amount for p in payouts if p.status == "Disbursed")
        available_balance = max(0.0, calculated_share - total_disbursed)

        if request.method == 'POST':
            # Request payout
            requested_amount = float(request.form.get('amount', available_balance))
            bank_name = request.form.get('bank_name', association.bank_name or 'CRDB Bank')
            account_number = request.form.get('account_number', association.bank_account_number or '0150992817200')

            if requested_amount <= 0 or requested_amount > available_balance:
                flash(f"Kiasi kilichoombwa (TZS {requested_amount:,.0f}) kinazidi bakaa inayopatikana (TZS {available_balance:,.0f}).", "danger")
                return redirect(url_for('association.revenue_sharing'))

            payout_ref = f"PAYOUT-{datetime.datetime.now().strftime('%Y%m')}-{association.code}-{len(payouts)+1:02d}"
            payout = AssociationPayout(
                payout_reference=payout_ref,
                association_id=association.id,
                amount=requested_amount,
                bank_name=bank_name,
                account_number=account_number,
                status="Pending Approval"
            )
            db.add(payout)
            db.commit()

            log_audit_event(
                actor_username=session.get('username'),
                action="ASSOCIATION_PAYOUT_REQUESTED",
                entity_type="PAYOUT",
                entity_id=str(payout.id),
                details=f"Association: {association.name}, Amount: TZS {requested_amount:,.0f}, Ref: {payout_ref}"
            )

            flash(f"Ombi la malipo ya gawio (TZS {requested_amount:,.0f}) limewasilishwa kwa TRA kwa uhakiki. Namba ya kumbukumbu: {payout_ref}.", "success")
            return redirect(url_for('association.revenue_sharing'))

        return render_template('association/revenue_sharing.html',
                               association=association,
                               total_collected=total_collected,
                               share_pct=share_pct,
                               calculated_share=calculated_share,
                               total_disbursed=total_disbursed,
                               available_balance=available_balance,
                               payouts=payouts)
    finally:
        db.close()

@association_bp.route('/projects', methods=['GET', 'POST'])
@login_required
@roles_required('association_admin', 'super_admin', 'tra_admin')
def projects():
    db = SessionLocal()
    try:
        association = db.query(Association).first()

        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            budget = float(request.form.get('budget', 0))
            market_loc = request.form.get('market_location', association.name)

            proj = CommunityProject(
                association_id=association.id,
                title=title,
                description=description,
                budget=budget,
                approved_expenditure=0.0,
                status="Proposed",
                completion_percentage=0,
                market_location=market_loc
            )
            db.add(proj)
            db.commit()

            log_audit_event(
                actor_username=session.get('username'),
                action="COMMUNITY_PROJECT_CREATED",
                entity_type="PROJECT",
                entity_id=str(proj.id),
                details=f"Title: {title}, Budget: TZS {budget:,.0f}"
            )

            flash(f"Mradi wa jamii '{title}' umerekodiwa kwa mafanikio.", "success")
            return redirect(url_for('association.projects'))

        projects_list = db.query(CommunityProject).filter(CommunityProject.association_id == association.id).order_by(CommunityProject.created_at.desc()).all()
        return render_template('association/projects.html', association=association, projects=projects_list)
    finally:
        db.close()
