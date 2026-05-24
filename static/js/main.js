/**
 * Main entry point for Carrots Budget JavaScript
 * Initializes all features based on page context
 */

import { Modal } from './core/modal.js';
import { MobileNav } from './features/navigation.js';
import { RolloverEditor } from './features/rollover-editor.js';
import { PurchaseFormManager } from './features/purchase-form.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize core features (on every page)
    new Modal();
    new MobileNav();

    // Initialize page-specific features based on DOM elements present

    // Rollover editor (yearly budget detail page)
    if (document.querySelector('.rollover-edit')) {
        const yearElement = document.querySelector('[data-year]');
        const year = yearElement ? yearElement.dataset.year : null;

        // If no data-year attribute, try to extract from page context
        // This handles the current implementation where year is in template
        if (!year) {
            // Year will be passed via data attribute in updated template
            const firstRollover = document.querySelector('.rollover-edit');
            if (firstRollover) {
                // For now, we'll need the year to be available
                // The template will need to provide it
                console.warn('Rollover editor requires year data attribute');
            }
        } else {
            new RolloverEditor(year);
        }
    }

    // Purchase form manager (purchase create page)
    if (document.querySelector('#purchase-form-container')) {
        new PurchaseFormManager();
    }

    // YTD month selector (yearly budget detail page)
    const monthSelect = document.querySelector('.month-select');
    if (monthSelect) {
        initYtdSelector(monthSelect);
    }
});

/**
 * Initialize the YTD month selector
 * @param {HTMLElement} select - The select element
 */
function initYtdSelector(select) {
    const urlParams = new URLSearchParams(window.location.search);
    const ytd = urlParams.get('ytd');

    if (ytd) {
        select.selectedIndex = parseInt(ytd) - 1;
    }

    select.addEventListener('change', function() {
        const currentPath = window.location.pathname;
        window.location.href = `${currentPath}?ytd=${this.value}`;
    });
}
