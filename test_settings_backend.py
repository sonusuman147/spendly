"""Comprehensive verification of Settings backend integration."""
from app import app

client = app.test_client()

# --- Register a fresh test user ---
resp = client.post('/register', data={
    'name': 'Settings Test',
    'email': 'settings.test@example.com',
    'password': 'password123',
    'confirm_password': 'password123',
    'security_question': 'What is your pet name?',
    'security_answer': 'Doge'
}, follow_redirects=True)
print('Register status:', resp.status_code)

# --- Login ---
resp = client.post('/login', data={
    'email': 'settings.test@example.com',
    'password': 'password123'
}, follow_redirects=True)
print('Login status:', resp.status_code)

# --- GET /settings ---
resp = client.get('/settings')
print('\n=== GET /settings ===')
print('Status:', resp.status_code)
html = resp.data.decode('utf-8')
print('User name in page:', 'Settings Test' in html)
print('User email in page:', 'settings.test@example.com' in html)
print('Member since present:', 'Member since' in html)
print('CSS linked:', 'settings.css' in html)
print('JS linked:', 'settings.js' in html)

# --- POST /settings/save ---
print('\n=== POST /settings/save ===')
resp = client.post('/settings/save', data={
    'name': 'Settings Updated',
    'email': 'updated@example.com',
    'currency': 'USD',
    'date_format': 'MM-DD-YYYY',
    'language': 'hi',
    'week_start': 'sunday',
    'budget_alert_threshold': '65',
    'default_payment_method': 'card',
    'theme': 'light',
    'accent_color': 'blue',
    'interface_density': 'compact',
    'two_factor_enabled': 'on',
    'login_alerts_enabled': 'on',
    'expense_reminders_enabled': 'on',
    'budget_alerts_enabled': 'on',
    'goal_milestones_enabled': 'on',
    'weekly_summary_enabled': 'on',
    'product_updates_enabled': 'on',
    'personalised_insights_enabled': 'on',
    'anonymous_usage_enabled': 'on',
}, follow_redirects=True)
print('Status:', resp.status_code)
print('Success message:', 'Settings saved successfully!' in resp.data.decode('utf-8'))

# --- Verify the settings were persisted ---
from database.db import get_user_settings, get_user_by_id, get_user_by_email
user = get_user_by_email('updated@example.com')
print('\n=== Verifying persisted data ===')
print('User found:', user is not None)
print('User name updated:', user['name'] == 'Settings Updated')
print('User email updated:', user['email'] == 'updated@example.com')

settings = get_user_settings(user['id'])
print('Currency:', settings['currency'])
print('Date format:', settings['date_format'])
print('Language:', settings['language'])
print('Week start:', settings['week_start'])
print('Budget alert threshold:', settings['budget_alert_threshold'])
print('Default payment method:', settings['default_payment_method'])
print('Theme:', settings['theme'])
print('Accent color:', settings['accent_color'])
print('Interface density:', settings['interface_density'])
print('2FA enabled:', settings['two_factor_enabled'])
print('Login alerts enabled:', settings['login_alerts_enabled'])
print('Expense reminders enabled:', settings['expense_reminders_enabled'])
print('Budget alerts enabled:', settings['budget_alerts_enabled'])
print('Goal milestones enabled:', settings['goal_milestones_enabled'])
print('Weekly summary enabled:', settings['weekly_summary_enabled'])
print('Product updates enabled:', settings['product_updates_enabled'])
print('Personalised insights enabled:', settings['personalised_insights_enabled'])
print('Anonymous usage enabled:', settings['anonymous_usage_enabled'])

# --- GET /settings shows updated data ---
client.get('/logout')
resp = client.post('/login', data={
    'email': 'updated@example.com',
    'password': 'password123'
}, follow_redirects=True)
resp = client.get('/settings')
html = resp.data.decode('utf-8')
print('\n=== GET /settings with updated data ===')
print('Updated name in page:', 'Settings Updated' in html)
print('Updated email in page:', 'updated@example.com' in html)

# --- POST /settings/change-password ---
print('\n=== POST /settings/change-password ===')
resp = client.post('/settings/change-password', data={
    'current_password': 'password123',
    'new_password': 'newpass456',
    'confirm_password': 'newpass456'
}, follow_redirects=True)
print('Status:', resp.status_code)
print('Password changed:', 'Password changed successfully!' in resp.data.decode('utf-8'))

# --- Verify new password works ---
client.get('/logout')
resp = client.post('/login', data={
    'email': 'updated@example.com',
    'password': 'newpass456'
}, follow_redirects=True)
print('Login with new password:', resp.status_code == 200)

# --- POST /settings/export ---
print('\n=== GET /settings/export ===')
resp = client.get('/settings/export')
print('Status:', resp.status_code)
print('Content-Type:', resp.headers.get('Content-Type'))
print('Has CSV data:', '=== TRANSACTIONS ===' in resp.data.decode('utf-8'))

# --- POST /settings/clear-data ---
print('\n=== POST /settings/clear-data ===')
resp = client.post('/settings/clear-data', follow_redirects=True)
print('Status:', resp.status_code)
print('Clear message:', 'Cleared' in resp.data.decode('utf-8'))

# --- POST /settings/delete-account ---
print('\n=== POST /settings/delete-account ===')
resp = client.post('/settings/delete-account', follow_redirects=True)
print('Status:', resp.status_code)
print('Account deleted message:', 'deleted' in resp.data.decode('utf-8').lower())

# Verify user no longer exists
user_after = get_user_by_email('updated@example.com')
print('User deleted:', user_after is None)

print('\n=== ALL SETTINGS BACKEND TESTS DONE ===')