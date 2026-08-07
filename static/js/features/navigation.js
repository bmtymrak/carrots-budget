/**
 * Mobile navigation menu toggle
 */

export class MobileNav {
    constructor() {
        this.menuToggle = document.getElementById('menu-toggle');
        this.nav = document.getElementById('primary-nav');

        if (this.menuToggle && this.nav) {
            this.init();
        }
    }

    init() {
        this.menuToggle.addEventListener('click', () => {
            this.nav.classList.toggle('nav-open');
        });
    }
}
