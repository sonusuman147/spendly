# Switch UI Design — Theme Toggle (Implementation Spec)

Copy-paste spec for adding the light / dark / system switch to your
Spendly site. **Add only what's in this file** — no extra toggles,
buttons, or controls beyond the one 3-segment switch described below.

```
Theme
[ ☀  ●☾  🖥 ]
```

---

## 0. Scope — what this touches

- One switch component, placed once in your shared sidebar partial
  (bottom, below the nav list — see image 4).
- A block of CSS custom properties on `:root` / `body` that every page
  already reads through your existing token names (`--surface`,
  `--text-primary`, etc.) — you're not adding new colors, just letting
  the switch flip the tokens you already use.
- Optional ~10-line JS snippet — **only needed because your site is
  multi-page** (`/dashboard`, `/profile`, ... are separate URL loads,
  not client-side routes). Skip section 4 entirely if your app is a
  single-page app that never does a full reload between those views.

That's it. Don't add a 4th option, a settings-page duplicate, or a
second switch anywhere else.

---

## 1. HTML — drop into the sidebar partial

Place this once, in the file that renders your sidebar on every page
(so it's identical on Dashboard, Profile, Expenses, etc.):

```html
<div class="theme-field">
  <span class="theme-label">Theme</span>
  <div class="theme-switch" role="radiogroup" aria-label="Theme">

    <input type="radio" name="theme" id="theme-light" value="light">
    <label for="theme-light" aria-label="Light theme">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
           stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="4"/>
        <path d="M12 2v2M12 20v2M4 12H2M22 12h-2
                 M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4
                 M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>
      </svg>
    </label>

    <input type="radio" name="theme" id="theme-dark" value="dark" checked>
    <label for="theme-dark" aria-label="Dark theme">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
           stroke="currentColor" stroke-width="1.5">
        <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/>
      </svg>
    </label>

    <input type="radio" name="theme" id="theme-system" value="system">
    <label for="theme-system" aria-label="System theme">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
           stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="4" width="18" height="12" rx="2"/>
        <path d="M8 20h8M12 16v4"/>
      </svg>
    </label>

  </div>
</div>
```

The `checked` attribute on `#theme-dark` is just the hardcoded default
for a fresh visitor with no saved preference — section 4 overrides it
per-page once someone has actually picked something.

---

## 2. CSS — add once, applies to every page

```css
/* --- base tokens, used everywhere unless overridden below --- */
:root {
  --bg:#F7F8F6; --surface:#FFFFFF; --surface-alt:#F1F3EF;
  --border:#E4E6E1; --text-primary:#101410; --text-secondary:#5B5F58;
  --accent:#14532D; --accent-bg:#E5F3E8; --accent-text:#166534;
}

/* dark theme, active while the dark radio is checked */
body:has(#theme-dark:checked) {
  --bg:#0B0F14; --surface:#12171D; --surface-alt:#1A2029;
  --border:#232A33; --text-primary:#F3F5F2; --text-secondary:#8C948E;
  --accent:#1F7A4D; --accent-bg:#163524; --accent-text:#4ADE80;
}

/* system theme: only follow OS dark mode while "system" is checked */
@media (prefers-color-scheme: dark) {
  body:has(#theme-system:checked) {
    --bg:#0B0F14; --surface:#12171D; --surface-alt:#1A2029;
    --border:#232A33; --text-primary:#F3F5F2; --text-secondary:#8C948E;
    --accent:#1F7A4D; --accent-bg:#163524; --accent-text:#4ADE80;
  }
}

/* --- switch component itself --- */
.theme-label {
  display:block; font-size:11px; text-transform:uppercase;
  letter-spacing:.05em; color:var(--text-secondary); margin-bottom:8px;
}

.theme-switch {
  display:flex; gap:2px; padding:2px; border-radius:999px;
  background:var(--surface-alt); width:100%;
}

.theme-switch input { position:absolute; opacity:0; pointer-events:none; }

.theme-switch label {
  flex:1; display:flex; align-items:center; justify-content:center;
  height:32px; border-radius:999px; cursor:pointer;
  color:var(--text-secondary); border:1px solid transparent;
  transition:background .15s ease, color .15s ease;
}

.theme-switch label:hover { background:var(--surface); color:var(--text-primary); }

.theme-switch input:checked + label {
  background:var(--surface); border-color:var(--border);
  color:var(--accent-text);
}

.theme-switch input:focus-visible + label {
  outline:2px solid var(--accent); outline-offset:2px;
}
```

Make sure the rest of your CSS across **all pages** (including
`/profile`) already reads `var(--bg)`, `var(--surface)`,
`var(--text-primary)` etc. for backgrounds/text instead of hardcoded
colors — that's the only reason `/profile` currently looks unstyled in
your screenshot: the page isn't wired to these tokens yet, nothing to
do with the switch itself.

---

## 3. Do you even need section 4?

- **Single-page app** (Dashboard/Profile/Expenses are swapped in by JS
  router, no full browser reload, sidebar never unmounts) → **stop
  here.** The checked radio stays in the DOM the whole session; sections
  1–2 are the entire feature.
- **Multi-page site** (each nav link is a real `<a href>` that reloads
  the page — matches your `/profile` URL bar in the screenshot) →
  continue to section 4, or the user's theme choice will silently reset
  to "dark" every time they click a nav link.

---

## 4. JS — only if multi-page (persist the choice across loads)

Two small pieces. Put the first one **as early as possible in `<head>`**
(inline, before your CSS file even) so there's no flash of the wrong
theme; put the second wherever your other page scripts load.

**a) Before paint — restore the saved choice:**

```html
<script>
  (function () {
    var saved = localStorage.getItem('spendly-theme'); // 'light' | 'dark' | 'system'
    if (saved) document.documentElement.dataset.pendingTheme = saved;
  })();
</script>
```

**b) After the switch markup exists in the DOM — apply it and save future changes:**

```html
<script>
  (function () {
    var pending = document.documentElement.dataset.pendingTheme;
    if (pending) {
      var el = document.getElementById('theme-' + pending);
      if (el) el.checked = true;
    }
    document.querySelectorAll('.theme-switch input').forEach(function (input) {
      input.addEventListener('change', function () {
        localStorage.setItem('spendly-theme', input.value);
      });
    });
  })();
</script>
```

That's the entire JS footprint — no framework, no state library, just
"remember the click, re-check the right radio on the next page load."

---

## 5. Accessibility (unchanged from spec, don't skip)

- `role="radiogroup"` + `aria-label="Theme"` on the wrapper.
- Each `<label>` has its own `aria-label` naming the option.
- No custom key handling — native radios already give arrow-key /
  Tab navigation for free.
- Keep `:focus-visible` outline visible; don't strip it for the
  border-only selected state.

---

## 6. Checklist before you call it done

- [ ] Switch appears once, in the sidebar, identical markup on every page
- [ ] All page CSS (including `/profile`) reads the `--bg` / `--surface`
      / `--text-*` tokens instead of hardcoded colors
- [ ] Dark mode matches image 1, light mode matches image 2
- [ ] If multi-page: reload from Dashboard → Profile with "Light"
      selected — confirm Profile opens in Light, not back to Dark
- [ ] No second theme control added anywhere else in the app
