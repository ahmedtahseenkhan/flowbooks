"""
FlowBooks – General Accounts / Inventory Management System
Main entry point: Login → Main Menu
"""

import sys
import os

# Ensure the app/ directory is in sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Project root (one level up from app/) so the `licensing` package resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import messagebox
import database as db
from config import *
from licensing import check_license, LicenseStatus, get_machine_id

# ── Late imports (avoid circular deps) ────────────────────────────────────────

def _import_forms():
    from forms.chart_of_accounts  import ChartOfAccounts, DefineHeadingAccounts
    from forms.inventory_master    import InventoryMaster
    from forms.inventory_heads     import InventoryHeads
    from forms.journal_voucher     import JournalVoucher
    from forms.purchase_form       import PurchaseTransactionsForm, SalesTransactionsForm
    from forms.opening_balances    import OpeningBalancesForm
    from forms.reports.general_ledger import (open_general_ledger, open_daily_transactions,
                                               open_trial_balance, open_screen_ledger)
    from forms.reports.inventory_reports import (open_inventory_stock, open_inventory_ledger,
                                                  open_inventory_activity, open_inv_wise_account,
                                                  open_daily_detail_inv, open_daily_inv_summary)
    return locals()


# ─────────────────────────────────────────────────────────────────────────────
# Login Window
# ─────────────────────────────────────────────────────────────────────────────

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} – Login")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._build()
        self._centre()
        self._user_row = None

    def _centre(self):
        self.update_idletasks()
        w, h = 360, 260
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        # Title bar
        hdr = tk.Frame(self, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text=APP_NAME, bg=GRID_HDR_BG, fg="white",
                 font=("Arial", 14, "bold"), pady=8).pack()
        tk.Label(hdr, text=COMPANY, bg=GRID_HDR_BG, fg="white",
                 font=("Arial", 8), pady=2).pack()

        body = tk.Frame(self, bg=BG, pady=16)
        body.pack(expand=True)

        for row, lbl, attr, show in [(0,"Username","_user_e",""),
                                     (1,"Password","_pass_e","*")]:
            tk.Label(body, text=lbl+":", bg=BG, fg=LABEL_FG,
                     font=FONT_BOLD, width=10, anchor="e").grid(row=row, column=0, padx=8, pady=6)
            e = tk.Entry(body, width=22, bg=ENTRY_BG, font=FONT_NORMAL,
                         relief="sunken", bd=2, show=show)
            e.grid(row=row, column=1, padx=8, pady=6)
            setattr(self, attr, e)

        self._user_e.insert(0, "admin")
        self._pass_e.insert(0, "admin123")

        btn_f = tk.Frame(body, bg=BG)
        btn_f.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(btn_f, text="Login", width=10, bg=BTN_BG, font=FONT_BOLD,
                  relief="raised", bd=2, command=self._login).pack(side="left", padx=8)
        tk.Button(btn_f, text="Exit",  width=10, bg=BTN_BG, font=FONT_NORMAL,
                  relief="raised", bd=2, command=self.destroy).pack(side="left", padx=8)

        self._pass_e.bind("<Return>", lambda e: self._login())

        # Footer
        tk.Frame(self, bg=BOTTOM_BAR, height=6).pack(fill="x", side="bottom")

    def _login(self):
        uname = self._user_e.get().strip()
        pwd   = self._pass_e.get().strip()
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username=? AND password=?", (uname, pwd)
            ).fetchone()
        if row:
            self._user_row = row
            self.destroy()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.", parent=self)
            self._pass_e.delete(0, "end")
            self._pass_e.focus_set()


# ─────────────────────────────────────────────────────────────────────────────
# Main Application Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(tk.Tk):
    def __init__(self, user_row):
        super().__init__()
        self._user     = user_row
        self._username = user_row["full_name"] or user_row["username"]
        self._forms    = _import_forms()

        self.title(f"Oracle Forms Runtime – [Main Menu]   {APP_NAME}")
        self.configure(bg=BG)
        self.state("zoomed")          # Start maximised (Windows / Linux)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _build(self):
        self._build_menubar()
        self._build_body()

    # ── Menu bar ───────────────────────────────────────────────────────────────

    def _build_menubar(self):
        mb = tk.Menu(self)
        self.config(menu=mb)

        # ── Accounts Setup
        m = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Accounts Setup", menu=m)
        m.add_command(label="Define Heading Accounts / DHA",     command=lambda: self._open(self._forms["DefineHeadingAccounts"]))
        m.add_command(label="Chart of Accounts - General / CAG", command=lambda: self._open_coa("general"))
        m.add_command(label="Chart of Accounts - Special / CAS", command=lambda: self._open_coa("special"))

        # ── Accounts Transactions
        m2 = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Accounts Transactions", menu=m2)
        m2.add_command(label="Opening Balances Form / OBF",       command=lambda: self._open(self._forms["OpeningBalancesForm"]))
        m2.add_command(label="Journal Voucher Form / JVF",         command=lambda: self._open(self._forms["JournalVoucher"]))
        m2.add_separator()
        m2.add_command(label="Daily General Transactions / DGT",   command=lambda: self._forms["open_daily_transactions"](self))
        m2.add_command(label="General Ledger Report / GLR",        command=lambda: self._forms["open_general_ledger"](self))
        m2.add_command(label="General Ledger Detail / GLD",        command=lambda: self._forms["open_screen_ledger"](self))
        m2.add_command(label="Screen Ledger / SCR_LGR",            command=lambda: self._forms["open_screen_ledger"](self))
        m2.add_command(label="Trial Balance / TB",                  command=lambda: self._forms["open_trial_balance"](self))
        m2.add_command(label="Detailed Trial Balance / DTB",        command=lambda: self._forms["open_trial_balance"](self))

        # ── Inventory Setup
        m3 = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Inventory Setup", menu=m3)
        m3.add_command(label="Inventory Heads",                   command=lambda: self._open(self._forms["InventoryHeads"]))
        m3.add_command(label="Inventory Master",                  command=lambda: self._open(self._forms["InventoryMaster"]))

        # ── Inventory Transactions
        m4 = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Inventory Transactions", menu=m4)
        m4.add_command(label="Opening Transactions Form / OTF",    command=lambda: self._open(self._forms["OpeningBalancesForm"]))
        m4.add_command(label="Purchases Transactions Form / PTF",  command=lambda: self._open(self._forms["PurchaseTransactionsForm"]))
        m4.add_command(label="Sales Transactions Form / STF",      command=lambda: self._open(self._forms["SalesTransactionsForm"]))
        m4.add_separator()
        m4.add_command(label="Inventory Ledger Reports / ILR",     command=lambda: self._forms["open_inventory_ledger"](self))
        m4.add_command(label="Inventory Activity Report / IAR",    command=lambda: self._forms["open_inventory_activity"](self))
        m4.add_command(label="Inv. Wise Account Activity / IWAA",  command=lambda: self._forms["open_inv_wise_account"](self))
        m4.add_command(label="Inventory Stock Report / ISR",       command=lambda: self._forms["open_inventory_stock"](self))
        m4.add_command(label="Daily Detail Inv Transactions / DDIT", command=lambda: self._forms["open_daily_detail_inv"](self))
        m4.add_command(label="Daily Inv Transactions Smry / DITS", command=lambda: self._forms["open_daily_inv_summary"](self))

        # ── Management Information
        m5 = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Management Information", menu=m5)
        m5.add_command(label="Balance Sheet",                     command=lambda: self._forms["open_trial_balance"](self))
        m5.add_command(label="Profit & Loss Statement",           command=lambda: self._forms["open_general_ledger"](self))
        m5.add_separator()
        m5.add_command(label="General Ledger Report",             command=lambda: self._forms["open_general_ledger"](self))
        m5.add_command(label="Trial Balance",                     command=lambda: self._forms["open_trial_balance"](self))
        m5.add_command(label="Inventory Stock Report",            command=lambda: self._forms["open_inventory_stock"](self))

        # ── Administration
        m6 = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Administration", menu=m6)
        m6.add_command(label="User Profile",                      command=self._show_user_profile)

        mb.add_command(label="Exit", command=self._on_exit)

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        # Bottom bar first (side="bottom" must come before pack fill)
        tk.Frame(self, bg=BOTTOM_BAR, height=8).pack(fill="x", side="bottom")
        tk.Label(self, text=f"User: {self._username}    {COMPANY}",
                 bg=STATUS_BG, fg=STATUS_FG, font=FONT_SMALL,
                 anchor="w").pack(fill="x", side="bottom", padx=4)

        # ── Main scrollable area ───────────────────────────────────────────────
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        # ── Top row: title + user profile card ────────────────────────────────
        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(top, text=COMPANY, bg=BG, fg=TITLE_FG,
                 font=("Arial", 13, "bold")).pack(side="left", padx=4)

        card = tk.LabelFrame(top, text="User Profile", bg="#D8DCF0",
                             fg=LABEL_FG, font=FONT_BOLD, bd=2, relief="groove")
        card.pack(side="right", padx=6)
        for i, (lbl, val) in enumerate([
            ("Emplyee Code",  "1"),
            ("Emplyee Name",  self._username),
            ("Designation",   self._user["designation"] or "MANAGER"),
            ("Department",    self._user["department"]  or "ACCOUNTS"),
            ("Section",       self._user["section"]     or "HEAD OFFICE"),
        ]):
            tk.Label(card, text=lbl+":", bg="#D8DCF0", fg=LABEL_FG,
                     font=FONT_BOLD, width=13, anchor="e").grid(row=i, column=0, padx=4, pady=1, sticky="e")
            tk.Label(card, text=val, bg="#D8DCF0", fg="black",
                     font=FONT_NORMAL, width=16, anchor="w").grid(row=i, column=1, padx=4, pady=1, sticky="w")

        tk.Frame(outer, bg=BORDER, height=2).pack(fill="x", padx=16, pady=6)

        # ── Navigation button groups ───────────────────────────────────────────
        nav = tk.Frame(outer, bg=BG)
        nav.pack(fill="both", expand=True, padx=16, pady=4)

        groups = [
            ("Accounts Setup", "#4C6890", [
                ("Define Heading Accounts / DHA",     lambda: self._open(self._forms["DefineHeadingAccounts"])),
                ("Chart of Accounts - General / CAG", lambda: self._open_coa("general")),
                ("Chart of Accounts - Special / CAS", lambda: self._open_coa("special")),
            ]),
            ("Accounts Transactions", "#4C6890", [
                ("Opening Balances Form / OBF",       lambda: self._open(self._forms["OpeningBalancesForm"])),
                ("Journal Voucher Form / JVF",         lambda: self._open(self._forms["JournalVoucher"])),
                ("Daily General Transactions / DGT",   lambda: self._forms["open_daily_transactions"](self)),
                ("General Ledger Report / GLR",        lambda: self._forms["open_general_ledger"](self)),
                ("Screen Ledger / SCR_LGR",            lambda: self._forms["open_screen_ledger"](self)),
                ("Trial Balance / TB",                 lambda: self._forms["open_trial_balance"](self)),
            ]),
            ("Inventory Setup", "#4C6890", [
                ("Inventory Heads",                    lambda: self._open(self._forms["InventoryHeads"])),
                ("Inventory Master",                   lambda: self._open(self._forms["InventoryMaster"])),
            ]),
            ("Inventory Transactions", "#4C6890", [
                ("Purchases Transactions / PTF",       lambda: self._open(self._forms["PurchaseTransactionsForm"])),
                ("Sales Transactions / STF",           lambda: self._open(self._forms["SalesTransactionsForm"])),
                ("Inventory Stock Report / ISR",       lambda: self._forms["open_inventory_stock"](self)),
                ("Inventory Ledger Reports / ILR",     lambda: self._forms["open_inventory_ledger"](self)),
                ("Inventory Activity Report / IAR",    lambda: self._forms["open_inventory_activity"](self)),
                ("Daily Detail Inv Trans / DDIT",      lambda: self._forms["open_daily_detail_inv"](self)),
                ("Daily Inv Trans Summary / DITS",     lambda: self._forms["open_daily_inv_summary"](self)),
            ]),
        ]

        for col, (grp_title, hdr_color, items) in enumerate(groups):
            col_frame = tk.Frame(nav, bg=BG)
            col_frame.grid(row=0, column=col, sticky="nw", padx=6, pady=4)

            # Group header
            hdr = tk.Frame(col_frame, bg=hdr_color)
            hdr.pack(fill="x")
            tk.Label(hdr, text=grp_title, bg=hdr_color, fg="white",
                     font=FONT_BOLD, pady=5, padx=8).pack(anchor="w")

            # Buttons
            btn_frame = tk.Frame(col_frame, bg="#D8DCE8", bd=1, relief="sunken")
            btn_frame.pack(fill="x")
            for label, cmd in items:
                b = tk.Button(btn_frame, text=label, anchor="w",
                              bg="#D8DCE8", fg=LABEL_FG, font=FONT_NORMAL,
                              relief="flat", bd=0, padx=10, pady=3,
                              cursor="hand2", command=cmd)
                b.pack(fill="x")
                b.bind("<Enter>", lambda e, btn=b: btn.configure(bg="#B8C8DC", fg=LABEL_FG))
                b.bind("<Leave>", lambda e, btn=b: btn.configure(bg="#D8DCE8", fg=LABEL_FG))
                # Separator line
                tk.Frame(btn_frame, bg=BORDER, height=1).pack(fill="x")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _open(self, FormClass):
        try:
            FormClass(self, username=self._username)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def _open_coa(self, mode):
        try:
            self._forms["ChartOfAccounts"](self, username=self._username, mode=mode)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def _show_user_profile(self):
        win = tk.Toplevel(self)
        win.title("User Profile")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        hdr = tk.Frame(win, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="User Profile", bg=GRID_HDR_BG, fg="white",
                 font=FONT_TITLE, pady=6).pack()

        body = tk.Frame(win, bg=BG, padx=20, pady=16)
        body.pack()
        for i, (lbl, val) in enumerate([
            ("Employee Code",  "1"),
            ("Employee Name",  self._username),
            ("Designation",    self._user["designation"] or "MANAGER"),
            ("Department",     self._user["department"]  or "ACCOUNTS"),
            ("Section",        self._user["section"]     or "HEAD OFFICE"),
            ("Username",       self._user["username"]),
        ]):
            tk.Label(body, text=lbl+":", bg=BG, fg=LABEL_FG,
                     font=FONT_BOLD, width=16, anchor="e").grid(row=i, column=0, padx=6, pady=3)
            tk.Label(body, text=val, bg=BG, fg="black",
                     font=FONT_NORMAL, width=20, anchor="w").grid(row=i, column=1, padx=6, pady=3)

        tk.Button(win, text="Close", bg=BTN_BG, font=FONT_NORMAL, relief="raised",
                  command=win.destroy).pack(pady=10)
        tk.Frame(win, bg=BOTTOM_BAR, height=6).pack(fill="x", side="bottom")

    def _on_exit(self):
        if messagebox.askyesno("Exit", "Exit FlowBooks?", parent=self):
            self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# License gate
# ─────────────────────────────────────────────────────────────────────────────

_BLOCKING_STATUSES = {
    LicenseStatus.TRIAL_EXPIRED,
    LicenseStatus.EXPIRED,
    LicenseStatus.MACHINE_MISMATCH,
    LicenseStatus.INVALID_SIGNATURE,
    LicenseStatus.TAMPERED,
    LicenseStatus.CLOCK_TAMPERED,
}


def _show_license_block(info):
    """Modal error window shown when the license is unusable.
    Always exposes the Machine ID so the user can email it to the vendor."""
    root = tk.Tk()
    root.title(f"{APP_NAME} – License")
    root.configure(bg=BG)
    root.resizable(False, False)

    hdr = tk.Frame(root, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text=f"{APP_NAME} – License Problem", bg=GRID_HDR_BG,
             fg="white", font=("Arial", 12, "bold"), pady=8).pack()

    body = tk.Frame(root, bg=BG, padx=24, pady=16)
    body.pack()

    tk.Label(body, text=f"Status: {info.status.name}", bg=BG, fg=LABEL_FG,
             font=FONT_BOLD, anchor="w").pack(fill="x", pady=(0, 4))
    tk.Label(body, text=info.message or "", bg=BG, fg="black",
             font=FONT_NORMAL, wraplength=420, justify="left",
             anchor="w").pack(fill="x", pady=(0, 10))

    tk.Label(body, text="Machine ID (send this to your vendor):",
             bg=BG, fg=LABEL_FG, font=FONT_BOLD,
             anchor="w").pack(fill="x")
    e = tk.Entry(body, font=FONT_MONO, bg=ENTRY_BG, relief="sunken", bd=2,
                 width=24, justify="center")
    e.insert(0, info.machine_id)
    e.configure(state="readonly")
    e.pack(fill="x", pady=(2, 12))

    tk.Button(body, text="Exit", width=10, bg=BTN_BG, font=FONT_BOLD,
              relief="raised", bd=2, command=root.destroy).pack(pady=4)
    tk.Frame(root, bg=BOTTOM_BAR, height=6).pack(fill="x", side="bottom")

    root.update_idletasks()
    w, h = 480, root.winfo_reqheight()
    x = (root.winfo_screenwidth()  - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.mainloop()


def _enforce_license() -> "LicenseInfo | None":
    """Return the LicenseInfo if the app may proceed, else None."""
    info = check_license(APP_NAME)
    if info.status in _BLOCKING_STATUSES:
        _show_license_block(info)
        return None
    if info.status == LicenseStatus.TRIAL_ACTIVE:
        # Non-blocking trial banner.
        tmp = tk.Tk(); tmp.withdraw()
        messagebox.showinfo(
            f"{APP_NAME} – Trial",
            f"Trial mode: {info.days_remaining} day(s) remaining.\n"
            f"Machine ID: {info.machine_id}",
            parent=tmp,
        )
        tmp.destroy()
    return info


# ─────────────────────────────────────────────────────────────────────────────
# Application bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if _enforce_license() is None:
        return

    db.init_db()

    login = LoginWindow()
    login.mainloop()

    if login._user_row is None:
        return  # user closed without logging in

    app = MainWindow(login._user_row)
    app.mainloop()


if __name__ == "__main__":
    main()
