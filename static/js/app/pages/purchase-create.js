(function () {
    function calculateTotal(form, total) {
        const amounts = form.querySelectorAll("[id$='-amount']")
        const totalAmount = [...amounts].reduce((previous, current) => {
            const currentValue = parseFloat(current.value)

            return previous + (Number.isNaN(currentValue) ? 0 : currentValue)
        }, 0)

        total.textContent = `Total: ${Math.round(totalAmount * 100) / 100}`
    }

    function initializePurchaseForm(form) {
        if (form.dataset.jsInitialized) {
            return
        }

        const purchaseForms = form.querySelectorAll(".purchase-form")
        const container = form
        const addButton = form.querySelector("#add-form")
        const submitButton = form.querySelector("#submit-button")
        const totalForms = form.querySelector("#id_form-TOTAL_FORMS")
        const total = form.querySelector("#total")

        if (!purchaseForms.length || !addButton || !submitButton || !totalForms || !total) {
            return
        }

        form.dataset.jsInitialized = "true"
        let formNumber = purchaseForms.length - 1

        addButton.addEventListener("click", (event) => {
            event.preventDefault()

            const newForm = purchaseForms[0].cloneNode(true)
            const formRegex = /form-\d+-/g

            newForm.querySelectorAll("[name$='-source'], [name$='-location']").forEach((input) => {
                const fieldContainer = input.closest("div")

                fieldContainer.replaceChildren()
                fieldContainer.classList.add("purchase-field-spacer")
                fieldContainer.setAttribute("aria-hidden", "true")
            })

            formNumber += 1
            newForm.innerHTML = newForm.innerHTML.replace(formRegex, `form-${formNumber}-`)
            container.insertBefore(newForm, submitButton)
            totalForms.value = String(formNumber + 1)

            const newFormAmount = form.querySelector(`#id_form-${formNumber}-amount`)
            const newFormItem = form.querySelector(`#id_form-${formNumber}-item`)

            if (newFormAmount) {
                newFormAmount.addEventListener("change", () => calculateTotal(form, total))
            }

            if (newFormItem) {
                newFormItem.focus()
            }
        })

        form.querySelectorAll("[id$='-amount']").forEach((input) => {
            input.addEventListener("change", () => calculateTotal(form, total))
        })
    }

    function initialize() {
        document.querySelectorAll('[data-behavior="purchase-create"]').forEach(initializePurchaseForm)
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, {once: true})
    } else {
        initialize()
    }
})()
