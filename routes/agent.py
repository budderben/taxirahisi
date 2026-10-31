from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import datetime
from database import (
    SessionLocal, User, Role, Taxpayer, Business, BusinessCategory, Region, District, Market,
    Association, AssociationMember, AssociationAgent, Registration, TaxAssessment, TaxPeriod,
    TaxBand, GracePeriod, AuditLog
)
from auth import login_required, roles_required, hash_password, log_audit_event
from tax_engine import (
    compute_presumptive_tax, generate_tin, generate_registration_reference, validate_nida_format
)

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

@agent_bp.route('/dashboard')
@login_required
@roles_required('association_agent', 'super_admin', 'tra_admin')
def dashboard():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        agent = db.query(AssociationAgent).filter(AssociationAgent.user_id == user_id).first()
        if not agent:
            # Fallback for admin previewing
            agent = db.query(AssociationAgent).first()

        assisted_regs = db.query(Registration).filter(Registration.assisted_by_agent_id == agent.id).all() if agent else []
        success_count = sum(1 for r in assisted_regs if r.status == "Approved")
        pending_count = sum(1 for r in assisted_regs if r.status == "Pending Verification")

        return render_template('agent/dashboard.html',
                               agent=agent,
                               total_assisted=len(assisted_regs),
                               success_count=success_count,
                               pending_count=pending_count,
                               recent_registrations=assisted_regs[-5:])
    finally:
        db.close()

@agent_bp.route('/onboard', methods=['GET', 'POST'])
@login_required
@roles_required('association_agent', 'super_admin', 'tra_admin')
def onboard():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        agent = db.query(AssociationAgent).filter(AssociationAgent.user_id == user_id).first()
        if not agent:
            agent = db.query(AssociationAgent).first()

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            nida_number = request.form.get('nida_number', '').strip()
            business_name = request.form.get('business_name', '').strip()
            category_id = int(request.form.get('category_id', 1))
            market_id = int(request.form.get('market_id', agent.assigned_market_id if agent and agent.assigned_market_id else 1))
            turnover = float(request.form.get('turnover', 6500000))
            has_records = request.form.get('has_records') == 'on'

            if not validate_nida_format(nida_number):
                flash("NIDA namba si sahihi (inahitaji tarakimu 20).", "danger")
                return redirect(url_for('agent.onboard'))

            existing_taxpayer = db.query(Taxpayer).filter(Taxpayer.nida_number == nida_number).first()
            if existing_taxpayer:
                flash(f"Mlipakodi huyu tayari amesajiliwa na TIN: {existing_taxpayer.tin}.", "warning")
                return redirect(url_for('agent.dashboard'))

            # 1. Create Taxpayer User
            taxpayer_role = db.query(Role).filter(Role.name == "taxpayer").first()
            user = User(
                username=phone_number,
                phone_number=phone_number,
                full_name=full_name,
                password_hash=hash_password("Tax@2026"),
                role_id=taxpayer_role.id,
                is_active=True
            )
            db.add(user)
            db.flush()

            # 2. Taxpayer Record
            tin = generate_tin()
            reg_ref = generate_registration_reference()
            taxpayer = Taxpayer(
                user_id=user.id,
                tin=tin,
                registration_reference=reg_ref,
                nida_number=nida_number,
                full_name=full_name,
                phone_number=phone_number,
                region_id=agent.association.region_id if agent else 1,
                district_id=agent.association.district_id if agent else 1,
                compliance_status="GRACE_PERIOD"
            )
            db.add(taxpayer)
            db.flush()

            # 3. Business
            business = Business(
                taxpayer_id=taxpayer.id,
                name=business_name or f"Biashara ya {full_name}",
                category_id=category_id,
                market_id=market_id,
                estimated_annual_turnover=turnover,
                has_accounting_records=has_records,
                status="ACTIVE"
            )
            db.add(business)
            db.flush()

            # 4. Association Membership
            member = AssociationMember(
                association_id=agent.association_id if agent else 1,
                taxpayer_id=taxpayer.id,
                membership_number=f"MEM-{agent.association.code if agent else 'VIB'}-{taxpayer.id:04d}",
                is_active=True
            )
            db.add(member)

            # 5. Registration Record with Agent ID
            reg = Registration(
                registration_reference=reg_ref,
                taxpayer_id=taxpayer.id,
                assisted_by_agent_id=agent.id if agent else None,
                channel="AGENT",
                phone_number=phone_number,
                nida_number=nida_number,
                status="Approved",
                approved_at=datetime.datetime.utcnow()
            )
            db.add(reg)

            # 6. Presumptive Assessment & Grace Period
            calc = compute_presumptive_tax(turnover, has_records)
            period = db.query(TaxPeriod).filter(TaxPeriod.is_active == True).first()
            band = db.query(TaxBand).filter(TaxBand.band_number == calc['band_number']).first()
            assessment = TaxAssessment(
                assessment_number=f"ASM-2026-{taxpayer.id:04d}",
                taxpayer_id=taxpayer.id,
                business_id=business.id,
                period_id=period.id if period else 1,
                band_id=band.id if band else 1,
                assessed_turnover=turnover,
                total_tax_liability=calc['annual_tax'],
                amount_paid=0.0,
                balance_due=calc['annual_tax'],
                status="ACTIVE",
                explanation=calc['explanation']
            )
            db.add(assessment)

            grace = GracePeriod(
                taxpayer_id=taxpayer.id,
                duration_months=12,
                start_date=datetime.datetime.utcnow(),
                end_date=datetime.datetime.utcnow() + datetime.timedelta(days=365),
                is_active=True,
                penalty_relief_granted=True
            )
            db.add(grace)

            db.commit()

            log_audit_event(
                actor_username=session.get('username'),
                action="AGENT_ONBOARDED_TAXPAYER",
                entity_type="REGISTRATION",
                entity_id=str(reg.id),
                details=f"Agent: {agent.agent_code if agent else 'N/A'}, Taxpayer: {full_name}, TIN: {tin}"
            )

            flash(f"Umefanikiwa kumsajili {full_name}! TIN iliyotolewa ni: {tin}.", "success")
            return redirect(url_for('agent.dashboard'))

        categories = db.query(BusinessCategory).all()
        markets = db.query(Market).all()
        return render_template('agent/onboard.html', agent=agent, categories=categories, markets=markets)
    finally:
        db.close()
