# PTS Demo - Manual & Mobile Testing Checklist

This document provides a comprehensive quality assurance checklist for verifying **PTS Demo** on mobile devices (specifically targeting a **360px-wide Android smartphone**) and validating role authorization.

---

## 1. 360px Android Phone Screen Test (Chrome / Firefox DevTools)

To simulate a real Android smartphone in your desktop browser:
1. Open Google Chrome or Mozilla Firefox.
2. Press **F12** (or right-click → **Inspect**).
3. Toggle Device Toolbar (**Ctrl + Shift + M**).
4. Set dimensions to: **Width: 360px, Height: 740px** (e.g. Samsung Galaxy A/S series).

### Visual & Layout Checklist (Real Android Phone: 320px - 400px)
| Test Item | Verification Criteria | Status |
|---|---|:---:|
| **Horizontal Scrolling** | Page width is strictly bounded. **Zero horizontal scrollbar** appears on Overview, Sales, Payments, Team, or Login pages at 320-400px. | [x] Passed |
| **KPI Card Values (Item 6)** | Large financial values (e.g., `1,916,000.00 ETB`) scale gracefully with `clamp()` and wrap cleanly without overflowing cards on narrow phones. | [x] Passed |
| **Currency Consistency (Item 7)** | All currency displays formatted strictly as `225,000.00 ETB` across cards, tables, modals, audit logs, and bot chats via shared `format_money`. | [x] Passed |
| **Team & Bot Mobile (Item 8)** | Action buttons (New Code / Reset Pwd / Disable) stack and wrap across full card width. Clipped "ons" label eliminated. Long names wrap without colliding with `@username`. | [x] Passed |
| **Timezone Accuracy (Item 9)** | All timestamps stored in UTC but displayed in Africa/Addis_Ababa (`UTC+3`, EAT) across web tables, audit log, bot messages, and Excel columns labeled `(EAT)`. | [x] Passed |
| **Filter Usability (Item 10)** | Date inputs on Sales and Payments display visible "From" and "To" labels. Payment method dropdown shortened to "All Methods". | [x] Passed |
| **Top Employees (Item 11)** | Header includes "All Time" period badge and sales metric displays "sales" rather than "completed sales". | [x] Passed |
| **Login Mobile Usability (Item 12)** | Username field includes `autocapitalize="none"`, `autocorrect="off"`, `spellcheck="false"`, `autocomplete="username"`. Password includes `autocomplete="current-password"`. Favicon returns HTTP 200 at `/favicon.ico`. | [x] Passed |
| **Add Team Member (Item 13)** | Password field includes show/hide eye toggle, `autocomplete="new-password"`, and enforces 8 character minimum. | [x] Passed |
| **Touch Tap Targets** | All buttons, text fields, and dropdowns maintain a minimum height of **44px** for comfortable touch tap targets. | [x] Passed |
| **Responsive Table Transformation** | The Sales and Payments tables collapse into standalone touch cards on small screens. | [x] Passed |
| **Quick Pay Modal** | Quick Pay modal dynamically populates formatted remaining balance (`225,000.00 ETB`) and pre-fills default amount on phone screens. | [x] Passed |

---

## 2. Role-Based Access Control Verification

Test each user account to confirm permissions and data isolation:

### Test Scenario A: CEO (`admin` / `Password123!`)
- [ ] Log in via `/auth/login`. Verify redirect to Overview.
- [ ] Verify that **Team & Bot** and **Audit Log** links are visible in the navigation bar.
- [ ] Navigate to `/employees/`. Confirm all staff accounts and link codes are displayed.
- [ ] Click **New Code** next to an employee. Confirm a fresh 8-character link code is generated.
- [ ] Navigate to `/audit/`. Confirm all system actions (logins, sales, updates) are listed.
- [ ] Download an Excel report from `/reports/`. Confirm HTTP 200 and valid file.

### Test Scenario B: Manager (`manager` / `Password123!`)
- [ ] Log in as `manager`.
- [ ] Verify that **Team & Bot** and **Audit Log** links are **hidden** from the top navigation.
- [ ] Manually attempt to navigate to `http://127.0.0.1:5000/employees/`. Verify **403 Forbidden** error page appears.
- [ ] Manually attempt to navigate to `http://127.0.0.1:5000/audit/`. Verify **403 Forbidden** error page appears.
- [ ] Navigate to `/reports/`. Confirm Manager **can** download Excel reports.
- [ ] Navigate to `/sales/`. Confirm Manager **can** see all company sales.

### Test Scenario C: Employee (`alemu` / `Password123!`)
- [ ] Log in as `alemu`.
- [ ] Navigate to `/sales/`.
- [ ] **Data Isolation Check**: Confirm that Alemu sees **only** his own sales. Verify that sales made by other employees (`chala` or `marta`) do **not** appear.
- [ ] Manually attempt to visit `/reports/`. Verify **403 Forbidden**.
- [ ] Manually attempt to visit `/employees/`. Verify **403 Forbidden**.

---

## 3. Telegram Bot Interactive Test Checklist

Connect your bot to a live token from `@BotFather` to run interactive end-to-end tests:

### Test Scenario A: Unauthorized Account Refusal
1. From an unlinked Telegram account, message: `/start`
2. **Expected Response:** Polite rejection message explaining that only pre-registered accounts can use the bot, with instructions to ask the CEO for a link code.
3. Message: `/sale`
4. **Expected Response:** Access denied.

### Test Scenario B: Account Linking & Duplicate Link Prevention
1. From CEO dashboard (`/employees/`), copy a fresh link code (e.g. `A1B2C3D4`).
2. If your Telegram account is already linked to another employee, sending `/start A1B2C3D4` must reply:
   *"⛔ Account Already Linked: This Telegram account is already linked to another user. Ask your administrator to unlink it first."*
   Verify that the code `A1B2C3D4` was **not consumed** and remains valid in the dashboard.
3. Unlink the Telegram ID from the dashboard, then send `/start A1B2C3D4`.
4. **Expected Response:** *"🎉 Account Linked Successfully!"* followed by available command menu.

### Test Scenario C: Guided Sale Creation & Input Validation (`/sale`)
1. Send: `/sale`
2. **Product Validation Test**: Paste a multi-line product description or text over 100 characters.
   - **Expected:** Bot politely rejects with error: *"Product name cannot contain multiple lines / is too long"* and stays on Step 1.
3. Enter valid product: `Samsung 24" IPS Monitor`
4. Enter quantity: `2`
5. Enter unit price: `12500`
6. **Customer Phone Validation Test**:
   - Enter invalid phone `011234567` → Bot rejects with clear error and example.
   - Enter local phone `0911223344` → Bot normalizes to `+251911223344`.
7. Bot displays confirmation summary with formatted currency: `25,000.00 ETB`.
8. Tap `[✅ Confirm & Save]`.

### Test Scenario D: Payment Recording (`/pay`)
1. **Interactive Prompt Test**: Send `/pay` without any argument.
   - **Expected:** Bot replies *"Which invoice number would you like to pay?"* and lists your recent unpaid invoices with remaining balances formatted as `25,000.00 ETB`.
2. Reply with invoice number: `51` (or your invoice ID).
   - If an employee enters another employee's invoice ID: *"⛔ You are only authorized to record payments for your own sales."*
   - If already paid: *"✅ Invoice is already fully paid!"*
3. Enter payment amount: `25000`
4. Select method: `[📱 Telebirr]`
5. **Expected Response:** Payment receipt `PAY-...` recorded, remaining balance `0.00 ETB`, and status `🎉 FULLY SETTLED`.

### Test Scenario E: Employee `/mysales` vs Manager `/today`
1. From Employee Telegram: Send `/mysales`.
   - **Expected:** Shows personal transactions recorded today, total sold, collected, and unpaid balances formatted as `225,000.00 ETB` with timestamps in `(EAT)`.
2. From Employee Telegram: Send `/today`.
   - **Expected:** *"🔒 Permission Denied: Restricted to CEO or Manager"*.
3. From Manager Telegram: Send `/today`.
   - **Expected:** Unified totals matching Dashboard and Excel Summary:
     - `Today's sales`
     - `Collected today (all invoices)`
     - `Total outstanding (all invoices)`
     - Payment methods breakdown using `format_money(...)`.
4. From Manager Telegram: Send `/report`.
   - **Expected:** Generates and delivers the multi-sheet `.xlsx` file directly into chat with `(EAT)` timestamps, Excel `=SUM(...)` formulas, and frozen headers.
   - **Expected:** Generates and delivers the multi-sheet `.xlsx` file directly into chat.

---

## 4. Automated Regression Testing

Always execute the automated test suite before deploying new changes:

```powershell
.venv\Scripts\pytest.exe -v
```

**Test Coverage Summary (21 Tests):**
- `tests/test_auth_roles.py`: 8 tests (Login, logout, bad passwords, deactivated accounts, CEO/Manager/Employee authorization, data isolation).
- `tests/test_sales.py`: 4 tests (Sale math, partial payments, full payments, overpayment rejection, input validation).
- `tests/test_bot.py`: 4 tests (ApplicationBuilder setup, account linking via link code, unauthorized refusal, role guards).
- `tests/test_reports.py`: 3 tests (openpyxl sheet structure, date range filtering, web download authorization).
- `tests/test_backup.py`: 2 tests (SQLite online backup integrity, 14-backup retention rotation).
