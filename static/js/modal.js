// Modal and navigation functionality
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.querySelector("#modal");
    const overlay = document.querySelector(".overlay");

    function showModal() {
        modal.classList.remove("hidden");
        overlay.classList.remove("hidden");
    }

    function closeModal() {
        modal.classList.add("hidden");
        overlay.classList.add("hidden");
    }

    htmx.on("htmx:afterSwap", (e) => {
        if (e.detail.target.id == "modal-content") {
            showModal();
            const dateInput = document.querySelector("#id_form-0-date");

            if (dateInput) {
                dateInput.focus();
            }
        }
    });

    overlay.addEventListener("click", (event) => {
        const clickedOutside = !event.target.closest(".modal");
        if (clickedOutside) {
            closeModal();
        }
    });

    window.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            closeModal();
        }
    });

    // Mobile menu toggle
    document.getElementById('menu-toggle').addEventListener('click', function() {
        const nav = document.getElementById('primary-nav');
        nav.classList.toggle('nav-open');
    });
});
