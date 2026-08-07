/**
 * Modal management for Carrots Budget
 * Handles showing/hiding modals and HTMX integration
 */

export class Modal {
    constructor() {
        this.modal = document.querySelector("#modal");
        this.modalContent = document.querySelector("#modal-content");
        this.overlay = document.querySelector(".overlay");

        if (this.modal && this.modalContent && this.overlay) {
            this.init();
        }
    }

    init() {
        // HTMX integration - show modal after content is swapped
        htmx.on("htmx:afterSwap", (e) => {
            if (e.detail.target.id === "modal-content") {
                this.show();
                this.focusFirstElement();
            }
        });

        // Close modal when clicking on overlay (outside modal)
        this.overlay.addEventListener("click", (event) => {
            const clickedOutside = !event.target.closest(".modal");
            if (clickedOutside) {
                this.close();
            }
        });

        // Close modal on Escape key
        window.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.close();
            }
        });
    }

    show() {
        this.modal.classList.remove("hidden");
        this.overlay.classList.remove("hidden");
        this.modal.scrollTo(0, 0);
    }

    close() {
        this.modal.classList.add("hidden");
        this.overlay.classList.add("hidden");
    }

    focusFirstElement() {
        const firstInteractiveElement = this.modalContent.querySelector(
            'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
        );

        if (firstInteractiveElement) {
            firstInteractiveElement.focus();
        }
    }
}
