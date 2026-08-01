# Spendly — Frontend Redesign Fix Pass (Frontend Only)

Scope: **Frontend only**. Do NOT modify backend, routes, DB, auth, or business logic.

## Steps

- [x] Initial redesign — left sidebar app shell, top header, dashboard redesign (welcome banner, filter bar, stat cards, recent transactions, CSS donut chart, quick actions), theme light/dark/system, responsive mobile drawer, collapsible sidebar (done in base.html, style.css, profile.css, profile.html, main.js).
- [x] Restore original Spendly branding in `static/css/style.css` — warm off-white "ghee" body background (`#f7f6f3` / `#f0ede6`), original ink palette, original green `--accent: #1a472a`, restored dark/system tokens, shared `.auth-success`, warm glass header.
- [x] Add shared `.auth-success` styling (in `style.css`).
- [x] Add profile-header styles to `static/css/profile.css`; remove duplicated `.auth-error`/`.auth-success` (now shared via `style.css`).
- [x] Fix broken HTML nesting in `templates/expenses/delete.html` (move actions out of details; close card/container correctly).
- [x] Add `page_title`/`breadcrumb` blocks to `templates/profile_edit.html`.
- [x] Polish expense list header + table (date chips, hover, actions) — frontend only.
- [x] Adapt `static/css/expenses.css` for the new app shell (form/delete centered cards, modern radii/shadows, responsive table).
- [x] JavaScript cleanup — sidebar collapse, mobile drawer, profile dropdown, theme switch (already implemented in `main.js`; verified no console errors).
- [x] Final verification — `pytest` (17 passed), page sweep (200s on all public pages), broken-link check, feature checklist, updated summary.

## Notes

- The `.claude/commands/create-specs.md` file does not exist; the actual command file is `.claude/commands/create-spec.md` (git feature-branch/spec workflow). It was read and its context applied (frontend-only, use CSS variables, Lucide icons, all templates extend base.html, preserve backend).
- `_diag.py` diagnostic script has been deleted (`Remove-Item _diag.py` — `Test-Path` returned `False`).

