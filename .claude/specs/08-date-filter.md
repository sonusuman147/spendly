# Implementation Plan — 08 Date Filter

## Overview

Add a simple date filter bar to the Profile page (`/profile`) that allows users to filter their expense statistics and recent transactions by date range. A horizontal filter bar sits below the profile header with quick filter buttons (All Time, This Month, Last 3 Months, Last 6 Months) and custom date inputs with an Apply button. The selected filter updates the page via GET query parameters without any JavaScript frameworks or page reloads beyond natural form submission.

This is the 8th feature in the Spendly roadmap, following the complete expense CRUD. The profile page already shows summary data — this step adds filtering capability to make it more useful for users who want to analyze spending over specific periods.

## Depends on
- Steps 01–07 (database, registration, login/logout, profile page, Google auth, profile backend, expense CRUD)

## Routes

- **No new routes** — only the existing `GET /profile` route is modified

## Database changes

**No schema changes.** The `expenses.date` column (TEXT, ISO format YYYY-MM-DD) is used with `WHERE` clauses for filtering.

### Modified function: `get_user_expenses_summary()`

Add optional `start_date` and `end_date` parameters:

```python
def get_user_expenses_summary(user_id, start_date=None, end_date=None):
```

When either is provided, append `AND date >= ?` and/or `AND date <= ?` to all three queries (total/count, category breakdown, recent expenses). Use parameterized queries — never string concatenation.

## Templates

- **Modify:** `templates/profile.html` — Add the filter bar HTML below the profile header, before the stats cards

## Files to change

1. `database/db.py` — Add `start_date`/`end_date` parameters to `get_user_expenses_summary()`
2. `app.py` — Read query params, compute period date ranges, pass to DB function and template
3. `templates/profile.html` — Add filter bar UI with quick buttons, date inputs, and Apply button
4. `static/css/profile.css` — Add filter bar styles
5. `static/js/main.js` — Add vanilla JS for quick filter click handling and active state

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — dynamic WHERE clauses use `?` placeholders
- Passwords hashed with werkzeug (not applicable in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All URLs use `url_for()` — no hardcoded paths
- Quick filter buttons should be `<a>` tags linking to `/profile?period=<value>` for clean GET navigation
- The date form should use `GET` method and preserve existing query params

## Definition of done

- [ ] Filter bar renders below profile header on `/profile`
- [ ] Quick filter buttons: All Time, This Month, Last 3 Months, Last 6 Months
- [ ] Clicking a quick filter updates the URL with `?period=<value>` and reloads the page
- [ ] Active filter button is visually highlighted
- [ ] Start Date and End Date inputs appear alongside the quick buttons
- [ ] Clicking Apply submits a GET request with `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- [ ] Profile stats (Total Spent, Transactions, Top Category) update based on the filtered data
- [ ] Category breakdown bars update based on the filtered data
- [ ] Recent expenses table shows only entries within the filtered date range
- [ ] All Time shows all expenses (no date filter)
- [ ] This Month filters expenses from the 1st of the current month to today
- [ ] Last 3 Months filters expenses from 3 months ago to today
- [ ] Last 6 Months filters expenses from 6 months ago to today
- [ ] Custom date range works correctly when Apply is clicked
- [ ] UI stays clean and responsive — no layout shifts or overflow
- [ ] Flash messages and all existing profile page functionality are preserved
- [ ] No errors when no expenses exist in the filtered range (empty states work)
- [ ] App starts without errors

