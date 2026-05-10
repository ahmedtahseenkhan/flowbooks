"""
Demo data seed for FlowBooks — Currency Exchange / Inventory Management System.
Matches the real client's data shown in the design screenshots.

Run:  /opt/homebrew/bin/python3.13 seed_demo.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import database as db

# ── 1. Initialise DB ──────────────────────────────────────────────────────────
db.init_db()

conn = sqlite3.connect(db.DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

def run(sql, *args):
    conn.execute(sql, args)

# ── 2. Clear old demo data (keep admin user) ──────────────────────────────────
tables = [
    "journal_voucher_lines", "journal_vouchers",
    "purchase_lines", "purchase_transactions",
    "sales_lines",    "sales_transactions",
    "opening_stock",  "opening_balances",
    "value_adjustments",
    "carry_lines",    "carry_transactions",
    "inventory_items", "account_heads",
    "chart_of_accounts",
]
for t in tables:
    conn.execute(f"DELETE FROM {t}")
conn.commit()
print("Cleared old data.")

# ── 3. Account Heads ───────────────────────────────────────────────────────────
heads = [
    ("1100", "PARTIES"),
    ("100",  "ASSETS"),
    ("200",  "LIABILITIES"),
    ("300",  "EQUITY / CAPITAL"),
    ("400",  "INCOME"),
    ("500",  "EXPENSES"),
]
conn.executemany("INSERT OR REPLACE INTO account_heads VALUES (?,?)", heads)
print(f"Account heads: {len(heads)}")

# ── 4. Chart of Accounts ───────────────────────────────────────────────────────
#   (ac_code, ac_name, head_code, head_name, ac_path, opening, balance, ac_type)
accounts = [
    # Cash & Bank
    ("1",    "CASH IN HAND",         "100", "ASSETS",            "Assets > Cash",      5_000_000, 5_000_000, "CURRENT ASSETS"),
    ("2",    "BANK ACCOUNT",         "100", "ASSETS",            "Assets > Bank",        500_000,   500_000, "CURRENT ASSETS"),
    ("201",  "INVENTORY CONTROL A/C","100", "ASSETS",            "Assets > Inventory",         0,         0, "CURRENT ASSETS"),
    # Capital
    ("1000", "CAPITAL / EQUITY",     "300", "EQUITY / CAPITAL",  "Equity",             10_000_000,10_000_000,"EQUITY"),
    # Income & Expense
    ("4001", "EXCHANGE INCOME",      "400", "INCOME",            "Income > Exchange",          0,         0, "INCOME"),
    ("5001", "EXCHANGE EXPENSE",     "500", "EXPENSES",          "Expenses > Exchange",        0,         0, "EXPENSE"),
    # ── Parties (customers / suppliers) — opening set to 0, OBF will post ─
    ("415",  "MISCELLANEOUS",        "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1003", "ADAM S COMPUTERS",     "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1024", "ABID",                 "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1055", "ADAM MOB",             "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1089", "AAQIB",                "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1107", "SAQIB ASIF STAR",      "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1110", "AHAD AFTAB",           "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1118", "ACTION SPORTS",        "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1142", "AFX SHAHEEN CROWN",    "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1154", "AFX NUMAISH",          "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1162", "ADNA BUT",             "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1176", "YASIR IBRAHIM",        "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
    ("1199", "ADEEL",                "1100","PARTIES", "Parties", 0, 0, "CURRENT ASSETS"),
]
conn.executemany(
    "INSERT OR REPLACE INTO chart_of_accounts "
    "(ac_code,ac_name,head_code,head_name,ac_path,opening,balance,ac_type) "
    "VALUES (?,?,?,?,?,?,?,?)", accounts)
print(f"Chart of accounts: {len(accounts)}")

# ── 5. Inventory Head ──────────────────────────────────────────────────────────
conn.execute("INSERT OR REPLACE INTO account_heads VALUES (?,?)", ("CUR","CURRENCY"))

# ── 6. Inventory Items (currencies) ───────────────────────────────────────────
#  (code,name,symbol,head,head_name,unit,last_sale_rate,last_sale_date,
#   last_purchase_rate,last_purchase_date,quantity,value)
TODAY = "2026-05-10"
currencies = [
    ("1",  "EURO",          "€",  "CUR","CURRENCY","EUR",  195.0, TODAY, 192.0, TODAY,    500.00,    96000.0),
    ("2",  "US DOLLAR",     "$",  "CUR","CURRENCY","USD",  285.5, TODAY, 283.0, TODAY,    150.00,    42450.0),
    ("3",  "BRITISH POUND", "£",  "CUR","CURRENCY","GBP",  390.0, TODAY, 389.0, TODAY,      0.25,       97.25),
    ("4",  "UAE DIRHAM",    "AED","CUR","CURRENCY","AED",   44.5, TODAY,  43.0, TODAY,  3500.00,   150500.0),
    ("5",  "SAUDI RIYAL",   "SAR","CUR","CURRENCY","SAR",   78.0, TODAY,  77.0, TODAY,  1000.00,    77000.0),
    ("6",  "QATARI RIYAL",  "QAR","CUR","CURRENCY","QAR",   34.0, TODAY,  33.88,TODAY,     0.00,        0.0),
    ("7",  "WFX - MALIK",   "",   "CUR","CURRENCY","AED",   55.8, TODAY,  55.0, TODAY,     0.00,        0.0),
    ("8",  "MIX CHAMAK",    "",   "CUR","CURRENCY","AED",   30.0, TODAY,  29.68,TODAY, 26866.25, 797188.3),
    ("9",  "OMANI REYAL",   "OMR","CUR","CURRENCY","OMR",115200.0,TODAY,115100.0,TODAY,    20.00, 2302000.0),
    ("10", "DIT MALI",      "",   "CUR","CURRENCY","AED",   78.0, TODAY,  77.8, TODAY,325047.52,25283697.56),
    ("11", "RMB",           "",   "CUR","CURRENCY","RMB",   23.0, TODAY,  22.95,TODAY,     0.00,        0.0),
    ("12", "KACHI",         "",   "CUR","CURRENCY","AED",   56.0, TODAY,  55.8, TODAY,     0.00,        0.0),
    ("13", "AHAD AED",      "AED","CUR","CURRENCY","AED",   44.0, TODAY,  43.5, TODAY,     0.00,        0.0),
]
conn.executemany("""INSERT OR REPLACE INTO inventory_items
    (code,name,symbol,head,head_name,unit,
     last_sale_rate,last_sale_date,last_purchase_rate,last_purchase_date,
     quantity,value) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", currencies)
print(f"Inventory items (currencies): {len(currencies)}")

# ── 7. Opening Balances for Party Accounts ────────────────────────────────────
# Close our direct connection first — save_opening_balance uses its own conn
conn.commit()
conn.close()

ob_entries = [
    # (ac_code, ac_name, debit, credit, dated)
    # CREDITORS (we owe them money) — credit → balance goes negative
    ("1176","YASIR IBRAHIM",        0, 15_247_912.80, "2026-05-01"),  # supplier, CR balance
    ("1154","AFX NUMAISH",          0,  8_710_000.00, "2026-05-01"),  # supplier, CR balance
    ("1142","AFX SHAHEEN CROWN",    0,  6_169_409.00, "2026-05-01"),  # supplier, CR balance
    ("1107","SAQIB ASIF STAR",      0,  3_500_000.00, "2026-05-01"),  # supplier, CR balance
    ("1110","AHAD AFTAB",           0,  1_200_000.00, "2026-05-01"),  # supplier, CR balance
    ("1024","ABID",                 0,  2_000_000.00, "2026-05-01"),  # supplier, CR balance
    ("1118","ACTION SPORTS",        0,    800_000.00, "2026-05-01"),  # supplier, CR balance
    ("1162","ADNA BUT",             0,    747_487.25, "2026-05-01"),  # supplier, CR balance
    # DEBTORS (they owe us money) — debit → balance goes positive
    ("1199","ADEEL",           26_960,          0,    "2026-05-01"),  # customer, DR balance
]
for row in ob_entries:
    db.save_opening_balance(row)
print(f"Opening balances: {len(ob_entries)}")

# ── 8. Journal Vouchers ────────────────────────────────────────────────────────
# (conn was closed above — all subsequent calls use db module's own connections)
vouchers = [
    # (voucher_no, date, description, debit, credit),  lines: [(vno,ac_code,title,dr,cr)]
    ("22562","2026-05-04","CAHS REC HUSSAIN PAID YASIR",1_800_000,1_800_000, [
        ("22562","1176","YASIR IBRAHIM",   1_800_000, 0),
        ("22562","1",   "CASH IN HAND",   0, 1_800_000),
    ]),
    ("22564","2026-05-05","CAHS REC HUSSAI PAID YASIR",3_700_000,3_700_000, [
        ("22564","1176","YASIR IBRAHIM",   3_700_000, 0),
        ("22564","1",   "CASH IN HAND",   0, 3_700_000),
    ]),
    ("22569","2026-05-05","CASH PAID YASIR",2_500_000,2_500_000, [
        ("22569","1176","YASIR IBRAHIM",   2_500_000, 0),
        ("22569","1",   "CASH IN HAND",   0, 2_500_000),
    ]),
    ("22570","2026-05-08","CAHS REC SAQIB",400_000,400_000, [
        ("22570","1107","SAQIB ASIF STAR", 0,       400_000),
        ("22570","1",   "CASH IN HAND",   400_000, 0),
    ]),
    ("22574","2026-05-06","CASH PAID YASIR",3_784_000,3_784_000, [
        ("22574","1176","YASIR IBRAHIM",   3_784_000, 0),
        ("22574","1",   "CASH IN HAND",   0, 3_784_000),
    ]),
    ("22579","2026-05-08","CAHS REC HASSAN SHWOROM PAID YASIR",1_500_000,1_500_000, [
        ("22579","1176","YASIR IBRAHIM",   1_500_000, 0),
        ("22579","1",   "CASH IN HAND",   0, 1_500_000),
    ]),
    ("22580","2026-05-09","CASH PAID AHAD AFTAB",800_000,800_000, [
        ("22580","1110","AHAD AFTAB",      800_000, 0),
        ("22580","1",   "CASH IN HAND",   0, 800_000),
    ]),
    ("22581","2026-05-10","CAHS REC AFX NUMAISH",2_000_000,2_000_000, [
        ("22581","1154","AFX NUMAISH",     0,       2_000_000),
        ("22581","1",   "CASH IN HAND",   2_000_000, 0),
    ]),
]
for vno, dt, desc, td, tc, lines in vouchers:
    db.save_voucher((vno, dt, desc, td, tc), lines)
print(f"Journal vouchers: {len(vouchers)}")

# ── 9. Purchase Transactions ───────────────────────────────────────────────────
purchases = [
    # header: (inv_no,dated,ac_code,ac_name,term,party,amount,in_words,desc,total)
    # lines:  [(inv_no,serial,inv_code,inv_name,qty,rate,value)]
    {
        "header": ("4467","2026-05-02","1176","YASIR IBRAHIM","CASH",
                   "YASIR 76600 @ 77.8", 5_959_480,
                   "FIFTY-NINE LAKH FIFTY-NINE THOUSAND FOUR HUNDRED EIGHTY",
                   "PURCHASE VIDE VR # PUR-4467", 5_959_480),
        "lines":  [("4467",1,"10","DIT MALI", 76_600, 77.8, 5_959_480)],
    },
    {
        "header": ("4466","2026-05-02","1176","YASIR IBRAHIM","CASH",
                   "YASIR 40000 @ 78.0", 3_120_000,
                   "THIRTY-ONE LAKH TWENTY THOUSAND ONLY",
                   "PURCHASE VIDE VR # PUR-4466", 3_120_000),
        "lines":  [("4466",1,"10","DIT MALI", 40_000, 78.0, 3_120_000)],
    },
    {
        "header": ("4465","2026-05-02","1024","ABID","CASH",
                   "ABID 53800 @ 78.3", 4_212_540,
                   "FORTY-TWO LAKH TWELVE THOUSAND FIVE HUNDRED FORTY",
                   "PURCHASE VIDE VR # PUR-4465", 4_212_540),
        "lines":  [("4465",1,"10","DIT MALI", 53_800, 78.3, 4_212_540)],
    },
    {
        "header": ("4460","2026-04-17","1024","ABID","CREDIT",
                   "USD 500 @ 285", 142_500,
                   "ONE LAKH FORTY-TWO THOUSAND FIVE HUNDRED ONLY",
                   "PURCHASE USD FROM ABID", 142_500),
        "lines":  [("4460",1,"2","US DOLLAR", 500, 285.0, 142_500)],
    },
    {
        "header": ("4458","2026-04-17","1110","AHAD AFTAB","CASH",
                   "EUR 300 @ 192", 57_600,
                   "FIFTY-SEVEN THOUSAND SIX HUNDRED ONLY",
                   "PURCHASE EURO FROM AHAD AFTAB", 57_600),
        "lines":  [("4458",1,"1","EURO", 300, 192.0, 57_600)],
    },
]
for p in purchases:
    db.save_purchase(p["header"], p["lines"])
print(f"Purchase transactions: {len(purchases)}")

# ── 10. Sales Transactions ─────────────────────────────────────────────────────
sales = [
    {
        "header": ("4841","2026-05-02","1107","SAQIB ASIF STAR","CREDIT",
                   "SAQIB 32K @ 78.3", 2_505_600,
                   "TWENTY-FIVE LAKH FIVE THOUSAND SIX HUNDRED ONLY",
                   "SALE VIDE VR # SALE-4841", 2_505_600),
        "lines":  [("4841",1,"10","DIT MALI", 32_000, 78.3, 2_505_600)],
    },
    {
        "header": ("4840","2026-05-02","1154","AFX NUMAISH","CREDIT",
                   "IDRESS -7260 @ 78.4", 569_184,
                   "FIVE LAKH SIXTY-NINE THOUSAND ONE HUNDRED EIGHTY-FOUR",
                   "SALE VIDE VR # SALE-4840", 569_184),
        "lines":  [("4840",1,"10","DIT MALI", 7_260, 78.4, 569_184)],
    },
    {
        "header": ("4820","2026-04-20","1199","ADEEL","CASH",
                   "USD 200 @ 285.5", 57_100,
                   "FIFTY-SEVEN THOUSAND ONE HUNDRED ONLY",
                   "SALE USD TO ADEEL", 57_100),
        "lines":  [("4820",1,"2","US DOLLAR", 200, 285.5, 57_100)],
    },
    {
        "header": ("4810","2026-04-15","1003","ADAM S COMPUTERS","CASH",
                   "EUR 100 @ 195", 19_500,
                   "NINETEEN THOUSAND FIVE HUNDRED ONLY",
                   "SALE EURO TO ADAM S COMPUTERS", 19_500),
        "lines":  [("4810",1,"1","EURO", 100, 195.0, 19_500)],
    },
]
for s in sales:
    db.save_sale(s["header"], s["lines"])
print(f"Sales transactions: {len(sales)}")

print()
print("="*55)
print("  Demo data seeded successfully!")
print("="*55)
print()
print("  ACCOUNTS CREATED:")
print("    Cash / Bank / Equity / Income / Expense")
print("    + 13 Party accounts (YASIR IBRAHIM, SAQIB, etc.)")
print()
print("  INVENTORY (CURRENCIES):")
print("    13 currencies: EURO, USD, GBP, AED, SAR, OMR, etc.")
print()
print("  TRANSACTIONS:")
print("    8  Journal Vouchers (cash receipts & payments)")
print("    5  Purchase transactions (buying currencies)")
print("    4  Sales transactions (selling currencies)")
print()
print("  OPENING BALANCES POSTED:")
print("    YASIR IBRAHIM      15,247,912 CR")
print("    SAQIB ASIF STAR     3,500,000 CR")
print("    AFX NUMAISH         8,710,000 CR")
print("    + 6 more parties")
print()
print("  Run the app to explore:")
print("  /opt/homebrew/bin/python3.13 main.py")
