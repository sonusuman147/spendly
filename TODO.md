# Theme Switch Implementation — Progress Tracker

## Steps

- [x] Step 1: Analyze codebase and create plan
- [x] Step 2: Edit `base.html` — Add before-paint script in `<head>`, theme switch HTML in navbar, after-DOM persistence script
- [x] Step 3: Edit `style.css` — Add light/dark/system theme variable overrides + switch component CSS
- [x] Step 4: Edit `profile.css` — Replace hardcoded colors with CSS variables for dark-mode compatibility (incl. edit-profile section + category tags + bar fills)
- [x] Step 5: Edit `expenses.css` — Convert hardcoded category tag colors to theme-aware CSS variables
- [x] Step 6: Fix dark-mode inconsistencies (footer tokens, `.auth-error` border, `.footer-name`/`.footer-*` muted text)
- [x] Step 7: Verify all files are consistent

## Files Modified

| File | Change |
|------|--------|
| `templates/base.html` | Theme switch HTML + before-paint restore script + change-persistence script |
| `static/css/style.css` | `:root` tokens, dark/system overrides, `.theme-field`/`.theme-switch` component CSS, footer tokens, category/bar tokens |
| `static/css/profile.css` | Edit-profile hardcoded colors → CSS vars; `.cat-*` tags → `--cat-*` tokens; `.bar-*` fills → `--bar-*` tokens |
| `static/css/expenses.css` | `.cat-*` tags → `--cat-*` tokens |
</content>

