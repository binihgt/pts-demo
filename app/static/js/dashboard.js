// PTS Demo - Client JavaScript Helpers

document.addEventListener("DOMContentLoaded", function () {
    // Populate Quick Pay Modal when a pay button is clicked
    const payModal = document.getElementById("payModal");
    if (payModal) {
        payModal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            const saleId = button.getAttribute("data-sale-id");
            const item = button.getAttribute("data-sale-item");
            const balance = button.getAttribute("data-sale-balance");

            const modalSaleId = payModal.querySelector("#modalSaleId");
            const modalItem = payModal.querySelector("#modalSaleItem");
            const modalBalance = payModal.querySelector("#modalSaleBalance");
            const modalAmountInput = payModal.querySelector("#payAmountInput");
            const modalForm = payModal.querySelector("#payForm");

            const numBal = parseFloat(balance) || 0;
            const formattedBal = numBal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " ETB";
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
    setTimeout(function () {
        const alerts = document.querySelectorAll(".alert-dismissible");
        alerts.forEach(function (alert) {
            const bsAlert = bootstrap.Alert.getInstance(alert) || new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 6000);
});
