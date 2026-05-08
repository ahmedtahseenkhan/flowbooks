"""Seed the database with demo data so the forms look populated."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db

db.init_db()

# Chart of Accounts
accounts = [
    ("1001", "Cash In Hand",        "100", "ASSETS",      "Assets > Cash",      50000, 50000),
    ("1002", "Bank Account - HBL",  "100", "ASSETS",      "Assets > Bank",     200000, 200000),
    ("2001", "Accounts Payable",    "200", "LIABILITIES", "Liabilities > AP",   30000, 30000),
    ("2002", "Loans Payable",       "200", "LIABILITIES", "Liabilities > Loans",80000, 80000),
    ("3001", "Owner Equity",        "300", "EQUITY",      "Equity",            100000,100000),
    ("4001", "Sales Revenue",       "400", "INCOME",      "Income > Sales",     75000, 75000),
    ("5001", "Purchase Expense",    "500", "EXPENSES",    "Expenses > Purchase",40000, 40000),
    ("5002", "Salaries Expense",    "500", "EXPENSES",    "Expenses > Salary",  20000, 20000),
    ("5003", "Rent Expense",        "500", "EXPENSES",    "Expenses > Rent",    12000, 12000),
]
for a in accounts:
    db.save_account(a)

# Inventory
from datetime import date
today = date.today().strftime("%Y-%m-%d")
items = [
    ("INV001", "Rice Basmati 5Kg",   "PKT",  "100", "Raw Material", "Kg",   85.0, today, 70.0, today, 500, 35000),
    ("INV002", "Sugar 1Kg",          "PKT",  "100", "Raw Material", "Kg",   65.0, today, 55.0, today, 300, 16500),
    ("INV003", "Cooking Oil 5Ltr",   "BTL",  "100", "Raw Material", "Ltr", 1200.0,today, 950.0,today, 100, 95000),
    ("INV004", "Tea Leaves 500g",    "PKT",  "100", "Raw Material", "Gm",  350.0, today, 290.0,today, 200, 58000),
    ("INV005", "Flour Wheat 10Kg",   "BAG",  "100", "Raw Material", "Kg",   45.0, today, 38.0, today, 800, 30400),
]
for it in items:
    db.save_inventory_item(it)

# Journal Vouchers
jv1 = ("00001", today, "Opening cash receipt", 50000, 50000)
jvl1 = [
    ("00001", "1001", "Cash In Hand", 50000, 0),
    ("00001", "3001", "Owner Equity", 0, 50000),
]
db.save_voucher(jv1, jvl1)

jv2 = ("00002", today, "Salary payment", 20000, 20000)
jvl2 = [
    ("00002", "5002", "Salaries Expense", 20000, 0),
    ("00002", "1001", "Cash In Hand", 0, 20000),
]
db.save_voucher(jv2, jvl2)

# Purchase transaction
ph = ("000001", today, "2001", "Accounts Payable", "CREDIT", "M/S Traders", 35000, "Thirty Five Thousand Only", "Rice purchase", 35000)
pl = [("000001", 1, "INV001", "Rice Basmati 5Kg", 500, 70.0, 35000)]
db.save_purchase(ph, pl)

# Sales transaction
sh = ("000001", today, "4001", "Sales Revenue", "CREDIT", "Walk-in Customer", 42500, "Forty Two Thousand Five Hundred Only", "Retail sale", 42500)
sl = [("000001", 1, "INV001", "Rice Basmati 5Kg", 500, 85.0, 42500)]
db.save_sale(sh, sl)

print("Demo data seeded successfully!")
