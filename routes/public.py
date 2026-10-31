from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
import io
from database import SessionLocal, User, Role, Taxpayer, Association, EducationalContent, Complaint, AuditLog, DigitalReceipt, Payment
from auth import verify_password, log_audit_event
from tax_engine import compute_presumptive_tax

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    db = SessionLocal()
    try:
        # Fetch real aggregated counts for transparent public reporting
        total_taxpayers = db.query(Taxpayer).count()
        total_associations = db.query(Association).filter(Association.status == "Active").count()
        educational_items = db.query(EducationalContent).filter(EducationalContent.is_active == True).limit(4).all()
        return render_template('public/index.html',
                               total_taxpayers=total_taxpayers,
                               total_associations=total_associations,
                               educational_items=educational_items)
    finally:
        db.close()

@public_bp.route('/about')
def about():
    return render_template('public/about.html')

@public_bp.route('/how-it-works')
def how_it_works():
    return render_template('public/how_it_works.html')

@public_bp.route('/ussd-simulator', endpoint='ussd_simulator')
@public_bp.route('/ussd', endpoint='ussd')
def ussd_simulator():
    return render_template('public/ussd_simulator.html')

@public_bp.route('/education')
def education():
    db = SessionLocal()
    try:
        contents = db.query(EducationalContent).filter(EducationalContent.is_active == True).all()
        return render_template('public/education.html', contents=contents)
    finally:
        db.close()

@public_bp.route('/education/download/<int:content_id>')
def download_guide(content_id):
    db = SessionLocal()
    try:
        content = db.query(EducationalContent).filter(EducationalContent.id == content_id).first()
        if not content:
            flash("Mwongozo haukupatikana.", "danger")
            return redirect(url_for('public.education'))
        
        # Generate plain text / markdown downloadable guide
        text_data = f"""================================================================================
MAMLAKA YA MAPATO TANZANIA (TRA) & TAXRAHISI
MWONGOZO WA ELIMU YA KODI KWA WAFANYABIASHARA WADOGO (SEKTA ISIYO RASMI)
================================================================================
Kichwa: {content.title}
Kitengo: {content.category}
Lugha: {content.language.upper()}
Imechapishwa na: {content.published_by}
Tarehe: {content.created_at.strftime('%d/%m/%Y')}
--------------------------------------------------------------------------------

MUHTASARI:
{content.summary}

MAELEZO KAMILI:
{content.content_body}

--------------------------------------------------------------------------------
Mfumo wa TaxRahisi — Kila mfanyabiashara ahesabiwe. Kila shilingi ikusanywe kwa haki.
Tovuti Rasmi: https://www.tra.go.tz | Dawati la Msaada: 0800 780 078 / 0800 110 016
================================================================================
"""
        mem = io.BytesIO()
        mem.write(text_data.encode('utf-8'))
        mem.seek(0)
        filename = f"TaxRahisi_Mwongozo_{content_id}.txt"
        return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/plain')
    finally:
        db.close()

@public_bp.route('/associations-programme', endpoint='associations_programme')
@public_bp.route('/associations', endpoint='associations')
def associations_programme():
    db = SessionLocal()
    try:
        associations = db.query(Association).filter(Association.status.in_(["Approved", "Active"])).all()
        return render_template('public/associations.html', associations=associations)
    finally:
        db.close()

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        category = request.form.get('category', 'General Inquiry')
        message = request.form.get('message')

        flash(f"Asante {full_name}. Ujumbe wako umepokelewa na kitengo cha huduma kwa wateja (TRA Call Centre). Tutawasiliana nawe kupitia {phone}.", "success")
        return redirect(url_for('public.contact'))
    return render_template('public/contact.html')

@public_bp.route('/verify', methods=['GET', 'POST'], endpoint='quick_verify')
@public_bp.route('/verify', methods=['GET', 'POST'], endpoint='verify')
def quick_verify():
    search_query = request.args.get('q', '').strip()
    result = None
    if search_query:
        db = SessionLocal()
        try:
            # Check if TIN or receipt
            receipt = db.query(DigitalReceipt).filter(
                (DigitalReceipt.receipt_number == search_query) |
                (DigitalReceipt.control_number == search_query) |
                (DigitalReceipt.verification_hash == search_query)
            ).first()

            taxpayer = None
            if not receipt:
                taxpayer = db.query(Taxpayer).filter(
                    (Taxpayer.tin == search_query) |
                    (Taxpayer.phone_number == search_query) |
                    (Taxpayer.registration_reference == search_query)
                ).first()

            result = {"receipt": receipt, "taxpayer": taxpayer, "searched": True}
        finally:
            db.close()
    return render_template('public/verify.html', result=result, query=search_query)

@public_bp.route('/calculator', methods=['GET'], endpoint='tax_calculator')
@public_bp.route('/calculator', methods=['GET'], endpoint='calculator')
def tax_calculator():
    turnover = float(request.args.get('turnover', 6500000))
    has_records = request.args.get('records', '0') == '1'
    calc_res = compute_presumptive_tax(turnover, has_records)
    return render_template('public/calculator.html', calc=calc_res)

@public_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect_by_role(session.get('user_role'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()

        db = SessionLocal()
        try:
            # Search user by phone, email, or username
            user = db.query(User).filter(
                (User.phone_number == identifier) |
                (User.email == identifier) |
                (User.username == identifier)
            ).first()

            if user and verify_password(password, user.password_hash):
                if not user.is_active:
                    flash("Akaunti yako imesimamishwa. Tafadhali wasiliana na TRA.", "danger")
                    return render_template('public/login.html')

                session['user_id'] = user.id
                session['username'] = user.username
                session['full_name'] = user.full_name
                session['user_role'] = user.role.name

                log_audit_event(
                    actor_username=user.username,
                    action="USER_LOGIN_SUCCESS",
                    entity_type="AUTH",
                    entity_id=str(user.id),
                    details=f"Role: {user.role.name}"
                )

                flash(f"Karibu, {user.full_name}!", "success")
                return redirect_by_role(user.role.name)
            else:
                log_audit_event(
                    actor_username=identifier,
                    action="USER_LOGIN_FAILED",
                    entity_type="AUTH",
                    details="Invalid credentials provided."
                )
                flash("Nambari ya simu au neno la siri si sahihi. Jaribu tena.", "danger")
        finally:
            db.close()

    return render_template('public/login.html')

@public_bp.route('/logout')
def logout():
    log_audit_event(
        actor_username=session.get('username', 'anonymous'),
        action="USER_LOGOUT",
        entity_type="AUTH",
        entity_id=str(session.get('user_id'))
    )
    session.clear()
    flash("Umetoka kwenye mfumo kwa usalama.", "info")
    return redirect(url_for('public.index'))

def redirect_by_role(role_name):
    if role_name in ['super_admin', 'tra_admin', 'revenue_officer', 'auditor']:
        return redirect(url_for('admin.dashboard'))
    elif role_name == 'association_admin':
        return redirect(url_for('association.dashboard'))
    elif role_name == 'association_agent':
        return redirect(url_for('agent.dashboard'))
    elif role_name == 'taxpayer':
        return redirect(url_for('taxpayer.dashboard'))
    return redirect(url_for('public.index'))
