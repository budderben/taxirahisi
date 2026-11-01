# TAXRAHISI — DIGITAL REVENUE COLLECTION & ADMINISTRATION PLATFORM
**Official Digital Innovation for Tanzania's Informal Sector Formalisation**

> **Jamhuri ya Muungano wa Tanzania &bull; Mamlaka ya Mapato Tanzania (TRA)**  
> *"Every trader counted. Every shilling fairly collected."*

---

## 1. Executive Summary

**TaxRahisi** is a production-ready, full-stack digital revenue administration platform built to bridge the gap between Tanzania's vast informal economy (over 60% of the active workforce) and the Tanzania Revenue Authority (TRA).

By leveraging real-time NIDA validation, transparent presumptive tax assessment under the **Income Tax Act (Cap 332 R.E. 2019)**, instant GePG payment control numbers, and a direct 3% revenue-sharing model with accredited market trade unions (VIBINDO, UWAWAMA, WAMAKU), TaxRahisi replaces bureaucratic friction with digital inclusion and trust.

---

## 2. Core Portals & Capabilities

The platform operates 5 integrated, role-based interfaces plus automated backend gateway integrations:

1. **Public Website (`/`)**:
   - **Mwanzo (`/`)**: Hero banner, live aggregate counts, trader spotlights (Mama Neema, Juma Machinga), and innovation pillars.
   - **Kuhusu Sisi (`/about`)**: Policy vision, Personal Data Protection Act (PDPA 2022) alignment, and informal sector context.
   - **Jinsi Inavyofanya Kazi (`/how-it-works`)**: 5-step registration-to-receipt flow.
   - **Elimu ya Kodi (`/education`)**: Cap 332 presumptive tax schedule, taxpayer rights, and downloadable guides (`/education/download/<id>`).
   - **Mpango wa Vyama (`/associations-programme`)**: Public registry of approved market associations.
   - **Kikokotoo cha Kodi (`/calculator`)**: Real-time interactive Cap 332 turnover calculator.
   - **Uhakiki wa Stakabadhi & TIN (`/verify?q=...`)**: Instant cryptographic verification hash and TIN validation.
   - **Mawasiliano (`/contact`)**: Regional offices, TRA toll-free lines (0800 110 016), and public inquiry form.

2. **Taxpayer Self-Service Portal (`/portal/`)**:
   - **Guided Registration (`/portal/register`)**: Instant 20-digit NIDA validation, instant TIN generation (`14X-XXX-XXX`), and automatic 12-month first-time grace period certification.
   - **Dashboard (`/portal/dashboard`)**: Compliance score meter, active grace period banner, assessment breakdown, and payment status.
   - **Assessment & Reassessment (`/portal/assessment`)**: Transparent breakdown of Cap 332 tax band calculation and formal reassessment request form (Section 71).
   - **GePG Payments (`/portal/payments`)**: Direct GePG control number generator (`991...`), mobile money instructions (M-Pesa, Tigo Pesa, Airtel Money), and instant receipt generation.
   - **Digital Tax Receipts (`/portal/receipts` & `/portal/receipts/<id>`)**: Formal electronic tax receipts with SHA-256 verification hash, TRA security stamp, and one-click printable format.
   - **Complaints & Grievances (`/portal/complaints`)**: Ticket creation and officer resolution history.
   - **Mlipakodi Bora (`/portal/compliance`)**: Compliance scorecard, recognition tier, and bank loan pre-qualification badges.

3. **Business Association Portal (`/association/`)**:
   - **Association Dashboard (`/association/dashboard`)**: Member headcount, compliant vs non-compliant ratio, verified collections, and accrued 3% revenue-share balance.
   - **Member Directory (`/association/members`)**: Privacy-safe trader directory protecting raw NIDA numbers according to PDPA 2022.
   - **Revenue Sharing (`/association/revenue-sharing`)**: Automated 3% calculation, bank account registration, and payout request submission to TRA.
   - **Community Projects (`/association/projects`)**: Sanitation, solar lighting, security gates, and market improvement tracking.

4. **Tax Agent Field Portal (`/agent/`)**:
   - **Agent Dashboard (`/agent/dashboard`)**: Agent code tracking, market assignment, and assisted registration history.
   - **Field Onboarding (`/agent/onboard`)**: Assisted trader registration attributing agent IDs and generating instant TINs on the ground.

5. **TRA Executive Administration Portal (`/admin/`)**:
   - **Executive Dashboard (`/admin/dashboard`)**: Macro revenue metrics, collections vs outstanding balances, regional distribution, and live GePG transaction feed.
   - **Taxpayer Administration (`/admin/taxpayers`)**: Multi-attribute search, regional filtering, compliance sorting, and account suspension/reactivation.
   - **Configurable Tax Rules (`/admin/tax-rules`)**: Dynamic tax band modification with Maker-Checker dual authorization and audit trails.
   - **Payment Administration (`/admin/payments`)**: Bank and mobile network reconciliation status.
   - **Risk Scoring Engine (`/admin/compliance`)**: Automated high, medium, and low risk stratification.
   - **Association Oversight & Payouts (`/admin/associations`)**: 3% payout approval, withholding, and disbursement actions.
   - **Central Complaint Resolution (`/admin/complaints`)**: Grievance management and taxpayer messaging.
   - **Executive Reports (`/admin/reports`)**: On-demand CSV data export for collections, taxpayers, and assessments.
   - **Security Audit Logs (`/admin/audit-logs`)**: Immutable audit trail recording timestamps, actors, actions, and IPs.

---

## 3. Telecom USSD Gateway & Integration API

Per user specifications, USSD is **not** simulated as a toy mobile dialer on the web page. Instead, TaxRahisi exposes the production-grade Telecom USSD Gateway endpoint (`/api/v1/ussd/gateway`) compatible with standard telecom aggregator protocols (Africa's Talking, Twilio, Vodacom, Tigo, Airtel):

- **Endpoint**: `POST /api/v1/ussd/gateway`
- **Parameters**: `sessionId`, `phoneNumber`, `text`, `serviceCode` (Default: `*150*88#`)
- **Protocol Response**: Text starting with `CON ` for continuing sessions and `END ` for terminal steps.
- **Payment Webhook**: `POST /api/v1/payments/webhook` with idempotent duplicate prevention.

---

## 4. Presumptive Tax Regime (Income Tax Act Cap 332)

TaxRahisi implements the exact presumptive rates stipulated by the Parliament of Tanzania:

| Band | Annual Turnover (TZS) | Tax Without Records | Tax With Records | Legal Requirements |
| :--- | :--- | :--- | :--- | :--- |
| **Band 1** | Up to 4,000,000 | **TZS 0 (NIL)** | **TZS 0 (NIL)** | Tax exempt for small micro-traders |
| **Band 2** | 4,000,001 – 7,000,000 | **TZS 100,000** | **3%** of turnover > 4,000,000 | Basic income & expense records |
| **Band 3** | 7,000,001 – 11,000,000 | **TZS 250,000** | **TZS 90,000 + 3%** > 7,000,000 | Standard simplified accounting |
| **Band 4** | 11,000,001 – 200,000,000 | **4.5%** of gross turnover | **4.5%** of gross turnover | Electronic Fiscal Device (EFD) mandatory |

---

## 5. Quickstart & Installation

### Option A: Local Python Environment
```bash
# 1. Navigate to platform folder
cd taxrahisi_platform

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed database with realistic Tanzanian reference data
python seed.py

# 4. Start the application
python app.py
```
Visit `http://localhost:5000` in your web browser.

### Option B: Docker & Docker Compose
```bash
docker-compose up --build
```
Access the application at `http://localhost:5000`.

---

## 6. Pre-seeded Demo Credentials

| Role | Username / Identifier | Password | Access Portal |
| :--- | :--- | :--- | :--- |
| **Taxpayer (Mama Neema)** | `0755123456` | `Pass123!` | `/portal/dashboard` |
| **Taxpayer (Juma)** | `0712345678` | `Pass123!` | `/portal/dashboard` |
| **Association Admin** | `vibindo.admin` au `vibindo@taxrahisi.or.tz` | `Pass123!` | `/association/dashboard` |
| **Market Agent** | `agent.mwangi` au `agent.juma@taxrahisi.or.tz` | `Pass123!` | `/agent/dashboard` |
| **TRA Administrator** | `tra.admin` au `admin@taxrahisi.go.tz` | `AdminPass123!` | `/admin/dashboard` |

---

## 7. Running the Automated Test Suite

To verify all 10 core innovation scenarios:
```bash
python3 -m unittest tests/test_platform.py
```
Expected output:
```text
Ran 11 tests in 5.612s
OK
```
