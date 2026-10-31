import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'taxrahisi-production-secret-tz-2026-key')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database configuration - defaults to SQLite for immediate execution, supports PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{os.path.join(BASE_DIR, 'taxrahisi.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production
    PERMANENT_SESSION_LIFETIME = 86400 # 24 hours
    
    # Official platform identity
    PLATFORM_NAME = "TaxRahisi"
    TAGLINE = "Every trader counted. Every shilling fairly collected."
    PRIMARY_STAKEHOLDER = "Tanzania Revenue Authority (TRA)"
    DEFAULT_CURRENCY = "TZS"
    
    # Telecom & GePG Gateway configs
    USSD_SERVICE_CODE = os.environ.get('USSD_SERVICE_CODE', '*150*88#')
    GEPG_SP_CODE = os.environ.get('GEPG_SP_CODE', 'SP2026TRA')
    GEPG_SYSTEM_ID = os.environ.get('GEPG_SYSTEM_ID', 'SYS_TAXRAHISI_01')
    
    # Default revenue share percentage for accredited associations
    DEFAULT_ASSOCIATION_SHARE_PCT = 3.0  # 3% of verified member collections
