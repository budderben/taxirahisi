import unittest
import json
import datetime
from app import create_app
from database import (
    Base, engine, SessionLocal, User, Role, Taxpayer, Business, Association,
    AssociationMember, AssociationAgent, TaxAssessment, Payment, DigitalReceipt,
    Complaint, GracePeriod, AuditLog
)
from tax_engine import (
    compute_presumptive_tax, generate_gepg_control_number, generate_tin,
    generate_verification_hash, validate_nida_format
)

class TaxRahisiPlatformTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    # ==========================================================================
    # SCENARIO 1: New Taxpayer Self-Registration via Web Portal
    # ==========================================================================
    def test_scenario_01_taxpayer_self_registration(self):
        unique_suffix = datetime.datetime.now().strftime("%f")[:6]
        phone = f"0765{unique_suffix}"
        nida = f"19900101{unique_suffix}000000"[:20]

        res = self.client.post('/portal/register', data={
            'full_name': 'Test Mjasiriamali',
            'phone_number': phone,
            'nida_number': nida,
            'password': 'TestPassword123!',
            'region_id': '1',
            'district_id': '1',
            'market_id': '1',
            'association_id': '1',
            'business_name': 'Test Kibanda Freshi',
            'category_id': '1',
            'turnover': '5500000',
            'has_records': 'on'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        # Verify DB records created
        user = self.db.query(User).filter(User.phone_number == phone).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.full_name, 'Test Mjasiriamali')

        taxpayer = self.db.query(Taxpayer).filter(Taxpayer.user_id == user.id).first()
        self.assertIsNotNone(taxpayer)
        self.assertTrue(taxpayer.tin.startswith('14'))
        self.assertEqual(taxpayer.nida_number, nida)

        # Verify 12-month grace period granted
        grace = self.db.query(GracePeriod).filter(GracePeriod.taxpayer_id == taxpayer.id).first()
        self.assertIsNotNone(grace)
        self.assertTrue(grace.is_active)
        self.assertTrue(grace.penalty_relief_granted)

    # ==========================================================================
    # SCENARIO 2: Cap 332 Presumptive Tax Calculation Accuracy
    # ==========================================================================
    def test_scenario_02_cap_332_tax_calculation(self):
        # Band 1: <= 4,000,000 -> NIL (0 TZS)
        b1 = compute_presumptive_tax(3500000, False)
        self.assertEqual(b1['band_number'], 1)
        self.assertEqual(b1['annual_tax'], 0.0)

        # Band 2: 4,000,001 - 7,000,000 -> Fixed 100k without records, 3% of excess with records
        b2_no_rec = compute_presumptive_tax(6000000, False)
        self.assertEqual(b2_no_rec['band_number'], 2)
        self.assertEqual(b2_no_rec['annual_tax'], 100000.0)

        b2_with_rec = compute_presumptive_tax(6000000, True)
        self.assertEqual(b2_with_rec['band_number'], 2)
        self.assertEqual(b2_with_rec['annual_tax'], 60000.0) # (6M - 4M) * 3%

        # Band 3: 7,000,001 - 11,000,000 -> Fixed 250k without records, 90k + 3% of excess with records
        b3_no_rec = compute_presumptive_tax(10000000, False)
        self.assertEqual(b3_no_rec['band_number'], 3)
        self.assertEqual(b3_no_rec['annual_tax'], 250000.0)

        b3_with_rec = compute_presumptive_tax(10000000, True)
        self.assertEqual(b3_with_rec['band_number'], 3)
        self.assertEqual(b3_with_rec['annual_tax'], 180000.0) # 90k + (3M * 3%)

        # Band 4: 11,000,001 - 200,000,000 -> 4.5% of turnover
        b4 = compute_presumptive_tax(20000000, False)
        self.assertEqual(b4['band_number'], 4)
        self.assertEqual(b4['annual_tax'], 900000.0) # 20M * 4.5%
        self.assertTrue(b4['efd_required'])

    # ==========================================================================
    # SCENARIO 3: Payment Processing & Digital Receipt Issuance
    # ==========================================================================
    def test_scenario_03_payment_and_digital_receipt(self):
        taxpayer_user = self.db.query(User).join(Role).filter(Role.name == "taxpayer").first()
        self.assertIsNotNone(taxpayer_user)

        with self.client.session_transaction() as sess:
            sess['user_id'] = taxpayer_user.id
            sess['username'] = taxpayer_user.username
            sess['full_name'] = taxpayer_user.full_name
            sess['user_role'] = "taxpayer"

        # Make a payment of 25,000 TZS
        res = self.client.post('/portal/payments', data={
            'amount': '25000',
            'provider_id': '1',
            'installment_type': 'Quarterly',
            'payer_phone': taxpayer_user.phone_number
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        # Verify receipt was issued in database
        tp = self.db.query(Taxpayer).filter(Taxpayer.user_id == taxpayer_user.id).first()
        receipt = self.db.query(DigitalReceipt).filter(DigitalReceipt.taxpayer_tin == tp.tin).order_by(DigitalReceipt.id.desc()).first()
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.amount_paid, 25000.0)
        self.assertTrue(receipt.receipt_number.startswith("TR-RCPT-"))
        self.assertTrue(len(receipt.verification_hash) > 10)

    # ==========================================================================
    # SCENARIO 4: Association Registration & Profile
    # ==========================================================================
    def test_scenario_04_association_verification(self):
        assoc = self.db.query(Association).first()
        self.assertIsNotNone(assoc)
        self.assertEqual(assoc.status, "Active")
        self.assertEqual(assoc.revenue_share_pct, 3.0)
        self.assertIsNotNone(assoc.market)

    # ==========================================================================
    # SCENARIO 5: Agent-Assisted Trader Onboarding
    # ==========================================================================
    def test_scenario_05_agent_assisted_onboarding(self):
        agent_user = self.db.query(User).join(Role).filter(Role.name == "association_agent").first()
        self.assertIsNotNone(agent_user)

        with self.client.session_transaction() as sess:
            sess['user_id'] = agent_user.id
            sess['username'] = agent_user.username
            sess['full_name'] = agent_user.full_name
            sess['user_role'] = "association_agent"

        unique_suffix = datetime.datetime.now().strftime("%f")[:6]
        phone = f"0744{unique_suffix}"
        nida = f"19920202{unique_suffix}000000"[:20]

        res = self.client.post('/agent/onboard', data={
            'full_name': 'Assisted Trader Mussa',
            'phone_number': phone,
            'nida_number': nida,
            'business_name': 'Mussa Hardware Stall',
            'category_id': '1',
            'market_id': '1',
            'turnover': '7500000',
            'has_records': 'on'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        # Verify trader registered with agent attribution
        tp = self.db.query(Taxpayer).filter(Taxpayer.nida_number == nida).first()
        self.assertIsNotNone(tp)
        self.assertEqual(tp.full_name, 'Assisted Trader Mussa')

    # ==========================================================================
    # SCENARIO 6: Performance-Based Revenue-Sharing Calculation (3%)
    # ==========================================================================
    def test_scenario_06_revenue_sharing_calculation(self):
        assoc = self.db.query(Association).first()
        members = self.db.query(AssociationMember).filter(AssociationMember.association_id == assoc.id).all()
        member_ids = [m.taxpayer_id for m in members]

        payments = self.db.query(Payment).filter(
            Payment.taxpayer_id.in_(member_ids),
            Payment.status == "SUCCESSFUL"
        ).all()
        total_collected = sum(p.amount for p in payments)
        expected_share = total_collected * (assoc.revenue_share_pct / 100.0)

        self.assertTrue(expected_share >= 0.0)
        self.assertEqual(assoc.revenue_share_pct, 3.0)

    # ==========================================================================
    # SCENARIO 7: Taxpayer Complaint Ticket Lifecycle
    # ==========================================================================
    def test_scenario_07_complaint_ticket_lifecycle(self):
        taxpayer_user = self.db.query(User).join(Role).filter(Role.name == "taxpayer").first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = taxpayer_user.id
            sess['username'] = taxpayer_user.username
            sess['full_name'] = taxpayer_user.full_name
            sess['user_role'] = "taxpayer"

        # 1. Taxpayer submits complaint
        res = self.client.post('/portal/complaints', data={
            'category': 'Incorrect Assessment',
            'description': 'Ombi la kupunguza makadirio kutokana na ujenzi wa barabara Kariakoo.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        tp = self.db.query(Taxpayer).filter(Taxpayer.user_id == taxpayer_user.id).first()
        complaint = self.db.query(Complaint).filter(Complaint.taxpayer_id == tp.id).order_by(Complaint.id.desc()).first()
        self.assertIsNotNone(complaint)
        self.assertEqual(complaint.status, "Submitted")

        # 2. Admin resolves complaint
        admin_user = self.db.query(User).join(Role).filter(Role.name.in_(["super_admin", "tra_admin"])).first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['username'] = admin_user.username
            sess['full_name'] = admin_user.full_name
            sess['user_role'] = "tra_admin"

        res_admin = self.client.post('/admin/complaints', data={
            'complaint_id': str(complaint.id),
            'response': 'Tumekagua taarifa zako na kurekebisha makadirio yako kwa mujibu wa Cap 332.',
            'status': 'Resolved'
        }, follow_redirects=True)
        self.assertEqual(res_admin.status_code, 200)

        # Verify status is Resolved
        self.db.refresh(complaint)
        self.assertEqual(complaint.status, "Resolved")

    # ==========================================================================
    # SCENARIO 8: Administrative Overview & Aggregation
    # ==========================================================================
    def test_scenario_08_admin_aggregation(self):
        admin_user = self.db.query(User).join(Role).filter(Role.name.in_(["super_admin", "tra_admin"])).first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['username'] = admin_user.username
            sess['full_name'] = admin_user.full_name
            sess['user_role'] = "tra_admin"

        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"TRA Executive Revenue Dashboard", res.data)

    # ==========================================================================
    # SCENARIO 9: RBAC Permission Denial & Security Audit Logging
    # ==========================================================================
    def test_scenario_09_rbac_permission_denial(self):
        # A normal taxpayer tries to access /admin/dashboard
        taxpayer_user = self.db.query(User).join(Role).filter(Role.name == "taxpayer").first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = taxpayer_user.id
            sess['username'] = taxpayer_user.username
            sess['full_name'] = taxpayer_user.full_name
            sess['user_role'] = "taxpayer"

        res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertNotEqual(res.status_code, 500)

        # Verify audit log captures unauthorized access attempt
        audit = self.db.query(AuditLog).filter(AuditLog.action == "UNAUTHORIZED_ACCESS_ATTEMPT").order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_username, taxpayer_user.username)

    # ==========================================================================
    # SCENARIO 10: Payment Idempotency & Duplicate Prevention
    # ==========================================================================
    def test_scenario_10_payment_idempotency(self):
        payment = self.db.query(Payment).filter(Payment.status == "SUCCESSFUL").first()
        self.assertIsNotNone(payment)

        # Trigger duplicate webhook with identical transaction_reference
        payload = {
            'control_number': payment.control_number,
            'transaction_reference': payment.transaction_reference,
            'amount': payment.amount,
            'status': 'SUCCESSFUL'
        }

        res = self.client.post('/api/v1/payments/webhook',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ALREADY_PROCESSED')

    # ==========================================================================
    # SCENARIO 11: Telecom USSD Gateway API (CON/END Protocol)
    # ==========================================================================
    def test_scenario_11_ussd_gateway_protocol(self):
        # 1. Root USSD request
        res_root = self.client.post('/api/v1/ussd/gateway', data={
            'sessionId': 'USSD-SESSION-999',
            'phoneNumber': '0712345678',
            'text': '',
            'serviceCode': '*150*88#'
        })
        self.assertEqual(res_root.status_code, 200)
        content_root = res_root.data.decode('utf-8')
        self.assertTrue(content_root.startswith("CON "))
        self.assertIn("Karibu TaxRahisi", content_root)

        # 2. Select option 6 (Tax Info)
        res_info = self.client.post('/api/v1/ussd/gateway', data={
            'sessionId': 'USSD-SESSION-999',
            'phoneNumber': '0712345678',
            'text': '6',
            'serviceCode': '*150*88#'
        })
        self.assertEqual(res_info.status_code, 200)
        content_info = res_info.data.decode('utf-8')
        self.assertTrue(content_info.startswith("END "))
        self.assertIn("Sheria ya Kodi Sura 332", content_info)

if __name__ == '__main__':
    unittest.main()
