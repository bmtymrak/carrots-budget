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

;(function () {
    function initializeFinancialList(region) {
        if (region.dataset.jsInitialized) {
            return
        }

        const rows = region.querySelector("tbody[data-collapsible-rows]")
        const toggle = region.querySelector("[data-financial-list-toggle]")

        if (!rows || !toggle) {
            return
        }

        region.dataset.jsInitialized = "true"
        const rowCount = rows.querySelectorAll("tr").length
        const expandedLabel = toggle.textContent.trim()

        toggle.dataset.hasOverflow = String(rowCount > 3)
        if (rowCount <= 3) {
            return
        }

        toggle.addEventListener("click", () => {
            const isExpanded = rows.classList.toggle("is-expanded")
            toggle.setAttribute("aria-expanded", String(isExpanded))
            toggle.textContent = isExpanded ? "Show fewer" : expandedLabel
        })
    }

    function initializeFinancialLists(root) {
        root.querySelectorAll(".financial-table-scroll").forEach(initializeFinancialList)
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => initializeFinancialLists(document), {once: true})
    } else {
        initializeFinancialLists(document)
    }

    document.addEventListener("htmx:afterSwap", (event) => initializeFinancialLists(event.detail.target))
})()
