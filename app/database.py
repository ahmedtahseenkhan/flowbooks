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


# ── Accounting engine helpers ─────────────────────────────────────────────────

def _recalc_account_balance(conn, ac_code):
    """Recompute a single account's balance from opening + all JV lines."""
    row = conn.execute(
        "SELECT opening FROM chart_of_accounts WHERE ac_code=?", (ac_code,)
    ).fetchone()
    if not row:
        return
    net = conn.execute(
        "SELECT COALESCE(SUM(debit),0) - COALESCE(SUM(credit),0) "
        "FROM journal_voucher_lines WHERE ac_code=?", (ac_code,)
    ).fetchone()[0]
    conn.execute(
        "UPDATE chart_of_accounts SET balance=? WHERE ac_code=?",
        (row["opening"] + net, ac_code)
    )


def _recalc_inventory(conn, inv_code):
    """Recompute inventory quantity & value from opening stock + purchases - sales + adjustments."""
    # Opening stock
    op = conn.execute(
        "SELECT COALESCE(SUM(quantity),0), COALESCE(SUM(value),0) "
        "FROM opening_stock WHERE inv_code=?", (inv_code,)
    ).fetchone()
    op_qty, op_val = op[0], op[1]

    # Purchases
    pur = conn.execute("""
        SELECT COALESCE(SUM(pl.quantity),0), COALESCE(SUM(pl.value),0),
               MAX(pl.rate), MAX(pt.dated)
        FROM purchase_lines pl
        JOIN purchase_transactions pt ON pl.invoice_no = pt.invoice_no
        WHERE pl.inv_code=?
    """, (inv_code,)).fetchone()
    pur_qty, pur_val, last_pur_rate, last_pur_date = pur

    # Carry-forward transactions (treated as additional stock)
    carry = conn.execute(
        "SELECT COALESCE(SUM(quantity),0), COALESCE(SUM(value),0) "
        "FROM carry_lines WHERE inv_code=?", (inv_code,)
    ).fetchone()
    carry_qty, carry_val = carry[0], carry[1]

    # Sales
    sal = conn.execute("""
        SELECT COALESCE(SUM(sl.quantity),0), COALESCE(SUM(sl.value),0),
               MAX(sl.rate), MAX(st.dated)
        FROM sales_lines sl
        JOIN sales_transactions st ON sl.invoice_no = st.invoice_no
        WHERE sl.inv_code=?
    """, (inv_code,)).fetchone()
    sal_qty, sal_val, last_sal_rate, last_sal_date = sal

    # Value adjustments (new_qty - old_qty)
    adj = conn.execute(
        "SELECT COALESCE(SUM(new_qty - old_qty),0), COALESCE(SUM(new_value - old_value),0) "
        "FROM value_adjustments WHERE inv_code=?", (inv_code,)
    ).fetchone()
    adj_qty, adj_val = adj[0], adj[1]

    net_qty = op_qty + pur_qty + carry_qty - sal_qty + adj_qty
    net_val = op_val + pur_val + carry_val - sal_val + adj_val

    conn.execute("""
        UPDATE inventory_items SET
            quantity=?, value=?,
            last_purchase_rate=COALESCE(?,last_purchase_rate),
            last_purchase_date=COALESCE(?,last_purchase_date),
            last_sale_rate=COALESCE(?,last_sale_rate),
            last_sale_date=COALESCE(?,last_sale_date)
        WHERE code=?
    """, (max(0.0, net_qty), max(0.0, net_val),
          last_pur_rate, last_pur_date,
          last_sal_rate, last_sal_date,
          inv_code))


def recalc_all_balances():
    """Full recalculation of every account balance and every inventory item."""
    with get_connection() as conn:
        for row in conn.execute("SELECT ac_code FROM chart_of_accounts").fetchall():
            _recalc_account_balance(conn, row["ac_code"])
        for row in conn.execute("SELECT code FROM inventory_items").fetchall():
            _recalc_inventory(conn, row["code"])
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
        conn.execute("""INSERT OR REPLACE INTO journal_vouchers
            (voucher_no, prepare_date, description, total_debit, total_credit) VALUES (?,?,?,?,?)""", header)
        conn.execute("DELETE FROM journal_voucher_lines WHERE voucher_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO journal_voucher_lines
                (voucher_no, ac_code, ac_title, debit, credit) VALUES (?,?,?,?,?)""", ln)
        # Recalculate affected account balances
        affected = {ln[1] for ln in lines if ln[1]}
        for ac in affected:
            _recalc_account_balance(conn, ac)
        conn.commit()

def delete_voucher(voucher_no):
    with get_connection() as conn:
        # Capture affected accounts before deleting
        rows = conn.execute(
            "SELECT DISTINCT ac_code FROM journal_voucher_lines WHERE voucher_no=?",
            (voucher_no,)
        ).fetchall()
        affected = {r["ac_code"] for r in rows}
        conn.execute("DELETE FROM journal_vouchers WHERE voucher_no=?", (voucher_no,))
        for ac in affected:
            _recalc_account_balance(conn, ac)
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
        conn.execute("""INSERT OR REPLACE INTO purchase_transactions
            (invoice_no, dated, ac_code, ac_name, term, party, amount, in_words, description, total_value)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", header)
        conn.execute("DELETE FROM purchase_lines WHERE invoice_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO purchase_lines
                (invoice_no, serial, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?,?)""", ln)
        # Recalculate affected inventory items
        affected = {ln[2] for ln in lines if ln[2]}
        for code in affected:
            _recalc_inventory(conn, code)
        conn.commit()

def delete_purchase(invoice_no):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT inv_code FROM purchase_lines WHERE invoice_no=?", (invoice_no,)
        ).fetchall()
        affected = {r["inv_code"] for r in rows}
        conn.execute("DELETE FROM purchase_transactions WHERE invoice_no=?", (invoice_no,))
        for code in affected:
            _recalc_inventory(conn, code)
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
        conn.execute("""INSERT OR REPLACE INTO sales_transactions
            (invoice_no, dated, ac_code, ac_name, term, party, amount, in_words, description, total_value)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", header)
        conn.execute("DELETE FROM sales_lines WHERE invoice_no=?", (header[0],))
        for ln in lines:
            conn.execute("""INSERT INTO sales_lines
                (invoice_no, serial, inv_code, inventory_name, quantity, rate, value) VALUES (?,?,?,?,?,?,?)""", ln)
        affected = {ln[2] for ln in lines if ln[2]}
        for code in affected:
            _recalc_inventory(conn, code)
        conn.commit()

def delete_sale(invoice_no):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT inv_code FROM sales_lines WHERE invoice_no=?", (invoice_no,)
        ).fetchall()
        affected = {r["inv_code"] for r in rows}
        conn.execute("DELETE FROM sales_transactions WHERE invoice_no=?", (invoice_no,))
        for code in affected:
            _recalc_inventory(conn, code)
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
        _recalc_inventory(conn, inv_code)
        conn.commit()

def delete_opening_stock(row_id, inv_code):
    with get_connection() as conn:
        conn.execute("DELETE FROM opening_stock WHERE id=?", (row_id,))
        _recalc_inventory(conn, inv_code)
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
        affected = {ln[1] for ln in lines if ln[1]}
        for code in affected:
            _recalc_inventory(conn, code)
        conn.commit()

def delete_carry(invoice_no):
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT inv_code FROM carry_lines WHERE invoice_no=?", (invoice_no,)).fetchall()
        affected = {r["inv_code"] for r in rows}
        conn.execute("DELETE FROM carry_transactions WHERE invoice_no=?", (invoice_no,))
        for code in affected:
            _recalc_inventory(conn, code)
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
        _recalc_inventory(conn, inv_code)
        conn.commit()

def delete_value_adjustment(row_id, inv_code):
    with get_connection() as conn:
        conn.execute("DELETE FROM value_adjustments WHERE id=?", (row_id,))
        _recalc_inventory(conn, inv_code)
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
