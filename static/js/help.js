// ================================================================== //
// Spendly — Help & Support Page Behaviour (vanilla JS)                //
// ================================================================== //

(function () {
    'use strict';

    function getEl(sel) { return document.querySelector(sel); }
    function getAll(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
    }

    var cards = getAll('.help-card');
    var activeTopic = 'all';
    var searchInput = getEl('[data-help-search]');
    var emptyState = getEl('[data-help-empty]');
    var cardsGrid = getEl('[data-help-cards]');
    var chipBtns = getAll('[data-help-topic]');

    function currentSearch() {
        return (searchInput && searchInput.value.trim().toLowerCase()) || '';
    }

    function matchesTopic(card) {
        return activeTopic === 'all' || card.getAttribute('data-help-topic-match') === activeTopic;
    }

    function matchesSearch(card, query) {
        if (!query) return true;
        return card.textContent.toLowerCase().indexOf(query) !== -1;
    }

    function applyFilters() {
        var q = currentSearch();
        var visible = 0;
        cards.forEach(function (card) {
            var show = matchesTopic(card) && matchesSearch(card, q);
            card.hidden = !show;
            if (show) visible++;
        });
        if (cardsGrid) cardsGrid.hidden = false;
        if (emptyState) emptyState.hidden = !(visible === 0 && q !== '');
    }

    function bindSearch() {
        if (!searchInput) return;
        searchInput.addEventListener('input', function () { applyFilters(); });
        document.addEventListener('keydown', function (e) {
            if (e.key === '/' && document.activeElement !== searchInput) {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }

    function setTopic(topic, btn) {
        activeTopic = topic;
        chipBtns.forEach(function (b) { b.classList.remove('is-active'); });
        if (btn) btn.classList.add('is-active');
    }

    function bindChips() {
        chipBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                setTopic(btn.getAttribute('data-help-topic'), btn);
                applyFilters();
            });
        });
    }

    function bindPopularTags() {
        getAll('[data-help-search-tag]').forEach(function (tag) {
            tag.addEventListener('click', function () {
                if (searchInput) {
                    searchInput.value = tag.textContent.trim();
                    setTopic('all', getEl('[data-help-topic="all"]'));
                    applyFilters();
                }
            });
        });
    }

    function bindClearSearch() {
        var clearBtn = getEl('[data-help-clear-search]');
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                if (searchInput) searchInput.value = '';
                setTopic('all', getEl('[data-help-topic="all"]'));
                applyFilters();
            });
        }
    }

    function bindFaq() {
        getAll('[data-help-faq]').forEach(function (item) {
            var summary = item.querySelector('summary');
            if (!summary) return;
            summary.addEventListener('click', function (e) {
                e.preventDefault();
                getAll('[data-help-faq]').forEach(function (other) {
                    if (other !== item) other.open = false;
                });
                item.open = !item.open;
                refreshIcons();
            });
        });
    }

    /* Modals */
    function openModal(modal) { if (modal) modal.hidden = false; refreshIcons(); }
    function closeAllModals() { getAll('.help-modal').forEach(function (m) { m.hidden = true; }); }

    function bindModalClose() {
        getAll('[data-help-modal-close]').forEach(function (btn) {
            btn.addEventListener('click', function () { closeAllModals(); });
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeAllModals();
        });
    }

    function showContactForm() {
        closeAllModals();
        var modal = getEl('[data-help-contact-modal]');
        if (modal) {
            var form = getEl('[data-help-contact-form]');
            if (form) form.hidden = false;
            var success = getEl('[data-help-form-success]');
            if (success) success.hidden = true;
            openModal(modal);
        }
    }

    function bindContactOpen() {
        getAll('[data-help-contact-open]').forEach(function (btn) {
            btn.addEventListener('click', showContactForm);
        });
        var newBtn = getEl('[data-help-new-ticket]');
        if (newBtn) newBtn.addEventListener('click', showContactForm);
    }

    function bindContactForm() {
        var form = getEl('[data-help-contact-form]');
        if (!form) return;
        var error = getEl('[data-help-form-error]');
        var errorText = getEl('[data-help-form-error-text]');
        var charCount = getEl('[data-help-char-count]');
        var textarea = form.querySelector('textarea[name="message"]');
        var success = getEl('[data-help-form-success]');
        var toast = getEl('[data-help-toast]');

        if (textarea && charCount) {
            textarea.addEventListener('input', function () {
                charCount.textContent = textarea.value.length;
            });
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var topic = form.querySelector('select[name="topic"]');
            var subject = form.querySelector('input[name="subject"]');
            var message = form.querySelector('textarea[name="message"]');
            var errorMsg = '';

            if (!topic || !topic.value) errorMsg = 'Please select a topic.';
            else if (!subject || !subject.value.trim()) errorMsg = 'Please enter a subject.';
            else if (!message || !message.value.trim()) errorMsg = 'Please write a message.';
            else if (message.value.trim().length < 10) errorMsg = 'Message must be at least 10 characters.';

            if (errorMsg) {
                if (error) error.hidden = false;
                if (errorText) errorText.textContent = errorMsg;
                return;
            }

            if (error) error.hidden = true;
            if (form) form.hidden = true;
            if (success) success.hidden = false;
            if (toast) {
                toast.hidden = false;
                var toastText = getEl('[data-help-toast-text]');
                if (toastText) toastText.textContent = 'Support request submitted successfully';
                refreshIcons();
                clearTimeout(bindContactForm._t);
                bindContactForm._t = setTimeout(function () { if (toast) toast.hidden = true; }, 3000);
            }
        });
    }

    function bindTicketView() {
        getAll('[data-help-view-ticket]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var ticket = btn.closest('[data-help-ticket]');
                if (!ticket) return;
                var detail = getEl('[data-help-ticket-detail]');
                var modal = getEl('[data-help-ticket-modal]');
                if (detail) {
                    function field(sel) {
                        var el = ticket.querySelector(sel);
                        return el ? el.textContent.trim() : '';
                    }
                    var title = field('.help-ticket-title');
                    var status = field('.help-ticket-status');
                    var desc = field('.help-ticket-desc');
                    detail.innerHTML = '' +
                        '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Ticket</span><span class="help-ticket-detail-value">' + title + '</span></div>' +
                        '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Status</span><span class="help-ticket-detail-value">' + status + '</span></div>' +
                        '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Details</span><span class="help-ticket-detail-value">' + desc + '</span></div>' +
                        '<p class="help-ticket-detail-message">Thank you for reaching out to Spendly support. Our team has received your request and is working on it.</p>';
                }
                if (modal) openModal(modal);
            });
        });
    }

    function bindStatusRefresh() {
        var btn = getEl('[data-help-status-refresh]');
        var toast = getEl('[data-help-toast]');
        if (!btn) return;
        btn.addEventListener('click', function () {
            btn.textContent = 'Checking...';
            setTimeout(function () {
                btn.textContent = 'Refresh status';
                if (toast) {
                    toast.hidden = false;
                    var toastText = getEl('[data-help-toast-text]');
                    if (toastText) toastText.textContent = 'All systems operational';
                    refreshIcons();
                    clearTimeout(bindStatusRefresh._t);
                    bindStatusRefresh._t = setTimeout(function () { if (toast) toast.hidden = true; }, 3000);
                }
            }, 1200);
        });
    }

    function init() {
        bindModalClose();
        bindContactOpen();
        bindContactForm();
        bindTicketView();
        bindStatusRefresh();
        bindSearch();
        bindChips();
        bindPopularTags();
        bindClearSearch();
        bindFaq();
        applyFilters();
        refreshIcons();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();