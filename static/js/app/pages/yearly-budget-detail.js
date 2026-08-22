(function () {
    const saveStates = new WeakMap()

    function getSaveState(input) {
        if (!saveStates.has(input)) {
            saveStates.set(input, {
                lastSavedValue: input.value,
                pendingValue: null,
                queuedValue: null,
            })
        }

        return saveStates.get(input)
    }

    function clearSaveError(input, errorMessage) {
        if (!errorMessage || errorMessage.dataset.inputId !== input.id) {
            return
        }

        errorMessage.hidden = true
        errorMessage.textContent = ""
        delete errorMessage.dataset.inputId
    }

    function showSaveError(input, errorMessage) {
        input.dataset.saveState = "error"

        if (!errorMessage) {
            return
        }

        errorMessage.dataset.inputId = input.id
        errorMessage.textContent = `Could not save the rollover for ${input.dataset.category}. Try again.`
        errorMessage.hidden = false
    }

    async function persistRollover(input, endpoint, year, value, saveState, errorMessage) {
        saveState.pendingValue = value
        input.setAttribute("aria-busy", "true")
        input.dataset.saveState = "pending"

        let result = "success"

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
                    amount: value,
                    category: input.dataset.category,
                    year,
                }),
            })

            if (!response.ok) {
                throw new Error(`Rollover update failed with status ${response.status}`)
            }

            saveState.lastSavedValue = value
            input.dataset.lastSavedValue = value
        } catch (error) {
            result = "error"
        } finally {
            saveState.pendingValue = null
            input.removeAttribute("aria-busy")
        }

        const queuedValue = saveState.queuedValue
        saveState.queuedValue = null

        if (queuedValue !== null && queuedValue !== saveState.lastSavedValue) {
            return persistRollover(input, endpoint, year, queuedValue, saveState, errorMessage)
        }

        if (result === "error" && input.value === value) {
            showSaveError(input, errorMessage)
            return
        }

        if (input.value !== saveState.lastSavedValue) {
            input.dataset.saveState = "idle"
            return
        }

        input.dataset.saveState = "success"
        clearSaveError(input, errorMessage)
    }

    function saveRollover(input, endpoint, year, errorMessage) {
        const saveState = getSaveState(input)
        const value = input.value

        if (saveState.pendingValue !== null) {
            saveState.queuedValue = value === saveState.pendingValue ? null : value
            return
        }

        if (saveState.lastSavedValue === value) {
            return
        }

        persistRollover(input, endpoint, year, value, saveState, errorMessage)
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
        const errorMessage = root.querySelector(".rollover-save-error")

        root.querySelectorAll(".rollover-edit").forEach((input) => {
            getSaveState(input)

            input.addEventListener("input", () => {
                delete input.dataset.skipNextBlur

                const saveState = getSaveState(input)
                if (saveState.pendingValue === null && input.value !== saveState.lastSavedValue) {
                    input.dataset.saveState = "idle"
                    clearSaveError(input, errorMessage)
                }
            })
            input.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") {
                    return
                }

                event.preventDefault()
                saveRollover(input, endpoint, year, errorMessage)
                input.dataset.skipNextBlur = "true"
            })

            input.addEventListener("blur", () => {
                if (input.dataset.skipNextBlur) {
                    delete input.dataset.skipNextBlur
                    return
                }
                saveRollover(input, endpoint, year, errorMessage)
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
