(function () {
    function saveRollover(input, endpoint, year) {

        if (input.dataset.lastSavedValue === input.value) {
            return
        }

        input.dataset.lastSavedValue = input.value

        fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": window.CarrotsBudget.getCsrfToken(),
            },
            body: JSON.stringify({
                amount: input.value,
                category: input.dataset.category,
                year,
            }),
        }).catch(() => {
            delete input.dataset.lastSavedValue
        })
    }

    function initializeYearlyBudget(root) {
        if (root.dataset.jsInitialized) {
            return
        }

        const endpoint = root.dataset.rolloverUrl
        const year = root.dataset.year

        if (!endpoint || !year) {
            return
        }

        root.dataset.jsInitialized = "true"

        root.querySelectorAll(".rollover-edit").forEach((input) => {
            input.addEventListener("input", () => {
                delete input.dataset.skipNextBlur
            })
            input.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") {
                    return
                }

                event.preventDefault()
                saveRollover(input, endpoint, year)
                input.dataset.skipNextBlur = "true"
            })

            input.addEventListener("blur", () => {
                if (input.dataset.skipNextBlur) {
                    delete input.dataset.skipNextBlur
                    return
                }
                saveRollover(input, endpoint, year)
            })
        })

        const monthYtdSelect = root.querySelector(".month-select")

        if (!monthYtdSelect) {
            return
        }

        if (root.dataset.ytdMonth) {
            monthYtdSelect.value = root.dataset.ytdMonth
        }

        monthYtdSelect.addEventListener("change", () => {
            window.location = `${root.dataset.ytdPath}?ytd=${monthYtdSelect.value}`
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
