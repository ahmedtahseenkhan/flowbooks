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
            balance REAL DEFAULT 0
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
    """)

    # Default admin user
    c.execute("INSERT OR IGNORE INTO users (username, password, full_name, designation, department, section) VALUES (?,?,?,?,?,?)",
              ("admin", "admin123", "DANISH", "MANAGER", "ACCOUNTS", "HEAD OFFICE"))

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
    conn.execute(
        "UPDATE chart_of_accounts SET balance = balance + ? - ? WHERE ac_code=?",
        (debit_delta, credit_delta, ac_code))

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
    with get_connection() as conn:
        conn.execute("""INSERT OR REPLACE INTO chart_of_accounts
            (ac_code, ac_name, head_code, head_name, ac_path, opening, balance) VALUES (?,?,?,?,?,?,?)""", data)
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
    with get_connection() as conn:
        # Reverse old lines
        old_lines = conn.execute(
            "SELECT inv_code, quantity, rate, value FROM purchase_lines WHERE invoice_no=?",
            (header[0],)).fetchall()
        for r in old_lines:
            _inv_delta(conn, r["inv_code"], -(r["quantity"] or 0), -(r["value"] or 0))
        # Save new
        conn.execute("""INSERT OR REPLACE INTO purchase_transactions
            (invoice_no, dated, ac_code, ac_name, term, party, amount, in_words, description, total_value)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", header)
        conn.execute("DELETE FROM purchase_lines WHERE invoice_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO purchase_lines
                (invoice_no, serial, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?,?)""", ln)
            if ln[2]:  # inv_code
                _inv_delta(conn, ln[2], ln[4] or 0, ln[6] or 0,
                           last_rate=ln[5], last_date=header[1], is_purchase=True)
        conn.commit()

def delete_purchase(invoice_no):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT inv_code, quantity, rate, value FROM purchase_lines WHERE invoice_no=?",
            (invoice_no,)).fetchall()
        for r in rows:
            _inv_delta(conn, r["inv_code"], -(r["quantity"] or 0), -(r["value"] or 0))
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
    with get_connection() as conn:
        # Reverse old lines
        old_lines = conn.execute(
            "SELECT inv_code, quantity, rate, value FROM sales_lines WHERE invoice_no=?",
            (header[0],)).fetchall()
        for r in old_lines:
            _inv_delta(conn, r["inv_code"], r["quantity"] or 0, r["value"] or 0)  # add back
        # Save new
        conn.execute("""INSERT OR REPLACE INTO sales_transactions
            (invoice_no, dated, ac_code, ac_name, term, party, amount, in_words, description, total_value)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", header)
        conn.execute("DELETE FROM sales_lines WHERE invoice_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO sales_lines
                (invoice_no, serial, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?,?)""", ln)
            if ln[2]:  # inv_code
                _inv_delta(conn, ln[2], -(ln[4] or 0), -(ln[6] or 0),
                           last_rate=ln[5], last_date=header[1], is_purchase=False)
        conn.commit()

def delete_sale(invoice_no):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT inv_code, quantity, rate, value FROM sales_lines WHERE invoice_no=?",
            (invoice_no,)).fetchall()
        for r in rows:
            _inv_delta(conn, r["inv_code"], r["quantity"] or 0, r["value"] or 0)  # add back
        conn.execute("DELETE FROM sales_transactions WHERE invoice_no=?", (invoice_no,))
        conn.commit()

# ── Opening Balances ───────────────────────────────────────────────────────────

def get_opening_balances(dated=None):
    with get_connection() as conn:
        if dated:
            return conn.execute("SELECT * FROM opening_balances WHERE dated=? ORDER BY ac_code", (dated,)).fetchall()
        return conn.execute("SELECT * FROM opening_balances ORDER BY dated DESC, ac_code").fetchall()

def save_opening_balance(data):
    with get_connection() as conn:
        conn.execute("INSERT INTO opening_balances (ac_code, ac_name, debit, credit, dated) VALUES (?,?,?,?,?)", data)
        conn.commit()

def delete_opening_balance(row_id):
    with get_connection() as conn:
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
                   ca.opening,
                   COALESCE(SUM(jvl.debit),0) as total_debit,
                   COALESCE(SUM(jvl.credit),0) as total_credit,
                   ca.balance
            FROM chart_of_accounts ca
            LEFT JOIN journal_voucher_lines jvl ON ca.ac_code = jvl.ac_code
            GROUP BY ca.ac_code, ca.ac_name, ca.opening, ca.balance
            ORDER BY ca.ac_code
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
    with get_connection() as conn:
        conn.execute("""INSERT INTO opening_stock
            (inv_code, inventory_name, quantity, rate, value, dated) VALUES (?,?,?,?,?,?)""",
            (inv_code, inv_name, qty, rate, value, dated))
        _inv_delta(conn, inv_code, qty, value, last_rate=rate, last_date=dated)
        conn.commit()

def delete_opening_stock(row_id, inv_code):
    with get_connection() as conn:
        row = conn.execute("SELECT quantity, value FROM opening_stock WHERE id=?", (row_id,)).fetchone()
        if row:
            _inv_delta(conn, inv_code, -(row["quantity"] or 0), -(row["value"] or 0))
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
    with get_connection() as conn:
        conn.execute("""INSERT OR REPLACE INTO carry_transactions
            (invoice_no, dated, description, total_value) VALUES (?,?,?,?)""", header)
        conn.execute("DELETE FROM carry_lines WHERE invoice_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO carry_lines
                (invoice_no, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?)""", ln)
        for ln in lines:
            if ln[1]:
                _inv_delta(conn, ln[1], ln[3] or 0, ln[5] or 0,
                           last_rate=ln[4], last_date=header[1])
        conn.commit()

def delete_carry(invoice_no):
    with get_connection() as conn:
        rows = conn.execute("SELECT inv_code, quantity, value FROM carry_lines WHERE invoice_no=?", (invoice_no,)).fetchall()
        for r in rows:
            _inv_delta(conn, r["inv_code"], -(r["quantity"] or 0), -(r["value"] or 0))
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
    with get_connection() as conn:
        conn.execute("""INSERT INTO value_adjustments
            (ref_no, adj_type, inv_code, inventory_name,
             old_qty, new_qty, old_value, new_value, dated, description)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ref_no, adj_type, inv_code, inv_name,
             old_qty, new_qty, old_value, new_value, dated, description))
        _inv_delta(conn, inv_code, new_qty - old_qty, new_value - old_value)
        conn.commit()

def delete_value_adjustment(row_id, inv_code):
    with get_connection() as conn:
        row = conn.execute("SELECT old_qty, new_qty, old_value, new_value FROM value_adjustments WHERE id=?", (row_id,)).fetchone()
        if row:
            _inv_delta(conn, inv_code, -(row["new_qty"]-row["old_qty"]), -(row["new_value"]-row["old_value"]))
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
