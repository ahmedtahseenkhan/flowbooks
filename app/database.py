import sqlite3
import os
import sys

# When frozen by PyInstaller, __file__ points into the temp _MEIPASS extraction
# folder (read-only, wiped on exit). Store the DB next to the .exe instead so
# data persists across runs and the user can back it up.
if getattr(sys, "frozen", False):
    _DB_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    _DB_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(_DB_DIR, "flowbooks.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS opening_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inv_code TEXT NOT NULL,
            inventory_name TEXT,
            quantity REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            value REAL DEFAULT 0,
            dated TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS carry_transactions (
            invoice_no TEXT PRIMARY KEY,
            dated TEXT NOT NULL,
            description TEXT,
            total_value REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS carry_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            inv_code TEXT,
            inventory_name TEXT,
            quantity REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            value REAL DEFAULT 0,
            FOREIGN KEY (invoice_no) REFERENCES carry_transactions(invoice_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS value_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_no TEXT,
            adj_type TEXT,
            inv_code TEXT,
            inventory_name TEXT,
            old_qty REAL DEFAULT 0,
            new_qty REAL DEFAULT 0,
            old_value REAL DEFAULT 0,
            new_value REAL DEFAULT 0,
            dated TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            designation TEXT DEFAULT 'MANAGER',
            department TEXT DEFAULT 'ACCOUNTS',
            section TEXT DEFAULT 'HEAD OFFICE'
        );

        CREATE TABLE IF NOT EXISTS account_heads (
            head_code TEXT PRIMARY KEY,
            head_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            ac_code TEXT PRIMARY KEY,
            ac_name TEXT NOT NULL,
            head_code TEXT,
            head_name TEXT,
            ac_path TEXT,
            opening REAL DEFAULT 0,
            balance REAL DEFAULT 0,
            ac_type TEXT DEFAULT 'EXPENSE'
        );

        CREATE TABLE IF NOT EXISTS inventory_items (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            symbol TEXT,
            head TEXT,
            head_name TEXT,
            unit TEXT,
            last_sale_rate REAL DEFAULT 0,
            last_sale_date TEXT,
            last_purchase_rate REAL DEFAULT 0,
            last_purchase_date TEXT,
            quantity REAL DEFAULT 0,
            value REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS journal_vouchers (
            voucher_no TEXT PRIMARY KEY,
            prepare_date TEXT NOT NULL,
            description TEXT,
            total_debit REAL DEFAULT 0,
            total_credit REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS journal_voucher_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no TEXT NOT NULL,
            ac_code TEXT,
            ac_title TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            FOREIGN KEY (voucher_no) REFERENCES journal_vouchers(voucher_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS purchase_transactions (
            invoice_no TEXT PRIMARY KEY,
            dated TEXT NOT NULL,
            ac_code TEXT,
            ac_name TEXT,
            term TEXT DEFAULT 'CREDIT',
            party TEXT,
            amount REAL DEFAULT 0,
            in_words TEXT,
            description TEXT,
            total_value REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS purchase_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            serial INTEGER,
            inv_code TEXT,
            inventory_name TEXT,
            quantity REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            value REAL DEFAULT 0,
            FOREIGN KEY (invoice_no) REFERENCES purchase_transactions(invoice_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sales_transactions (
            invoice_no TEXT PRIMARY KEY,
            dated TEXT NOT NULL,
            ac_code TEXT,
            ac_name TEXT,
            term TEXT DEFAULT 'CREDIT',
            party TEXT,
            amount REAL DEFAULT 0,
            in_words TEXT,
            description TEXT,
            total_value REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sales_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            serial INTEGER,
            inv_code TEXT,
            inventory_name TEXT,
            quantity REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            value REAL DEFAULT 0,
            FOREIGN KEY (invoice_no) REFERENCES sales_transactions(invoice_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS opening_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ac_code TEXT,
            ac_name TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            dated TEXT
        );

        CREATE TABLE IF NOT EXISTS account_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term_name TEXT UNIQUE NOT NULL
        );
    """)

    # Default admin user
    c.execute("INSERT OR IGNORE INTO users (username, password, full_name, designation, department, section) VALUES (?,?,?,?,?,?)",
              ("admin", "admin123", "DANISH", "MANAGER", "ACCOUNTS", "HEAD OFFICE"))

    # Seed default account types (INSERT OR IGNORE so existing data is preserved)
    default_types = [
        ('CURRENT ASSETS',), ('FIXED ASSETS',),
        ('CURRENT LIABILITIES',), ('LONG TERM LIABILITIES',),
        ('EQUITY',), ('INCOME',), ('COST OF GOODS SOLD',), ('EXPENSE',),
    ]
    c.executemany("INSERT OR IGNORE INTO account_types (type_name) VALUES (?)", default_types)

    # Seed default payment terms
    default_terms = [('CASH',), ('CREDIT',), ('CHEQUE',), ('BANK TRANSFER',)]
    c.executemany("INSERT OR IGNORE INTO payment_terms (term_name) VALUES (?)", default_terms)

    # Sample account heads
    heads = [
        ("100", "ASSETS"), ("200", "LIABILITIES"), ("300", "EQUITY"),
        ("400", "INCOME"), ("500", "EXPENSES"),
    ]
    c.executemany("INSERT OR IGNORE INTO account_heads VALUES (?,?)", heads)

    conn.commit()
    conn.close()


# ── Accounting engine (delta approach) ───────────────────────────────────────
# Deltas preserve manually-set baseline quantities in Inventory Master.

def _ac_delta(conn, ac_code, debit_delta, credit_delta):
    """Apply a debit/credit delta to one account balance."""
    if ac_code:
        conn.execute(
            "UPDATE chart_of_accounts SET balance = balance + ? - ? WHERE ac_code=?",
            (debit_delta, credit_delta, ac_code))

def _find_ac(conn, ac_type=None, name_like=None):
    """Find the first account matching an ac_type or name pattern."""
    if name_like:
        row = conn.execute(
            "SELECT ac_code FROM chart_of_accounts WHERE LOWER(ac_name) LIKE ? ORDER BY ac_code LIMIT 1",
            (f"%{name_like.lower()}%",)).fetchone()
        if row:
            return row["ac_code"]
    if ac_type:
        row = conn.execute(
            "SELECT ac_code FROM chart_of_accounts WHERE ac_type=? ORDER BY ac_code LIMIT 1",
            (ac_type,)).fetchone()
        if row:
            return row["ac_code"]
    return None

def _inventory_control_ac(conn):
    """Return the Inventory Control account code (searches by name then type)."""
    return _find_ac(conn, name_like="inventory") or _find_ac(conn, ac_type="CURRENT ASSETS")

def _income_ac(conn):
    """Return the first Income account code."""
    return _find_ac(conn, ac_type="INCOME")

def _expense_ac(conn):
    """Return the first Expense account code."""
    return _find_ac(conn, ac_type="EXPENSE") or _find_ac(conn, ac_type="COST OF GOODS SOLD")

def _equity_ac(conn):
    """Return the first Equity/Capital account code."""
    return _find_ac(conn, ac_type="EQUITY")

def _inv_delta(conn, inv_code, qty_delta, val_delta,
               last_rate=None, last_date=None, is_purchase=True):
    """Apply a qty/value delta to one inventory item (preserves baseline)."""
    if last_rate and is_purchase:
        conn.execute("""UPDATE inventory_items
            SET quantity=MAX(0,quantity+?), value=MAX(0,value+?),
                last_purchase_rate=?, last_purchase_date=?
            WHERE code=?""", (qty_delta, val_delta, last_rate, last_date, inv_code))
    elif last_rate:
        conn.execute("""UPDATE inventory_items
            SET quantity=MAX(0,quantity+?), value=MAX(0,value+?),
                last_sale_rate=?, last_sale_date=?
            WHERE code=?""", (qty_delta, val_delta, last_rate, last_date, inv_code))
    else:
        conn.execute("""UPDATE inventory_items
            SET quantity=MAX(0,quantity+?), value=MAX(0,value+?)
            WHERE code=?""", (qty_delta, val_delta, inv_code))

def recalc_all_balances():
    """Full recompute from scratch (repair / audit tool). Normal saves use deltas."""
    with get_connection() as conn:
        conn.execute("UPDATE chart_of_accounts SET balance = opening")
        rows = conn.execute(
            "SELECT ac_code, COALESCE(SUM(debit),0) d, COALESCE(SUM(credit),0) c "
            "FROM journal_voucher_lines GROUP BY ac_code").fetchall()
        for r in rows:
            conn.execute("UPDATE chart_of_accounts SET balance=balance+?-? WHERE ac_code=?",
                         (r["d"], r["c"], r["ac_code"]))
        conn.execute("UPDATE inventory_items SET quantity=0, value=0")
        for tbl, sign in [("purchase_lines",1),("carry_lines",1),("sales_lines",-1)]:
            rows2 = conn.execute(
                f"SELECT inv_code, COALESCE(SUM(quantity)*{sign},0) q, "
                f"COALESCE(SUM(value)*{sign},0) v FROM {tbl} GROUP BY inv_code").fetchall()
            for r in rows2:
                conn.execute("UPDATE inventory_items SET quantity=MAX(0,quantity+?),value=MAX(0,value+?) WHERE code=?",
                             (r["q"],r["v"],r["inv_code"]))
        rows3 = conn.execute(
            "SELECT inv_code, COALESCE(SUM(quantity),0) q, COALESCE(SUM(value),0) v "
            "FROM opening_stock GROUP BY inv_code").fetchall()
        for r in rows3:
            conn.execute("UPDATE inventory_items SET quantity=quantity+?,value=value+? WHERE code=?",
                         (r["q"],r["v"],r["inv_code"]))
        rows4 = conn.execute(
            "SELECT inv_code, COALESCE(SUM(new_qty-old_qty),0) dq, "
            "COALESCE(SUM(new_value-old_value),0) dv "
            "FROM value_adjustments GROUP BY inv_code").fetchall()
        for r in rows4:
            conn.execute("UPDATE inventory_items SET quantity=MAX(0,quantity+?),value=MAX(0,value+?) WHERE code=?",
                         (r["dq"],r["dv"],r["inv_code"]))
        conn.commit()

# ── Chart of Accounts ──────────────────────────────────────────────────────────

def get_all_accounts():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM chart_of_accounts ORDER BY ac_code").fetchall()

def get_account(ac_code):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM chart_of_accounts WHERE ac_code=?", (ac_code,)).fetchone()

def search_accounts(term, by="code"):
    with get_connection() as conn:
        if by == "code":
            return conn.execute("SELECT * FROM chart_of_accounts WHERE ac_code LIKE ? ORDER BY ac_code", (f"%{term}%",)).fetchall()
        return conn.execute("SELECT * FROM chart_of_accounts WHERE ac_name LIKE ? ORDER BY ac_name", (f"%{term}%",)).fetchall()

def save_account(data):
    """data = (ac_code, ac_name, head_code, head_name, ac_path, opening, balance[, ac_type])"""
    with get_connection() as conn:
        if len(data) >= 8:
            conn.execute("""INSERT OR REPLACE INTO chart_of_accounts
                (ac_code, ac_name, head_code, head_name, ac_path, opening, balance, ac_type)
                VALUES (?,?,?,?,?,?,?,?)""", data[:8])
        else:
            conn.execute("""INSERT OR REPLACE INTO chart_of_accounts
                (ac_code, ac_name, head_code, head_name, ac_path, opening, balance)
                VALUES (?,?,?,?,?,?,?)""", data[:7])
        conn.commit()

def next_account_code():
    """Return the next available numeric account code (max + 1)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT ac_code FROM chart_of_accounts").fetchall()
        max_code = 0
        for r in rows:
            try:
                n = int(r["ac_code"])
                if n > max_code:
                    max_code = n
            except (ValueError, TypeError):
                pass
        return str(max_code + 1) if max_code > 0 else "1001"

def get_account_types():
    """Return list of type_name strings from the account_types table."""
    with get_connection() as conn:
        rows = conn.execute("SELECT type_name FROM account_types ORDER BY type_name").fetchall()
        return [r["type_name"] for r in rows] or [
            'CURRENT ASSETS', 'FIXED ASSETS', 'CURRENT LIABILITIES',
            'LONG TERM LIABILITIES', 'EQUITY', 'INCOME', 'COST OF GOODS SOLD', 'EXPENSE',
        ]

def get_all_account_types():
    """Return full rows (id, type_name) for the CRUD form."""
    with get_connection() as conn:
        return conn.execute("SELECT * FROM account_types ORDER BY type_name").fetchall()

def save_account_type(type_name, row_id=None):
    """Insert new or update existing account type. Returns (ok, message)."""
    type_name = type_name.strip().upper()
    if not type_name:
        return False, "Type name cannot be empty."
    with get_connection() as conn:
        if row_id:
            conn.execute("UPDATE account_types SET type_name=? WHERE id=?", (type_name, row_id))
        else:
            try:
                conn.execute("INSERT INTO account_types (type_name) VALUES (?)", (type_name,))
            except Exception:
                return False, f"'{type_name}' already exists."
        conn.commit()
    return True, "Saved."

def delete_account_type(row_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM account_types WHERE id=?", (row_id,))
        conn.commit()

# ── Payment Terms ──────────────────────────────────────────────────────────────

def get_payment_terms():
    """Return list of term_name strings."""
    with get_connection() as conn:
        rows = conn.execute("SELECT term_name FROM payment_terms ORDER BY term_name").fetchall()
        return [r["term_name"] for r in rows] or ["CASH", "CREDIT"]

def get_all_payment_terms():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM payment_terms ORDER BY term_name").fetchall()

def save_payment_term(term_name, row_id=None):
    term_name = term_name.strip().upper()
    if not term_name:
        return False, "Term name cannot be empty."
    with get_connection() as conn:
        if row_id:
            conn.execute("UPDATE payment_terms SET term_name=? WHERE id=?", (term_name, row_id))
        else:
            try:
                conn.execute("INSERT INTO payment_terms (term_name) VALUES (?)", (term_name,))
            except Exception:
                return False, f"'{term_name}' already exists."
        conn.commit()
    return True, "Saved."

def delete_payment_term(row_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM payment_terms WHERE id=?", (row_id,))
        conn.commit()

def delete_account(ac_code):
    with get_connection() as conn:
        conn.execute("DELETE FROM chart_of_accounts WHERE ac_code=?", (ac_code,))
        conn.commit()

def get_all_heads():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM account_heads ORDER BY head_code").fetchall()

def save_head(head_code, head_name):
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO account_heads VALUES (?,?)", (head_code, head_name))
        conn.commit()

def delete_head(head_code):
    with get_connection() as conn:
        conn.execute("DELETE FROM account_heads WHERE head_code=?", (head_code,))
        conn.commit()

# ── Inventory ──────────────────────────────────────────────────────────────────

def get_all_inventory():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM inventory_items ORDER BY code").fetchall()

def get_inventory_item(code):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM inventory_items WHERE code=?", (code,)).fetchone()

def search_inventory(term, by="code"):
    with get_connection() as conn:
        if by == "code":
            return conn.execute("SELECT * FROM inventory_items WHERE code LIKE ? ORDER BY code", (f"%{term}%",)).fetchall()
        return conn.execute("SELECT * FROM inventory_items WHERE name LIKE ? ORDER BY name", (f"%{term}%",)).fetchall()

def save_inventory_item(data):
    with get_connection() as conn:
        conn.execute("""INSERT OR REPLACE INTO inventory_items
            (code, name, symbol, head, head_name, unit,
             last_sale_rate, last_sale_date, last_purchase_rate, last_purchase_date,
             quantity, value) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", data)
        conn.commit()

def delete_inventory_item(code):
    with get_connection() as conn:
        conn.execute("DELETE FROM inventory_items WHERE code=?", (code,))
        conn.commit()

# ── Journal Voucher ────────────────────────────────────────────────────────────

def get_all_vouchers():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM journal_vouchers ORDER BY voucher_no DESC").fetchall()

def get_voucher(voucher_no):
    with get_connection() as conn:
        hdr = conn.execute("SELECT * FROM journal_vouchers WHERE voucher_no=?", (voucher_no,)).fetchone()
        lines = conn.execute("SELECT * FROM journal_voucher_lines WHERE voucher_no=?", (voucher_no,)).fetchall()
        return hdr, lines

def save_voucher(header, lines):
    with get_connection() as conn:
        # Reverse old lines (if updating existing voucher)
        old_lines = conn.execute(
            "SELECT ac_code, debit, credit FROM journal_voucher_lines WHERE voucher_no=?",
            (header[0],)).fetchall()
        for r in old_lines:
            _ac_delta(conn, r["ac_code"], -(r["debit"] or 0), -(r["credit"] or 0))
        # Save new
        conn.execute("""INSERT OR REPLACE INTO journal_vouchers
            (voucher_no, prepare_date, description, total_debit, total_credit) VALUES (?,?,?,?,?)""", header)
        conn.execute("DELETE FROM journal_voucher_lines WHERE voucher_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO journal_voucher_lines
                (voucher_no, ac_code, ac_title, debit, credit) VALUES (?,?,?,?,?)""", ln)
            if ln[1]:  # ac_code
                _ac_delta(conn, ln[1], ln[3] or 0, ln[4] or 0)
        conn.commit()

def delete_voucher(voucher_no):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ac_code, debit, credit FROM journal_voucher_lines WHERE voucher_no=?",
            (voucher_no,)).fetchall()
        for r in rows:
            _ac_delta(conn, r["ac_code"], -(r["debit"] or 0), -(r["credit"] or 0))
        conn.execute("DELETE FROM journal_vouchers WHERE voucher_no=?", (voucher_no,))
        conn.commit()

def next_voucher_no():
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(CAST(voucher_no AS INTEGER)) FROM journal_vouchers").fetchone()
        return str((row[0] or 0) + 1).zfill(5)

# ── Purchase Transactions ──────────────────────────────────────────────────────

def get_all_purchases():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM purchase_transactions ORDER BY invoice_no DESC").fetchall()

def get_purchase(invoice_no):
    with get_connection() as conn:
        hdr = conn.execute("SELECT * FROM purchase_transactions WHERE invoice_no=?", (invoice_no,)).fetchone()
        lines = conn.execute("SELECT * FROM purchase_lines WHERE invoice_no=? ORDER BY serial", (invoice_no,)).fetchall()
        return hdr, lines

def save_purchase(header, lines):
    """
    Saves a purchase and:
    1. Updates inventory quantities (delta)
    2. Credits the party account (balance -= total) — we owe them more
       Reverses old posting if this is an update.
    """
    ac_code    = header[2]   # party account code
    total_new  = header[9]   # total_value of new invoice
    with get_connection() as conn:
        # Reverse old inventory lines
        old_lines = conn.execute(
            "SELECT inv_code, quantity, rate, value FROM purchase_lines WHERE invoice_no=?",
            (header[0],)).fetchall()
        for r in old_lines:
            _inv_delta(conn, r["inv_code"], -(r["quantity"] or 0), -(r["value"] or 0))

        # Reverse old party posting
        old_hdr = conn.execute(
            "SELECT ac_code, total_value FROM purchase_transactions WHERE invoice_no=?",
            (header[0],)).fetchone()
        if old_hdr and old_hdr["ac_code"]:
            # Un-credit: balance += old_total (reverse the credit)
            conn.execute("UPDATE chart_of_accounts SET balance=balance+? WHERE ac_code=?",
                         (old_hdr["total_value"] or 0, old_hdr["ac_code"]))

        # Save new header & lines
        conn.execute("""INSERT OR REPLACE INTO purchase_transactions
            (invoice_no, dated, ac_code, ac_name, term, party, amount, in_words, description, total_value)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", header)
        conn.execute("DELETE FROM purchase_lines WHERE invoice_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO purchase_lines
                (invoice_no, serial, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?,?)""", ln)
            if ln[2]:
                _inv_delta(conn, ln[2], ln[4] or 0, ln[6] or 0,
                           last_rate=ln[5], last_date=header[1], is_purchase=True)

        # Post GL entries:
        #   DR Inventory Control (stock increases)
        #   CR Party Account    (we owe them)
        inv_ctrl = _inventory_control_ac(conn)
        _ac_delta(conn, inv_ctrl, total_new or 0, 0)           # DR inventory
        if ac_code:
            conn.execute("UPDATE chart_of_accounts SET balance=balance-? WHERE ac_code=?",
                         (total_new or 0, ac_code))             # CR party
        conn.commit()

def delete_purchase(invoice_no):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT inv_code, quantity, rate, value FROM purchase_lines WHERE invoice_no=?",
            (invoice_no,)).fetchall()
        for r in rows:
            _inv_delta(conn, r["inv_code"], -(r["quantity"] or 0), -(r["value"] or 0))

        # Reverse GL entries
        hdr = conn.execute(
            "SELECT ac_code, total_value FROM purchase_transactions WHERE invoice_no=?",
            (invoice_no,)).fetchone()
        if hdr:
            tv = hdr["total_value"] or 0
            inv_ctrl = _inventory_control_ac(conn)
            _ac_delta(conn, inv_ctrl, 0, tv)                   # CR inventory (reverse DR)
            if hdr["ac_code"]:
                conn.execute("UPDATE chart_of_accounts SET balance=balance+? WHERE ac_code=?",
                             (tv, hdr["ac_code"]))              # DR party (reverse CR)
        conn.execute("DELETE FROM purchase_transactions WHERE invoice_no=?", (invoice_no,))
        conn.commit()

def next_invoice_no(table="purchase_transactions"):
    with get_connection() as conn:
        row = conn.execute(f"SELECT MAX(CAST(invoice_no AS INTEGER)) FROM {table}").fetchone()
        return str((row[0] or 0) + 1).zfill(6)

# ── Sales Transactions ─────────────────────────────────────────────────────────

def get_all_sales():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM sales_transactions ORDER BY invoice_no DESC").fetchall()

def get_sale(invoice_no):
    with get_connection() as conn:
        hdr = conn.execute("SELECT * FROM sales_transactions WHERE invoice_no=?", (invoice_no,)).fetchone()
        lines = conn.execute("SELECT * FROM sales_lines WHERE invoice_no=? ORDER BY serial", (invoice_no,)).fetchall()
        return hdr, lines

def save_sale(header, lines):
    """
    Saves a sale and:
    1. Updates inventory quantities (delta — reduces stock)
    2. Debits the party account (balance += total) — they owe us more
       Reverses old posting if this is an update.
    """
    ac_code   = header[2]
    total_new = header[9]
    with get_connection() as conn:
        # Reverse old inventory lines (add stock back)
        old_lines = conn.execute(
            "SELECT inv_code, quantity, rate, value FROM sales_lines WHERE invoice_no=?",
            (header[0],)).fetchall()
        for r in old_lines:
            _inv_delta(conn, r["inv_code"], r["quantity"] or 0, r["value"] or 0)

        # Reverse old party posting
        old_hdr = conn.execute(
            "SELECT ac_code, total_value FROM sales_transactions WHERE invoice_no=?",
            (header[0],)).fetchone()
        if old_hdr and old_hdr["ac_code"]:
            # Un-debit: balance -= old_total (reverse the debit)
            conn.execute("UPDATE chart_of_accounts SET balance=balance-? WHERE ac_code=?",
                         (old_hdr["total_value"] or 0, old_hdr["ac_code"]))

        # Save new header & lines
        conn.execute("""INSERT OR REPLACE INTO sales_transactions
            (invoice_no, dated, ac_code, ac_name, term, party, amount, in_words, description, total_value)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", header)
        conn.execute("DELETE FROM sales_lines WHERE invoice_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO sales_lines
                (invoice_no, serial, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?,?)""", ln)
            if ln[2]:
                _inv_delta(conn, ln[2], -(ln[4] or 0), -(ln[6] or 0),
                           last_rate=ln[5], last_date=header[1], is_purchase=False)

        # Post GL entries with Exchange Income/Loss recognition:
        #   DR Party Account        (they owe us — at sale value)
        #   CR Inventory Control    (stock out — at cost/book value)
        #   CR Exchange Income      (profit: sale value - cost value)
        #   OR DR Exchange Expense  (loss: cost value - sale value)
        inv_ctrl   = _inventory_control_ac(conn)
        income_ac  = _income_ac(conn)
        expense_ac = _expense_ac(conn)

        # Calculate cost basis for each line using WAC (last_purchase_rate)
        total_cost = 0.0
        new_lines_data = conn.execute(
            "SELECT sl.inv_code, sl.quantity, sl.value "
            "FROM sales_lines sl WHERE sl.invoice_no=?", (header[0],)).fetchall()
        for ln in new_lines_data:
            item = conn.execute(
                "SELECT last_purchase_rate FROM inventory_items WHERE code=?",
                (ln["inv_code"],)).fetchone()
            cost_rate = item["last_purchase_rate"] if item else 0
            total_cost += (ln["quantity"] or 0) * (cost_rate or 0)

        exchange_diff = (total_new or 0) - total_cost  # positive = profit

        if ac_code:
            conn.execute("UPDATE chart_of_accounts SET balance=balance+? WHERE ac_code=?",
                         (total_new or 0, ac_code))         # DR party (sale value)
        _ac_delta(conn, inv_ctrl, 0, total_cost)            # CR inventory (at cost)
        if exchange_diff > 0:
            _ac_delta(conn, income_ac, 0, exchange_diff)    # CR exchange income
        elif exchange_diff < 0:
            _ac_delta(conn, expense_ac, abs(exchange_diff), 0)  # DR exchange expense
        conn.commit()

def delete_sale(invoice_no):
    with get_connection() as conn:
        # Get lines before deletion for cost calculation
        lines = conn.execute(
            "SELECT sl.inv_code, sl.quantity, sl.value, ii.last_purchase_rate "
            "FROM sales_lines sl "
            "LEFT JOIN inventory_items ii ON sl.inv_code=ii.code "
            "WHERE sl.invoice_no=?", (invoice_no,)).fetchall()

        # Restore inventory quantities
        for r in lines:
            _inv_delta(conn, r["inv_code"], r["quantity"] or 0, r["value"] or 0)

        # Reverse GL entries
        hdr = conn.execute(
            "SELECT ac_code, total_value FROM sales_transactions WHERE invoice_no=?",
            (invoice_no,)).fetchone()
        if hdr:
            tv = hdr["total_value"] or 0
            total_cost = sum((r["quantity"] or 0) * (r["last_purchase_rate"] or 0) for r in lines)
            exchange_diff = tv - total_cost

            inv_ctrl   = _inventory_control_ac(conn)
            income_ac  = _income_ac(conn)
            expense_ac = _expense_ac(conn)

            if hdr["ac_code"]:
                conn.execute("UPDATE chart_of_accounts SET balance=balance-? WHERE ac_code=?",
                             (tv, hdr["ac_code"]))          # reverse party debit
            _ac_delta(conn, inv_ctrl, total_cost, 0)        # reverse inventory credit
            if exchange_diff > 0:
                _ac_delta(conn, income_ac, exchange_diff, 0)    # reverse income
            elif exchange_diff < 0:
                _ac_delta(conn, expense_ac, 0, abs(exchange_diff))  # reverse expense

        conn.execute("DELETE FROM sales_transactions WHERE invoice_no=?", (invoice_no,))
        conn.commit()

def check_stock_for_sale(lines, existing_invoice_no=None):
    """Return list of (inv_code, name, available, requested) where stock is insufficient."""
    shortfalls = []
    with get_connection() as conn:
        for ln in lines:
            inv_code = ln.get("inv_code") or (ln[2] if isinstance(ln, (list, tuple)) else None)
            req_qty  = ln.get("quantity") or (ln[4] if isinstance(ln, (list, tuple)) else 0)
            try:
                req_qty = float(str(req_qty).replace(',', '') or 0)
            except ValueError:
                req_qty = 0
            if not inv_code or req_qty <= 0:
                continue
            item = conn.execute(
                "SELECT quantity, name FROM inventory_items WHERE code=?", (inv_code,)
            ).fetchone()
            if not item:
                continue
            available = item["quantity"]
            # If updating existing invoice, add back what was already sold on it
            if existing_invoice_no:
                old = conn.execute(
                    "SELECT COALESCE(SUM(quantity),0) q FROM sales_lines "
                    "WHERE invoice_no=? AND inv_code=?",
                    (existing_invoice_no, inv_code)
                ).fetchone()
                available += (old["q"] or 0)
            if req_qty > available:
                shortfalls.append((inv_code, item["name"], available, req_qty))
    return shortfalls

# ── Opening Balances ───────────────────────────────────────────────────────────

def get_opening_balances(dated=None):
    with get_connection() as conn:
        if dated:
            return conn.execute("SELECT * FROM opening_balances WHERE dated=? ORDER BY ac_code", (dated,)).fetchall()
        return conn.execute("SELECT * FROM opening_balances ORDER BY dated DESC, ac_code").fetchall()

def save_opening_balance(data):
    """data = (ac_code, ac_name, debit, credit, dated)
    Posts net to the account's opening/balance AND posts the reverse entry to the
    Capital/Equity account so every opening balance is a balanced double-entry."""
    ac_code, ac_name, debit, credit, dated = data
    with get_connection() as conn:
        conn.execute("INSERT INTO opening_balances (ac_code, ac_name, debit, credit, dated) VALUES (?,?,?,?,?)",
                     data)
        # Post net opening to account: debit increases balance, credit decreases
        net = (debit or 0) - (credit or 0)
        existing = conn.execute(
            "SELECT opening FROM chart_of_accounts WHERE ac_code=?", (ac_code,)
        ).fetchone()
        if existing:
            new_opening = (existing["opening"] or 0) + net
            conn.execute(
                "UPDATE chart_of_accounts SET opening=?, balance=balance+? WHERE ac_code=?",
                (new_opening, net, ac_code)
            )
        # Balanced double-entry: post reverse to Capital/Equity
        # (DR account → CR Capital; CR account → DR Capital)
        equity = _equity_ac(conn)
        if equity and equity != ac_code:
            _ac_delta(conn, equity, credit or 0, debit or 0)
        conn.commit()

def delete_opening_balance(row_id):
    with get_connection() as conn:
        # Reverse the posted amount before deleting
        row = conn.execute(
            "SELECT ac_code, debit, credit FROM opening_balances WHERE id=?", (row_id,)
        ).fetchone()
        if row:
            net = (row["debit"] or 0) - (row["credit"] or 0)
            conn.execute(
                "UPDATE chart_of_accounts SET opening=opening-?, balance=balance-? WHERE ac_code=?",
                (net, net, row["ac_code"])
            )
            # Reverse the Capital counterpart
            equity = _equity_ac(conn)
            if equity and equity != row["ac_code"]:
                _ac_delta(conn, equity, row["debit"] or 0, row["credit"] or 0)
        conn.execute("DELETE FROM opening_balances WHERE id=?", (row_id,))
        conn.commit()

# ── Reports ────────────────────────────────────────────────────────────────────

def get_general_ledger(from_date, to_date):
    with get_connection() as conn:
        return conn.execute("""
            SELECT jv.prepare_date as dated, jv.voucher_no, jvl.ac_code, jvl.ac_title,
                   jvl.debit, jvl.credit, jv.description
            FROM journal_voucher_lines jvl
            JOIN journal_vouchers jv ON jvl.voucher_no = jv.voucher_no
            WHERE jv.prepare_date BETWEEN ? AND ?
            ORDER BY jv.prepare_date, jv.voucher_no
        """, (from_date, to_date)).fetchall()

def get_trial_balance():
    with get_connection() as conn:
        return conn.execute("""
            SELECT ca.ac_code, ca.ac_name,
                   COALESCE(ca.ac_type, 'EXPENSE') as ac_type,
                   ca.opening,
                   COALESCE(SUM(jvl.debit),0)  as total_debit,
                   COALESCE(SUM(jvl.credit),0) as total_credit,
                   ca.balance
            FROM chart_of_accounts ca
            LEFT JOIN journal_voucher_lines jvl ON ca.ac_code = jvl.ac_code
            GROUP BY ca.ac_code, ca.ac_name, ca.ac_type, ca.opening, ca.balance
            ORDER BY ca.ac_type, ca.ac_code
        """).fetchall()

def get_inventory_stock(dated):
    with get_connection() as conn:
        return conn.execute("""
            SELECT code, name, unit, quantity, last_purchase_rate,
                   (quantity * last_purchase_rate) as stock_value, value
            FROM inventory_items
            ORDER BY code
        """).fetchall()

def get_daily_general_transactions(dated):
    with get_connection() as conn:
        return conn.execute("""
            SELECT jv.prepare_date, jv.voucher_no, jvl.ac_code, jvl.ac_title,
                   jvl.debit, jvl.credit, jv.description
            FROM journal_voucher_lines jvl
            JOIN journal_vouchers jv ON jvl.voucher_no = jv.voucher_no
            WHERE jv.prepare_date = ?
            ORDER BY jv.voucher_no
        """, (dated,)).fetchall()

def get_inventory_ledger(from_date, to_date, inv_code=None):
    with get_connection() as conn:
        if inv_code:
            q = """
                SELECT pl.inv_code, pl.inventory_name, pt.dated, pt.invoice_no, 'PURCHASE' as type,
                       pl.quantity, pl.rate, pl.value
                FROM purchase_lines pl JOIN purchase_transactions pt ON pl.invoice_no=pt.invoice_no
                WHERE pt.dated BETWEEN ? AND ? AND pl.inv_code=?
                UNION ALL
                SELECT sl.inv_code, sl.inventory_name, st.dated, st.invoice_no, 'SALE' as type,
                       sl.quantity, sl.rate, sl.value
                FROM sales_lines sl JOIN sales_transactions st ON sl.invoice_no=st.invoice_no
                WHERE st.dated BETWEEN ? AND ? AND sl.inv_code=?
                ORDER BY dated
            """
            return conn.execute(q, (from_date, to_date, inv_code, from_date, to_date, inv_code)).fetchall()
        q = """
            SELECT pl.inv_code, pl.inventory_name, pt.dated, pt.invoice_no, 'PURCHASE' as type,
                   pl.quantity, pl.rate, pl.value
            FROM purchase_lines pl JOIN purchase_transactions pt ON pl.invoice_no=pt.invoice_no
            WHERE pt.dated BETWEEN ? AND ?
            UNION ALL
            SELECT sl.inv_code, sl.inventory_name, st.dated, st.invoice_no, 'SALE' as type,
                   sl.quantity, sl.rate, sl.value
            FROM sales_lines sl JOIN sales_transactions st ON sl.invoice_no=st.invoice_no
            WHERE st.dated BETWEEN ? AND ?
            ORDER BY dated
        """
        return conn.execute(q, (from_date, to_date, from_date, to_date)).fetchall()


# ── Opening Stock (OTF) ────────────────────────────────────────────────────────

def get_opening_stock():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM opening_stock ORDER BY dated, inv_code").fetchall()

def save_opening_stock(inv_code, inv_name, qty, rate, value, dated):
    """
    GL: DR Inventory Control (stock in)
        CR Equity/Capital     (financed by owner investment)
    """
    with get_connection() as conn:
        conn.execute("""INSERT INTO opening_stock
            (inv_code, inventory_name, quantity, rate, value, dated) VALUES (?,?,?,?,?,?)""",
            (inv_code, inv_name, qty, rate, value, dated))
        _inv_delta(conn, inv_code, qty, value, last_rate=rate, last_date=dated)
        inv_ctrl = _inventory_control_ac(conn)
        equity   = _equity_ac(conn)
        _ac_delta(conn, inv_ctrl, value or 0, 0)          # DR inventory control
        _ac_delta(conn, equity,   0, value or 0)          # CR equity/capital
        conn.commit()

def delete_opening_stock(row_id, inv_code):
    with get_connection() as conn:
        row = conn.execute("SELECT quantity, value FROM opening_stock WHERE id=?", (row_id,)).fetchone()
        if row:
            v = row["value"] or 0
            _inv_delta(conn, inv_code, -(row["quantity"] or 0), -v)
            inv_ctrl = _inventory_control_ac(conn)
            equity   = _equity_ac(conn)
            _ac_delta(conn, inv_ctrl, 0, v)               # CR inventory (reverse DR)
            _ac_delta(conn, equity,   v, 0)               # DR equity (reverse CR)
        conn.execute("DELETE FROM opening_stock WHERE id=?", (row_id,))
        conn.commit()


# ── Carry Transactions (CHF) ───────────────────────────────────────────────────

def get_all_carry():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM carry_transactions ORDER BY invoice_no DESC").fetchall()

def get_carry(invoice_no):
    with get_connection() as conn:
        hdr  = conn.execute("SELECT * FROM carry_transactions WHERE invoice_no=?", (invoice_no,)).fetchone()
        lines = conn.execute("SELECT * FROM carry_lines WHERE invoice_no=?", (invoice_no,)).fetchall()
        return hdr, lines

def save_carry(header, lines):
    """
    Carry transaction (internal stock carry-forward).
    GL: DR Inventory Control (stock received)
        CR Equity/Capital    (internal carry-in)
    """
    with get_connection() as conn:
        # Reverse old lines if updating
        old_lines = conn.execute(
            "SELECT inv_code, quantity, value FROM carry_lines WHERE invoice_no=?",
            (header[0],)).fetchall()
        old_total = sum(r["value"] or 0 for r in old_lines)
        for r in old_lines:
            _inv_delta(conn, r["inv_code"], -(r["quantity"] or 0), -(r["value"] or 0))

        conn.execute("""INSERT OR REPLACE INTO carry_transactions
            (invoice_no, dated, description, total_value) VALUES (?,?,?,?)""", header)
        conn.execute("DELETE FROM carry_lines WHERE invoice_no=?", (header[0],))
        total_new = 0.0
        for ln in lines:
            conn.execute("""INSERT INTO carry_lines
                (invoice_no, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?)""", ln)
            if ln[1]:
                _inv_delta(conn, ln[1], ln[3] or 0, ln[5] or 0,
                           last_rate=ln[4], last_date=header[1])
                total_new += ln[5] or 0

        # GL posting: reverse old, apply new
        inv_ctrl = _inventory_control_ac(conn)
        equity   = _equity_ac(conn)
        _ac_delta(conn, inv_ctrl, 0, old_total)            # reverse old DR
        _ac_delta(conn, equity,   old_total, 0)            # reverse old CR
        _ac_delta(conn, inv_ctrl, total_new, 0)            # new DR
        _ac_delta(conn, equity,   0, total_new)            # new CR
        conn.commit()

def delete_carry(invoice_no):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT inv_code, quantity, value FROM carry_lines WHERE invoice_no=?",
            (invoice_no,)).fetchall()
        total = sum(r["value"] or 0 for r in rows)
        for r in rows:
            _inv_delta(conn, r["inv_code"], -(r["quantity"] or 0), -(r["value"] or 0))
        inv_ctrl = _inventory_control_ac(conn)
        equity   = _equity_ac(conn)
        _ac_delta(conn, inv_ctrl, 0, total)                # CR inventory (reverse DR)
        _ac_delta(conn, equity,   total, 0)                # DR equity (reverse CR)
        conn.execute("DELETE FROM carry_transactions WHERE invoice_no=?", (invoice_no,))
        conn.commit()

def next_carry_no():
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM carry_transactions").fetchone()
        return f"CHF-{(row[0]+1):05d}"


# ── Value Adjustments (VAF / AVADJ / VADF) ────────────────────────────────────

def get_value_adjustments(adj_type=None):
    with get_connection() as conn:
        if adj_type:
            return conn.execute("SELECT * FROM value_adjustments WHERE adj_type=? ORDER BY dated DESC", (adj_type,)).fetchall()
        return conn.execute("SELECT * FROM value_adjustments ORDER BY dated DESC").fetchall()

def save_value_adjustment(ref_no, adj_type, inv_code, inv_name,
                          old_qty, new_qty, old_value, new_value, dated, description):
    """
    GL for value increase: DR Inventory Control, CR Exchange Income
    GL for value decrease: DR Exchange Expense, CR Inventory Control
    GL for qty change:    mirrors value direction
    """
    dq  = (new_qty   or 0) - (old_qty   or 0)
    dv  = (new_value or 0) - (old_value or 0)
    with get_connection() as conn:
        conn.execute("""INSERT INTO value_adjustments
            (ref_no, adj_type, inv_code, inventory_name,
             old_qty, new_qty, old_value, new_value, dated, description)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ref_no, adj_type, inv_code, inv_name,
             old_qty, new_qty, old_value, new_value, dated, description))
        _inv_delta(conn, inv_code, dq, dv)
        inv_ctrl = _inventory_control_ac(conn)
        if dv > 0:
            income_ac = _income_ac(conn)
            _ac_delta(conn, inv_ctrl,  dv, 0)      # DR inventory (value up)
            _ac_delta(conn, income_ac, 0,  dv)     # CR exchange income
        elif dv < 0:
            expense_ac = _expense_ac(conn)
            _ac_delta(conn, expense_ac, abs(dv), 0)  # DR exchange expense (value down)
            _ac_delta(conn, inv_ctrl,   0, abs(dv))  # CR inventory
        conn.commit()

def delete_value_adjustment(row_id, inv_code):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT old_qty, new_qty, old_value, new_value FROM value_adjustments WHERE id=?",
            (row_id,)).fetchone()
        if row:
            dq = (row["new_qty"]   or 0) - (row["old_qty"]   or 0)
            dv = (row["new_value"] or 0) - (row["old_value"] or 0)
            _inv_delta(conn, inv_code, -dq, -dv)
            inv_ctrl = _inventory_control_ac(conn)
            if dv > 0:
                income_ac = _income_ac(conn)
                _ac_delta(conn, inv_ctrl,  0,  dv)     # reverse: CR inventory
                _ac_delta(conn, income_ac, dv, 0)      # reverse: DR income
            elif dv < 0:
                expense_ac = _expense_ac(conn)
                _ac_delta(conn, expense_ac, 0, abs(dv))  # reverse: CR expense
                _ac_delta(conn, inv_ctrl, abs(dv), 0)    # reverse: DR inventory
        conn.execute("DELETE FROM value_adjustments WHERE id=?", (row_id,))
        conn.commit()

def auto_value_adjust(dated):
    """AVADJ: revalue all inventory at current last_purchase_rate."""
    with get_connection() as conn:
        items = conn.execute("SELECT * FROM inventory_items WHERE quantity > 0").fetchall()
        for item in items:
            old_val = item["value"]
            new_val = item["quantity"] * item["last_purchase_rate"]
            if abs(new_val - old_val) > 0.01:
                conn.execute("""INSERT INTO value_adjustments
                    (ref_no, adj_type, inv_code, inventory_name,
                     old_qty, new_qty, old_value, new_value, dated, description)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (f"AVADJ-{dated}", "AVADJ", item["code"], item["name"],
                     item["quantity"], item["quantity"], old_val, new_val,
                     dated, "Auto Value Adjustment"))
                conn.execute("UPDATE inventory_items SET value=? WHERE code=?",
                             (new_val, item["code"]))
        conn.commit()
        return len(items)


# ── User Management ────────────────────────────────────────────────────────────

def get_all_users():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users ORDER BY id").fetchall()

def save_user(data):
    """data = (username, password, full_name, designation, department, section, user_id_or_None)"""
    username, password, full_name, designation, department, section, uid = data
    with get_connection() as conn:
        if uid:
            conn.execute("""UPDATE users SET username=?, password=?, full_name=?,
                designation=?, department=?, section=? WHERE id=?""",
                (username, password, full_name, designation, department, section, uid))
        else:
            conn.execute("""INSERT INTO users (username, password, full_name, designation, department, section)
                VALUES (?,?,?,?,?,?)""",
                (username, password, full_name, designation, department, section))
        conn.commit()

def delete_user(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()

def change_password(user_id, new_password):
    with get_connection() as conn:
        conn.execute("UPDATE users SET password=? WHERE id=?", (new_password, user_id))
        conn.commit()

def get_detailed_trial_balance():
    """Trial balance with per-voucher breakdown."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT ca.ac_code, ca.ac_name, ca.opening,
                   jv.prepare_date, jv.voucher_no, jvl.debit, jvl.credit,
                   jv.description
            FROM chart_of_accounts ca
            LEFT JOIN journal_voucher_lines jvl ON ca.ac_code = jvl.ac_code
            LEFT JOIN journal_vouchers jv ON jvl.voucher_no = jv.voucher_no
            ORDER BY ca.ac_code, jv.prepare_date, jv.voucher_no
        """).fetchall()
