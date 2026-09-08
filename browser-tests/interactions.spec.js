const path = require("path")
const {expect, test} = require("@playwright/test")


const repositoryRoot = path.resolve(__dirname, "..")

function scriptPath(relativePath) {
    return path.join(repositoryRoot, relativePath)
}


test("modal opens swapped content with an accessible name and closes", async ({page}) => {
    await page.setContent(`
        <button id="opener">Open</button>
        <dialog id="modal">
            <div id="modal-content">
                <h2>Delete purchase</h2>
                <button data-modal-close>Cancel</button>
            </div>
        </dialog>
    `)
    await page.addScriptTag({path: scriptPath("static/js/app/modal.js")})
    await page.evaluate(() => {
        const target = document.querySelector("#modal-content")
        document.dispatchEvent(new CustomEvent("htmx:afterSwap", {detail: {target}}))
    })

    const modal = page.locator("#modal")
    await expect(modal).toHaveAttribute("open", "")
    await expect(modal).toHaveAttribute("aria-label", "Delete purchase")
    await page.getByRole("button", {name: "Cancel"}).click()
    await expect(modal).not.toHaveAttribute("open", "")
})


test("purchase entry rows reindex and recalculate the total", async ({page}) => {
    await page.setContent(`
        <form data-behavior="purchase-create" data-trash-url="/trash.svg">
            <input id="id_form-TOTAL_FORMS" value="1">
            <div data-purchase-rows>
                <article data-purchase-row>
                    <h2 class="purchase-entry-title">Purchase <span data-row-number>1</span></h2>
                    <label for="id_form-0-item">Item</label><input id="id_form-0-item" name="form-0-item">
                    <label for="id_form-0-amount">Amount</label><input id="id_form-0-amount" name="form-0-amount" value="10.00">
                    <div data-receipt-field="source"><input name="form-0-source" value="Card"></div>
                    <div data-receipt-field="location"><input name="form-0-location" value="Shop"></div>
                </article>
            </div>
            <button id="add-form" type="button">Add another</button>
            <span data-purchase-count></span>
            <div id="total"><strong></strong></div>
        </form>
    `)
    await page.addScriptTag({path: scriptPath("static/js/app/pages/purchase-create.js")})

    await expect(page.locator("[data-purchase-count]" )).toHaveText("1 purchase")
    await page.locator("#add-form").click()
    await page.locator('[name="form-1-amount"]').fill("5.25")
    await expect(page.locator("#id_form-TOTAL_FORMS")).toHaveValue("2")
    await expect(page.locator("#total strong")).toHaveText("$15.25")
    await page.getByRole("button", {name: "Remove purchase 2"}).first().click()
    await expect(page.locator("#id_form-TOTAL_FORMS")).toHaveValue("1")
    await expect(page.locator("[data-purchase-count]")).toHaveText("1 purchase")
    await expect(page.locator("#total strong")).toHaveText("$10.00")
})


test("recurring purchase selection updates count, total, and submit state", async ({page}) => {
    await page.setContent(`
        <form data-behavior="recurring-selection">
            <div data-recurring-row>
                <input type="checkbox" name="form-0-selected">
                <input name="form-0-amount" value="12.50">
            </div>
            <div data-recurring-row>
                <input type="checkbox" name="form-1-selected">
                <input name="form-1-amount" value="7.25">
            </div>
            <button type="button" data-select-all>Select all</button>
            <button type="button" data-clear-all>Clear all</button>
            <span data-selection-count></span>
            <strong data-selection-total></strong>
            <button type="submit" data-selection-submit></button>
        </form>
    `)
    await page.addScriptTag({path: scriptPath("static/js/app/modal.js")})

    const submit = page.locator("[data-selection-submit]")
    await expect(submit).toBeDisabled()
    await page.locator("[data-select-all]").click()
    await expect(page.locator("[data-selection-count]")).toHaveText("2")
    await expect(page.locator("[data-selection-total]")).toHaveText("$19.75")
    await expect(submit).toHaveText("Add 2 purchases")
    await page.locator("[data-clear-all]").click()
    await expect(submit).toBeDisabled()
})


test("rollover editor saves inline and reports a failed retry", async ({page}) => {
    let failRequest = false
    let submittedBody
    let submittedHeaders
    await page.route("http://carrots.test/rollover", async (route) => {
        submittedBody = route.request().postDataJSON()
        submittedHeaders = route.request().headers()
        await route.fulfill({
            status: failRequest ? 500 : 200,
            body: "{}",
        })
    })
    await page.route("http://carrots.test/", (route) => route.fulfill({
        contentType: "text/html",
        body: `
        <main data-behavior="yearly-budget-detail" data-rollover-url="/rollover" data-year="2024" data-ytd-month="6">
            <form data-ytd-selector><select class="month-select"><option value="6">June</option></select><button class="ytd-selector-submit">Apply</button></form>
            <details class="rollover-details" open><summary>Rollover</summary>
                <div class="rollover-popover"><strong>$10.00</strong><strong>$20.00</strong>
                    <button data-rollover-edit data-category="Food" data-current="10" data-next="20">Edit</button>
                </div>
            </details>
            <dialog class="rollover-dialog">
                <form data-rollover-form>
                    <span data-rollover-category></span><span data-rollover-current></span>
                    <input data-rollover-next type="number" step="0.01" required>
                    <p data-rollover-error hidden></p>
                    <button type="button" data-rollover-close>Cancel</button>
                    <button type="submit">Save</button>
                </form>
            </dialog>
        </main>
        `,
    }))
    await page.goto("http://carrots.test/")
    await page.evaluate(() => {
        window.CarrotsBudget = {getCsrfToken: () => "token"}
    })
    await page.addScriptTag({path: scriptPath("static/js/app/pages/yearly-budget-detail.js")})

    await page.getByRole("button", {name: "Edit"}).click()
    await page.locator("[data-rollover-next]").fill("35.50")
    await page.getByRole("button", {name: "Save"}).click()
    await expect(page.locator(".rollover-dialog")).not.toHaveAttribute("open", "")
    await expect(page.locator(".rollover-popover strong").nth(1)).toHaveText("$35.50")
    expect(submittedBody).toEqual({amount: "35.50", category: "Food", year: "2024"})
    expect(submittedHeaders["x-csrftoken"]).toBe("token")
    expect(submittedHeaders["x-requested-with"]).toBe("XMLHttpRequest")

    failRequest = true
    await page.locator(".rollover-details summary").click()
    await page.getByRole("button", {name: "Edit"}).click()
    await page.locator("[data-rollover-next]").fill("40")
    await page.getByRole("button", {name: "Save"}).click()
    await expect(page.locator("[data-rollover-error]")).toBeVisible()
    await expect(page.locator("[data-rollover-error]")).toContainText("Could not save")
})
