(function () {
    function initializeNavigation() {
        const menuToggle = document.getElementById("menu-toggle")
        const nav = document.getElementById("primary-nav")

        if (!menuToggle || !nav || menuToggle.dataset.jsInitialized) {
            return
        }

        menuToggle.dataset.jsInitialized = "true"
        menuToggle.addEventListener("click", function () {
            const isOpen = nav.classList.toggle("nav-open")
            this.setAttribute("aria-expanded", String(isOpen))
        })
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeNavigation, {once: true})
    } else {
        initializeNavigation()
    }
})()
