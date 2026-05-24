/**
 * Rollover editor for yearly budget detail page
 * Handles inline editing of rollover amounts
 */

import { getCookie } from '../core/utils.js';

export class RolloverEditor {
    constructor(year) {
        this.year = year;
        this.csrfToken = getCookie('csrftoken');
        this.inputs = document.querySelectorAll(".rollover-edit");

        if (this.inputs.length > 0) {
            this.init();
        }
    }

    init() {
        this.inputs.forEach((input) => {
            input.addEventListener('keydown', (event) => this.handleKeydown(event));
            input.addEventListener('blur', (event) => this.save(event));
        });
    }

    handleKeydown(event) {
        if (event.key === "Enter") {
            this.save(event);
        }
    }

    async save(event) {
        if (event.key === "Enter" || event.type === 'blur') {
            event.preventDefault();
            const amount = event.currentTarget.value;
            const category = event.currentTarget.dataset.category;

            try {
                const response = await fetch('/budgets/rollover/update/', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': this.csrfToken,
                    },
                    body: JSON.stringify({
                        amount: amount,
                        category: category,
                        year: this.year
                    })
                });

                if (!response.ok) {
                    console.error('Failed to save rollover:', response.statusText);
                }
            } catch (error) {
                console.error('Error saving rollover:', error);
            }
        }
    }
}
