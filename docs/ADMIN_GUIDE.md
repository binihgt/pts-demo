# PTS Demo - Business Owner & Administrator Guide

Welcome to **PTS Demo**! This guide is written specifically for business owners, executives, and managers. You do not need any coding or technical knowledge to manage your business using this system.

---

## 1. Accessing Your Web Dashboard

1. Open your web browser on your computer or smartphone (Chrome, Safari, Firefox, Edge).
2. Enter your portal URL (for example: `https://demo.yourcompany.com` or `http://localhost:5000` for local demo).
3. Enter your CEO username (`admin`) and your secure password.
4. Click **Sign In to Dashboard**.

> [!TIP]
> **Using on your phone:** The dashboard is designed to work smoothly on your smartphone screen. You can add it to your phone's Home Screen for quick 1-tap access just like an app.

---

## 2. Understanding Your Overview Page

When you log in, your main screen shows the financial heartbeat of your business:

- **Today's Sales**: Total value of goods or services sold today and the number of transactions.
- **This Week / This Month**: Running totals of sales versus the actual cash/electronic payments you have collected.
- **Unpaid Balances (Credit Watchlist)**: Highlights money owed to your company by customers. 
  - To record a customer paying down their balance, simply tap the green **Pay** button next to their name.
- **Sales Trend Chart**: A visual line showing your daily revenue over the last 14 days so you can see if business is trending up or down.
- **Top Sales Employees**: Ranks your top-performing team members by revenue generated.

---

## 3. Managing Employees & Staff Accounts

Only the CEO can access the **Team & Bot** menu.

### Adding a New Employee
1. In the top menu, tap **Team & Bot**.
2. Click the blue **Add Team Member** button.
3. Fill in:
   - **Full Name**: e.g., `Dawit Haile`
   - **Username**: e.g., `dawit` (lowercase, letters and numbers)
   - **Initial Password**: A temporary password (at least 8 characters)
   - **Role**:
     - **Employee**: Can record sales and payments and only see their own work.
     - **Manager**: Can see company-wide totals and download reports.
     - **CEO**: Full administrative access.
4. Click **Create Member**.
5. The system will create the account and automatically generate an 8-character **Telegram Link Code** (e.g. `A1B2C3D4`).

### Linking an Employee's Telegram Account
To allow an employee to record sales through Telegram:
1. Copy the 8-character link code shown next to their name on the Team page.
2. Send the code to your employee via SMS, WhatsApp, or Telegram.
3. Instruct the employee to:
   - Open Telegram and search for your bot.
   - Send the message: `/start <code>` (for example: `/start A1B2C3D4`).
4. The bot will reply: *"🎉 Account Linked Successfully!"* and their account is now active.
5. On your dashboard, their status will update to **Linked**.

### Deactivating an Employee Who Leaves the Company
If an employee leaves your company:
1. Go to **Team & Bot**.
2. Find the employee and tap the red **Disable** button.
3. Their web access is immediately blocked, and their Telegram bot will instantly refuse to process any new commands. Their historical sales records remain safely saved in your reports.

### Resetting a Forgotten Password
1. In **Team & Bot**, click **Reset Pwd** next to the employee's name.
2. Enter a new temporary password and click **Save Password**.

---

## 4. How Employees Record Sales on Telegram

Your employees never need to log into a computer. They can record sales on the road or in your shop directly from Telegram:

1. Employee sends: `/sale`
2. **Bot asks:** *What product was sold?* → Employee types: `Samsung 24" Monitor`
3. **Bot asks:** *How many units?* → Employee types: `2`
4. **Bot asks:** *What is the unit price in ETB?* → Employee types: `12500`
5. **Bot asks:** *Who is the customer?* → Employee types: `Desta Haile, +251911223344` (or `/skip` if walk-in).
6. **Confirmation:** The bot shows a summary card with the total (`25,000.00 ETB`) and buttons `[✅ Confirm & Save]` or `[❌ Cancel]`.
7. Once confirmed, the sale is recorded in your database instantly and appears on your CEO dashboard in real time!

---

## 5. How Payments Are Recorded

When a customer pays (full payment or installment):
- **Via Telegram Bot:** Employee types `/pay <invoice_id>` (e.g., `/pay 14`). The bot displays the remaining balance and presents quick buttons for **Telebirr**, **Bank Transfer / CBE**, or **Cash**.
- **Via Web Dashboard:** Find the sale on the **Sales** or **Overview** page and click the green **Pay** button. Enter the amount received and select the payment method.

The system will never allow recording a payment greater than the remaining invoice balance.

---

## 6. Downloading Financial Reports (Excel)

1. Tap **Reports** in the top navigation bar.
2. Choose a date range:
   - Click one of the quick buttons (**Today**, **This Week**, **This Month**, or **All Time**).
   - Or choose custom **Start Date** and **End Date** calendars.
3. Click the green **Download Excel (.xlsx)** button.
4. An Excel workbook will be downloaded to your device with 3 pre-formatted sheets:
   - **Summary**: High-level executive KPI numbers and collection breakdown.
   - **Sales**: Complete ledger of every item sold, price, employee, customer, and balance.
   - **Payments**: Detailed receipts list showing all cash, Telebirr, and bank transfers received.

> [!TIP]
> **Instant Telegram Reports:** You or your manager can simply message `/report` to the Telegram bot, and it will immediately generate and send the Excel spreadsheet directly into your chat!

---

## 7. Database Backups & Emergency Restore

### Automatic Daily Backups
The system automatically creates a complete snapshot of your database every night at **02:00 AM**. 
- It keeps the last **14 days** of backups.
- Backups older than 14 days are automatically cleaned up to save disk space.

### Restoring from a Backup
If you ever need to restore your database to an earlier day:
1. Locate the backup file in the `backups/` folder (e.g., `pts_backup_20261025_020000.db`).
2. Stop the web and bot services.
3. Replace the active `instance/pts_demo.db` with your chosen backup file:
   ```bash
   cp backups/pts_backup_20261025_020000.db instance/pts_demo.db
   ```
4. Restart the services. Your data will be restored to that exact point in time.
