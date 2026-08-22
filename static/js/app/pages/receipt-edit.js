(function () {
    function initializeReceiptForm(form) {
        if (form.dataset.jsInitialized) {
            return
        }

        const receiptAmountInputs = form.querySelectorAll(
            ".receipt-purchase-editor input[id$='-amount']"
        )
        const receiptTotal = form.querySelector("#receipt-total span")

        if (!receiptAmountInputs.length || !receiptTotal) {
            return
        }

        form.dataset.jsInitialized = "true"

        function updateReceiptTotal() {
            const total = [...receiptAmountInputs].reduce((sum, input) => {
                const amount = parseFloat(input.value)

                return sum + (Number.isNaN(amount) ? 0 : amount)
            }, 0)

            receiptTotal.textContent = total.toFixed(2)
        }

        receiptAmountInputs.forEach((input) => {
            input.addEventListener("input", updateReceiptTotal)
        })
    }

    function initialize() {
        document.querySelectorAll('[data-behavior="receipt-edit"]').forEach(initializeReceiptForm)
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, {once: true})
    } else {
        initialize()
    }
})()
