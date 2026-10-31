from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import datetime
from database import (
    SessionLocal, User, Role, Taxpayer, Business, BusinessCategory, Region, District, Ward, Market,
    Association, AssociationMember, TaxAssessment, TaxPeriod, TaxBand, Payment, PaymentProvider,
    DigitalReceipt, Complaint, ComplaintResponse, GracePeriod, Registration, AuditLog
)
from auth import login_required, roles_required, hash_password, log_audit_event
from tax_engine import (
    compute_presumptive_tax, generate_gepg_control_number, generate_tin,
    generate_registration_reference, generate_receipt_number, generate_verification_hash,
    validate_nida_format
)

taxpayer_bp = Blueprint('taxpayer', __name__, url_prefix='/portal')

@taxpayer_bp.route('/register', methods=['GET', 'POST'])
def register():
    db = SessionLocal()
    try:
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            nida_number = request.form.get('nida_number', '').strip()
            password = request.form.get('password', '').strip()
            region_id = int(request.form.get('region_id', 1))
            district_id = int(request.form.get('district_id', 1))
            market_id = int(request.form.get('market_id', 1))
            business_name = request.form.get('business_name', '').strip()
            category_id = int(request.form.get('category_id', 1))
            association_id = int(request.form.get('association_id', 1))
            turnover = float(request.form.get('turnover', 6500000))
            has_records = request.form.get('has_records') == 'on'

            # Validations
            if not validate_nida_format(nida_number):
                flash("Nambari ya NIDA si sahihi. Tafadhali weka tarakimu 20 sahihi.", "danger")
                return redirect(url_for('taxpayer.register'))

            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.phone_number == phone_number) | (User.username == phone_number)
            ).first()
            if existing_user:
                flash(f"Nambari ya simu {phone_number} tayari imesajiliwa. Tafadhali ingia kwenye mfumo.", "warning")
                return redirect(url_for('public.login'))

            existing_taxpayer = db.query(Taxpayer).filter(Taxpayer.nida_number == nida_number).first()
            if existing_taxpayer:
                flash(f"Nambari hii ya NIDA tayari imesajiliwa na TIN: {existing_taxpayer.tin}.", "warning")
                return redirect(url_for('public.login'))

            # 1. Create User Account
            taxpayer_role = db.query(Role).filter(Role.name == "taxpayer").first()
            user = User(
                username=phone_number,
                phone_number=phone_number,
                full_name=full_name,
                password_hash=hash_password(password or "Tax@2026"),
                role_id=taxpayer_role.id,
                is_active=True
            )
            db.add(user)
            db.flush()

            # 2. Create Taxpayer Profile & Issue TIN
            tin = generate_tin()
            reg_ref = generate_registration_reference()
            taxpayer = Taxpayer(
                user_id=user.id,
                tin=tin,
                registration_reference=reg_ref,
                nida_number=nida_number,
                full_name=full_name,
                phone_number=phone_number,
                region_id=region_id,
                district_id=district_id,
                compliance_status="GRACE_PERIOD",
                photo_path="images/mama_neema.jpg"
            )
            db.add(taxpayer)
            db.flush()

            # 3. Create Business Profile
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

            # 4. Link to Market Association
            assoc_member = AssociationMember(
                association_id=association_id,
                taxpayer_id=taxpayer.id,
                membership_number=f"MEM-{association_id}-{taxpayer.id:04d}",
                is_active=True
            )
            db.add(assoc_member)

            # 5. Create Registration Audit Record
            registration_record = Registration(
                registration_reference=reg_ref,
                taxpayer_id=taxpayer.id,
                channel="WEB",
                phone_number=phone_number,
                nida_number=nida_number,
                status="Approved",
                approved_at=datetime.datetime.utcnow()
            )
            db.add(registration_record)

            # 6. Compute & Assign Initial Cap 332 Presumptive Tax Assessment
            calc = compute_presumptive_tax(turnover, has_records)
            current_period = db.query(TaxPeriod).filter(TaxPeriod.is_active == True).first()
            if not current_period:
                current_period = TaxPeriod(
                    year=2026,
                    quarter=1,
                    name="Mwaka wa Fedha 2026 - Robo 1",
                    start_date=datetime.datetime(2026, 1, 1),
                    end_date=datetime.datetime(2026, 3, 31)
                )
                db.add(current_period)
                db.flush()

            band = db.query(TaxBand).filter(TaxBand.band_number == calc['band_number']).first()
            if not band:
                band = db.query(TaxBand).first()

            assessment = TaxAssessment(
                assessment_number=f"ASM-2026-{taxpayer.id:04d}",
                taxpayer_id=taxpayer.id,
                business_id=business.id,
                period_id=current_period.id,
                band_id=band.id if band else 1,
                assessed_turnover=turnover,
                total_tax_liability=calc['annual_tax'],
                amount_paid=0.0,
                balance_due=calc['annual_tax'],
                status="ACTIVE",
                explanation=calc['explanation']
            )
            db.add(assessment)

            # 7. Grant 12-Month First-Time Business Grace Period
            grace = GracePeriod(
                taxpayer_id=taxpayer.id,
                duration_months=12,
                start_date=datetime.datetime.utcnow(),
                end_date=datetime.datetime.utcnow() + datetime.timedelta(days=365),
                is_active=True,
                penalty_relief_granted=True,
                notes="Msamaha wa adhabu kwa mlipakodi mpya wa sekta isiyo rasmi (Mwezi 1-12)."
            )
            db.add(grace)

            db.commit()

            # Automatically authenticate newly registered user
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['user_role'] = "taxpayer"

            log_audit_event(
                actor_username=user.username,
                action="TAXPAYER_SELF_REGISTERED",
                entity_type="TAXPAYER",
                entity_id=str(taxpayer.id),
                details=f"TIN: {tin}, Ref: {reg_ref}, Association: {association_id}"
            )

            flash(f"Hongera sana {full_name}! Usajili wako umekamilika. TIN yako ni: {tin}.", "success")
            return redirect(url_for('taxpayer.dashboard'))

        # GET request - load dropdown reference data
        regions = db.query(Region).all()
        districts = db.query(District).all()
        markets = db.query(Market).all()
        categories = db.query(BusinessCategory).all()
        associations = db.query(Association).filter(Association.status.in_(["Approved", "Active"])).all()

        return render_template('taxpayer/register.html',
                               regions=regions,
                               districts=districts,
                               markets=markets,
                               categories=categories,
                               associations=associations)
    finally:
        db.close()

@taxpayer_bp.route('/dashboard')
@login_required
@roles_required('taxpayer')
def dashboard():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        taxpayer = db.query(Taxpayer).filter(Taxpayer.user_id == user_id).first()
        if not taxpayer:
            flash("Wasifu wa mlipakodi haukupatikana.", "danger")
            return redirect(url_for('public.index'))

        assessments = db.query(TaxAssessment).filter(TaxAssessment.taxpayer_id == taxpayer.id).all()
        payments = db.query(Payment).filter(Payment.taxpayer_id == taxpayer.id).order_by(Payment.created_at.desc()).all()
        grace_period = db.query(GracePeriod).filter(GracePeriod.taxpayer_id == taxpayer.id, GracePeriod.is_active == True).first()

        total_assessed = sum(a.total_tax_liability for a in assessments)
        total_paid = sum(p.amount for p in payments if p.status == "SUCCESSFUL")
        balance_due = max(0.0, total_assessed - total_paid)

        # Update compliance status
        if total_assessed == 0 or total_paid >= total_assessed:
            taxpayer.compliance_status = "COMPLIANT"
        elif grace_period and grace_period.is_active:
            taxpayer.compliance_status = "GRACE_PERIOD"
        elif total_paid > 0:
            taxpayer.compliance_status = "PARTIAL"
        else:
            taxpayer.compliance_status = "NON_COMPLIANT"
        db.commit()

        return render_template('taxpayer/dashboard.html',
                               taxpayer=taxpayer,
                               assessments=assessments,
                               payments=payments,
                               grace_period=grace_period,
                               total_assessed=total_assessed,
                               total_paid=total_paid,
                               balance_due=balance_due)
    finally:
        db.close()

@taxpayer_bp.route('/assessment', methods=['GET', 'POST'])
@login_required
@roles_required('taxpayer')
def assessment():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        taxpayer = db.query(Taxpayer).filter(Taxpayer.user_id == user_id).first()
        assessment = db.query(TaxAssessment).filter(TaxAssessment.taxpayer_id == taxpayer.id).order_by(TaxAssessment.created_at.desc()).first()

        if request.method == 'POST':
            # Taxpayer requesting reassessment
            reason = request.form.get('reason')
            revised_turnover = float(request.form.get('revised_turnover', 0))

            complaint = Complaint(
                ticket_number=f"TKT-ASM-{datetime.datetime.now().strftime('%Y%m')}-{taxpayer.id:04d}",
                taxpayer_id=taxpayer.id,
                category="Incorrect Assessment",
                description=f"Ombi la kurudiwa kwa makadirio. Mauzo yaliyopendekezwa: TZS {revised_turnover:,.0f}. Sababu: {reason}",
                status="Submitted"
            )
            db.add(complaint)
            db.commit()

            log_audit_event(
                actor_username=session.get('username'),
                action="REASSESSMENT_REQUESTED",
                entity_type="ASSESSMENT",
                entity_id=str(assessment.id if assessment else 0),
                details=f"Ticket: {complaint.ticket_number}"
            )

            flash(f"Ombi lako la kurudia tathmini limepokelewa. Nambari ya Tiketi: {complaint.ticket_number}.", "success")
            return redirect(url_for('taxpayer.complaints'))

        bands = db.query(TaxBand).order_by(TaxBand.band_number.asc()).all()
        return render_template('taxpayer/assessment.html', taxpayer=taxpayer, assessment=assessment, bands=bands)
    finally:
        db.close()

@taxpayer_bp.route('/payments', methods=['GET', 'POST'])
@login_required
@roles_required('taxpayer')
def payments():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        taxpayer = db.query(Taxpayer).filter(Taxpayer.user_id == user_id).first()
        assessment = db.query(TaxAssessment).filter(TaxAssessment.taxpayer_id == taxpayer.id).order_by(TaxAssessment.created_at.desc()).first()
        providers = db.query(PaymentProvider).filter(PaymentProvider.is_active == True).all()

        if request.method == 'POST':
            amount = float(request.form.get('amount', 25000))
            provider_id = int(request.form.get('provider_id', 1))
            installment_type = request.form.get('installment_type', 'Quarterly')
            payer_phone = request.form.get('payer_phone', taxpayer.phone_number)

            ctrl_no = generate_gepg_control_number()
            trx_ref = f"TRX-TZ-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-{taxpayer.id}"

            # Create Payment Record
            payment = Payment(
                control_number=ctrl_no,
                taxpayer_id=taxpayer.id,
                assessment_id=assessment.id if assessment else None,
                provider_id=provider_id,
                amount=amount,
                installment_type=installment_type,
                transaction_reference=trx_ref,
                status="SUCCESSFUL", # Simulated successful transaction
                payment_date=datetime.datetime.utcnow(),
                payer_phone=payer_phone
            )
            db.add(payment)
            db.flush()

            # Update assessment balance
            if assessment:
                assessment.amount_paid += amount
                assessment.balance_due = max(0.0, assessment.total_tax_liability - assessment.amount_paid)

            # Generate Digital Receipt
            receipt_no = generate_receipt_number()
            verif_hash = generate_verification_hash(trx_ref, taxpayer.tin, amount)
            receipt = DigitalReceipt(
                receipt_number=receipt_no,
                payment_id=payment.id,
                verification_hash=verif_hash,
                taxpayer_name=taxpayer.full_name,
                taxpayer_tin=taxpayer.tin,
                amount_paid=amount,
                control_number=ctrl_no
            )
            db.add(receipt)
            db.commit()

            log_audit_event(
                actor_username=session.get('username'),
                action="PAYMENT_PROCESSED_SUCCESS",
                entity_type="PAYMENT",
                entity_id=str(payment.id),
                details=f"Amount: TZS {amount:,.0f}, Control: {ctrl_no}, Receipt: {receipt_no}"
            )

            flash(f"Malipo ya TZS {amount:,.0f} yamekamilika kwa mafanikio! Risiti Namba: {receipt_no}.", "success")
            return redirect(url_for('taxpayer.receipt_detail', receipt_id=receipt.id))

        payments_list = db.query(Payment).filter(Payment.taxpayer_id == taxpayer.id).order_by(Payment.created_at.desc()).all()
        return render_template('taxpayer/payments.html',
                               taxpayer=taxpayer,
                               assessment=assessment,
                               providers=providers,
                               payments=payments_list,
                               default_control=generate_gepg_control_number())
    finally:
        db.close()

@taxpayer_bp.route('/receipts')
@login_required
@roles_required('taxpayer')
def receipts():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        taxpayer = db.query(Taxpayer).filter(Taxpayer.user_id == user_id).first()
        receipts_list = db.query(DigitalReceipt).join(Payment).filter(Payment.taxpayer_id == taxpayer.id).order_by(DigitalReceipt.issued_at.desc()).all()
        return render_template('taxpayer/receipts.html', taxpayer=taxpayer, receipts=receipts_list)
    finally:
        db.close()

@taxpayer_bp.route('/receipts/<int:receipt_id>')
@login_required
def receipt_detail(receipt_id):
    db = SessionLocal()
    try:
        receipt = db.query(DigitalReceipt).filter(DigitalReceipt.id == receipt_id).first()
        if not receipt:
            flash("Risiti haikupatikana.", "danger")
            return redirect(url_for('taxpayer.receipts'))

        # Security check: Taxpayers can only see their own receipts
        if session.get('user_role') == 'taxpayer':
            taxpayer = db.query(Taxpayer).filter(Taxpayer.user_id == session.get('user_id')).first()
            if receipt.payment.taxpayer_id != taxpayer.id:
                flash("Huna ruhusa ya kuona risiti hii.", "danger")
                return redirect(url_for('taxpayer.dashboard'))

        return render_template('taxpayer/receipt_detail.html', receipt=receipt)
    finally:
        db.close()

@taxpayer_bp.route('/complaints', methods=['GET', 'POST'])
@login_required
@roles_required('taxpayer')
def complaints():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        taxpayer = db.query(Taxpayer).filter(Taxpayer.user_id == user_id).first()

        if request.method == 'POST':
            category = request.form.get('category')
            description = request.form.get('description')
            ticket = f"TKT-{datetime.datetime.now().strftime('%Y%m')}-{taxpayer.id:04d}-{random_digits(3)}"

            complaint = Complaint(
                ticket_number=ticket,
                taxpayer_id=taxpayer.id,
                category=category,
                description=description,
                status="Submitted"
            )
            db.add(complaint)
            db.commit()

            log_audit_event(
                actor_username=session.get('username'),
                action="COMPLAINT_SUBMITTED",
                entity_type="COMPLAINT",
                entity_id=str(complaint.id),
                details=f"Category: {category}, Ticket: {ticket}"
            )

            flash(f"Malalamiko yako yamewasilishwa. Namba ya kumbukumbu: {ticket}.", "success")
            return redirect(url_for('taxpayer.complaints'))

        complaints_list = db.query(Complaint).filter(Complaint.taxpayer_id == taxpayer.id).order_by(Complaint.created_at.desc()).all()
        return render_template('taxpayer/complaints.html', taxpayer=taxpayer, complaints=complaints_list)
    finally:
        db.close()

@taxpayer_bp.route('/compliance')
@login_required
@roles_required('taxpayer')
def compliance():
    db = SessionLocal()
    try:
        user_id = session.get('user_id')
        taxpayer = db.query(Taxpayer).filter(Taxpayer.user_id == user_id).first()
        grace_period = db.query(GracePeriod).filter(GracePeriod.taxpayer_id == taxpayer.id, GracePeriod.is_active == True).first()
        payments = db.query(Payment).filter(Payment.taxpayer_id == taxpayer.id, Payment.status == "SUCCESSFUL").all()
        return render_template('taxpayer/compliance.html', taxpayer=taxpayer, grace=grace_period, payments=payments)
    finally:
        db.close()

def random_digits(n):
    import random
    return "".join(str(random.randint(0, 9)) for _ in range(n))
