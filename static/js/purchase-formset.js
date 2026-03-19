// Purchase formset management and total calculation
document.addEventListener('DOMContentLoaded', function() {
    let purchaseForm = document.querySelectorAll(".purchase-form");
    let container = document.querySelector("#purchase-form-container");
    let addButton = document.querySelector("#add-form");
    let submitButton = document.querySelector("#submit-button");
    let totalForms = document.querySelector("#id_form-TOTAL_FORMS");
    let amount = document.querySelectorAll("[id$='-amount']");
    let total = document.querySelector('#total');

    let formNum = purchaseForm.length - 1;
    addButton.addEventListener('click', addForm);

    amount.forEach(input => input.addEventListener('change', calculateTotal));

    function addForm(e) {
        e.preventDefault();

        let newForm = purchaseForm[0].cloneNode(true);
        let formRegex = RegExp(`form-(\\d){1}-`, 'g');

        formNum++;
        newForm.innerHTML = newForm.innerHTML.replace(formRegex, `form-${formNum}-`);
        container.insertBefore(newForm, submitButton);
        
        totalForms.setAttribute('value', `${formNum + 1}`);

        let newFormAmount = document.querySelector(`#id_form-${formNum}-amount`);

        newFormAmount.addEventListener('change', calculateTotal);
        document.querySelector(`#id_form-${formNum}-item`).focus();
    }

    function calculateTotal(e) {
        e.preventDefault();
        let amounts = document.querySelectorAll("[id$='-amount']");
        let totalAmount;

        if (amounts.length === 1) {
            totalAmount = amounts[0].value;
        }
        else {
            console.log(`Amounts = ${[...amounts]}`);
            totalAmount = [...amounts].reduce((prev, curr) => {
                console.log(`Curr.value = ${parseFloat(curr.value)}`);
                let currValue;
                if (isNaN(parseFloat(curr.value))) {
                    currValue = 0;
                }
                else {
                    currValue = curr.value;
                }
                return Math.round((prev + parseFloat(currValue)) * 100) / 100;
            }, 0);
            console.log(`Total amount = ${totalAmount}`);
        }

        total.innerHTML = `Total: ${totalAmount}`;
    }
});
