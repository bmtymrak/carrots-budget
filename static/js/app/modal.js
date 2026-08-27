(function () {
    const focusableSelector = [
        "a[href]",
        "button:not([disabled])",
        'input:not([type="hidden"]):not([disabled])',
        "select:not([disabled])",
        "textarea:not([disabled])",
        '[tabindex]:not([tabindex="-1"])',
    ].join(", ")

    function initializeModal() {
        const modal = document.querySelector("#modal")
        const modalContent = document.querySelector("#modal-content")

        if (!modal || !modalContent || modal.dataset.jsInitialized) {
            return
        }

        modal.dataset.jsInitialized = "true"

        modalContent.addEventListener("click", (event) => {
            const closeButton = event.target.closest("[data-modal-close]")
            if (closeButton) {
                modal.close()
            }
        })

        function updateAccessibleName() {
            const heading = modalContent.querySelector("h1, h2, h3")
            const headingText = heading && heading.textContent.trim()

            modal.setAttribute("aria-label", headingText || "Dialog")
        }

        document.addEventListener("htmx:afterSwap", (event) => {
            const target = event.detail && event.detail.target

            if (!target || target.id !== "modal-content") {
                return
            }

            updateAccessibleName()
            modal.scrollTo(0, 0)

            if (!modal.open) {
                modal.showModal()
                return
            }

            const focusTarget = modalContent.querySelector(focusableSelector)
            if (focusTarget) {
                focusTarget.focus()
            }
        })
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeModal, {once: true})
    } else {
        initializeModal()
    }
})()

;(function () {
    const desktopRecurringDetails = window.matchMedia("(min-width: 769px)")

    function parseAmount(value) {
        const amount = Number.parseFloat(value)
        return Number.isNaN(amount) ? 0 : amount
    }

    function synchronizeRecurringEditors(root) {
        root.querySelectorAll('[data-behavior="recurring-selection"]').forEach((form) => {
            form.querySelectorAll(".recurring-row-editor").forEach((editor) => {
                const toggle = editor.querySelector(".recurring-row-toggle")
                const fields = editor.querySelector(".modal-form-grid")

                if (!toggle || !fields) {
                    return
                }

                if (!editor.dataset.toggleInitialized) {
                    editor.dataset.toggleInitialized = "true"
                    editor.dataset.mobileExpanded = "false"
                    toggle.addEventListener("click", () => {
                        const expanded = toggle.getAttribute("aria-expanded") !== "true"
                        editor.dataset.mobileExpanded = String(expanded)
                        toggle.setAttribute("aria-expanded", String(expanded))
                        fields.hidden = !expanded
                    })
                }

                if (desktopRecurringDetails.matches) {
                    toggle.setAttribute("aria-expanded", "true")
                    fields.hidden = false
                } else {
                    const expanded = editor.dataset.mobileExpanded === "true"
                    toggle.setAttribute("aria-expanded", String(expanded))
                    fields.hidden = !expanded
                }
            })
            form.classList.add("recurring-details-enhanced")
        })
    }

    function initializeRecurringSelection(form) {
        if (form.dataset.jsInitialized) {
            return
        }

        const selectable = [...form.querySelectorAll('[data-recurring-row]:not([data-already-added="true"])')]
        const total = form.querySelector("[data-selection-total]")
        const count = form.querySelector("[data-selection-count]")
        const submit = form.querySelector("[data-selection-submit]")

        if (!selectable.length || !total || !count || !submit) {
            return
        }

        form.dataset.jsInitialized = "true"

        function updateSelection() {
            const selected = selectable.filter((row) => row.querySelector('[name$="-selected"]').checked)
            const amount = selected.reduce((sum, row) => sum + parseAmount(row.querySelector('[name$="-amount"]').value), 0)
            count.textContent = String(selected.length)
            total.textContent = `$${amount.toFixed(2)}`
            submit.textContent = selected.length ? `Add ${selected.length} purchase${selected.length === 1 ? "" : "s"}` : "Add purchases"
            submit.disabled = selected.length === 0
        }

        form.addEventListener("change", updateSelection)
        form.querySelector("[data-select-all]")?.addEventListener("click", () => {
            selectable.forEach((row) => { row.querySelector('[name$="-selected"]').checked = true })
            updateSelection()
        })
        form.querySelector("[data-clear-all]")?.addEventListener("click", () => {
            selectable.forEach((row) => { row.querySelector('[name$="-selected"]').checked = false })
            updateSelection()
        })
        updateSelection()
    }

    function initialize(root) {
        root.querySelectorAll('[data-behavior="recurring-selection"]').forEach(initializeRecurringSelection)
        synchronizeRecurringEditors(root)
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => initialize(document), {once: true})
    } else {
        initialize(document)
    }
    document.addEventListener("htmx:afterSwap", (event) => initialize(event.detail.target))
    desktopRecurringDetails.addEventListener("change", () => synchronizeRecurringEditors(document))
})()
