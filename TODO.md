# TODO: Refactor Profile Page UX — COMPLETED ✅

## 1. Update `templates/profile.html` — Clean read-only overview
- [x] Remove Edit Profile section card
- [x] Remove Change Password section card
- [x] Add "Edit Profile" button to top-right of profile-header
- [x] Add `.profile-header-action` container in the header

## 2. Create `templates/profile_edit.html` — Dedicated edit page
- [x] New template with form card
- [x] Fields: Full Name, Email, Current Password, New Password, Confirm New Password
- [x] Save Changes and Cancel buttons
- [x] Loads profile.css for consistent styling

## 3. Update `app.py` — Add `/profile/edit` route
- [x] New GET/POST route for `/profile/edit`
- [x] POST validates and updates profile + optionally password
- [x] Redirect back to `/profile` on success

## 4. Update `static/css/profile.css` — Button + edit page styles
- [x] `.profile-header-action` for Edit button positioning
- [x] `.btn-edit-profile` button styles
- [x] `.profile-edit-page` section styles
- [x] Edit form card, sections, and action button styles

## 5. Verification
- [x] App loads without errors
