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
