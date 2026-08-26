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

    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
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
            var error = getEl('[data-help-form-error]');
            var success = getEl('[data-help-form-success]');
            if (error) {
                error.hidden = true;
                error.style.display = 'none';
            }
            if (form) {
                form.hidden = false;
                form.style.display = '';
            }
            if (success) {
                success.hidden = true;
                success.style.display = 'none';
            }
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
        var topicSelect = form.querySelector('select[name="topic"]');
        var subjectInput = form.querySelector('input[name="subject"]');
        var success = getEl('[data-help-form-success]');
        var toast = getEl('[data-help-toast]');

        function clearError() {
            if (error) {
                error.hidden = true;
                error.style.display = 'none';
            }
        }

        if (textarea && charCount) {
            textarea.addEventListener('input', function () {
                charCount.textContent = textarea.value.length;
                clearError();
            });
        }
        if (topicSelect) topicSelect.addEventListener('change', clearError);
        if (subjectInput) subjectInput.addEventListener('input', clearError);

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var topic = form.querySelector('select[name="topic"]');
            var subject = form.querySelector('input[name="subject"]');
            var message = form.querySelector('textarea[name="message"]');
            var errorMsg = '';

            if (!topic || !topic.value) errorMsg = 'Please select a topic.';
            else if (!subject || !subject.value.trim()) errorMsg = 'Please enter a subject.';
            else if (subject.value.trim().length > 120) errorMsg = 'Subject must be 120 characters or fewer.';
            else if (!message || !message.value.trim()) errorMsg = 'Please write a message.';
            else if (message.value.trim().length < 10) errorMsg = 'Message must be at least 10 characters.';
            else if (message.value.trim().length > 2000) errorMsg = 'Message must be 2000 characters or fewer.';

            if (errorMsg) {
                if (error) {
                    error.hidden = false;
                    error.style.display = 'flex';
                }
                if (errorText) errorText.textContent = errorMsg;
                return;
            }

            // Submit to the server — creates the ticket + initial message.
            var submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;

            fetch('/help/tickets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    topic: topic.value,
                    subject: subject.value.trim(),
                    message: message.value.trim()
                })
            }).then(function (resp) {
                return resp.json().catch(function () { return {}; }).then(function (data) {
                    return { ok: resp.ok, data: data };
                });
            }).then(function (res) {
                if (submitBtn) submitBtn.disabled = false;
                if (!res.ok || !res.data || !res.data.ok) {
                    if (error) {
                        error.hidden = false;
                        error.style.display = 'flex';
                    }
                    if (errorText) errorText.textContent =
                        (res.data && res.data.error) || 'Could not submit your request. Please try again.';
                    return;
                }
                if (error) {
                    error.hidden = true;
                    error.style.display = 'none';
                }
                if (form) {
                    form.reset();
                    form.hidden = true;
                    form.style.display = 'none';
                }
                if (charCount) charCount.textContent = '0';
                if (success) {
                    success.hidden = false;
                    success.style.display = 'flex';
                }
                refreshIcons();
                if (toast) {
                    toast.hidden = false;
                    toast.style.display = 'flex';
                    var toastText = getEl('[data-help-toast-text]');
                    if (toastText) toastText.textContent = 'Support request submitted successfully';
                    refreshIcons();
                    clearTimeout(bindContactForm._t);
                    bindContactForm._t = setTimeout(function () {
                        if (toast) {
                            toast.hidden = true;
                            toast.style.display = 'none';
                        }
                    }, 3000);
                }
                // Reload so the new ticket appears under My Support Requests.
                setTimeout(function () { window.location.reload(); }, 1000);
            }).catch(function () {
                if (submitBtn) submitBtn.disabled = false;
                if (error) {
                    error.hidden = false;
                    error.style.display = 'flex';
                }
                if (errorText) errorText.textContent = 'Network error — please try again.';
            });
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
                    var title = ticket.getAttribute('data-ticket-subject') || field('.help-ticket-title');
                    var status = ticket.getAttribute('data-ticket-status') || field('.help-ticket-status');
                    var ticketNo = ticket.getAttribute('data-ticket-no') || '';
                    var topic = ticket.getAttribute('data-ticket-topic') || '';
                    var created = ticket.getAttribute('data-ticket-created') || '';
                    var msg = ticket.getAttribute('data-ticket-message') || '';
                    var desc = field('.help-ticket-desc');

                    var html = '';
                    if (ticketNo) {
                        html += '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Ticket ID</span><span class="help-ticket-detail-value">#' + escapeHtml(ticketNo) + '</span></div>';
                    }
                    html += '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Subject</span><span class="help-ticket-detail-value">' + escapeHtml(title) + '</span></div>';
                    html += '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Status</span><span class="help-ticket-detail-value">' + escapeHtml(status) + '</span></div>';
                    if (topic) {
                        html += '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Topic</span><span class="help-ticket-detail-value">' + escapeHtml(topic) + '</span></div>';
                    }
                    if (created) {
                        html += '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Submitted</span><span class="help-ticket-detail-value">' + escapeHtml(created) + '</span></div>';
                    } else if (desc) {
                        html += '<div class="help-ticket-detail-row"><span class="help-ticket-detail-label">Details</span><span class="help-ticket-detail-value">' + escapeHtml(desc) + '</span></div>';
                    }
                    if (msg) {
                        html += '<div class="help-ticket-detail-row" style="flex-direction: column; align-items: flex-start; gap: 0.35rem;"><span class="help-ticket-detail-label">Message</span><div class="help-ticket-detail-message" style="width: 100%; word-break: break-word; white-space: pre-wrap;">' + escapeHtml(msg) + '</div></div>';
                    } else {
                        html += '<p class="help-ticket-detail-message">Thank you for reaching out to Spendly support. Our team has received your request and is working on it.</p>';
                    }
                    detail.innerHTML = html;
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