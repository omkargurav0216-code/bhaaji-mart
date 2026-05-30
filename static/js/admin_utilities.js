/**
 * Bhaaji Mart - Admin Quick Utility Panel JS
 * Handles panel display, tab toggles, drag-and-drop, calculators, and accessibility features.
 */

document.addEventListener('DOMContentLoaded', () => {
    const fab = document.getElementById('admin-utility-fab');
    const panel = document.getElementById('admin-utility-panel');
    const header = document.getElementById('admin-utility-header');
    const closeBtn = document.getElementById('admin-utility-close');
    const minimizeBtn = document.getElementById('admin-utility-minimize');
    
    if (!fab || !panel) return;

    // --- State Variables ---
    let isMinimized = false;
    let dragStartX = 0, dragStartY = 0;
    let panelStartX = 0, panelStartY = 0;
    let isDragging = false;

    // --- Open / Close Toggle ---
    function openPanel() {
        panel.classList.remove('hidden');
        panel.focus();
        fab.setAttribute('aria-expanded', 'true');
        // If it was positioned out of viewport, reset it
        ensureViewportContainment();
    }

    function closePanel() {
        panel.classList.add('hidden');
        fab.setAttribute('aria-expanded', 'false');
        fab.focus();
    }

    fab.addEventListener('click', (e) => {
        e.stopPropagation();
        if (panel.classList.contains('hidden')) {
            openPanel();
        } else {
            closePanel();
        }
    });

    closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closePanel();
    });

    // --- Minimize Toggle ---
    minimizeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        isMinimized = !isMinimized;
        if (isMinimized) {
            panel.classList.add('minimized');
            minimizeBtn.title = "Expand";
            minimizeBtn.setAttribute('aria-label', 'Expand panel');
            minimizeBtn.querySelector('svg').innerHTML = '<line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line>';
        } else {
            panel.classList.remove('minimized');
            minimizeBtn.title = "Minimize";
            minimizeBtn.setAttribute('aria-label', 'Minimize panel');
            minimizeBtn.querySelector('svg').innerHTML = '<line x1="5" y1="12" x2="19" y2="12"></line>';
        }
    });

    // Close on ESC key
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !panel.classList.contains('hidden')) {
            closePanel();
        }
    });

    // --- Draggable Header System ---
    header.addEventListener('mousedown', startDrag);
    header.addEventListener('touchstart', startDrag, { passive: true });

    function startDrag(e) {
        // Only allow dragging on desktop
        if (window.innerWidth <= 768) return;
        
        // Don't drag if clicking buttons
        if (e.target.closest('.header-btn')) return;

        isDragging = true;
        panel.classList.add('dragging');

        const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

        // Get initial positioning style
        const rect = panel.getBoundingClientRect();
        panelStartX = rect.left;
        panelStartY = rect.top;

        dragStartX = clientX;
        dragStartY = clientY;

        // Temporarily clear bottom/right positioning to use top/left for dragging
        panel.style.bottom = 'auto';
        panel.style.right = 'auto';
        panel.style.left = `${panelStartX}px`;
        panel.style.top = `${panelStartY}px`;

        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', stopDrag);
        document.addEventListener('touchmove', drag, { passive: false });
        document.addEventListener('touchend', stopDrag);
    }

    function drag(e) {
        if (!isDragging) return;

        // Prevent window scrolling on touch move
        if (e.type.startsWith('touch')) {
            e.preventDefault();
        }

        const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

        const dx = clientX - dragStartX;
        const dy = clientY - dragStartY;

        let newX = panelStartX + dx;
        let newY = panelStartY + dy;

        // Bounds constraints
        const rect = panel.getBoundingClientRect();
        const maxX = window.innerWidth - rect.width;
        const maxY = window.innerHeight - rect.height;

        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));

        panel.style.left = `${newX}px`;
        panel.style.top = `${newY}px`;
    }

    function stopDrag() {
        isDragging = false;
        panel.classList.remove('dragging');
        document.removeEventListener('mousemove', drag);
        document.removeEventListener('mouseup', stopDrag);
        document.removeEventListener('touchmove', drag);
        document.removeEventListener('touchend', stopDrag);
    }

    function ensureViewportContainment() {
        if (window.innerWidth <= 768) {
            // Reset mobile positioning styles
            panel.style.left = '';
            panel.style.top = '';
            panel.style.bottom = '';
            panel.style.right = '';
            return;
        }
        
        const rect = panel.getBoundingClientRect();
        if (panel.style.left) {
            let left = parseFloat(panel.style.left);
            let top = parseFloat(panel.style.top);
            const maxX = window.innerWidth - rect.width;
            const maxY = window.innerHeight - rect.height;

            left = Math.max(0, Math.min(left, maxX));
            top = Math.max(0, Math.min(top, maxY));

            panel.style.left = `${left}px`;
            panel.style.top = `${top}px`;
        }
    }

    window.addEventListener('resize', ensureViewportContainment);

    // --- Tab System ---
    const tabs = panel.querySelectorAll('.tab-link');
    const panes = panel.querySelectorAll('.tab-pane');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            panes.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            tab.setAttribute('aria-selected', 'true');
            
            const paneId = tab.getAttribute('aria-controls');
            const targetPane = document.getElementById(paneId);
            if (targetPane) {
                targetPane.classList.add('active');
                // Auto focus first input if applicable
                const firstInput = targetPane.querySelector('input');
                if (firstInput) firstInput.focus();
            }
        });
    });

    // --- Tab Focus Trapping ---
    panel.addEventListener('keydown', (e) => {
        if (e.key !== 'Tab') return;
        
        const focusables = panel.querySelectorAll('button:not([disabled]), input:not([disabled]), [tabindex="0"]');
        if (focusables.length === 0) return;

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
            if (document.activeElement === first) {
                last.focus();
                e.preventDefault();
            }
        } else {
            if (document.activeElement === last) {
                first.focus();
                e.preventDefault();
            }
        }
    });


    // ==========================================
    // TAB 1: STANDARD CALCULATOR
    // ==========================================
    const calcScreen = document.getElementById('calc-screen');
    const calcExpression = document.getElementById('calc-expression');
    const calcButtons = panel.querySelectorAll('.calc-btn');
    
    let currentInput = '';
    let previousInput = '';
    let operation = null;
    let shouldResetScreen = false;

    calcButtons.forEach(button => {
        button.addEventListener('click', () => {
            const val = button.getAttribute('data-val');
            handleCalcInput(val);
            button.blur(); // Remove focus outline to keep clean UI
        });
    });

    // Calculator Keyboard Listener (only when calculator tab is visible)
    window.addEventListener('keydown', (e) => {
        const calcPane = document.getElementById('calc-tab');
        if (!calcPane || !calcPane.classList.contains('active') || panel.classList.contains('hidden')) return;

        let key = e.key;
        if (key === 'Enter') key = '=';
        if (key === 'Escape') key = 'C';
        if (key === 'Delete') key = 'C';
        
        const validKeys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '+', '-', '*', '/', '%', '=', 'Backspace', 'C'];
        if (validKeys.includes(key)) {
            e.preventDefault();
            handleCalcInput(key);
        }
    });

    function handleCalcInput(val) {
        if (val === 'C') {
            currentInput = '';
            previousInput = '';
            operation = null;
            calcScreen.textContent = '0';
            calcExpression.textContent = '';
        } else if (val === 'Backspace') {
            if (currentInput) {
                currentInput = currentInput.slice(0, -1);
                calcScreen.textContent = currentInput || '0';
            }
        } else if (val === 'Copy') {
            copyToClipboard(calcScreen.textContent);
        } else if (['+', '-', '*', '/', '%'].includes(val)) {
            if (currentInput === '' && previousInput === '') return;
            if (currentInput === '') {
                operation = val;
                calcExpression.textContent = `${previousInput} ${getOpSymbol(val)}`;
                return;
            }
            if (previousInput !== '') {
                calculate();
            } else {
                previousInput = currentInput;
            }
            operation = val;
            calcExpression.textContent = `${previousInput} ${getOpSymbol(val)}`;
            shouldResetScreen = true;
            currentInput = '';
        } else if (val === '=') {
            if (currentInput === '' || previousInput === '' || !operation) return;
            calcExpression.textContent = `${previousInput} ${getOpSymbol(operation)} ${currentInput} =`;
            calculate();
            operation = null;
            previousInput = '';
            shouldResetScreen = true;
        } else {
            // Numbers & Decimal Point
            if (val === '.' && currentInput.includes('.')) return;
            if (shouldResetScreen) {
                currentInput = '';
                shouldResetScreen = false;
            }
            if (currentInput === '0' && val !== '.') {
                currentInput = val;
            } else {
                currentInput += val;
            }
            calcScreen.textContent = currentInput;
        }
    }

    function getOpSymbol(op) {
        if (op === '*') return '×';
        if (op === '/') return '÷';
        if (op === '-') return '−';
        if (op === '+') return '+';
        return op;
    }

    function calculate() {
        let result = 0;
        const prev = parseFloat(previousInput);
        const current = parseFloat(currentInput);
        if (isNaN(prev) || isNaN(current)) return;

        switch (operation) {
            case '+': result = prev + current; break;
            case '-': result = prev - current; break;
            case '*': result = prev * current; break;
            case '/': 
                result = current === 0 ? 'Error' : prev / current; 
                break;
            case '%': result = (prev * current) / 100; break;
            default: return;
        }

        if (typeof result === 'number') {
            // Keep decimal representation clean
            result = parseFloat(result.toFixed(8)).toString();
        }
        
        calcScreen.textContent = result;
        previousInput = result;
    }

    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            // Temporary visual feedback
            const copyBtn = panel.querySelector('[data-val="Copy"]');
            if (copyBtn) {
                const originalHTML = copyBtn.innerHTML;
                copyBtn.innerHTML = '✓';
                copyBtn.style.color = '#10b981';
                setTimeout(() => {
                    copyBtn.innerHTML = originalHTML;
                    copyBtn.style.color = '';
                }, 1000);
            }
        });
    }


    // ==========================================
    // TAB 2: GST CALCULATOR
    // ==========================================
    const gstAmountInput = document.getElementById('gst-amount');
    const gstRateInput = document.getElementById('gst-rate');
    const gstQuickBtns = panel.querySelectorAll('.quick-rate-btn');
    const gstRadios = panel.querySelectorAll('input[name="gst_type"]');
    
    const gstNetVal = document.getElementById('gst-res-net');
    const gstTaxVal = document.getElementById('gst-res-tax');
    const gstCgstVal = document.getElementById('gst-res-cgst');
    const gstSgstVal = document.getElementById('gst-res-sgst');
    const gstTotalVal = document.getElementById('gst-res-total');

    function calculateGST() {
        const amt = parseFloat(gstAmountInput.value) || 0;
        const rate = parseFloat(gstRateInput.value) || 0;
        const isInclusive = panel.querySelector('input[name="gst_type"]:checked').value === 'inclusive';

        let net = 0;
        let tax = 0;
        let total = 0;

        if (isInclusive) {
            net = amt / (1 + (rate / 100));
            tax = amt - net;
            total = amt;
        } else {
            net = amt;
            tax = amt * (rate / 100);
            total = amt + tax;
        }

        const cgst = tax / 2;
        const sgst = tax / 2;

        gstNetVal.innerHTML = `&#8377;${net.toFixed(2)}`;
        gstTaxVal.innerHTML = `&#8377;${tax.toFixed(2)}`;
        gstCgstVal.innerHTML = `&#8377;${cgst.toFixed(2)}`;
        gstSgstVal.innerHTML = `&#8377;${sgst.toFixed(2)}`;
        gstTotalVal.innerHTML = `&#8377;${total.toFixed(2)}`;
    }

    // Attach GST calculation listeners
    gstAmountInput.addEventListener('input', calculateGST);
    gstRateInput.addEventListener('input', () => {
        // Deactivate active quick chips if rate doesn't match
        gstQuickBtns.forEach(btn => {
            if (btn.getAttribute('data-rate') !== gstRateInput.value) {
                btn.classList.remove('active');
            }
        });
        calculateGST();
    });

    gstQuickBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            gstQuickBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            gstRateInput.value = btn.getAttribute('data-rate');
            calculateGST();
        });
    });

    gstRadios.forEach(radio => {
        radio.addEventListener('change', calculateGST);
    });


    // ==========================================
    // TAB 3: DISCOUNT CALCULATOR
    // ==========================================
    const discPriceInput = document.getElementById('disc-price');
    const discPercentInput = document.getElementById('disc-percent');
    const discSaveVal = document.getElementById('disc-res-save');
    const discFinalVal = document.getElementById('disc-res-final');

    function calculateDiscount() {
        const price = parseFloat(discPriceInput.value) || 0;
        const pct = parseFloat(discPercentInput.value) || 0;

        const save = price * (pct / 100);
        const final = price - save;

        discSaveVal.innerHTML = `&#8377;${save.toFixed(2)}`;
        discFinalVal.innerHTML = `&#8377;${final.toFixed(2)}`;
    }

    discPriceInput.addEventListener('input', calculateDiscount);
    discPercentInput.addEventListener('input', calculateDiscount);


    // ==========================================
    // TAB 4: PROFIT & MARGIN CALCULATOR
    // ==========================================
    const profCostInput = document.getElementById('prof-cost');
    const profSellInput = document.getElementById('prof-sell');
    
    const profAmtVal = document.getElementById('prof-res-amt');
    const profPctVal = document.getElementById('prof-res-percent');
    const profMarginVal = document.getElementById('prof-res-margin');

    function calculateProfit() {
        const cost = parseFloat(profCostInput.value) || 0;
        const sell = parseFloat(profSellInput.value) || 0;

        const profit = sell - cost;
        
        let profitPct = 0;
        if (cost > 0) {
            profitPct = (profit / cost) * 100;
        }

        let marginPct = 0;
        if (sell > 0) {
            marginPct = (profit / sell) * 100;
        }

        // Display styling depending on profit or loss
        if (profit >= 0) {
            profAmtVal.innerHTML = `&#8377;${profit.toFixed(2)}`;
            profAmtVal.style.color = '#10b981'; // Green
        } else {
            profAmtVal.innerHTML = `&minus;&#8377;${Math.abs(profit).toFixed(2)}`;
            profAmtVal.style.color = 'var(--danger)'; // Red
        }

        profPctVal.textContent = `${profitPct.toFixed(2)}%`;
        profMarginVal.textContent = `${marginPct.toFixed(2)}%`;
    }

    profCostInput.addEventListener('input', calculateProfit);
    profSellInput.addEventListener('input', calculateProfit);
});
