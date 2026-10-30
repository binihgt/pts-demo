#!/usr/bin/env python3
"""
Seed script populating realistic demonstration data for PTS Demo.
Creates:
    - 5 Users: 1 CEO, 1 Manager, 3 Sales Employees
    - 8 Customers
    - 50 Sales spanning today, this week, and the past month
    - Associated Payments (cash, telebirr, bank) with full, partial, and unpaid balances
    - Realistic AuditLog trail
"""
import sys
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.customer import Customer
from app.models.sale import Sale
from app.models.payment import Payment
from app.models.audit import AuditLog


def seed_database(app=None, recreate: bool = False):
    """Seed the database with realistic demonstration data."""
    if app is None:
        app = create_app()

    with app.app_context():
        if recreate:
            print("[*] Recreating database tables...")
            db.drop_all()
            db.create_all()
        else:
            db.create_all()
            from app.models.user import User
            if User.query.first() is not None:
                # Database is already populated
                return

        print("[*] Seeding users...")
        users_data = [
            ("Abebe Bekele", "admin", "Password123!", User.ROLE_CEO, 987654321),
            ("Bethlehem Tadesse", "manager", "Password123!", User.ROLE_MANAGER, 876543210),
            ("Alemu Kebede", "alemu", "Password123!", User.ROLE_EMPLOYEE, None),
            ("Chala Degefa", "chala", "Password123!", User.ROLE_EMPLOYEE, None),
            ("Marta Hailu", "marta", "Password123!", User.ROLE_EMPLOYEE, None),
            ("Demo CEO (Read-Only)", "demo_ceo", "DemoCEO123!", User.ROLE_CEO, None),
        ]

        users = {}
        for name, uname, pwd, role, tg_id in users_data:
            u = User(
                name=name,
                username=uname,
                role=role,
                telegram_id=tg_id,
                is_active=True
            )
            u.set_password(pwd)
            if tg_id is None and uname != "demo_ceo":
                # Provide sample link codes for employees ready to link
                u.generate_telegram_link_code()
            db.session.add(u)
            users[uname] = u

        db.session.flush()

        # Seed Customers
        print("[*] Seeding customers...")
        customers_data = [
            ("Desta Haile", "+251911223344"),
            ("Selamawit Fikru", "+251922334455"),
            ("Yonas Girma", "+251933445566"),
            ("Tigist Assefa", "+251944556677"),
            ("Dawit Mengistu", "+251911998877"),
            ("Hanna Tesfaye", "+251922887766"),
            ("Kassahun Woldie", "+251933776655"),
            ("Meron Getachew", "+251944665544"),
        ]
        customers = []
        for c_name, c_phone in customers_data:
            c = Customer(name=c_name, phone=c_phone)
            db.session.add(c)
            customers.append(c)

        db.session.flush()

        # Catalog of products
        catalog = [
            ("Dell Latitude 5420 Laptop", 45000.00),
            ("Samsung 24\" IPS Monitor", 12500.00),
            ("Logitech MX Master 3S Mouse", 6800.00),
            ("Logitech Mechanical Keyboard", 8500.00),
            ("HP LaserJet Pro M404dn", 28000.00),
            ("Cat6 Ethernet Cable (305m Roll)", 7200.00),
            ("MikroTik hEX Router", 5400.00),
            ("APC Smart-UPS 1500VA", 36000.00),
            ("Kingston 1TB NVMe SSD", 5900.00),
            ("Crucial 16GB DDR4 RAM", 2800.00),
            ("Cisco 24-Port Gigabit Switch", 19500.00),
            ("Anker PowerConf Bluetooth Speakerphone", 11200.00),
        ]

        # Employees recording sales
        sales_employees = [users["alemu"], users["chala"], users["marta"]]

        print("[*] Seeding 50 realistic sales & payments...")
        now = datetime.now(timezone.utc)
        random.seed(42)  # Deterministic seed for reproducible testing

        total_sales_count = 50
        sales_created = []

        for i in range(total_sales_count):
            # Spread sales: 10 today, 15 this week (past 1-7 days), 25 earlier (past 8-30 days)
            if i < 10:
                hours_ago = random.randint(1, 10)
                sale_time = now - timedelta(hours=hours_ago)
            elif i < 25:
                days_ago = random.randint(1, 7)
                hours_ago = random.randint(0, 23)
                sale_time = now - timedelta(days=days_ago, hours=hours_ago)
            else:
                days_ago = random.randint(8, 30)
                hours_ago = random.randint(0, 23)
                sale_time = now - timedelta(days=days_ago, hours=hours_ago)

            employee = random.choice(sales_employees)
            customer = random.choice(customers) if random.random() > 0.15 else None
            item_name, unit_price = random.choice(catalog)
            quantity = random.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 5, 5])[0]
            total = round(quantity * unit_price, 2)

            sale = Sale(
                employee_id=employee.id,
                customer_id=customer.id if customer else None,
                item=item_name,
                quantity=quantity,
                unit_price=unit_price,
                total=total,
                created_at=sale_time
            )
            db.session.add(sale)
            sales_created.append((sale, sale_time, employee))

        db.session.flush()

        # Generate Payments for sales
        payment_methods = [Payment.METHOD_TELEBIRR, Payment.METHOD_BANK, Payment.METHOD_CASH]
        weights = [45, 35, 20]  # telebirr popular, then bank, then cash

        payment_count = 0
        for sale, sale_time, employee in sales_created:
            # 65% fully paid, 20% partial payment, 15% unpaid
            fate = random.random()
            if fate < 0.65:
                # Fully paid (either 1 single payment or 2 split payments)
                if random.random() < 0.85:
                    p = Payment(
                        sale_id=sale.id,
                        amount=sale.total,
                        method=random.choices(payment_methods, weights=weights)[0],
                        created_at=sale_time + timedelta(minutes=random.randint(2, 30))
                    )
                    db.session.add(p)
                    payment_count += 1
                else:
                    half1 = round(sale.total * 0.5, 2)
                    half2 = round(sale.total - half1, 2)
                    p1 = Payment(
                        sale_id=sale.id,
                        amount=half1,
                        method=random.choices(payment_methods, weights=weights)[0],
                        created_at=sale_time + timedelta(minutes=5)
                    )
                    p2 = Payment(
                        sale_id=sale.id,
                        amount=half2,
                        method=random.choices(payment_methods, weights=weights)[0],
                        created_at=sale_time + timedelta(hours=3)
                    )
                    db.session.add(p1)
                    db.session.add(p2)
                    payment_count += 2
            elif fate < 0.85:
                # Partial payment (e.g. 30% to 70% paid)
                ratio = round(random.uniform(0.3, 0.7), 2)
                paid_amt = round(sale.total * ratio, 2)
                p = Payment(
                    sale_id=sale.id,
                    amount=paid_amt,
                    method=random.choices(payment_methods, weights=weights)[0],
                    created_at=sale_time + timedelta(minutes=15)
                )
                db.session.add(p)
                payment_count += 1
            else:
                # Unpaid credit sale
                pass

        # Seed Audit Logs
        print("[*] Seeding audit logs...")
        AuditLog.log("DATABASE_SEEDED", user_id=users["admin"].id, details="Database initialized with demonstration dataset.")
        AuditLog.log("USER_CREATED", user_id=users["admin"].id, details="Created employee accounts: alemu, chala, marta.")
        AuditLog.log("LINK_CODE_GENERATED", user_id=users["admin"].id, details=f"Generated Telegram link code for user alemu.")
        AuditLog.log("TELEGRAM_LINKED", user_id=users["manager"].id, details="Manager Bethlehem linked Telegram account (ID 876543210).")

        db.session.commit()

        # Display summary
        print("\n" + "=" * 65)
        print("          PTS Demo - Seeding Completed Successfully!")
        print("=" * 65)
        print(f"[+] Total Users:     {User.query.count()} (1 CEO, 1 Manager, 3 Employees)")
        print(f"[+] Total Customers: {Customer.query.count()}")
        print(f"[+] Total Sales:     {Sale.query.count()}")
        print(f"[+] Total Payments:  {payment_count}")
        print(f"[+] Total Logs:      {AuditLog.query.count()}")
        print("\nCredentials for testing & demo:")
        print("    - Demo CEO:  Username: demo_ceo / Password: DemoCEO123! (Read-Only)")
        print("    - Live CEO:  Username: admin    / Password: Password123!")
        print("    - Manager:   Username: manager  / Password: Password123!")
        print("    - Employee:  Username: alemu    / Password: Password123!")
        print("    - Employee:  Username: chala    / Password: Password123!")
        print("    - Employee:  Username: marta    / Password: Password123!")
        print("=" * 65)


def seed():
    """CLI compatibility entrypoint for recreating and seeding database."""
    seed_database(recreate=True)


if __name__ == "__main__":
    seed()
