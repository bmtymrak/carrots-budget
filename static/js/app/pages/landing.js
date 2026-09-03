/* A progressive enhancement: sign-in works without JavaScript. */
(() => {
    document.querySelectorAll('[data-behavior="password-toggle"]').forEach((toggle) => {
        if (toggle.dataset.initialized) return;
        const password = document.getElementById(toggle.getAttribute('aria-controls'));
        if (!password) return;

        toggle.dataset.initialized = 'true';
        toggle.hidden = false;
        toggle.addEventListener('click', () => {
            const showPassword = password.type === 'password';
            password.type = showPassword ? 'text' : 'password';
            toggle.setAttribute('aria-pressed', String(showPassword));
            toggle.setAttribute('aria-label', showPassword ? toggle.dataset.hideLabel : toggle.dataset.showLabel);
        });
    });
})();
