(function () {
    function initializeYearlyBudget(root) {
        if (root.dataset.jsInitialized) {
            return
        }

        const endpoint = root.dataset.rolloverUrl
        const year = root.dataset.year
        const monthSelect = root.querySelector(".month-select")
        const monthForm = root.querySelector("[data-ytd-selector]")
        const monthSubmit = monthForm && monthForm.querySelector(".ytd-selector-submit")
        const dialog = root.querySelector(".rollover-dialog")
        const form = dialog && dialog.querySelector("[data-rollover-form]")

        if (!monthSelect || !monthForm) {
            return
        }

        root.dataset.jsInitialized = "true"
        monthSelect.value = root.dataset.ytdMonth || monthSelect.value
        monthSelect.addEventListener("change", () => monthForm.requestSubmit())
        if (monthSubmit) {
            monthSubmit.hidden = true
        }

        if (!endpoint || !year || !dialog || !form) {
            return
        }

        const categoryText = dialog.querySelector("[data-rollover-category]")
        const currentValue = dialog.querySelector("[data-rollover-current]")
        const nextInput = dialog.querySelector("[data-rollover-next]")
        const errorMessage = dialog.querySelector("[data-rollover-error]")
        let activeTrigger = null

        document.addEventListener("click", (event) => {
            root.querySelectorAll(".rollover-details[open]").forEach((details) => {
                if (!details.contains(event.target)) {
                    details.removeAttribute("open")
                }
            })
        })

        root.querySelectorAll("[data-rollover-edit]").forEach((button) => {
            button.addEventListener("click", () => {
                activeTrigger = button
                categoryText.textContent = button.dataset.category
                currentValue.textContent = `$${Number(button.dataset.current).toFixed(2)}`
                currentValue.classList.toggle("value-negative", Number(button.dataset.current) < 0)
                nextInput.value = button.dataset.next
                errorMessage.hidden = true
                errorMessage.textContent = ""
                button.closest(".rollover-details")?.removeAttribute("open")
                dialog.showModal()
                nextInput.focus()
                nextInput.select()
            })
        })

        dialog.querySelectorAll("[data-rollover-close]").forEach((button) => {
            button.addEventListener("click", () => dialog.close())
        })

        form.addEventListener("submit", async (event) => {
            event.preventDefault()
            if (!activeTrigger || !form.reportValidity()) {
                return
            }

            const submitButton = form.querySelector('[type="submit"]')
            submitButton.disabled = true
            errorMessage.hidden = true

            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": window.CarrotsBudget.getCsrfToken(),
                    },
                    body: JSON.stringify({
                        amount: nextInput.value,
                        category: activeTrigger.dataset.category,
                        year,
                    }),
                })

                if (!response.ok) {
                    throw new Error("Rollover update failed")
                }

                activeTrigger.dataset.next = nextInput.value
                const nextValue = activeTrigger.closest(".rollover-popover").querySelectorAll("strong")[1]
                if (nextValue) {
                    nextValue.textContent = `$${Number(nextInput.value).toFixed(2)}`
                }
                dialog.close()
                activeTrigger.focus()
            } catch (error) {
                errorMessage.textContent = `Could not save the rollover for ${activeTrigger.dataset.category}. Try again.`
                errorMessage.hidden = false
            } finally {
                submitButton.disabled = false
            }
        })
    }

    function initialize() {
        document.querySelectorAll('[data-behavior="yearly-budget-detail"]').forEach(initializeYearlyBudget)
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, {once: true})
    } else {
        initialize()
    }
})()
