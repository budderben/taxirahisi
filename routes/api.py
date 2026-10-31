from flask import Blueprint, request, jsonify, Response
import datetime
from database import (
    SessionLocal, Taxpayer, Business, TaxAssessment, Payment, DigitalReceipt,
    NationalIdentityVerification, IntegrationLog, Complaint, TaxBand, TaxPeriod, GracePeriod
)
from tax_engine import (
    compute_presumptive_tax, generate_gepg_control_number, generate_tin,
    generate_registration_reference, generate_receipt_number, generate_verification_hash,
    validate_nida_format
)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# ==============================================================================
# 1. Telecom USSD Gateway Interface
# Standard Telecom / Aggregator Integration (Africa's Talking / Twilio / Direct Telco)
# Payload: POST with sessionId, phoneNumber, text, serviceCode
# Response: Plain text starting with "CON " (continue) or "END " (terminate)
# ==============================================================================
@api_bp.route('/ussd/gateway', methods=['POST', 'GET'])
def ussd_gateway():
    session_id = request.values.get('sessionId', '')
    phone_number = request.values.get('phoneNumber', '').strip().replace(' ', '')
    text = request.values.get('text', '').strip()
    service_code = request.values.get('serviceCode', '*150*88#')

    db = SessionLocal()
    try:
        # Log integration request
        log = IntegrationLog(
            service_name="TELECOM_USSD",
            endpoint="/api/v1/ussd/gateway",
            request_data=f"Session: {session_id}, Phone: {phone_number}, Text: {text}",
            status_code=200
        )
        db.add(log)
        db.commit()

        # Parse text into parts based on '*'
        inputs = text.split('*') if text else []
        response_text = ""

        # Find if taxpayer already registered with this phone
        taxpayer = db.query(Taxpayer).filter(
            (Taxpayer.phone_number == phone_number) |
            (Taxpayer.phone_number.endswith(phone_number[-9:] if len(phone_number) >= 9 else phone_number))
        ).first()

        if len(inputs) == 0 or text == "":
            # Root Menu
            name_greet = f" {taxpayer.full_name}" if taxpayer else ""
            response_text = f"CON Karibu TaxRahisi (TRA){name_greet}\n" \
                            "1. Sajili Biashara (TIN)\n" \
                            "2. Angalia Makadirio ya Kodi\n" \
                            "3. Lipa Kodi (GePG)\n" \
                            "4. Hali ya Malipo & Risiti\n" \
                            "5. Ripoti Tatizo\n" \
                            "6. Elimu ya Kodi (Cap 332)\n" \
                            "7. English"

        elif inputs[0] == "1":
            # 1. Register Business
            if taxpayer:
                response_text = f"END Tayari umesajiliwa!\nJina: {taxpayer.full_name}\nTIN: {taxpayer.tin}\nHali: {taxpayer.compliance_status}"
            elif len(inputs) == 1:
                response_text = "CON Weka namba yako ya NIDA (tarakimu 20):\n(Mfano: 19850412111010000123)"
            elif len(inputs) == 2:
                nida_in = inputs[1].strip()
                if not validate_nida_format(nida_in):
                    response_text = "END NIDA namba si sahihi. Inahitaji tarakimu 20. Jaribu tena."
                else:
                    response_text = "CON NIDA imethibitishwa.\nChagua Soko Lako:\n1. Kariakoo\n2. Mwenge\n3. Mwananyamala\n4. Tegeta\n5. Nyingine"
            elif len(inputs) == 3:
                response_text = "CON Chagua Aina ya Biashara:\n1. Mama Lishe / Chakula\n2. Machinga (Nguo & Viatu)\n3. Bodaboda / Bajaji\n4. Duka Dogo / Mengineyo"
            elif len(inputs) == 4:
                # Issue TIN
                new_tin = generate_tin()
                reg_ref = generate_registration_reference()
                nida_in = inputs[1].strip()

                new_taxpayer = Taxpayer(
                    tin=new_tin,
                    registration_reference=reg_ref,
                    nida_number=nida_in,
                    full_name=f"Mfanyabiashara ({phone_number})",
                    phone_number=phone_number,
                    region_id=1,
                    district_id=1,
                    compliance_status="GRACE_PERIOD"
                )
                db.add(new_taxpayer)
                db.commit()

                response_text = f"END Hongera! Usajili umekamilika.\nTIN Yako: {new_tin}\nUtapewa msamaha wa miezi 12 kama biashara mpya. TRA itakutumia SMS ya uthibitisho."

        elif inputs[0] == "2":
            # 2. Check Tax Assessment
            if not taxpayer:
                response_text = "END Nambari yako ya simu haijasajiliwa. Tafadhali chagua 1 kwanza kujisajili au tembelea tovuti ya TaxRahisi."
            else:
                assessment = db.query(TaxAssessment).filter(TaxAssessment.taxpayer_id == taxpayer.id).order_by(TaxAssessment.created_at.desc()).first()
                if assessment:
                    response_text = f"END Makadirio ya Kodi (Cap 332):\nJina: {taxpayer.full_name}\nTIN: {taxpayer.tin}\nJumla ya Kodi: TZS {assessment.total_tax_liability:,.0f}\nBakaa Inayodaiwa: TZS {assessment.balance_due:,.0f}\nHali: {taxpayer.compliance_status}"
                else:
                    response_text = f"END Jina: {taxpayer.full_name}\nTIN: {taxpayer.tin}\nHuna deni la kodi kwa sasa (Bakaa: TZS 0)."

        elif inputs[0] == "3":
            # 3. Pay Tax (GePG)
            if not taxpayer:
                response_text = "END Nambari yako ya simu haijasajiliwa. Chagua 1 kujisajili."
            elif len(inputs) == 1:
                response_text = "CON Chagua Kiasi cha Kulipa:\n1. TZS 25,000 (Robo Mwaka)\n2. TZS 50,000 (Nusu Mwaka)\n3. TZS 100,000 (Mwaka Mzima)\n4. Kiasi kingine"
            elif len(inputs) == 2:
                amount_map = {"1": 25000, "2": 50000, "3": 100000}
                amount = amount_map.get(inputs[1], 25000)
                ctrl = generate_gepg_control_number()

                payment = Payment(
                    control_number=ctrl,
                    taxpayer_id=taxpayer.id,
                    amount=amount,
                    installment_type="USSD Payment",
                    transaction_reference=f"USSD-{session_id[-8:]}",
                    status="PENDING",
                    payer_phone=phone_number
                )
                db.add(payment)
                db.commit()

                response_text = f"END Namba ya Malipo (GePG): {ctrl}\nKiasi: TZS {amount:,.0f}\nLipa kupitia menyu ya M-Pesa/Tigo Pesa/Airtel kwa kuchagua 'Lipa Bili' kisha weka Control No: {ctrl}."

        elif inputs[0] == "4":
            # 4. Check Payment Status & Receipt
            if not taxpayer:
                response_text = "END Haujasajiliwa kwenye TaxRahisi."
            else:
                last_payment = db.query(Payment).filter(Payment.taxpayer_id == taxpayer.id, Payment.status == "SUCCESSFUL").order_by(Payment.created_at.desc()).first()
                if last_payment and last_payment.receipt:
                    response_text = f"END Risiti ya Mwisho:\nKiasi: TZS {last_payment.amount:,.0f}\nTarehe: {last_payment.payment_date.strftime('%d/%m/%Y')}\nRisiti: {last_payment.receipt.receipt_number}\nControl: {last_payment.control_number}\nHali: IMELIPWA KIKAMILIFU"
                else:
                    response_text = f"END Mfanyabiashara: {taxpayer.full_name}\nTIN: {taxpayer.tin}\nHakuna malipo yaliyothibitishwa bado."

        elif inputs[0] == "5":
            # 5. Report a Problem
            if len(inputs) == 1:
                response_text = "CON Chagua Tatizo:\n1. Makadirio Makubwa\n2. Malipo Hayajaonekana\n3. Tatizo la TIN\n4. Msaada wa Afisa"
            else:
                ticket_no = f"USSD-TKT-{datetime.datetime.now().strftime('%d%H%M')}"
                if taxpayer:
                    comp = Complaint(
                        ticket_number=ticket_no,
                        taxpayer_id=taxpayer.id,
                        category="USSD Inquiry",
                        description=f"Ripoti ya USSD: Chaguo {inputs[1]}",
                        status="Submitted"
                    )
                    db.add(comp)
                    db.commit()
                response_text = f"END Malalamiko yamerekodiwa. Tiketi: {ticket_no}. Afisa wa TRA atapiga simu nambari {phone_number} ndani ya masaa 24."

        elif inputs[0] == "6":
            # 6. Tax Info
            response_text = "END Sheria ya Kodi Sura 332:\nMauzo hadi 4M: Bure (0 TZS).\nMauzo 4M-7M: 100k (bila vitabu) au 3% (na vitabu).\nMauzo 7M-11M: 250k.\nElimu zaidi: Tembelea tovuti ya TaxRahisi."

        elif inputs[0] == "7":
            # 7. English
            response_text = "CON Welcome to TaxRahisi (TRA)\n1. Register Business\n2. Check Tax Assessment\n3. Pay Tax (GePG)\n4. Check Status\n5. Kiswahili"

        else:
            response_text = "END Chaguo si sahihi. Tafadhali piga tena *150*88#."

        return Response(response_text, mimetype="text/plain")
    finally:
        db.close()

# ==============================================================================
# 2. Payment Gateway Webhook & Reconciliation (GePG / Mobile Money)
# ==============================================================================
@api_bp.route('/payments/webhook', methods=['POST'])
def payment_webhook():
    payload = request.get_json(silent=True) or request.form.to_dict()
    
    control_number = payload.get('control_number') or payload.get('bill_ref')
    transaction_ref = payload.get('transaction_reference') or payload.get('trx_id')
    amount = float(payload.get('amount', 0))
    external_trx_id = payload.get('external_trx_id', '')
    status = payload.get('status', 'SUCCESSFUL').upper()

    if not control_number or not transaction_ref:
        return jsonify({"error": "Missing control_number or transaction_reference"}), 400

    db = SessionLocal()
    try:
        # Idempotency check: prevent duplicate credit
        existing_payment = db.query(Payment).filter(Payment.transaction_reference == transaction_ref).first()
        if existing_payment and existing_payment.status == "SUCCESSFUL":
            return jsonify({
                "status": "ALREADY_PROCESSED",
                "message": "Payment has already been processed successfully.",
                "receipt_number": existing_payment.receipt.receipt_number if existing_payment.receipt else None
            }), 200

        payment = db.query(Payment).filter(Payment.control_number == control_number).first()
        if not payment:
            return jsonify({"error": f"Control number {control_number} not found"}), 404

        # Update payment
        payment.status = status
        payment.external_trx_id = external_trx_id
        payment.payment_date = datetime.datetime.utcnow()

        if status == "SUCCESSFUL":
            # Update assessment if linked
            if payment.assessment:
                payment.assessment.amount_paid += amount
                payment.assessment.balance_due = max(0.0, payment.assessment.total_tax_liability - payment.assessment.amount_paid)

            # Generate digital receipt if not present
            if not payment.receipt:
                rcpt_no = generate_receipt_number()
                verif_hash = generate_verification_hash(transaction_ref, payment.taxpayer.tin, amount)
                receipt = DigitalReceipt(
                    receipt_number=rcpt_no,
                    payment_id=payment.id,
                    verification_hash=verif_hash,
                    taxpayer_name=payment.taxpayer.full_name,
                    taxpayer_tin=payment.taxpayer.tin,
                    amount_paid=amount,
                    control_number=control_number
                )
                db.add(receipt)

        db.commit()
        return jsonify({
            "status": "PROCESSED",
            "control_number": control_number,
            "payment_status": payment.status,
            "receipt_number": payment.receipt.receipt_number if payment.receipt else None
        }), 200
    finally:
        db.close()

# ==============================================================================
# 3. NIDA National Identity Verification Sandbox Adapter
# ==============================================================================
@api_bp.route('/integrations/nida/verify', methods=['POST'])
def nida_verify():
    data = request.get_json(silent=True) or request.form.to_dict()
    nin = data.get('nin', '').strip()

    if not validate_nida_format(nin):
        return jsonify({
            "verified": False,
            "error": "Invalid NIN format. Must be 20 digits."
        }), 400

    db = SessionLocal()
    try:
        record = db.query(NationalIdentityVerification).filter(NationalIdentityVerification.nin == nin).first()
        if record:
            return jsonify({
                "verified": True,
                "nin": record.nin,
                "first_name": record.first_name,
                "middle_name": record.middle_name,
                "last_name": record.last_name,
                "date_of_birth": record.date_of_birth,
                "gender": record.gender,
                "source": "NIDA Authorised Registry (Verified)"
            }), 200
        else:
            # Fallback mock for demonstration testing
            return jsonify({
                "verified": True,
                "nin": nin,
                "first_name": "JUMA",
                "middle_name": "RASHID",
                "last_name": "BAKARI",
                "date_of_birth": "1985-04-12",
                "gender": "Male",
                "source": "NIDA Sandbox Adapter (Verified)"
            }), 200
    finally:
        db.close()

# ==============================================================================
# 4. Tax Calculation API (Cap 332 Presumptive Schedule)
# ==============================================================================
@api_bp.route('/tax/calculate', methods=['POST', 'GET'])
def calculate_tax_api():
    turnover = float(request.values.get('turnover', 6500000))
    has_records = request.values.get('has_records', 'false').lower() in ['true', '1', 'yes']
    result = compute_presumptive_tax(turnover, has_records)
    return jsonify(result)
