// PTS Demo & Saledash - Client JavaScript Helpers

document.addEventListener("DOMContentLoaded", function () {
    // 1. Dynamic Greeting (Good Morning, Good Afternoon, Good Evening)
    updateGreeting();

    // 2. Dynamic Date Pill (Formatted e.g. 14 Aug 2026)
    updateDatePill();

    // 3. Sidebar Collapse Toggle
    initSidebarCollapse();

    // 4. Populate Quick Pay Modal when a pay button is clicked
    initPayModal();

    // 5. Auto-dismiss flash alerts after 6 seconds
    initAutoDismissAlerts();
});

// Update greeting based on local time
function updateGreeting() {
    const greetingElem = document.getElementById("greetingText");
    if (!greetingElem) return;

    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) {
        greetingElem.textContent = "Good Morning";
    } else if (hour >= 12 && hour < 17) {
        greetingElem.textContent = "Good Afternoon";
    } else {
        greetingElem.textContent = "Good Evening";
    }
}

// Update date pill display
function updateDatePill() {
    const dateElem = document.getElementById("currentDateStr");
    if (!dateElem) return;

    const now = new Date();
    const options = { day: "numeric", month: "short", year: "numeric" };
    dateElem.textContent = now.toLocaleDateString("en-GB", options);
}

// Sidebar Desktop Collapse / Expand Toggle
function initSidebarCollapse() {
    const collapseBtn = document.getElementById("sidebarCollapseBtn");
    const appShell = document.getElementById("appShell");
    const collapseIcon = document.getElementById("collapseIcon");

    if (collapseBtn && appShell) {
        collapseBtn.addEventListener("click", function () {
            appShell.classList.toggle("sidebar-collapsed");
            if (collapseIcon) {
                if (appShell.classList.contains("sidebar-collapsed")) {
                    collapseIcon.classList.remove("bi-chevron-left");
                    collapseIcon.classList.add("bi-chevron-right");
                } else {
                    collapseIcon.classList.remove("bi-chevron-right");
                    collapseIcon.classList.add("bi-chevron-left");
                }
            }
        });
    }
}

// Populate Quick Pay Modal with sale details
function initPayModal() {
    const payModal = document.getElementById("payModal");
    if (!payModal) return;

    payModal.addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        if (!button) return;

        const saleId = button.getAttribute("data-sale-id");
        const item = button.getAttribute("data-sale-item");
        const balance = button.getAttribute("data-sale-balance");

        const modalSaleId = payModal.querySelector("#modalSaleId");
        const modalItem = payModal.querySelector("#modalSaleItem");
        const modalBalance = payModal.querySelector("#modalSaleBalance");
        const modalAmountInput = payModal.querySelector("#payAmountInput");
        const modalForm = payModal.querySelector("#payForm");

        const numBal = parseFloat(balance) || 0;
        const formattedBal = numBal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " ETB";

        if (modalSaleId) modalSaleId.textContent = "#" + saleId;
        if (modalItem) modalItem.textContent = item;
        if (modalBalance) modalBalance.textContent = formattedBal;
        if (modalAmountInput) {
            modalAmountInput.value = numBal.toFixed(2);
            modalAmountInput.max = numBal.toFixed(2);
        }
        if (modalForm) {
            modalForm.action = "/payments/record/" + saleId;
        }
    });
}

// Auto-dismiss alerts after 6 seconds
function initAutoDismissAlerts() {
    setTimeout(function () {
        const alerts = document.querySelectorAll(".alert-dismissible");
        alerts.forEach(function (alert) {
            const bsAlert = bootstrap.Alert.getInstance(alert) || new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 6000);
}
