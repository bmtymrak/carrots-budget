(function () {
    function initializeModal() {
        const modal = document.querySelector("#modal")
        const modalContent = document.querySelector("#modal-content")
        const overlay = document.querySelector(".overlay")

        if (!modal || !modalContent || !overlay || modal.dataset.jsInitialized) {
            return
        }

        modal.dataset.jsInitialized = "true"

        function focusFirstModalElement() {
            const firstInteractiveElement = modalContent.querySelector(
                "input:not([type=\"hidden\"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), a[href], [tabindex]:not([tabindex=\"-1\"])"
            )

            if (firstInteractiveElement) {
                firstInteractiveElement.focus()
            }
        }

        function showModal() {
            modal.classList.remove("hidden")
            overlay.classList.remove("hidden")
            modal.scrollTo(0, 0)
        }

        function closeModal() {
            modal.classList.add("hidden")
            overlay.classList.add("hidden")
        }

        document.addEventListener("htmx:afterSwap", (event) => {
            const target = event.detail && event.detail.target

            if (target && target.id === "modal-content") {
                showModal()
                focusFirstModalElement()
            }
        })

        overlay.addEventListener("click", (event) => {
            const clickedOutside = !event.target.closest(".modal")

            if (clickedOutside) {
                closeModal()
            }
        })

        window.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeModal()
            }
        })
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeModal, {once: true})
    } else {
        initializeModal()
    }
})()
