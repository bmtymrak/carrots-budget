(function () {
    function initializePurchaseForm(form) {
        if (form.dataset.jsInitialized) {
            return
        }

        const rowsContainer = form.querySelector("[data-purchase-rows]")
        const addButton = form.querySelector("#add-form")
        const totalForms = form.querySelector("#id_form-TOTAL_FORMS")
        const total = form.querySelector("#total strong")
        const count = form.querySelector("[data-purchase-count]")

        if (!rowsContainer || !addButton || !totalForms || !total || !count) {
            return
        }

        form.dataset.jsInitialized = "true"

        function rows() {
            return [...rowsContainer.querySelectorAll("[data-purchase-row]")]
        }

        function updateSummary() {
            const activeRows = rows().filter((row) => !row.classList.contains("hidden"))
            const amount = activeRows.reduce((sum, row) => {
                const value = Number.parseFloat(row.querySelector('[name$="-amount"]')?.value)
                return sum + (Number.isNaN(value) ? 0 : value)
            }, 0)

            count.textContent = `${activeRows.length} purchase${activeRows.length === 1 ? "" : "s"}`
            total.textContent = `$${amount.toFixed(2)}`
            total.classList.toggle("value-negative", amount < 0)
        }

        function reindexRows() {
            rows().forEach((row, index) => {
                row.querySelectorAll("[name], [id], label[for]").forEach((element) => {
                    for (const attribute of ["name", "id", "for"]) {
                        const value = element.getAttribute(attribute)
                        if (value) {
                            element.setAttribute(attribute, value.replace(/form-\d+-/g, `form-${index}-`))
                        }
                    }
                })
                row.querySelector("[data-row-number]").textContent = String(index + 1)
                row.querySelectorAll("[data-remove-purchase]").forEach((button) => {
                    button.setAttribute("aria-label", `Remove purchase ${index + 1}`)
                })
            })
            totalForms.value = String(rows().length)
        }

        function addRemoveButton(row, container, desktop) {
            const button = document.createElement("button")
            button.type = "button"
            button.className = `remove-purchase${desktop ? " remove-purchase--desktop" : ""}`
            button.dataset.removePurchase = ""
            const image = document.createElement("img")
            image.src = form.dataset.trashUrl
            image.alt = ""
            image.setAttribute("aria-hidden", "true")
            button.append(image)
            container.append(button)
        }

        function makeInherited(wrapper) {
            const input = wrapper.querySelector("input, select, textarea")
            if (input) {
                input.type = "hidden"
                input.value = ""
            }
            const note = document.createElement("span")
            note.className = "purchase-inherited"
            note.textContent = "Same as item 1"
            wrapper.append(note)
        }

        addButton.addEventListener("click", () => {
            const sourceRow = rows()[0]
            const newRow = sourceRow.cloneNode(true)

            newRow.classList.remove("hidden")
            newRow.querySelectorAll("input, select, textarea").forEach((field) => {
                if (field.matches('[name$="-date"]')) {
                    return
                }
                if (field.type === "checkbox") {
                    field.checked = false
                } else {
                    field.value = ""
                }
            })
            newRow.querySelectorAll(".errorlist").forEach((errors) => errors.remove())
            newRow.querySelectorAll('[data-receipt-field="source"], [data-receipt-field="location"]').forEach(makeInherited)

            const title = newRow.querySelector(".purchase-entry-title")
            addRemoveButton(newRow, title, false)
            addRemoveButton(newRow, newRow, true)
            rowsContainer.append(newRow)
            reindexRows()
            updateSummary()
            newRow.querySelector('[name$="-item"]')?.focus()
        })

        rowsContainer.addEventListener("click", (event) => {
            const removeButton = event.target.closest("[data-remove-purchase]")
            if (!removeButton) {
                return
            }
            const row = removeButton.closest("[data-purchase-row]")
            if (row && row !== rows()[0]) {
                row.remove()
                reindexRows()
                updateSummary()
                addButton.focus()
            }
        })

        rowsContainer.addEventListener("input", updateSummary)
        updateSummary()
    }

    function initialize() {
        document.querySelectorAll('[data-behavior="purchase-create"]').forEach(initializePurchaseForm)
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, {once: true})
    } else {
        initialize()
    }
})()
