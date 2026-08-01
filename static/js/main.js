// ================================================================== //
// Spendly — SaaS Dashboard Frontend Behaviour (vanilla JS)           //
// ================================================================== //

(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Sidebar collapse (desktop) + mobile drawer                          */
    /* ------------------------------------------------------------------ */

    var shell = document.querySelector('.app-shell');
    var sidebar = document.getElementById('appSidebar');
    var backdrop = document.querySelector('[data-app-backdrop]');
    var toggleBtns = document.querySelectorAll('[data-sidebar-toggle]');
    var closeBtns = document.querySelectorAll('[data-sidebar-close]');
    var isMobile = function () { return window.innerWidth <= 768; };

    // Restore saved sidebar state on desktop (default expanded)
    if (shell) {
        var saved = localStorage.getItem('spendly-sidebar');
        if (saved === 'collapsed' && !isMobile()) {
            shell.setAttribute('data-sidebar', 'collapsed');
        } else if (!isMobile()) {
            shell.setAttribute('data-sidebar', 'expanded');
        }
    }

    function setSidebarCollapsed(collapsed) {
        if (!shell) return;
        if (isMobile()) return; // mobile uses drawer, not collapse
        shell.setAttribute('data-sidebar', collapsed ? 'collapsed' : 'expanded');
        localStorage.setItem('spendly-sidebar', collapsed ? 'collapsed' : 'expanded');
    }

    function openDrawer() {
        if (!shell || !backdrop) return;
        shell.classList.add('sidebar-open');
        backdrop.hidden = false;
        // Force reflow so the transition plays
        void backdrop.offsetWidth;
        backdrop.classList.add('visible');
        document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
        if (!shell || !backdrop) return;
        shell.classList.remove('sidebar-open');
        backdrop.classList.remove('visible');
        document.body.style.overflow = '';
        // Hide backdrop after transition completes
        setTimeout(function () { backdrop.hidden = true; }, 250);
    }

    toggleBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (isMobile()) {
                openDrawer();
            } else {
                var collapsed = shell.getAttribute('data-sidebar') === 'expanded';
                setSidebarCollapsed(collapsed);
            }
        });
    });

    closeBtns.forEach(function (btn) {
        btn.addEventListener('click', closeDrawer);
    });

    if (backdrop) {
        backdrop.addEventListener('click', closeDrawer);
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && shell && shell.classList.contains('sidebar-open')) {
            closeDrawer();
        }
    });

    // When resizing back to desktop, close any open drawer state
    window.addEventListener('resize', function () {
        if (!isMobile() && shell && shell.classList.contains('sidebar-open')) {
            closeDrawer();
        }
    });

    /* ------------------------------------------------------------------ */
    /* User profile dropdown                                               */
    /* ------------------------------------------------------------------ */

    var profileWrap = document.querySelector('[data-profile-dropdown]');
    var profileToggle = document.querySelector('[data-profile-toggle]');
    var profileMenu = profileWrap ? profileWrap.querySelector('.app-profile-menu') : null;

    function closeAllDropdowns() {
        if (profileMenu) profileMenu.hidden = true;
    }

    if (profileToggle && profileMenu) {
        profileToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            profileMenu.hidden = !profileMenu.hidden;
        });

        // Close when clicking outside
        document.addEventListener('click', function (e) {
            if (!profileWrap.contains(e.target)) {
                profileMenu.hidden = true;
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /* Notification toggle (UI only)                                       */
    /* ------------------------------------------------------------------ */

    var notifBtn = document.querySelector('[data-notification-toggle]');
    if (notifBtn) {
        notifBtn.addEventListener('click', function () {
            notifBtn.classList.toggle('is-active');
        });
    }

    /* ------------------------------------------------------------------ */
    /* Global keyboard shortcut: "/" focuses search                        */
    /* ------------------------------------------------------------------ */

    var searchInput = document.querySelector('.app-search-input');
    document.addEventListener('keydown', function (e) {
        if (e.key === '/' && searchInput && !/input|textarea|select/i.test(document.activeElement.tagName)) {
            e.preventDefault();
            searchInput.focus();
        }
    });

    /* ------------------------------------------------------------------ */
    /* Re-run lucide icon rendering whenever dynamic elements change       */
    /* ------------------------------------------------------------------ */

    window.Spendly = {
        refreshIcons: function () {
            if (window.lucide) window.lucide.createIcons();
        }
    };
})();

