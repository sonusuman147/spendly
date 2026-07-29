# Edit Profile Page Redesign - Complete ✓

## ✅ Step 1: Update `templates/base.html` — Navbar Redesign
- User chip with dynamic initials (green circle `#1B4332`), name, dropdown chevron
- "Sign out" as outlined button with `log-out` icon
- "Dashboard" link alongside "Expenses"
- Navbar stays white

## ✅ Step 2: Rewrite `templates/profile_edit.html` — Complete Layout
- Page header: muted "← Back to Profile", bold "Edit Profile" H1, gray subtext
- Card 1 (Profile Information): Two-column grid — left avatar, right fields
- Dynamic avatar initials from `user.name`
- Camera icon button overlay on avatar
- Full name + Email side-by-side with leading person/mail icons
- Green shield-check note below email
- Card 2 (Change Password): Lock icon title + subtitle, 3 pill-style rows with eye-toggle
- Hidden actual inputs wired via JS (name attributes unchanged: `current_password`, `new_password`, `confirm_new_password`)
- Pale green password tips banner with shield-check icon
- Footer bar: outlined gray "Cancel" + solid dark-green "Save Changes" with save icon
- Flash messages preserved and styled
- Form action unchanged (`method="POST" action="{{ url_for('profile_edit') }}"`)
- All input names preserved for backend compatibility

## ✅ Step 3: Add styles to `static/css/profile.css`
- All new styles scoped under `.edit-page-*` prefix (no conflict with profile view)
- White cards with 18px border-radius, subtle shadow, generous padding
- Avatar: 96px pale green circle, 2rem bold initials, camera overlay button
- Two-column grid layout (1fr 1.8fr)
- Inputs styled with 9px radius, soft borders, icon-left padding, light fill
- Password pill rows with lock icon, label+hint, eye toggle
- Tips banner with pale green background
- Footer bar: white, right-aligned, Cancel/Save buttons
- Deep forest green accent (`#1B4332`) throughout
- Responsive: collapses to single column at 768px

## ✅ Step 4: Add password toggle JS
- Vanilla JS in `{% block scripts %}` — event delegation on all `.edit-pwd-toggle` buttons
- Toggles between `eye` and `eye-off` Lucide icons
- Updates `aria-label` for accessibility
- Focus sync: clicking pill row focuses hidden input

