/**
 * Purchase form manager for dynamic form creation
 * Allows adding multiple purchase items in one submission
 */

export class PurchaseFormManager {
    constructor() {
        this.container = document.querySelector("#purchase-form-container");
        this.purchaseForms = document.querySelectorAll(".purchase-form");
        this.addButton = document.querySelector("#add-form");
        this.submitButton = document.querySelector("#submit-button");
        this.totalFormsInput = document.querySelector("#id_form-TOTAL_FORMS");
        this.totalDisplay = document.querySelector('#total');

        if (this.container && this.purchaseForms.length > 0) {
            this.formNum = this.purchaseForms.length - 1;
            this.init();
        }
    }

    init() {
        // Add event listener to the "Add Item" button
        if (this.addButton) {
            this.addButton.addEventListener('click', (e) => this.addForm(e));
        }

        // Add event listeners to all amount inputs for total calculation
        const amountInputs = document.querySelectorAll("[id$='-amount']");
        amountInputs.forEach(input => {
            input.addEventListener('change', (e) => this.calculateTotal(e));
        });
    }

    addForm(e) {
        e.preventDefault();

        // Clone the first form
        const newForm = this.purchaseForms[0].cloneNode(true);
        const formRegex = RegExp(`form-(\\d){1}-`, 'g');

        this.formNum++;
        newForm.innerHTML = newForm.innerHTML.replace(formRegex, `form-${this.formNum}-`);

        // Insert the new form before the submit button
        this.container.insertBefore(newForm, this.submitButton);

        // Update the total forms count
        this.totalFormsInput.setAttribute('value', `${this.formNum + 1}`);

        // Add event listener to the new amount input
        const newAmountInput = document.querySelector(`#id_form-${this.formNum}-amount`);
        if (newAmountInput) {
            newAmountInput.addEventListener('change', (e) => this.calculateTotal(e));
        }

        // Focus on the item field of the new form
        const newItemInput = document.querySelector(`#id_form-${this.formNum}-item`);
        if (newItemInput) {
            newItemInput.focus();
        }
    }

    calculateTotal(e) {
        e.preventDefault();
        const amounts = document.querySelectorAll("[id$='-amount']");

        const total = [...amounts].reduce((sum, input) => {
            const value = parseFloat(input.value);
            if (isNaN(value)) {
                return sum;
            }
            return Math.round((sum + value) * 100) / 100;
        }, 0);

        this.totalDisplay.innerHTML = `Total: $${total.toFixed(2)}`;
    }
}
