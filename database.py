import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import create_engine
from config import Config

Base = declarative_base()
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, connect_args={"check_same_thread": False} if "sqlite" in Config.SQLALCHEMY_DATABASE_URI else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================================================================
# 1. Access Control & Identity (Users, Roles, Sessions)
# ==============================================================================
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False) # super_admin, tra_admin, revenue_officer, association_admin, association_agent, taxpayer, auditor, support_officer
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False) # phone or email or staff id
    email = Column(String(120), unique=True, nullable=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    role = relationship("Role")
    taxpayer_profile = relationship("Taxpayer", back_populates="user", uselist=False)
    agent_profile = relationship("AssociationAgent", back_populates="user", uselist=False)

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(50))
    user_agent = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

# ==============================================================================
# 2. Geographic & Market Entities
# ==============================================================================
class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    code = Column(String(10), unique=True, nullable=False) # e.g. DSM, MZA, ARS
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    name = Column(String(80), nullable=False)
    region = relationship("Region")

class Ward(Base):
    __tablename__ = "wards"
    id = Column(Integer, primary_key=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    name = Column(String(80), nullable=False)
    district = relationship("District")

class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    market_type = Column(String(50), default="Formal Market") # Street, Formal Market, Crafts Centre, Bodaboda Stand
    estimated_traders = Column(Integer, default=500)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    region = relationship("Region")
    district = relationship("District")

# ==============================================================================
# 3. Business Associations & Agents
# ==============================================================================
class Association(Base):
    __tablename__ = "associations"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    code = Column(String(30), unique=True, nullable=False) # e.g. VIBINDO, UWAWAMA
    registration_number = Column(String(80), unique=True, nullable=False)
    association_type = Column(String(80), default="Informal Sector Trade Union")
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=True)
    contact_person = Column(String(120), nullable=False)
    phone_number = Column(String(30), nullable=False)
    email = Column(String(120), nullable=True)
    bank_name = Column(String(100), nullable=True)
    bank_account_number = Column(String(60), nullable=True)
    status = Column(String(30), default="Pending Verification") # Pending Verification, Approved, Active, Suspended, Rejected
    revenue_share_pct = Column(Float, default=3.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    region = relationship("Region")
    district = relationship("District")
    market = relationship("Market")
    members = relationship("AssociationMember", back_populates="association")
    agents = relationship("AssociationAgent", back_populates="association")

class AssociationMember(Base):
    __tablename__ = "association_members"
    id = Column(Integer, primary_key=True)
    association_id = Column(Integer, ForeignKey("associations.id"), nullable=False)
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"), nullable=False)
    membership_number = Column(String(60), nullable=False)
    joined_date = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    association = relationship("Association", back_populates="members")
    taxpayer = relationship("Taxpayer", back_populates="memberships")

class AssociationAgent(Base):
    __tablename__ = "association_agents"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    association_id = Column(Integer, ForeignKey("associations.id"), nullable=False)
    agent_code = Column(String(50), unique=True, nullable=False) # e.g. AGT-VIB-001
    national_id = Column(String(30), nullable=False)
    phone_number = Column(String(20), nullable=False)
    assigned_market_id = Column(Integer, ForeignKey("markets.id"), nullable=True)
    is_authorized = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="agent_profile")
    association = relationship("Association", back_populates="agents")
    assigned_market = relationship("Market")

# ==============================================================================
# 4. Taxpayer & Business Profiles
# ==============================================================================
class NationalIdentityVerification(Base):
    __tablename__ = "national_identity_verifications"
    id = Column(Integer, primary_key=True)
    nin = Column(String(30), unique=True, nullable=False)
    first_name = Column(String(60), nullable=False)
    middle_name = Column(String(60), nullable=True)
    last_name = Column(String(60), nullable=False)
    date_of_birth = Column(String(20), nullable=False)
    gender = Column(String(10), nullable=False)
    verification_source = Column(String(50), default="NIDA Sandbox Adapter")
    is_verified = Column(Boolean, default=True)
    verified_at = Column(DateTime, default=datetime.datetime.utcnow)

class Taxpayer(Base):
    __tablename__ = "taxpayers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tin = Column(String(20), unique=True, nullable=False) # e.g. 142-984-102
    registration_reference = Column(String(50), unique=True, nullable=False) # e.g. TR-REG-2026-9812
    nida_number = Column(String(30), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(120), nullable=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    compliance_status = Column(String(30), default="COMPLIANT") # COMPLIANT, PARTIAL, NON_COMPLIANT, GRACE_PERIOD
    is_mlipakodi_bora = Column(Boolean, default=False)
    photo_path = Column(String(255), default="images/mama_neema.jpg")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="taxpayer_profile")
    region = relationship("Region")
    district = relationship("District")
    ward = relationship("Ward")
    businesses = relationship("Business", back_populates="taxpayer")
    memberships = relationship("AssociationMember", back_populates="taxpayer")
    assessments = relationship("TaxAssessment", back_populates="taxpayer")
    payments = relationship("Payment", back_populates="taxpayer")
    complaints = relationship("Complaint", back_populates="taxpayer")

class BusinessCategory(Base):
    __tablename__ = "business_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(255))
    is_presumptive_eligible = Column(Boolean, default=True)

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"), nullable=False)
    name = Column(String(150), nullable=False)
    category_id = Column(Integer, ForeignKey("business_categories.id"), nullable=False)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=True)
    stall_number = Column(String(50), nullable=True)
    estimated_annual_turnover = Column(Float, default=6500000.0)
    has_accounting_records = Column(Boolean, default=False)
    status = Column(String(30), default="ACTIVE") # ACTIVE, SUSPENDED, CEASED
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)

    taxpayer = relationship("Taxpayer", back_populates="businesses")
    category = relationship("BusinessCategory")
    market = relationship("Market")

class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True)
    registration_reference = Column(String(50), unique=True, nullable=False)
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"), nullable=True)
    assisted_by_agent_id = Column(Integer, ForeignKey("association_agents.id"), nullable=True)
    channel = Column(String(20), default="WEB") # WEB, USSD, AGENT, MOBILE_APP
    phone_number = Column(String(20), nullable=False)
    nida_number = Column(String(30), nullable=False)
    status = Column(String(30), default="Approved") # Draft, Pending Verification, Pending Approval, Approved, Rejected, Suspended
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    agent = relationship("AssociationAgent")

# ==============================================================================
# 5. Configurable Tax Assessment Engine (Cap 332)
# ==============================================================================
class TaxCategory(Base):
    __tablename__ = "tax_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(30), unique=True, nullable=False) # e.g. PRESUMPTIVE_INDIVIDUAL
    description = Column(String(255))
    is_active = Column(Boolean, default=True)

class TaxBand(Base):
    __tablename__ = "tax_bands"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("tax_categories.id"), nullable=False)
    band_number = Column(Integer, nullable=False) # 1, 2, 3, 4, 5
    name = Column(String(100), nullable=False) # e.g. Band 1: Up to 4,000,000 TZS
    min_turnover = Column(Float, nullable=False)
    max_turnover = Column(Float, nullable=False)
    fixed_tax_amount = Column(Float, default=0.0)
    percentage_rate = Column(Float, default=0.0)
    records_fixed_tax = Column(Float, default=0.0)
    records_percentage_rate = Column(Float, default=0.0)
    records_threshold = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime, default=datetime.datetime.utcnow)

    category = relationship("TaxCategory")

class TaxRule(Base):
    __tablename__ = "tax_rules"
    id = Column(Integer, primary_key=True)
    rule_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    previous_value = Column(String(100))
    current_value = Column(String(100))
    approved_by = Column(String(100))
    effective_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(30), default="APPROVED") # PROPOSED, APPROVED, REJECTED

class TaxPeriod(Base):
    __tablename__ = "tax_periods"
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=True) # 1, 2, 3, 4 or NULL for full year
    name = Column(String(80), nullable=False) # e.g. Mwaka wa Fedha 2026 - Robo 1
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

class TaxAssessment(Base):
    __tablename__ = "tax_assessments"
    id = Column(Integer, primary_key=True)
    assessment_number = Column(String(50), unique=True, nullable=False) # e.g. ASM-2026-8812
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"), nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    period_id = Column(Integer, ForeignKey("tax_periods.id"), nullable=False)
    band_id = Column(Integer, ForeignKey("tax_bands.id"), nullable=False)
    assessed_turnover = Column(Float, nullable=False)
    total_tax_liability = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    balance_due = Column(Float, nullable=False)
    status = Column(String(30), default="ACTIVE") # ACTIVE, PAID, REASSESSED, CANCELLED
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    taxpayer = relationship("Taxpayer", back_populates="assessments")
    business = relationship("Business")
    period = relationship("TaxPeriod")
    band = relationship("TaxBand")
    payments = relationship("Payment", back_populates="assessment")

# ==============================================================================
# 6. Payment Processing & GePG Gateway
# ==============================================================================
class PaymentProvider(Base):
    __tablename__ = "payment_providers"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False) # M-Pesa, Tigo Pesa, Airtel Money, HaloPesa, CRDB, NMB
    provider_type = Column(String(40), default="Mobile Money") # Mobile Money, Bank, Card
    channel_code = Column(String(30), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    control_number = Column(String(30), nullable=False, index=True) # 12-digit GePG control number e.g. 991240091823
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("tax_assessments.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("payment_providers.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(5), default="TZS")
    installment_type = Column(String(50), default="Quarterly") # Quarterly, Monthly, Full Year
    transaction_reference = Column(String(80), unique=True, nullable=False) # Idempotent unique transaction ref
    external_trx_id = Column(String(80), nullable=True) # Provider transaction id
    status = Column(String(30), default="PENDING") # PENDING, SUCCESSFUL, FAILED, CANCELLED, UNDER_RECONCILIATION
    payment_date = Column(DateTime, nullable=True)
    payer_phone = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    taxpayer = relationship("Taxpayer", back_populates="payments")
    assessment = relationship("TaxAssessment", back_populates="payments")
    provider = relationship("PaymentProvider")
    receipt = relationship("DigitalReceipt", back_populates="payment", uselist=False)

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    request_payload = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)
    status_code = Column(String(30))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PaymentReconciliation(Base):
    __tablename__ = "payment_reconciliations"
    id = Column(Integer, primary_key=True)
    reconciliation_date = Column(DateTime, default=datetime.datetime.utcnow)
    total_expected_amount = Column(Float, default=0.0)
    total_received_amount = Column(Float, default=0.0)
    variance_amount = Column(Float, default=0.0)
    status = Column(String(30), default="MATCHED") # MATCHED, DISCREPANCY, RESOLVED
    notes = Column(Text, nullable=True)

class DigitalReceipt(Base):
    __tablename__ = "digital_receipts"
    id = Column(Integer, primary_key=True)
    receipt_number = Column(String(60), unique=True, nullable=False) # e.g. TR-RCPT-2026-90412
    payment_id = Column(Integer, ForeignKey("payments.id"), unique=True, nullable=False)
    verification_hash = Column(String(128), unique=True, nullable=False)
    taxpayer_name = Column(String(150), nullable=False)
    taxpayer_tin = Column(String(30), nullable=False)
    amount_paid = Column(Float, nullable=False)
    control_number = Column(String(30), nullable=False)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)

    payment = relationship("Payment", back_populates="receipt")

# ==============================================================================
# 7. Complaints & Reassessment Engine
# ==============================================================================
class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(50), unique=True, nullable=False) # e.g. TKT-2026-4401
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"), nullable=False)
    category = Column(String(80), nullable=False) # Incorrect Assessment, Failed Payment, Duplicate Charge, Registration Issue, General Inquiry
    description = Column(Text, nullable=False)
    status = Column(String(40), default="Submitted") # Submitted, Under Review, Additional Information Required, Resolved, Rejected, Closed
    assigned_officer = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    taxpayer = relationship("Taxpayer", back_populates="complaints")
    responses = relationship("ComplaintResponse", back_populates="complaint")

class ComplaintResponse(Base):
    __tablename__ = "complaint_responses"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    author_name = Column(String(100), nullable=False)
    author_role = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    complaint = relationship("Complaint", back_populates="responses")

# ==============================================================================
# 8. Grace Period & Incentive Programmes
# ==============================================================================
class GracePeriod(Base):
    __tablename__ = "grace_periods"
    id = Column(Integer, primary_key=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayers.id"), nullable=False)
    duration_months = Column(Integer, default=12)
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    penalty_relief_granted = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

# ==============================================================================
# 9. Performance-Based Revenue Sharing & Community Projects
# ==============================================================================
class RevenueSharingRule(Base):
    __tablename__ = "revenue_sharing_rules"
    id = Column(Integer, primary_key=True)
    rule_name = Column(String(120), nullable=False)
    percentage = Column(Float, default=3.0)
    effective_from = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

class RevenueSharingCalculation(Base):
    __tablename__ = "revenue_sharing_calculations"
    id = Column(Integer, primary_key=True)
    association_id = Column(Integer, ForeignKey("associations.id"), nullable=False)
    period_id = Column(Integer, ForeignKey("tax_periods.id"), nullable=False)
    total_member_collections = Column(Float, default=0.0)
    percentage_applied = Column(Float, default=3.0)
    calculated_amount = Column(Float, default=0.0)
    status = Column(String(30), default="Calculated") # Calculated, Approved, Disbursed, Withheld
    calculated_at = Column(DateTime, default=datetime.datetime.utcnow)

    association = relationship("Association")
    period = relationship("TaxPeriod")

class AssociationPayout(Base):
    __tablename__ = "association_payouts"
    id = Column(Integer, primary_key=True)
    payout_reference = Column(String(50), unique=True, nullable=False) # e.g. PAYOUT-2026-VIB-01
    association_id = Column(Integer, ForeignKey("associations.id"), nullable=False)
    amount = Column(Float, nullable=False)
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(60), nullable=False)
    status = Column(String(30), default="Pending Approval") # Pending Approval, Approved, Disbursed, Rejected, Withheld
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    association = relationship("Association")

class CommunityProject(Base):
    __tablename__ = "community_projects"
    id = Column(Integer, primary_key=True)
    association_id = Column(Integer, ForeignKey("associations.id"), nullable=False)
    title = Column(String(150), nullable=False) # e.g. Usafi wa Soko Kariakoo, Ulinzi Shirikishi Mwenge
    description = Column(Text, nullable=False)
    budget = Column(Float, nullable=False)
    approved_expenditure = Column(Float, default=0.0)
    funding_source = Column(String(100), default="TaxRahisi Revenue Sharing Allocation")
    status = Column(String(40), default="In Progress") # Proposed, Approved, In Progress, Completed
    completion_percentage = Column(Integer, default=50)
    market_location = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    association = relationship("Association")

# ==============================================================================
# 10. Notifications, Educational Content & Audit Trails
# ==============================================================================
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    recipient_phone = Column(String(20), nullable=False)
    recipient_email = Column(String(120), nullable=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(20), default="SMS") # SMS, EMAIL, IN_APP
    is_sent = Column(Boolean, default=True)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)

class EducationalContent(Base):
    __tablename__ = "educational_contents"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    category = Column(String(80), nullable=False) # Presumptive Tax, Record Keeping, Taxpayer Rights, Payments
    language = Column(String(10), default="sw") # sw, en
    summary = Column(Text, nullable=False)
    content_body = Column(Text, nullable=False)
    download_link = Column(String(255), nullable=True)
    published_by = Column(String(100), default="TRA Directorate of Taxpayer Services")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_username = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(String(80), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(80), unique=True, nullable=False)
    setting_value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)

class IntegrationLog(Base):
    __tablename__ = "integration_logs"
    id = Column(Integer, primary_key=True)
    service_name = Column(String(50), nullable=False) # NIDA, GEPG, TELECOM_USSD, SMS_GATEWAY
    endpoint = Column(String(200), nullable=False)
    request_data = Column(Text, nullable=True)
    response_data = Column(Text, nullable=True)
    status_code = Column(Integer, default=200)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("TaxRahisi database initialized successfully!")

if __name__ == "__main__":
    init_db()
