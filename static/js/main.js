/**
 * TAXRAHISI — Official Digital Revenue Collection Platform
 * Client-Side Application JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 1. Dismissible alerts
    document.querySelectorAll('.alert-close').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var alert = this.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.remove();
                }, 200);
            }
        });
    });

    // 2. Client-Side Cap 332 Presumptive Tax Calculator
    var turnoverInput = document.getElementById('calc-turnover');
    var recordsCheckbox = document.getElementById('calc-records');
    var calcResultBox = document.getElementById('calc-result');

    function calculateTax() {
        if (!turnoverInput || !calcResultBox) return;
        var turnover = parseFloat(turnoverInput.value) || 0;
        var hasRecords = recordsCheckbox ? recordsCheckbox.checked : false;

        var tax = 0;
        var band = "";
        var explanation = "";

        if (turnover <= 4000000) {
            tax = 0;
            band = "Band 1 (Up to TZS 4,000,000)";
            explanation = "Exempt from presumptive income tax under Income Tax Act Cap 332.";
        } else if (turnover <= 7000000) {
            band = "Band 2 (TZS 4,000,001 – 7,000,000)";
            if (hasRecords) {
                tax = (turnover - 4000000) * 0.03;
                explanation = "3% of turnover exceeding TZS 4,000,000 (with records).";
            } else {
                tax = 100000;
                explanation = "Fixed rate of TZS 100,000 (without complete records).";
            }
        } else if (turnover <= 11000000) {
            band = "Band 3 (TZS 7,000,001 – 11,000,000)";
            if (hasRecords) {
                tax = 90000 + ((turnover - 7000000) * 0.03);
                explanation = "TZS 90,000 + 3% of turnover exceeding TZS 7,000,000 (with records).";
            } else {
                tax = 250000;
                explanation = "Fixed rate of TZS 250,000 (without complete records).";
            }
        } else if (turnover <= 200000000) {
            band = "Band 4 (TZS 11,000,001 – 200,000,000)";
            tax = turnover * 0.045;
            explanation = "4.5% of gross turnover under standard presumptive bracket (EFD required).";
        } else {
            band = "Standard Corporate / Individual Regime (> TZS 200,000,000)";
            tax = turnover * 0.30;
            explanation = "Turnover exceeds informal presumptive threshold (30% standard rate on net profits applies).";
        }

        var formattedTax = new Intl.NumberFormat('en-TZ', { style: 'currency', currency: 'TZS', maximumFractionDigits: 0 }).format(tax);
        var formattedTurnover = new Intl.NumberFormat('en-TZ', { style: 'currency', currency: 'TZS', maximumFractionDigits: 0 }).format(turnover);

        var html = `
            <div style="background:var(--gold-subtle); border:2px solid var(--gold-border); border-radius:8px; padding:16px;">
                <div style="font-size:0.85rem; color:var(--gold-dark); font-weight:800; text-transform:uppercase;">${band}</div>
                <div style="font-size:1.8rem; font-weight:900; color:var(--primary-dark); margin:6px 0;">${formattedTax}</div>
                <div style="font-size:0.85rem; color:var(--text-main);">${explanation}</div>
                <div style="margin-top:10px; font-size:0.8rem; color:var(--text-muted);">
                    Annual Turnover: <strong>${formattedTurnover}</strong> &bull; Records Maintained: <strong>${hasRecords ? 'Yes' : 'No'}</strong>
                </div>
            </div>
        `;
        calcResultBox.innerHTML = html;
    }

    if (turnoverInput) {
        turnoverInput.addEventListener('input', calculateTax);
    }
    if (recordsCheckbox) {
        recordsCheckbox.addEventListener('change', calculateTax);
    }

    // 3. Print receipt trigger
    var printBtn = document.getElementById('btn-print-receipt');
    if (printBtn) {
        printBtn.addEventListener('click', function() {
            window.print();
        });
    }

    // 4. Dropdown Navigation Menu Handler
    var dropdowns = document.querySelectorAll('.nav-dropdown');
    dropdowns.forEach(function(dropdown) {
        var toggle = dropdown.querySelector('.dropdown-toggle');
        if (toggle) {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                var isOpen = dropdown.classList.contains('open');
                // Close all other dropdowns
                dropdowns.forEach(function(d) { d.classList.remove('open'); });
                if (!isOpen) {
                    dropdown.classList.add('open');
                }
            });
        }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.nav-dropdown')) {
            dropdowns.forEach(function(d) { d.classList.remove('open'); });
        }
    });

    // Close dropdowns when pressing Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            dropdowns.forEach(function(d) { d.classList.remove('open'); });
        }
    });
});

