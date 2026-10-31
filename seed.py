import datetime
from database import (
    Base, engine, SessionLocal, Role, User, Region, District, Market, BusinessCategory,
    Association, AssociationMember, AssociationAgent, Taxpayer, Business, Registration,
    TaxCategory, TaxBand, TaxPeriod, TaxAssessment, Payment, PaymentProvider, DigitalReceipt,
    GracePeriod, CommunityProject, EducationalContent, AuditLog
)
from auth import hash_password
from tax_engine import generate_gepg_control_number, generate_verification_hash

def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding TaxRahisi database...")

        # 1. Roles
        roles = [
            Role(name="super_admin", description="Full platform configuration & oversight"),
            Role(name="tra_admin", description="TRA Central Revenue Administration"),
            Role(name="revenue_officer", description="Assigned revenue operations & monitoring"),
            Role(name="association_admin", description="Market association executive"),
            Role(name="association_agent", description="Accredited field tax onboarding agent"),
            Role(name="taxpayer", description="Informal sector trader"),
            Role(name="auditor", description="Independent audit & verification oversight"),
            Role(name="support_officer", description="Taxpayer inquiries and complaints officer")
        ]
        db.add_all(roles)
        db.flush()

        role_map = {r.name: r.id for r in roles}

        # 2. Regions & Districts
        r_dsm = Region(name="Dar es Salaam", code="DSM")
        r_mza = Region(name="Mwanza", code="MZA")
        r_ars = Region(name="Arusha", code="ARS")
        r_dod = Region(name="Dodoma", code="DOD")
        r_mby = Region(name="Mbeya", code="MBY")
        db.add_all([r_dsm, r_mza, r_ars, r_dod, r_mby])
        db.flush()

        dist_ilala = District(name="Ilala", region_id=r_dsm.id)
        dist_kinondoni = District(name="Kinondoni", region_id=r_dsm.id)
        dist_ubungo = District(name="Ubungo", region_id=r_dsm.id)
        dist_temeke = District(name="Temeke", region_id=r_dsm.id)
        dist_nyamagana = District(name="Nyamagana", region_id=r_mza.id)
        dist_arusha = District(name="Arusha Mjini", region_id=r_ars.id)
        db.add_all([dist_ilala, dist_kinondoni, dist_ubungo, dist_temeke, dist_nyamagana, dist_arusha])
        db.flush()

        # 3. Markets
        m_kariakoo = Market(name="Soko Kuu la Kariakoo", region_id=r_dsm.id, district_id=dist_ilala.id, market_type="Formal Market", estimated_traders=25000)
        m_mwenge = Market(name="Mwenge Vinyago & Crafts", region_id=r_dsm.id, district_id=dist_kinondoni.id, market_type="Crafts & Textile", estimated_traders=4500)
        m_mwananyamala = Market(name="Mwananyamala Sokoni", region_id=r_dsm.id, district_id=dist_kinondoni.id, market_type="Food & Fresh Produce", estimated_traders=2200)
        m_tegeta = Market(name="Tegeta Nyuki", region_id=r_dsm.id, district_id=dist_kinondoni.id, market_type="General Market", estimated_traders=1800)
        m_complex = Market(name="Machinga Complex Ilala", region_id=r_dsm.id, district_id=dist_ilala.id, market_type="Machinga Commercial Mall", estimated_traders=7000)
        db.add_all([m_kariakoo, m_mwenge, m_mwananyamala, m_tegeta, m_complex])
        db.flush()

        # 4. Business Categories
        categories = [
            BusinessCategory(name="Mama Lishe / Huduma za Chakula", code="FOOD", description="Wauza vyakula na vinywaji masokoni", is_presumptive_eligible=True),
            BusinessCategory(name="Wamachinga (Nguo na Viatu)", code="TEXTILE", description="Wafanyabiashara wa nguo, mitumba na viatu", is_presumptive_eligible=True),
            BusinessCategory(name="Bodaboda na Bajaji", code="TRANSPORT", description="Wasafirishaji wa abiria kwa pikipiki na bajaji", is_presumptive_eligible=True),
            BusinessCategory(name="Fundi na Sanaa za Mikono", code="CRAFTS", description="Mafundi viatu, seremala na wachonga vinyago", is_presumptive_eligible=True),
            BusinessCategory(name="Matunda na Mbogamboga", code="PRODUCE", description="Wauza matunda, nafaka na mbogamboga", is_presumptive_eligible=True),
            BusinessCategory(name="Maduka Madogo (Rejareja)", code="RETAIL", description="Vibanda vya rejareja mitaani", is_presumptive_eligible=True)
        ]
        db.add_all(categories)
        db.flush()

        # 5. Associations
        assoc_vibindo = Association(
            name="VIBINDO Society (Vikundi vya Biashara Ndogo)",
            code="VIBINDO",
            registration_number="SO-1995-VIB-01",
            association_type="Shirikisho la Kitaifa la Sekta Isiyo Rasmi",
            region_id=r_dsm.id,
            district_id=dist_ilala.id,
            market_id=m_kariakoo.id,
            contact_person="Mwenyekiti Gaston Kikuwi",
            phone_number="+255 754 112 233",
            email="vibindo@taxrahisi.or.tz",
            bank_name="CRDB Bank Plc",
            bank_account_number="0150992817200",
            status="Active",
            revenue_share_pct=3.0
        )
        assoc_uwawama = Association(
            name="UWAWAMA (Umoja wa Wamachinga Mkoa wa Dar es Salaam)",
            code="UWAWAMA",
            registration_number="SO-2018-UWA-04",
            association_type="Umoja wa Wamachinga",
            region_id=r_dsm.id,
            district_id=dist_ilala.id,
            market_id=m_complex.id,
            contact_person="Katibu Stephen Lusinde",
            phone_number="+255 713 445 566",
            email="uwawama@taxrahisi.or.tz",
            bank_name="NMB Bank Plc",
            bank_account_number="20108849201",
            status="Active",
            revenue_share_pct=3.0
        )
        assoc_wamaku = Association(
            name="WAMAKU (Wafanyabiashara Soko la Kariakoo)",
            code="WAMAKU",
            registration_number="SO-2015-WAM-02",
            association_type="Chama cha Wafanyabiashara wa Soko",
            region_id=r_dsm.id,
            district_id=dist_ilala.id,
            market_id=m_kariakoo.id,
            contact_person="Haji Ramadhani",
            phone_number="+255 784 778 899",
            email="wamaku@taxrahisi.or.tz",
            bank_name="CRDB Bank Plc",
            bank_account_number="0150774829100",
            status="Active",
            revenue_share_pct=3.0
        )
        db.add_all([assoc_vibindo, assoc_uwawama, assoc_wamaku])
        db.flush()

        # 6. Tax Category & Approved Cap 332 Presumptive Tax Bands
        cat_presumptive = TaxCategory(
            name="Presumptive Income Tax (Cap 332)",
            code="PRESUMPTIVE_INDIVIDUAL",
            description="Kodi ya makadirio kwa wafanyabiashara wadogo walio chini ya mauzo ya TZS 200,000,000",
            is_active=True
        )
        db.add(cat_presumptive)
        db.flush()

        bands = [
            TaxBand(category_id=cat_presumptive.id, band_number=1, name="Hadi TZS 4,000,000", min_turnover=0, max_turnover=4000000, fixed_tax_amount=0.0, percentage_rate=0.0, records_fixed_tax=0.0, records_percentage_rate=0.0),
            TaxBand(category_id=cat_presumptive.id, band_number=2, name="TZS 4,000,001 - 7,000,000", min_turnover=4000001, max_turnover=7000000, fixed_tax_amount=100000.0, percentage_rate=0.0, records_fixed_tax=0.0, records_percentage_rate=0.03, records_threshold=4000000),
            TaxBand(category_id=cat_presumptive.id, band_number=3, name="TZS 7,000,001 - 11,000,000", min_turnover=7000001, max_turnover=11000000, fixed_tax_amount=250000.0, percentage_rate=0.0, records_fixed_tax=90000.0, records_percentage_rate=0.03, records_threshold=7000000),
            TaxBand(category_id=cat_presumptive.id, band_number=4, name="TZS 11,000,001 - 200,000,000", min_turnover=11000001, max_turnover=200000000, fixed_tax_amount=0.0, percentage_rate=0.045, records_fixed_tax=0.0, records_percentage_rate=0.045, records_threshold=0.0)
        ]
        db.add_all(bands)
        db.flush()

        # 7. Tax Period
        period_2026 = TaxPeriod(
            year=2026,
            quarter=1,
            name="Mwaka wa Fedha 2026 - Robo 1",
            start_date=datetime.datetime(2026, 1, 1),
            end_date=datetime.datetime(2026, 3, 31),
            is_active=True
        )
        db.add(period_2026)
        db.flush()

        # 8. Payment Providers
        providers = [
            PaymentProvider(name="M-Pesa (Vodacom)", provider_type="Mobile Money", channel_code="VODA_MPESA", is_active=True),
            PaymentProvider(name="Tigo Pesa", provider_type="Mobile Money", channel_code="TIGO_PESA", is_active=True),
            PaymentProvider(name="Airtel Money", provider_type="Mobile Money", channel_code="AIRTEL_MONEY", is_active=True),
            PaymentProvider(name="HaloPesa", provider_type="Mobile Money", channel_code="HALOPESA", is_active=True),
            PaymentProvider(name="CRDB Bank", provider_type="Bank", channel_code="CRDB_DIRECT", is_active=True),
            PaymentProvider(name="NMB Bank", provider_type="Bank", channel_code="NMB_DIRECT", is_active=True)
        ]
        db.add_all(providers)
        db.flush()

        # 9. Administrative & Portal Users
        u_admin = User(
            username="admin@taxrahisi.go.tz",
            email="admin@taxrahisi.go.tz",
            phone_number="+255700000001",
            full_name="Dr. Emmanuel Mwakyusa (Kamishna wa Mapato)",
            password_hash=hash_password("Admin@2026"),
            role_id=role_map["super_admin"],
            is_active=True
        )
        u_officer = User(
            username="officer@tra.go.tz",
            email="officer@tra.go.tz",
            phone_number="+255700000002",
            full_name="Mariam Mtoro (Afisa Kodi Mwandamizi - Ilala)",
            password_hash=hash_password("Officer@2026"),
            role_id=role_map["revenue_officer"],
            is_active=True
        )
        u_assoc_vibindo = User(
            username="vibindo@taxrahisi.or.tz",
            email="vibindo@taxrahisi.or.tz",
            phone_number="+255754112233",
            full_name="Gaston Kikuwi (Mwenyekiti VIBINDO)",
            password_hash=hash_password("Vibindo@2026"),
            role_id=role_map["association_admin"],
            is_active=True
        )
        u_agent = User(
            username="agent.juma@taxrahisi.or.tz",
            email="agent.juma@taxrahisi.or.tz",
            phone_number="+255711223344",
            full_name="Juma Selemani Bakari (Wakala wa VIBINDO)",
            password_hash=hash_password("Agent@2026"),
            role_id=role_map["association_agent"],
            is_active=True
        )
        db.add_all([u_admin, u_officer, u_assoc_vibindo, u_agent])
        db.flush()

        agent_record = AssociationAgent(
            user_id=u_agent.id,
            association_id=assoc_vibindo.id,
            agent_code="AGT-VIB-001",
            national_id="19870512-11102-00005-44",
            phone_number=u_agent.phone_number,
            assigned_market_id=m_kariakoo.id,
            is_authorized=True
        )
        db.add(agent_record)
        db.flush()

        # 10. Sample Traders (Taxpayers)
        # Trader 1: Mama Neema (Kariakoo)
        u_neema = User(
            username="0755123456",
            email="neema.mwamba@gmail.com",
            phone_number="0755123456",
            full_name="Neema Mwamba (Mama Neema)",
            password_hash=hash_password("Neema@2026"),
            role_id=role_map["taxpayer"],
            is_active=True
        )
        db.add(u_neema)
        db.flush()

        tp_neema = Taxpayer(
            user_id=u_neema.id,
            tin="142-984-102",
            registration_reference="TR-REG-2026-0001",
            nida_number="19850412-11101-00001-23",
            full_name=u_neema.full_name,
            phone_number=u_neema.phone_number,
            email=u_neema.email,
            region_id=r_dsm.id,
            district_id=dist_ilala.id,
            compliance_status="COMPLIANT",
            is_mlipakodi_bora=True,
            photo_path="images/mama_neema.jpg"
        )
        db.add(tp_neema)
        db.flush()

        biz_neema = Business(
            taxpayer_id=tp_neema.id,
            name="Mama Neema Food Stall & Catering",
            category_id=categories[0].id, # Food
            market_id=m_kariakoo.id,
            stall_number="KAR-ST-402",
            estimated_annual_turnover=6500000.0,
            has_accounting_records=False,
            status="ACTIVE"
        )
        db.add(biz_neema)
        db.flush()

        db.add(AssociationMember(
            association_id=assoc_vibindo.id,
            taxpayer_id=tp_neema.id,
            membership_number="MEM-VIB-0142",
            is_active=True
        ))

        # Assessment for Mama Neema: 6.5M -> 100k
        asm_neema = TaxAssessment(
            assessment_number="ASM-2026-0001",
            taxpayer_id=tp_neema.id,
            business_id=biz_neema.id,
            period_id=period_2026.id,
            band_id=bands[1].id, # Band 2 (100k)
            assessed_turnover=6500000.0,
            total_tax_liability=100000.0,
            amount_paid=50000.0,
            balance_due=50000.0,
            status="ACTIVE",
            explanation="Band 2 (TZS 4M - 7M): Kiwango maalum cha TZS 100,000 bila vitabu vya hesabu."
        )
        db.add(asm_neema)
        db.flush()

        # Payments for Mama Neema: 2 installments of 25k = 50k
        pay1 = Payment(
            control_number="991240091823",
            taxpayer_id=tp_neema.id,
            assessment_id=asm_neema.id,
            provider_id=providers[0].id, # M-Pesa
            amount=25000.0,
            installment_type="Robo ya 1 (Q1)",
            transaction_reference="TRX-TZ-2601150930-101",
            external_trx_id="MPESA-MP260115.9812",
            status="SUCCESSFUL",
            payment_date=datetime.datetime(2026, 1, 15, 9, 30),
            payer_phone=tp_neema.phone_number
        )
        pay2 = Payment(
            control_number="991240091824",
            taxpayer_id=tp_neema.id,
            assessment_id=asm_neema.id,
            provider_id=providers[1].id, # Tigo Pesa
            amount=25000.0,
            installment_type="Robo ya 2 (Q2)",
            transaction_reference="TRX-TZ-2604101415-102",
            external_trx_id="TIGO-TP260410.1420",
            status="SUCCESSFUL",
            payment_date=datetime.datetime(2026, 4, 10, 14, 15),
            payer_phone=tp_neema.phone_number
        )
        db.add_all([pay1, pay2])
        db.flush()

        db.add(DigitalReceipt(
            receipt_number="TR-RCPT-2026-000101",
            payment_id=pay1.id,
            verification_hash=generate_verification_hash(pay1.transaction_reference, tp_neema.tin, 25000.0),
            taxpayer_name=tp_neema.full_name,
            taxpayer_tin=tp_neema.tin,
            amount_paid=25000.0,
            control_number=pay1.control_number,
            issued_at=pay1.payment_date
        ))
        db.add(DigitalReceipt(
            receipt_number="TR-RCPT-2026-000102",
            payment_id=pay2.id,
            verification_hash=generate_verification_hash(pay2.transaction_reference, tp_neema.tin, 25000.0),
            taxpayer_name=tp_neema.full_name,
            taxpayer_tin=tp_neema.tin,
            amount_paid=25000.0,
            control_number=pay2.control_number,
            issued_at=pay2.payment_date
        ))

        # Trader 2: Juma Rashid (Mwenge Crafts)
        u_juma = User(
            username="0712345678",
            email="juma.mchinga@gmail.com",
            phone_number="0712345678",
            full_name="Juma Rashid (Mwenge Vinyago)",
            password_hash=hash_password("Juma@2026"),
            role_id=role_map["taxpayer"],
            is_active=True
        )
        db.add(u_juma)
        db.flush()

        tp_juma = Taxpayer(
            user_id=u_juma.id,
            tin="145-812-409",
            registration_reference="TR-REG-2026-0002",
            nida_number="19900824-11103-00002-88",
            full_name=u_juma.full_name,
            phone_number=u_juma.phone_number,
            region_id=r_dsm.id,
            district_id=dist_kinondoni.id,
            compliance_status="GRACE_PERIOD",
            photo_path="images/mwenge_artisan.jpg"
        )
        db.add(tp_juma)
        db.flush()

        biz_juma = Business(
            taxpayer_id=tp_juma.id,
            name="Mwenge Wood Carvings & African Art",
            category_id=categories[3].id, # Crafts
            market_id=m_mwenge.id,
            stall_number="MWN-CR-08",
            estimated_annual_turnover=9500000.0,
            has_accounting_records=True,
            status="ACTIVE"
        )
        db.add(biz_juma)
        db.flush()

        db.add(AssociationMember(
            association_id=assoc_uwawama.id,
            taxpayer_id=tp_juma.id,
            membership_number="MEM-UWA-0089",
            is_active=True
        ))

        # Grace period for Juma
        db.add(GracePeriod(
            taxpayer_id=tp_juma.id,
            duration_months=12,
            start_date=datetime.datetime.utcnow(),
            end_date=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            is_active=True,
            penalty_relief_granted=True,
            notes="Biashara mpya iliyosajiliwa Mwenge."
        ))

        # 11. Community Projects
        projects = [
            CommunityProject(
                association_id=assoc_vibindo.id,
                title="Mradi wa Usafi na Vyoo vya Kisasa Soko la Kariakoo",
                description="Uboreshaji wa mazingira, madumu ya taka na ujenzi wa vyoo vya kisasa kwa wajasiriamali.",
                budget=15000000.0,
                approved_expenditure=7500000.0,
                funding_source="Gawio la TaxRahisi (Revenue Sharing)",
                status="In Progress",
                completion_percentage=65,
                market_location="Soko Kuu la Kariakoo"
            ),
            CommunityProject(
                association_id=assoc_uwawama.id,
                title="Ulinzi Shirikishi na Taa za Sola Machinga Complex",
                description="Kuweka taa za sola na kuimarisha walinzi shirikishi ili kuwezesha biashara kufanyika hadi usiku.",
                budget=8000000.0,
                approved_expenditure=5000000.0,
                funding_source="Gawio la TaxRahisi (Revenue Sharing)",
                status="In Progress",
                completion_percentage=80,
                market_location="Machinga Complex Ilala"
            )
        ]
        db.add_all(projects)

        # 12. Educational Contents
        ed_contents = [
            EducationalContent(
                title="Kodi ya Makadirio (Presumptive Tax) ni Nini Chini ya Cap 332?",
                category="Presumptive Tax",
                language="sw",
                summary="Fahamu jinsi kodi ya makadirio inavyorahisisha ulipaji kodi kwa wajasiriamali wadogo bila uhasibu mgumu.",
                content_body="Kodi ya makadirio (Presumptive Tax) inasimamiwa chini ya Sheria ya Kodi ya Mapato, Sura ya 332. Inawalenga wafanyabiashara binafsi ambao mauzo yao kwa mwaka hayazidi TZS 200,000,000. Chini ya mfumo huu, mfanyabiashara anayepata chini ya TZS 4,000,000 halipi kodi yoyote (Bure). Kwa wenye mauzo ya 4M hadi 7M, kodi ni TZS 100,000 tu kwa mwaka mzima, au unafuu wa 3% ukiwa na vitabu vya kumbukumbu.",
                download_link="/education/download/1",
                published_by="TRA Directorate of Taxpayer Services",
                is_active=True
            ),
            EducationalContent(
                title="Jinsi ya Kutunza Vitabu vya Mapato na Matumizi Kupata Unafuu wa Kodi",
                category="Record Keeping",
                language="sw",
                summary="Mwongozo rahisi wa kijitabu cha mauzo (Cash Book) unaokuwezesha kupata punguzo la asilimia 3% ya kodi.",
                content_body="Kuweka rekodi za biashara hakuhitaji shahada ya uhasibu. Unachohitaji ni daftari rahisi la kuingiza mauzo ya kila siku (Cash Received) na matumizi ya biashara (Expenses). TRA inatambua rekodi hizi na kukupa unafuu wa kulipa kodi kulingana na faida halisi badala ya kiwango cha makadirio yasiyobadilika.",
                download_link="/education/download/2",
                published_by="TRA Taxpayer Education Department",
                is_active=True
            ),
            EducationalContent(
                title="Haki na Wajibu wa Mlipakodi wa Sekta Isiyo Rasmi",
                category="Taxpayer Rights",
                language="sw",
                summary="Tambua haki zako za kisheria unapotembelea ofisi za TRA au unapotembelewa na maofisa kodi masokoni.",
                content_body="Kama mlipakodi, una haki ya: 1. Kupata taarifa sahihi na kuelimishwa kwa lugha rahisi ya Kiswahili; 2. Kupewa risiti halali ya serikali (GePG); 3. Kukata rufaa au kuomba tathmini upya usiporidhika na makadirio; 4. Kuheshimiwa na kulindewa usiri wa taarifa zako za biashara.",
                download_link="/education/download/3",
                published_by="TRA Legal and Compliance Directorate",
                is_active=True
            ),
            EducationalContent(
                title="Mwongozo wa Malipo Kupitia GePG na Nambari ya Kumbukumbu (Control Number)",
                category="Payments",
                language="sw",
                summary="Hatua kwa hatua ya kulipia kodi yako kupitia Vodacom M-Pesa, Tigo Pesa, Airtel Money, au benki kwa simu.",
                content_body="Nambari ya Kumbukumbu ya Serikali (GePG Control Number) ni nambari maalum yenye tarakimu 12 inayoanza na 991. Ukishapata namba hii kwenye TaxRahisi au USSD *150*88#, unaingia kwenye menyu ya simu yako ya fedha, unachagua 'Lipa Bili', unachagua 'Kodi ya TRA', na kuweka Control Number. Pesa huenda moja kwa moja Hazina ya Serikali bila kupitia mkono wa mtu.",
                download_link="/education/download/4",
                published_by="Ministry of Finance & Planning GePG Unit",
                is_active=True
            )
        ]
        db.add_all(ed_contents)

        # 13. Audit Log
        db.add(AuditLog(
            actor_username="SYSTEM",
            action="DATABASE_INITIALIZED_AND_SEEDED",
            entity_type="SYSTEM",
            details="Seeded initial associations, markets, Cap 33Cap 332 bands, and pilot traders."
        ))

        db.commit()
        print("Database seeded successfully with realistic Tanzanian public-sector data!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
