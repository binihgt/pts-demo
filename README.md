# PTS Demo - Business Management System

A production-quality business management system designed for small and medium retail businesses. Employees record sales and payment collections through a guided Telegram bot, while executives monitor cash flow, inventory, and sales performance through a secure, mobile-first web dashboard.

---

## 🌟 Key Highlights & Architecture

```text
                  ┌────────────────────────────────────────┐
                  │          Telegram Cloud API            │
                  └───────────────────▲────────────────────┘
                                      │ Polling / Webhook
                                      ▼
┌─────────────────────────┐     ┌──────────────────────────┐
│  Mobile Web Dashboard   │     │   Telegram Sales Bot     │
│  (Flask / Bootstrap 5)  │     │ (python-telegram-bot v20)│
└────────────┬────────────┘     └────────────┬─────────────┘
             │                               │
             ▼                               ▼
      ┌─────────────────────────────────────────────┐
      │          Shared Service Layer               │
      │  (SalesService, ReportService, Auth)        │
      └──────────────────────┬──────────────────────┘
                             │
                             ▼
      ┌─────────────────────────────────────────────┐
      │         SQLite / PostgreSQL (ORM)           │
      │   (Users, Customers, Sales, Payments, Audit)│
      └──────────────────────┬──────────────────────┘
                             │
                             ▼
      ┌─────────────────────────────────────────────┐
      │         Automated Online Backups            │
      │      (SQLite Backup API + 14-Day Rotate)    │
      └─────────────────────────────────────────────┘
```

- **Executive Web Dashboard**: Flask, Flask-Login, Flask-WTF (CSRF), Flask-Limiter, Chart.js, Bootstrap 5.
- **Telegram Sales Bot**: Built with `python-telegram-bot` v20+ using asynchronous `ConversationHandler` workflows for fast on-the-go data entry.
- **Role-Based Access Control**:
  - **CEO**: Full administrative privileges (manage team, reset passwords, generate Telegram link codes, audit logs, financial reports).
  - **Manager**: Company-wide sales oversight, collections, and financial report generation.
  - **Employee**: Can view and record only their own sales and collections; zero access to administrative controls.
- **Multi-Sheet Excel Reporting**: Automated `.xlsx` generation using `openpyxl` with KPI summaries, sales ledgers, and receipt logs.
- **Zero-Downtime SQLite Backups**: Live online snapshotting via `sqlite3.Connection.backup()` with a rolling 14-backup retention policy.

---

## 📱 User Interface Previews

> *Mobile-First Design: Hand-crafted to collapse into touch cards on 360px Android smartphone screens with zero horizontal scrolling.*

| Desktop Executive Dashboard | Mobile Phone Card View (360px) |
|:---:|:---:|
| `[ Overview KPI Cards + 14-Day Sales Trend Line Chart ]` | `[ Responsive Table Collapsed into Touch Cards ]` |

| Telegram Bot /sale Wizard | Telegram Bot /pay Flow |
|:---:|:---:|
| `[ Step-by-step Item -> Qty -> Price -> Confirm ]` | `[ Invoice Lookup -> Balance Check -> Telebirr/Bank/Cash ]` |

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11 or higher
- Git

### 2. Setup Virtual Environment & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/your-username/pts-demo.git
cd pts-demo

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional)* Add your Telegram Bot Token from [@BotFather](https://t.me/BotFather) to test live Telegram interactions.

### 4. Seed the Database with Realistic Demo Data
Populates 5 staff accounts, 8 customers, and 50 realistic sales transactions across the last 30 days:
```bash
python scripts/seed_data.py
```

### 5. Launch the Web Application
```bash
python wsgi.py
```
Open your browser and visit: **`http://127.0.0.1:5000`**

### Demo Login Credentials
> ⚠️ **DEMO ONLY**: The credentials below (`Password123!`) are strictly for local demonstration and evaluation. The system enforces production safeguards and **refuses to boot** in production (`FLASK_ENV=production`) if default secrets or demo passwords are detected.

| Role | Username | Password (Demo Only) |
|---|---|---|
| **CEO** | `admin` | `Password123!` *(demo only)* |
| **Manager** | `manager` | `Password123!` *(demo only)* |
| **Employee 1** | `alemu` | `Password123!` *(demo only)* |
| **Employee 2** | `chala` | `Password123!` *(demo only)* |
| **Employee 3** | `marta` | `Password123!` *(demo only)* |

### 6. Start the Telegram Bot (Optional)
In a separate terminal window:
```bash
python bot/main.py
```

---

## 🧪 Automated Testing

The project includes a comprehensive test suite covering authentication, role isolation, sales math, payment constraints, Telegram handlers, Excel generation, and backup retention:

```bash
# Run all tests
pytest -v
```

---

## 📚 Detailed Documentation

- **[CEO & Business Owner's Guide](docs/ADMIN_GUIDE.md)**: Plain-language instructions for daily business operations, adding employees, Telegram pairing, and Excel downloads.
- **[Ubuntu VPS Deployment Guide](docs/DEPLOYMENT.md)**: Step-by-step production setup with Docker Compose, Nginx reverse proxy, and Let's Encrypt SSL.
- **[Security Architecture Document](docs/SECURITY.md)**: Detailed security controls (CSRF, cookies, password hashing, headers, rate limits).
- **[Mobile & Functional Testing Checklist](docs/TESTING.md)**: Manual verification checklist for 360px mobile screens and roles.

---

## 📄 License
MIT License. Built as a production-grade portfolio project.
