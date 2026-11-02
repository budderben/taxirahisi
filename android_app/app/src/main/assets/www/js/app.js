// TaxRahisi Mobile Application Logic
// Designed for Android WebView and Standalone Execution
// Integrated with Native AndroidBridge, Web Audio API, and Cap 332 Tax Engine
// THEME: Glassmorphism, 6-Month Grace Period Policy & Prototype Demo Accounts

let currentLang = 'sw';
let isOnline = false;
let serverBaseUrl = 'http://10.0.2.2:5000';
let audioEnabled = true;
let audioCtx = null;
let currentProfileKey = 'mama';

// Demo Profiles matching Website Prototype
const demoProfiles = {
    mama: {
        name: 'Neema Juma Mwangi',
        shortName: 'Mama Neema',
        phone: '0755123456',
        nida: '19850412-11101-00001-23',
        tin: '142-984-102',
        market: 'Soko Kuu Kariakoo',
        bizType: 'Mama Lishe (Chakula)',
        assoc: 'VIBINDO Society',
        photo: 'images/mama_neema.jpg',
        complianceStatus: 'HALI: AMELIPA KODI (COMPLIANT)',
        isGrace: false,
        taxTurnover: 6500000
    },
    juma: {
        name: 'Juma Rashid Bakari',
        shortName: 'Juma Hamisi',
        phone: '0712345678',
        nida: '19920815-22104-00003-45',
        tin: '149-802-331',
        market: 'Soko Kuu Kariakoo',
        bizType: 'Machinga (Nguo & Viatu)',
        assoc: 'UWAWAMA',
        photo: 'images/kariakoo_trader.jpg',
        complianceStatus: 'KIPINDI CHA NEEMA (MIEZI 6)',
        isGrace: true,
        taxTurnover: 9500000
    },
    vibindo: {
        name: 'John Aloyce Mrema',
        shortName: 'John Mrema (VIBINDO)',
        phone: '0784998877',
        nida: '19790210-31102-00002-11',
        tin: '140-552-901',
        market: 'Mwenge Crafts Market',
        bizType: 'Chama cha Wafanyabiashara',
        assoc: 'VIBINDO Society (Mwenyekiti)',
        photo: 'images/mwenge_artisan.jpg',
        complianceStatus: 'MRETOSHO: 3% GAWIO LA SOKO',
        isGrace: false,
        taxTurnover: 13000000
    },
    agent: {
        name: 'Juma Bakari Mwangi',
        shortName: 'Juma Bakari (Wakala)',
        phone: '0768222333',
        nida: '19901124-41103-00004-99',
        tin: '145-771-204',
        market: 'Machinga Complex Ilala',
        bizType: 'Wakala wa Ushuru Masokoni',
        assoc: 'TRA Market Field Agent',
        photo: 'images/kariakoo_trader.jpg',
        complianceStatus: 'WAKALA RASMI WA TRA',
        isGrace: false,
        taxTurnover: 6500000
    },
    admin: {
        name: 'Dr. Emmanuel Mwakyusa',
        shortName: 'Dr. Mwakyusa (TRA)',
        phone: '0754112233',
        nida: '19720518-10101-00001-02',
        tin: '100-001-000',
        market: 'TRA Headquarters Dar es Salaam',
        bizType: 'Kamishna wa Mapato ya Ndani',
        assoc: 'Tanzania Revenue Authority',
        photo: 'images/tra_icon.png',
        complianceStatus: 'TRA ADMINISTRATOR (KAMISHNA)',
        isGrace: false,
        taxTurnover: 25000000
    }
};

// Audio Context helper
function getAudioContext() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            audioCtx = new AudioContext();
        }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    return audioCtx;
}

// DTMF audio feedback synthesizer
function playKeyTone(key) {
    if (!audioEnabled) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;

        const dtmf = {
            '1': [697, 1209], '2': [697, 1336], '3': [697, 1477],
            '4': [770, 1209], '5': [770, 1336], '6': [770, 1477],
            '7': [852, 1209], '8': [852, 1336], '9': [852, 1477],
            '*': [941, 1209], '0': [941, 1336], '#': [941, 1477]
        };

        const now = ctx.currentTime;
        const freqs = dtmf[key] || [520, 800];

        freqs.forEach(f => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(f, now);
            gain.gain.setValueAtTime(0.08, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now);
            osc.stop(now + 0.12);
        });
    } catch (e) {
        console.warn('Audio feedback error:', e);
    }
}

function toggleAudio() {
    audioEnabled = !audioEnabled;
    const lbl = document.getElementById('audioStatusLbl');
    if (lbl) {
        lbl.innerText = audioEnabled ? 'Sauti: ON' : 'Sauti: OFF';
    }
    callNativeBridge('showToast', audioEnabled ? 'Mlio wa vitufe umewashwa' : 'Mlio wa vitufe umezimwa');
}

// Live Clock for Phone Screen
function updateClock() {
    const now = new Date();
    const hrs = String(now.getHours()).padStart(2, '0');
    const mins = String(now.getMinutes()).padStart(2, '0');
    const el = document.getElementById('lcdClock');
    if (el) el.innerText = hrs + ':' + mins;
}
setInterval(updateClock, 1000);
updateClock();

// Native Android Bridge Helper
function callNativeBridge(funcName, ...args) {
    if (window.AndroidBridge && typeof window.AndroidBridge[funcName] === 'function') {
        try {
            return window.AndroidBridge[funcName](...args);
        } catch (e) {
            console.error('AndroidBridge call failed:', e);
        }
    }
    return null;
}

// Multi-language Translations (Synchronized with 6-Month Grace Period)
const translations = {
    sw: {
        subtitle: 'Mamlaka ya Mapato Tanzania',
        calc_title: 'Kikokotoo cha Kodi ya Makadirio',
        calc_desc: 'Hesabu kodi yako kwa urahisi kulingana na mauzo yako ya mwaka chini ya Cap 332 na ufaidike na kipindi cha neema cha miezi sita (6).',
        turnover_label: 'Mauzo Yaliyokadiriwa kwa Mwaka (TZS):',
        record_toggle: 'Una rekodi za hesabu (Daftari la Mauzo)?',
        record_sub: 'Pata unafuu wa asilimia 3% ya mauzo',
        total_tax: 'KODI YA MWAKA (ANNUAL TAX):',
        quarterly: 'Robo Mwaka (Qtr)',
        monthly: 'Kila Mwezi',
        weekly: 'Kila Wiki',
        pay_via_gepg: 'Lipa kwa GePG',
        tax_rates_title: 'Viwango Rasmi vya Cap 332 R.E. 2023',
        reg_title: 'Pata TIN Yako Papo Hapo',
        grace_badge: 'Kipindi cha Neema (Grace Period) cha Miezi Sita:',
        grace_desc: 'Mara baada ya mfumo wa TaxRahisi kuanza kutumika, kutakuwa na kipindi cha neema cha miezi sita (6) kitakachowapa wafanyabiashara fursa ya kujisajili kwa hiari bila kutozwa faini au adhabu yoyote.',
        full_name: 'Jina Kamili la Mfanyabiashara:',
        phone_number: 'Namba ya Simu (M-Pesa / Tigo Pesa):',
        nida_number: 'Namba ya NIDA (Tarakimu 20):',
        market_loc: 'Soko / Eneo:',
        biz_type: 'Aina ya Biashara:',
        association: 'Chama cha Wafanyabiashara:',
        btn_register: 'Thibitisha NIDA na Toa TIN',
        nav_calc: 'Kodi',
        nav_reg: 'Sajili',
        nav_pay: 'Malipo',
        nav_card: 'Kadi'
    },
    en: {
        subtitle: 'Tanzania Revenue Authority',
        calc_title: 'Presumptive Tax Calculator',
        calc_desc: 'Calculate your annual tax liability transparently under Cap 332 and benefit from the 6-month statutory grace period.',
        turnover_label: 'Estimated Annual Turnover (TZS):',
        record_toggle: 'Do you keep business records (Sales Ledger)?',
        record_sub: 'Enjoy 3% statutory rate on turnover',
        total_tax: 'ANNUAL TAX LIABILITY:',
        quarterly: 'Quarterly',
        monthly: 'Monthly',
        weekly: 'Weekly',
        pay_via_gepg: 'Pay via GePG',
        tax_rates_title: 'Statutory Bands (Cap 332 R.E. 2023)',
        reg_title: 'Instant TIN Self-Registration',
        grace_badge: '6-Month Grace Period Relief Scheme:',
        grace_desc: 'Immediately after the TaxRahisi system goes live, there will be a six (6) month grace period giving traders who are not yet registered an opportunity to register voluntarily without fines or penalties.',
        full_name: 'Full Legal Name:',
        phone_number: 'Mobile Phone (M-Pesa / Tigo Pesa):',
        nida_number: 'NIDA Number (20 Digits):',
        market_loc: 'Market / Location:',
        biz_type: 'Business Sector:',
        association: 'Market Association / Union:',
        btn_register: 'Verify NIDA & Issue TIN',
        nav_calc: 'Tax',
        nav_reg: 'Register',
        nav_pay: 'Pay',
        nav_card: 'Card'
    }
};

function toggleLanguage() {
    currentLang = currentLang === 'sw' ? 'en' : 'sw';
    document.getElementById('currentLangLabel').innerText = currentLang.toUpperCase();

    const dict = translations[currentLang];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
            el.innerText = dict[key];
        }
    });

    const sub = document.getElementById('lbl-subtitle');
    if (sub) sub.innerText = dict.subtitle;

    callNativeBridge('showToast', currentLang === 'sw' ? 'Lugha imebadilishwa kuwa Kiswahili' : 'Language switched to English');
    callNativeBridge('vibrate', 20);
}

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    const targetTab = document.getElementById('tab-' + tabId);
    const targetNav = document.getElementById('nav-' + tabId);

    if (targetTab) targetTab.classList.add('active');
    if (targetNav) targetNav.classList.add('active');

    window.scrollTo(0, 0);
    callNativeBridge('vibrate', 25);
}

// Prototype Account Selection (Website Parity)
function selectDemoProfile(key) {
    if (!demoProfiles[key]) return;
    currentProfileKey = key;
    const p = demoProfiles[key];

    // Update active chip
    document.querySelectorAll('.demo-chip').forEach(btn => btn.classList.remove('active'));
    const activeChip = document.getElementById('demo-' + key);
    if (activeChip) activeChip.classList.add('active');

    // Update registration form fields
    const regName = document.getElementById('regFullName');
    const regPhone = document.getElementById('regPhone');
    const regNida = document.getElementById('regNida');
    if (regName) regName.value = p.name;
    if (regPhone) regPhone.value = p.phone;
    if (regNida) regNida.value = p.nida;

    // Update digital card
    const cName = document.getElementById('cardName');
    const cTin = document.getElementById('cardTin');
    const cBiz = document.getElementById('cardBiz');
    const cMarket = document.getElementById('cardMarket');
    const cAssoc = document.getElementById('cardAssoc');
    const cPhoto = document.getElementById('cardPhoto');
    const cStatus = document.getElementById('cardComplianceText');

    if (cName) cName.innerText = p.name;
    if (cTin) cTin.innerText = p.tin;
    if (cBiz) cBiz.innerText = p.bizType;
    if (cMarket) cMarket.innerText = p.market;
    if (cAssoc) cAssoc.innerText = p.assoc;
    if (cPhoto) cPhoto.src = p.photo;
    if (cStatus) cStatus.innerText = p.complianceStatus;

    // Update USSD persona select
    const ussdSel = document.getElementById('personaSelect');
    if (ussdSel) {
        for (let i = 0; i < ussdSel.options.length; i++) {
            if (ussdSel.options[i].value === p.phone) {
                ussdSel.selectedIndex = i;
                break;
            }
        }
    }
    ussdState.name = p.shortName;
    ussdState.phone = p.phone;
    resetUssdSession();

    // Update calculator turnover
    if (p.taxTurnover) {
        const tInput = document.getElementById('calcTurnover');
        if (tInput) {
            tInput.value = p.taxTurnover;
            calculateTax();
        }
    }

    callNativeBridge('showToast', 'Akaunti: ' + p.name + ' imechaguliwa');
    callNativeBridge('vibrate', 25);
}

// Cap 332 Tax Calculation Engine
function calculateTax() {
    const turnoverInput = document.getElementById('calcTurnover');
    const category = document.getElementById('calcCategory') ? document.getElementById('calcCategory').value : 'general';
    const hasRecords = document.getElementById('calcHasRecords').checked;
    const turnover = parseFloat(turnoverInput.value) || 0;

    let totalTax = 0;
    let bandName = 'Band 1';

    // Specific flat rates under Cap 332
    if (category === 'bodaboda') {
        totalTax = 65000;
        bandName = 'Bodaboda Flat (Cap 332)';
    } else if (category === 'bajaj') {
        totalTax = 120000;
        bandName = 'Bajaj Flat (Cap 332)';
    } else if (category === 'daladala') {
        totalTax = 250000;
        bandName = 'Daladala Flat (Cap 332)';
    } else if (category === 'lori') {
        totalTax = 450000;
        bandName = 'Lori Tani 1-3 Flat (Cap 332)';
    } else {
        // General Presumptive Schedule
        if (turnover <= 4000000) {
            totalTax = 0;
            bandName = 'Band 1 (Bure / NIL)';
        } else if (turnover <= 7000000) {
            bandName = 'Band 2 (4M - 7M)';
            totalTax = hasRecords ? (turnover - 4000000) * 0.03 : 100000;
        } else if (turnover <= 11000000) {
            bandName = 'Band 3 (7M - 11M)';
            totalTax = hasRecords ? (90000 + (turnover - 7000000) * 0.03) : 250000;
        } else {
            bandName = 'Band 4 (11M - 200M)';
            totalTax = turnover * 0.04;
        }
    }

    const quarterly = Math.round(totalTax / 4);
    const monthly = Math.round(totalTax / 12);
    const weekly = Math.round(totalTax / 52);
    const marketShare = Math.round(totalTax * 0.03);

    document.getElementById('totalTaxDisplay').innerText = 'TZS ' + Math.round(totalTax).toLocaleString();
    document.getElementById('taxBandBadge').innerText = bandName;
    document.getElementById('quarterlyDisplay').innerText = 'TZS ' + quarterly.toLocaleString();
    document.getElementById('monthlyDisplay').innerText = 'TZS ' + monthly.toLocaleString();
    document.getElementById('weeklyDisplay').innerText = 'TZS ' + weekly.toLocaleString();

    const mkt = document.getElementById('marketShareDisplay');
    if (mkt) mkt.innerText = marketShare.toLocaleString();

    window.currentCalculatedQuarterly = quarterly;
}

function setPresetTurnover(val) {
    document.getElementById('calcTurnover').value = val;
    if (document.getElementById('calcCategory')) {
        document.getElementById('calcCategory').value = 'general';
    }
    document.querySelectorAll('.chip').forEach(btn => btn.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
    calculateTax();
    callNativeBridge('vibrate', 15);
}

function transferToPayment() {
    const amount = window.currentCalculatedQuarterly || 25000;
    document.getElementById('payAmount').value = amount > 0 ? amount : 25000;
    generateNewControlNumber();
    switchTab('payments');
    callNativeBridge('showToast', 'Kiasi cha kodi kimehamishwa kwenye mfumo wa malipo.');
}

// ==============================================================================
// USSD ENGINE (BUTTON PHONE / SIMU YA KITOCHI)
// ==============================================================================
let ussdState = {
    screen: 'IDLE',
    phone: '0755123456',
    name: 'Mama Neema',
    history: []
};

function onPersonaChange() {
    const sel = document.getElementById('personaSelect');
    ussdState.phone = sel.value;
    const opt = sel.options[sel.selectedIndex].text;
    ussdState.name = opt.split('(')[0].trim();
    resetUssdSession();
    callNativeBridge('showToast', 'Mtumiaji: ' + ussdState.name);
}

function renderUssdScreen() {
    const display = document.getElementById('lcdTextDisplay');
    const softLeft = document.getElementById('lcdSoftLeft');
    const softRight = document.getElementById('lcdSoftRight');

    softLeft.innerText = '[ SAWA ]';
    softRight.innerText = '[ FUTA ]';

    switch (ussdState.screen) {
        case 'IDLE':
            display.innerText = 'MAMLAKA YA MAPATO (TRA)\nKaribu TaxRahisi USSD\n-----------------------\nPiga *152*00# kuanza\nau bofya kitufe cha PIGA';
            softLeft.innerText = '[ PIGA ]';
            softRight.innerText = '[ ZIMA ]';
            break;
        case 'ROOT':
            display.innerText = 'Karibu TaxRahisi (TRA)\n1. Sajili Biashara (TIN)\n2. Lipa Kodi (GePG)\n3. Angalia Bakaa & Risiti\n4. Gawio la Soko (3%)\n5. Elimu ya Neema (Miezi 6)\n6. Ripoti Changamoto\n0. English';
            break;
        case 'REG_NIDA':
            display.innerText = 'Weka namba yako ya NIDA ya tarakimu 20:\n(Mfano: 19850412111010000123)';
            break;
        case 'REG_MARKET':
            display.innerText = 'NIDA Imethibitishwa: ' + ussdState.name + '\nChagua Soko Lako:\n1. Kariakoo\n2. Mwenge\n3. Ilala Complex\n4. Buguruni';
            break;
        case 'REG_DONE':
            display.innerText = 'Hongera! Biashara Imesajiliwa.\nTIN Yako Mpya: 149-802-331.\nKipindi cha neema cha miezi 6 kimeidhinishwa bila faini.\nLipa kodi kwa *152*00#.';
            softLeft.innerText = '[ SAWA ]';
            softRight.innerText = '[ MENU ]';
            break;
        case 'PAY_TIN':
            display.innerText = 'Weka Namba ya TIN ya Biashara:\n(Mfano: 142984102)';
            break;
        case 'PAY_CONFIRM':
            display.innerText = 'Kodi ya Robo 1: TZS 25,000\nControl No: 991240091823\nWeka PIN ya M-Pesa kuthibitisha:';
            break;
        case 'PAY_DONE':
            display.innerText = 'Umefanikiwa kulipa TZS 25,000 kwa TRA.\nRisiti: TRX-TZ-88492.\nGawio la Soko lako (3%): TZS 750.\nKadi yako imesasishwa.';
            break;
        case 'BALANCE':
            display.innerText = ussdState.name + '\nTIN: 142-984-102\nBakaa ya Kodi: TZS 0 (Umefuta)\nHali: AMELIPA KODI (Hai)\nNafuu ya miezi 6 imeunganishwa.\nAsante kwa kujenga Taifa!';
            break;
        case 'MARKET_SHARE':
            display.innerText = 'UBIA WA TRA NA VYAMA (3%):\nAsilimia 3% ya kodi inarejeshwa kwa soko lako kwa miradi ya:\n- Taa za Sola na Ulinzi\n- Usafi na Vyoo vya Kisasa.';
            break;
        case 'EDUCATION':
            display.innerText = 'ELIMU YA KODI & KIPINDI CHA NEEMA:\n- Miezi 6 ya Neema: Jisajili bila faini au adhabu yoyote.\n- Hadi 4M: Bure (0 TZS)\n- 4M-7M: 100k au 3%\n- 7M-11M: 250k au 90k+3%\n- Zaidi ya 11M: 4.0%';
            softLeft.innerText = '[ SAWA ]';
            softRight.innerText = '[ MENU ]';
            break;
        case 'COMPLAINT':
            display.innerText = 'DAWATI LA MALALAMIKO TRA:\n1. Kukadiria isivyo halali\n2. Afisa kutoa lugha chafu\n3. Tatizo la GePG\nSimu Bure: 0800 110 016.';
            break;
    }
}

function handleSoftLeft() {
    playKeyTone('5');
    callNativeBridge('vibrate', 25);

    if (ussdState.screen === 'IDLE') {
        handleCall();
        return;
    }

    const input = document.getElementById('lcdInputField');
    const val = input.value.trim();
    input.value = '';

    if (ussdState.screen === 'ROOT') {
        if (val === '1') ussdState.screen = 'REG_NIDA';
        else if (val === '2') ussdState.screen = 'PAY_TIN';
        else if (val === '3') ussdState.screen = 'BALANCE';
        else if (val === '4') ussdState.screen = 'MARKET_SHARE';
        else if (val === '5') ussdState.screen = 'EDUCATION';
        else if (val === '6') ussdState.screen = 'COMPLAINT';
        else if (val === '0') {
            toggleLanguage();
            ussdState.screen = 'ROOT';
        } else {
            callNativeBridge('showToast', 'Chaguo si sahihi.');
        }
    } else if (ussdState.screen === 'REG_NIDA') {
        ussdState.screen = 'REG_MARKET';
    } else if (ussdState.screen === 'REG_MARKET') {
        ussdState.screen = 'REG_DONE';
    } else if (ussdState.screen === 'PAY_TIN') {
        ussdState.screen = 'PAY_CONFIRM';
    } else if (ussdState.screen === 'PAY_CONFIRM') {
        ussdState.screen = 'PAY_DONE';
    } else {
        ussdState.screen = 'ROOT';
    }

    renderUssdScreen();
}

function handleSoftRight() {
    playKeyTone('#');
    callNativeBridge('vibrate', 20);

    const input = document.getElementById('lcdInputField');
    if (input.value.length > 0) {
        input.value = input.value.slice(0, -1);
    } else {
        if (ussdState.screen !== 'IDLE' && ussdState.screen !== 'ROOT') {
            ussdState.screen = 'ROOT';
            renderUssdScreen();
        } else if (ussdState.screen === 'ROOT') {
            handleEnd();
        }
    }
}

function handleCall() {
    playKeyTone('3');
    callNativeBridge('vibrate', 35);
    const input = document.getElementById('lcdInputField');
    const val = input.value.trim();

    if (ussdState.screen === 'IDLE' || val === '*152*00#' || val === '*222#' || val === '*150*88#') {
        input.value = '';
        ussdState.screen = 'ROOT';
        renderUssdScreen();
    } else {
        handleSoftLeft();
    }
}

function handleEnd() {
    playKeyTone('*');
    callNativeBridge('vibrate', 40);
    ussdState.screen = 'IDLE';
    document.getElementById('lcdInputField').value = '';
    renderUssdScreen();
}

function pressKey(num) {
    playKeyTone(num);
    const input = document.getElementById('lcdInputField');
    input.value += num;
    callNativeBridge('vibrate', 18);
}

function resetUssdSession() {
    handleEnd();
}

function dialNativeUssd(code) {
    callNativeBridge('vibrate', 35);
    const success = callNativeBridge('dialUssd', code);
    if (!success) {
        window.location.href = 'tel:' + encodeURIComponent(code);
    }
}

// Registration Form Handler (With 6-Month Grace Period)
function handleRegistration(e) {
    e.preventDefault();
    const name = document.getElementById('regFullName').value;
    const phone = document.getElementById('regPhone').value;
    const market = document.getElementById('regMarket').value;
    const bizType = document.getElementById('regBizType').value;
    const assoc = document.getElementById('regAssoc').value;

    const randomTin = '14' + Math.floor(1000000 + Math.random() * 9000000).toString().replace(/(\d{3})(\d{3})(\d{3})/, '$1-$2-$3');

    document.getElementById('resName').innerText = name;
    document.getElementById('resTin').innerText = randomTin;
    document.getElementById('resAssoc').innerText = assoc;

    document.getElementById('regSuccessCard').classList.remove('hidden');

    // Update Digital ID Card
    document.getElementById('cardName').innerText = name;
    document.getElementById('cardTin').innerText = randomTin;
    document.getElementById('cardBiz').innerText = bizType;
    document.getElementById('cardMarket').innerText = market + ' Market';
    document.getElementById('cardAssoc').innerText = assoc;
    const cStatus = document.getElementById('cardComplianceText');
    if (cStatus) cStatus.innerText = 'KIPINDI CHA NEEMA (MIEZI 6)';

    callNativeBridge('showToast', 'Hongera! TIN: ' + randomTin + ' imetolewa na miezi 6 ya neema imeidhinishwa.');
    callNativeBridge('vibrate', 60);
}

function viewGeneratedCard() {
    switchTab('card');
}

// GePG Payment Simulation
function generateNewControlNumber() {
    const ctrl = '991' + Math.floor(100000000 + Math.random() * 900000000);
    document.getElementById('payControlNumber').value = ctrl;
    callNativeBridge('vibrate', 20);
    callNativeBridge('showToast', 'Namba Mpya ya GePG Control imetengenezwa.');
}

function triggerPaymentSimulation() {
    const ctrl = document.getElementById('payControlNumber').value;
    const amount = document.getElementById('payAmount').value || '25000';
    const providerRadio = document.querySelector('input[name="payProvider"]:checked');
    const provider = providerRadio ? providerRadio.value : 'M-Pesa';
    const trader = (document.getElementById('cardName') && document.getElementById('cardName').innerText) || 'Mama Neema';
    const tin = (document.getElementById('cardTin') && document.getElementById('cardTin').innerText) || '142-984-102';

    callNativeBridge('vibrate', 60);

    const now = new Date();
    const dateStr = now.toLocaleDateString('sw-TZ') + ' ' + now.toLocaleTimeString('sw-TZ');
    const txId = 'TZ-GEPG-' + Math.floor(10000000 + Math.random() * 90000000);
    const parsedAmount = parseInt(amount) || 25000;
    const marketShare = Math.round(parsedAmount * 0.03);

    document.getElementById('rcptDate').innerText = dateStr;
    document.getElementById('rcptCtrl').innerText = ctrl;
    document.getElementById('rcptTrader').innerText = trader;
    document.getElementById('rcptTin').innerText = tin;
    document.getElementById('rcptAmount').innerText = 'TZS ' + parsedAmount.toLocaleString();
    document.getElementById('rcptProvider').innerText = provider;
    document.getElementById('rcptTxId').innerText = txId;
    document.getElementById('rcptMarketShare').innerText = 'TZS ' + marketShare.toLocaleString();

    const receipt = document.getElementById('receiptCard');
    receipt.classList.remove('hidden');
    callNativeBridge('showToast', 'Malipo ya GePG yamekamilika! Risiti imetolewa.');
    callNativeBridge('vibrate', 100);

    setTimeout(() => {
        receipt.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 150);
}

function shareOfficialReceipt() {
    const ctrl = document.getElementById('rcptCtrl').innerText;
    const amount = document.getElementById('rcptAmount').innerText;
    const txId = document.getElementById('rcptTxId').innerText;
    const trader = document.getElementById('rcptTrader').innerText;
    const share = document.getElementById('rcptMarketShare').innerText;

    const receiptText = '*MAMLAKA YA MAPATO TANZANIA (TRA)*\nSTAKABADHI YA MALIPO YA KODI (GePG)\n\nMlipaji: ' + trader + '\nControl No: ' + ctrl + '\nKiasi: ' + amount + '\nTransaction ID: ' + txId + '\nGawio la Soko (3%): ' + share + '\nHali: IMELIPWA KIKAMILIFU\n\nImetolewa kupitia TaxRahisi Mobile App.';

    const shared = callNativeBridge('shareText', 'Stakabadhi ya Kodi TRA', receiptText);
    if (!shared && navigator.share) {
        navigator.share({
            title: 'Stakabadhi ya Kodi TRA',
            text: receiptText
        }).catch(err => console.log('Share canceled'));
    }
}

function shareDigitalCard() {
    const name = document.getElementById('cardName').innerText;
    const tin = document.getElementById('cardTin').innerText;
    const assoc = document.getElementById('cardAssoc').innerText;

    const cardText = '*KADI YA MLIPAKODI WA SEKTA ISIYO RASMI (TRA)*\nJina: ' + name + '\nTIN: ' + tin + '\nChama: ' + assoc + '\nHali: AMELIPA KODI (COMPLIANT / MIEZI 6 NEEMA)\n\nImehakikiwa na Mfumo wa TaxRahisi Tanzania.';

    callNativeBridge('shareText', 'Kadi ya Mlipakodi TRA', cardText);
}

function verifyCardOnline() {
    const tin = document.getElementById('cardTin').innerText;
    callNativeBridge('showToast', 'Inahakiki TIN: ' + tin + ' kwenye kanzidata ya TRA...');
    callNativeBridge('vibrate', 30);
    setTimeout(() => {
        alert('Uhakiki wa TRA:\n\nTIN: ' + tin + '\nHali: INAFAA & HALALI (COMPLIANT)\nMlipakodi anafaidika na unafuu wa Kipindi cha Neema cha Miezi Sita (6) chini ya Sheria ya Kodi ya Mapato (Sura ya 332 R.E. 2023).');
    }, 600);
}

// Server Connection Settings
function toggleServerModal() {
    const modal = document.getElementById('serverModal');
    modal.classList.toggle('hidden');
}

function testServerConnection() {
    const url = document.getElementById('serverUrlInput').value.trim();
    callNativeBridge('showToast', 'Inajaribu kuunganisha: ' + url);

    fetch(url + '/api/v1/ussd/gateway', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'sessionId=test&phoneNumber=+255755123456&text='
    })
    .then(res => res.text())
    .then(text => {
        isOnline = true;
        document.getElementById('connStatusLabel').innerText = 'Online';
        callNativeBridge('showToast', 'Imeunganishwa na Seva ya TaxRahisi!');
        toggleServerModal();
    })
    .catch(err => {
        alert('Haikuweza kuunganishwa na seva ya mtandao: ' + err.message + '\nMfumo utaendelea kufanya kazi Offline bila intaneti.');
    });
}

// Initial Run
window.addEventListener('DOMContentLoaded', () => {
    calculateTax();
    renderUssdScreen();
    selectDemoProfile('mama');
});
