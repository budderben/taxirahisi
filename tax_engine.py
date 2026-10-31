import random
import hashlib
import datetime
import re

def compute_presumptive_tax(turnover: float, has_records: bool = False, custom_bands: list = None) -> dict:
    """
    Computes presumptive tax based on Tanzania Income Tax Act Cap 332 rules:
    - Band 1: Up to 4,000,000 TZS -> NIL (0 TZS)
    - Band 2: 4,000,001 - 7,000,000 TZS ->
        Without records: 100,000 TZS
        With records: 3% of turnover in excess of 4,000,000 TZS
    - Band 3: 7,000,001 - 11,000,000 TZS ->
        Without records: 250,000 TZS
        With records: 90,000 TZS + 3% of turnover in excess of 7,000,000 TZS
    - Band 4: 11,000,001 - 200,000,000 TZS ->
        4.5% of annual turnover (standard Cap 332 schedule)
    """
    turnover = float(turnover) if turnover else 0.0

    if turnover <= 4000000:
        band_num = 1
        band_name = "Band 1 (Hadi TZS 4,000,000)"
        annual_tax = 0.0
        formula_explanation = "Chini ya kiwango cha chini cha kodi (Msamaha wa Kodi - NIL)."
    elif turnover <= 7000000:
        band_num = 2
        band_name = "Band 2 (TZS 4,000,001 - 7,000,000)"
        if has_records:
            annual_tax = (turnover - 4000000) * 0.03
            formula_explanation = f"3% ya ziada ya TZS 4,000,000 (Mauzo TZS {turnover:,.0f} - 4,000,000 x 3%)."
        else:
            annual_tax = 100000.0
            formula_explanation = "Kiwango maalum kisichobadilika bila vitabu vya hesabu (Fixed TZS 100,000)."
    elif turnover <= 11000000:
        band_num = 3
        band_name = "Band 3 (TZS 7,000,001 - 11,000,000)"
        if has_records:
            annual_tax = 90000.0 + ((turnover - 7000000) * 0.03)
            formula_explanation = f"TZS 90,000 + 3% ya ziada ya TZS 7,000,000 (TZS {turnover:,.0f} - 7,000,000 x 3%)."
        else:
            annual_tax = 250000.0
            formula_explanation = "Kiwango maalum kisichobadilika bila vitabu vya hesabu (Fixed TZS 250,000)."
    elif turnover <= 200000000:
        band_num = 4
        band_name = "Band 4 (TZS 11,000,001 - 200,000,000)"
        annual_tax = turnover * 0.045
        formula_explanation = f"4.5% ya mauzo ghafi ya mwaka (Mauzo TZS {turnover:,.0f} x 4.5%). Mtumiaji anahitaji EFD."
    else:
        band_num = 5
        band_name = "Zaidi ya TZS 200,000,000"
        annual_tax = turnover * 0.045
        formula_explanation = "Inazidi kiwango cha presumptive. Mlipakodi anatakiwa kuwasilisha mahesabu kamili ya ukaguzi."

    quarterly = round(annual_tax / 4.0, 2)
    monthly = round(annual_tax / 12.0, 2)
    weekly = round(annual_tax / 52.0, 2)

    return {
        "turnover": turnover,
        "band_number": band_num,
        "band_name": band_name,
        "has_records": has_records,
        "annual_tax": round(annual_tax, 2),
        "quarterly_tax": quarterly,
        "monthly_tax": monthly,
        "weekly_tax": weekly,
        "explanation": formula_explanation,
        "efd_required": turnover >= 11000000
    }

def generate_gepg_control_number() -> str:
    """Generates standard 12-digit Tanzanian GePG control number starting with 991"""
    digits = "991" + "".join([str(random.randint(0, 9)) for _ in range(8)])
    # Compute Modulo-10 checksum digit
    s = sum(int(d) * (2 if i % 2 == 0 else 1) for i, d in enumerate(digits))
    check = (10 - (s % 10)) % 10
    return digits + str(check)

def generate_tin() -> str:
    """Generates 9-digit Tanzanian Taxpayer Identification Number in format XXX-XXX-XXX"""
    p1 = random.randint(140, 149)
    p2 = random.randint(100, 999)
    p3 = random.randint(100, 999)
    return f"{p1}-{p2}-{p3}"

def generate_registration_reference() -> str:
    year = datetime.datetime.now().year
    rand = random.randint(10000, 99999)
    return f"TR-REG-{year}-{rand}"

def generate_receipt_number() -> str:
    year = datetime.datetime.now().year
    rand = random.randint(100000, 999999)
    return f"TR-RCPT-{year}-{rand}"

def generate_verification_hash(payment_ref: str, tin: str, amount: float) -> str:
    raw = f"{payment_ref}:{tin}:{amount}:{datetime.datetime.utcnow().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24].upper()

def validate_nida_format(nida: str) -> bool:
    """Validates 20-digit Tanzanian NIDA NIN (format YYYYMMDD-XXXXX-XXXXX-XX or 20 digits)"""
    cleaned = re.sub(r'[^0-9]', '', nida or '')
    return len(cleaned) == 20
