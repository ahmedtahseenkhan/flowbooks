"""
General Ledger Report / GLR, Daily General Transactions / DGT,
Account Ledger Detail, Trial Balance, Screen Ledger.
All dialogs match design images exactly.
"""

import tkinter as tk
from tkinter import messagebox, font as tkfont
from config import *
from forms.base_form import DateRangeDialog, make_grid, AccountLOVDialog
import database as db
from datetime import date


# ── General Ledger Report / GLR ───────────────────────────────────────────────

def open_general_ledger(master, username="ADMIN"):
    """Dialog matches design: Print on Laser/Dot Matrix, SHORT/LONG, From Account Code."""
    dlg = _GLRDialog(master, "GENERAL LEDGER REPORT / GLR")
    if not dlg.result:
        return
    from_d, to_d, ac_code, ac_name, style = dlg.result
    rows = db.get_general_ledger(from_d, to_d)
    if ac_code:
        rows = [r for r in rows if r["ac_code"] == ac_code]

    cols = [("dated","Date",80), ("vno","Voucher#",70),
            ("ac_code","A/C Code",70), ("ac_title","A/C Title",180),
            ("debit","Debit",90), ("credit","Credit",90),
            ("desc","Description",140)]
    data = [(r["dated"], r["voucher_no"], r["ac_code"], r["ac_title"],
             f"{r['debit']:,.2f}", f"{r['credit']:,.2f}", r["description"] or "")
            for r in rows]
    td = sum(r["debit"]   for r in rows)
    tc = sum(r["credit"]  for r in rows)
    _report_window(master, "General Ledger Report / GLR",
                   "GENERAL LEDGER REPORT", cols, data,
                   f"Total Debit: {td:,.2f}    Total Credit: {tc:,.2f}")


class _GLRDialog(tk.Toplevel):
    """Matches design image: Print on, SHORT/LONG, From Account Code."""

    def __init__(self, master, title):
        super().__init__(master)
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.result = None
        self.grab_set()

        from datetime import date as _date
        today = _date.today()

        # Header
        hdr = tk.Frame(self, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="General Ledger (Detail)", bg=GRID_HDR_BG, fg="white",
                 font=("Arial", 11, "bold"), pady=8).pack()

        body = tk.Frame(self, bg=BG, padx=24, pady=10)
        body.pack(fill="both", expand=True)

        # Print on
        pr = tk.Frame(body, bg=BG)
        pr.grid(row=0, column=0, columnspan=4, sticky="e", pady=4)
        tk.Label(pr, text="Print on :", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left")
        self._print_var = tk.StringVar(value="laser")
        for v, t in [("laser","Laser"), ("dot","Dot Matrix")]:
            tk.Radiobutton(pr, text=t, variable=self._print_var, value=v,
                           bg=BG, fg=LABEL_FG, font=FONT_NORMAL).pack(side="left", padx=6)

        # From date
        tk.Label(body, text="From", bg=BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=8, anchor="e").grid(row=1, column=0, sticky="e", pady=5)
        self._from_var = tk.StringVar(value=today.replace(month=1, day=1).strftime("%d/%m/%Y"))
        tk.Entry(body, textvariable=self._from_var, width=14,
                 bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2).grid(
            row=1, column=1, sticky="w", padx=6, pady=5)
        tk.Label(body, text="DD/MM/YYYY", bg=BG, fg=LABEL_FG,
                 font=("Arial",7)).grid(row=1, column=2, sticky="w")

        # To date
        tk.Label(body, text="To", bg=BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=8, anchor="e").grid(row=2, column=0, sticky="e", pady=5)
        self._to_var = tk.StringVar(value=today.strftime("%d/%m/%Y"))
        tk.Entry(body, textvariable=self._to_var, width=14,
                 bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2).grid(
            row=2, column=1, sticky="w", padx=6, pady=5)
        tk.Label(body, text="DD/MM/YYYY", bg=BG, fg=LABEL_FG,
                 font=("Arial",7)).grid(row=2, column=2, sticky="w")

        # SHORT / LONG
        slr = tk.Frame(body, bg=BG)
        slr.grid(row=3, column=0, columnspan=4, sticky="w", pady=4, padx=40)
        self._style_var = tk.StringVar(value="short")
        for v, t in [("short","SHORT"), ("long","LONG")]:
            tk.Radiobutton(slr, text=t, variable=self._style_var, value=v,
                           bg=BG, fg=LABEL_FG, font=FONT_NORMAL).pack(side="left", padx=10)

        # From Account Code
        acr = tk.Frame(body, bg=BG)
        acr.grid(row=4, column=0, columnspan=4, sticky="w", pady=6)
        tk.Label(acr, text="From Account Code [L]", bg=BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="left")
        self._ac_var = tk.StringVar()
        ac_e = tk.Entry(acr, textvariable=self._ac_var, width=10,
                        bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        ac_e.pack(side="left", padx=6)
        tk.Label(acr, text="Name", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left")
        self._ac_name_var = tk.StringVar()
        tk.Entry(acr, textvariable=self._ac_name_var, width=28,
                 bg="#E8E8E8", font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).pack(side="left", padx=4)
        ac_e.bind("<F9>", lambda e: self._f9(ac_e))
        ac_e.bind("<FocusOut>", lambda e: self._lookup(ac_e))

        # Buttons
        bf = tk.Frame(self, bg=BG, pady=10)
        bf.pack()
        tk.Button(bf, text="OK",     width=8, bg=BTN_BG, font=FONT_NORMAL,
                  relief="raised", command=self._ok).pack(side="left", padx=8)
        tk.Button(bf, text="Cancel", width=8, bg=BTN_BG, font=FONT_NORMAL,
                  relief="raised", command=self.destroy).pack(side="left", padx=8)

        tk.Frame(self, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")
        self.transient(master)
        self.wait_window(self)

    def _f9(self, entry):
        dlg = AccountLOVDialog(self, entry.get())
        if dlg.result:
            self._ac_var.set(dlg.result[0])
            self._ac_name_var.set(dlg.result[1])

    def _lookup(self, _):
        code = self._ac_var.get().strip()
        if code:
            row = db.get_account(code)
            if row:
                self._ac_name_var.set(row["ac_name"])

    def _ok(self):
        try:
            from datetime import datetime
            fd = datetime.strptime(self._from_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            td = datetime.strptime(self._to_var.get(),   "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY format.", parent=self)
            return
        self.result = (fd, td,
                       self._ac_var.get().strip(),
                       self._ac_name_var.get(),
                       self._style_var.get())
        self.destroy()


# ── Account Ledger Detail – running balance ────────────────────────────────────

def open_account_ledger_detail(master, username="ADMIN"):
    """Running-balance ledger per account – matches acd:Previewer design image."""
    dlg = _GLRDialog(master, "GENERAL LEDGER REPORT / GLR")
    if not dlg.result:
        return
    from_d, to_d, ac_code, ac_name, style = dlg.result

    if not ac_code:
        messagebox.showwarning("Filter",
                               "Please enter an Account Code for Account Ledger Detail.",
                               parent=master)
        return

    rows = db.get_general_ledger(from_d, to_d)
    rows = [r for r in rows if r["ac_code"] == ac_code]

    # Get opening balance
    acct = db.get_account(ac_code)
    opening = float(acct["opening"]) if acct else 0.0

    _account_ledger_window(master, ac_code, ac_name or (acct["ac_name"] if acct else ""),
                           from_d, to_d, rows, opening)


def _account_ledger_window(master, ac_code, ac_name, from_d, to_d, rows, opening):
    win = tk.Toplevel(master)
    win.title(f"Account Ledger Detail – {ac_code}")
    win.configure(bg="white")
    win.geometry("960x580")
    win.grab_set()

    # Report header
    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text="ACCOUNT LEDGER (DETAIL)", bg=GRID_HDR_BG, fg="white",
             font=("Arial", 11, "bold"), pady=6).pack()

    info = tk.Frame(win, bg="white")
    info.pack(fill="x", padx=10, pady=4)
    tk.Label(info, text=f"[ {ac_code} ]  {ac_name}",
             bg="white", fg=LABEL_FG, font=("Arial", 10, "bold")).pack(side="left")
    tk.Label(info, text=f"FROM: {from_d}    TO: {to_d}",
             bg="white", fg=LABEL_FG, font=FONT_NORMAL).pack(side="right")

    # Grid
    cols = [("dated","DATE",80), ("desc","DESCRIPTION",200),
            ("ref","REF",80), ("debit","DEBIT",100),
            ("credit","CREDIT",100), ("drcr","DR/CR",50),
            ("bal","BALANCE",110)]
    gf, tree = make_grid(win, cols, height=22)
    gf.pack(fill="both", expand=True, padx=10, pady=4)

    # Opening balance row
    balance = opening
    dr_cr = "DR" if balance >= 0 else "CR"
    tree.insert("", "end", values=(
        from_d, "OPENING BALANCE", "OPN",
        f"{balance:,.2f}", "", dr_cr, f"{abs(balance):,.2f}"
    ), tags=("odd",))

    for i, r in enumerate(rows):
        balance += r["debit"] - r["credit"]
        dr_cr = "DR" if balance >= 0 else "CR"
        tag = "even" if i % 2 else "odd"
        tree.insert("", "end", values=(
            r["dated"],
            r["description"] or r["ac_title"] or "",
            r["voucher_no"],
            f"{r['debit']:,.2f}" if r["debit"] else "",
            f"{r['credit']:,.2f}" if r["credit"] else "",
            dr_cr,
            f"{abs(balance):,.2f}"
        ), tags=(tag,))

    # Total row
    td = sum(r["debit"]  for r in rows)
    tc = sum(r["credit"] for r in rows)
    tk.Label(win,
             text=f"Total Debit: {td:,.2f}    Total Credit: {tc:,.2f}    "
                  f"Closing Balance: {abs(balance):,.2f} {'DR' if balance>=0 else 'CR'}",
             bg=STATUS_BG, fg=LABEL_FG, font=FONT_BOLD).pack(
        fill="x", side="bottom", padx=8, pady=2)
    tk.Button(win, text="Close", bg=BTN_BG, font=FONT_NORMAL,
              relief="raised", command=win.destroy).pack(side="bottom", pady=4)
    tk.Frame(win, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")


# ── Daily General Transactions / DGT ──────────────────────────────────────────

def open_daily_transactions(master, username="ADMIN"):
    dlg = DateRangeDialog(master, "Daily General Transactions", show_period=False)
    if not dlg.result:
        return
    from_d, _ = dlg.result
    rows = db.get_daily_general_transactions(from_d)
    cols = [("dated","Date",80),("vno","Voucher#",70),("ac_code","A/C Code",70),
            ("ac_title","A/C Title",180),("debit","Debit",90),("credit","Credit",90),
            ("desc","Description",150)]
    data = [(r["dated"], r["voucher_no"], r["ac_code"], r["ac_title"],
             f"{r['debit']:,.2f}", f"{r['credit']:,.2f}", r["description"] or "")
            for r in rows]
    td = sum(r["debit"]  for r in rows)
    tc = sum(r["credit"] for r in rows)
    _report_window(master, "Daily General Transactions / DGT",
                   "DAILY GENERAL TRANSACTIONS", cols, data,
                   f"Total Debit: {td:,.2f}    Total Credit: {tc:,.2f}")


# ── Trial Balance / TB ────────────────────────────────────────────────────────

def open_trial_balance(master, username="ADMIN"):
    rows = db.get_trial_balance()
    cols = [("ac_code","A/C Code",80), ("ac_name","Account Name",220),
            ("opening","Opening",90), ("total_debit","Total Debit",100),
            ("total_credit","Total Credit",100), ("balance","Balance",100)]
    data = [(r["ac_code"], r["ac_name"],
             f"{r['opening']:,.2f}", f"{r['total_debit']:,.2f}",
             f"{r['total_credit']:,.2f}", f"{r['balance']:,.2f}")
            for r in rows]
    td = sum(r["total_debit"]   for r in rows)
    tc = sum(r["total_credit"]  for r in rows)
    _report_window(master, "Trial Balance / TB",
                   "TRIAL BALANCE", cols, data,
                   f"Total Debit: {td:,.2f}    Total Credit: {tc:,.2f}")


# ── Balance Sheet ─────────────────────────────────────────────────────────────

def open_balance_sheet(master, username="ADMIN"):
    rows = db.get_trial_balance()
    assets  = [r for r in rows if (r["ac_code"] or "").startswith("1")]
    liabs   = [r for r in rows if (r["ac_code"] or "").startswith("2")]
    equity  = [r for r in rows if (r["ac_code"] or "").startswith("3")]

    total_assets  = sum(r["balance"] for r in assets)
    total_liabs   = sum(r["balance"] for r in liabs)
    total_equity  = sum(r["balance"] for r in equity)

    win = tk.Toplevel(master)
    win.title("Balance Sheet")
    win.configure(bg="white")
    win.geometry("800x560")
    win.grab_set()

    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text="BALANCE SHEET", bg=GRID_HDR_BG, fg="white",
             font=("Arial", 12, "bold"), pady=8).pack()
    tk.Label(hdr, text=f"As at {date.today().strftime('%d/%m/%Y')}",
             bg=GRID_HDR_BG, fg="white", font=FONT_NORMAL).pack()

    body = tk.Frame(win, bg="white")
    body.pack(fill="both", expand=True, padx=10, pady=10)

    # Two columns: Assets | Liabilities + Equity
    left  = tk.Frame(body, bg="white")
    right = tk.Frame(body, bg="white")
    left.pack(side="left",  fill="both", expand=True, padx=4)
    right.pack(side="right", fill="both", expand=True, padx=4)

    def section(frame, title, items, total):
        tk.Label(frame, text=title, bg="white", fg=LABEL_FG,
                 font=FONT_BOLD, anchor="w").pack(fill="x", pady=(8,2))
        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x")
        for r in items:
            row_f = tk.Frame(frame, bg="white")
            row_f.pack(fill="x")
            tk.Label(row_f, text=f"  {r['ac_code']} {r['ac_name']}",
                     bg="white", fg="black", font=FONT_SMALL,
                     anchor="w").pack(side="left")
            tk.Label(row_f, text=f"{r['balance']:,.2f}",
                     bg="white", fg="black", font=FONT_SMALL,
                     anchor="e").pack(side="right")
        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x", pady=2)
        tot_f = tk.Frame(frame, bg="white")
        tot_f.pack(fill="x")
        tk.Label(tot_f, text=f"Total {title}",
                 bg="white", fg=LABEL_FG, font=FONT_BOLD, anchor="w").pack(side="left")
        tk.Label(tot_f, text=f"{total:,.2f}",
                 bg="white", fg=LABEL_FG, font=FONT_BOLD, anchor="e").pack(side="right")

    section(left,  "ASSETS",     assets,  total_assets)
    section(right, "LIABILITIES", liabs,   total_liabs)
    section(right, "EQUITY",      equity,  total_equity)

    tk.Label(win, text=f"Total Liabilities + Equity: {total_liabs+total_equity:,.2f}",
             bg=STATUS_BG, fg=LABEL_FG, font=FONT_BOLD).pack(
        fill="x", side="bottom", padx=8, pady=2)
    tk.Button(win, text="Close", bg=BTN_BG, font=FONT_NORMAL,
              relief="raised", command=win.destroy).pack(side="bottom", pady=4)
    tk.Frame(win, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")


# ── Profit & Loss Statement ───────────────────────────────────────────────────

def open_profit_loss(master, username="ADMIN"):
    rows = db.get_trial_balance()
    income   = [r for r in rows if (r["ac_code"] or "").startswith("4")]
    expenses = [r for r in rows if (r["ac_code"] or "").startswith("5")]

    total_income   = sum(r["total_credit"] for r in income)
    total_expenses = sum(r["total_debit"]  for r in expenses)
    net = total_income - total_expenses

    win = tk.Toplevel(master)
    win.title("Profit & Loss Statement")
    win.configure(bg="white")
    win.geometry("700x500")
    win.grab_set()

    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text="PROFIT & LOSS STATEMENT", bg=GRID_HDR_BG, fg="white",
             font=("Arial", 12, "bold"), pady=8).pack()
    tk.Label(hdr, text=f"Period ending {date.today().strftime('%d/%m/%Y')}",
             bg=GRID_HDR_BG, fg="white", font=FONT_NORMAL).pack()

    body = tk.Frame(win, bg="white", padx=20)
    body.pack(fill="both", expand=True, pady=10)

    def section(title, items, total, is_income=True):
        tk.Label(body, text=title, bg="white", fg=LABEL_FG,
                 font=FONT_BOLD, anchor="w").pack(fill="x", pady=(10,2))
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x")
        for r in items:
            v = r["total_credit"] if is_income else r["total_debit"]
            row_f = tk.Frame(body, bg="white")
            row_f.pack(fill="x")
            tk.Label(row_f, text=f"  {r['ac_code']} {r['ac_name']}",
                     bg="white", fg="black", font=FONT_SMALL, anchor="w").pack(side="left")
            tk.Label(row_f, text=f"{v:,.2f}", bg="white", fg="black",
                     font=FONT_SMALL, anchor="e").pack(side="right")
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=2)
        tot_f = tk.Frame(body, bg="white")
        tot_f.pack(fill="x")
        tk.Label(tot_f, text=f"Total {title}", bg="white", fg=LABEL_FG,
                 font=FONT_BOLD, anchor="w").pack(side="left")
        tk.Label(tot_f, text=f"{total:,.2f}", bg="white", fg=LABEL_FG,
                 font=FONT_BOLD, anchor="e").pack(side="right")

    section("INCOME / REVENUE", income,   total_income,   is_income=True)
    section("EXPENSES",          expenses, total_expenses, is_income=False)

    # Net profit/loss
    color = "#006600" if net >= 0 else "#990000"
    lbl   = "NET PROFIT" if net >= 0 else "NET LOSS"
    tk.Frame(body, bg=GRID_HDR_BG, height=2).pack(fill="x", pady=4)
    nf = tk.Frame(body, bg="white")
    nf.pack(fill="x")
    tk.Label(nf, text=lbl, bg="white", fg=color,
             font=("Arial", 10, "bold"), anchor="w").pack(side="left")
    tk.Label(nf, text=f"{abs(net):,.2f}", bg="white", fg=color,
             font=("Arial", 10, "bold"), anchor="e").pack(side="right")

    tk.Button(win, text="Close", bg=BTN_BG, font=FONT_NORMAL,
              relief="raised", command=win.destroy).pack(side="bottom", pady=4)
    tk.Frame(win, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")


# ── Screen Ledger / SCR_LGR ───────────────────────────────────────────────────

def open_screen_ledger(master, username="ADMIN"):
    win = tk.Toplevel(master)
    win.title("Screen Ledger / SCR_LGR")
    win.configure(bg=BG)
    win.geometry("900x520")
    win.grab_set()

    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text="Screen Ledger / SCR_LGR", bg=GRID_HDR_BG, fg="white",
             font=FONT_TITLE, pady=6).pack(side="left", padx=10)

    ff = tk.Frame(win, bg=BG, pady=6)
    ff.pack(fill="x", padx=10)
    tk.Label(ff, text="A/C Code:", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
    ac_var = tk.StringVar()
    ac_e = tk.Entry(ff, textvariable=ac_var, width=12, bg=ENTRY_BG,
                    font=FONT_NORMAL, relief="sunken", bd=2)
    ac_e.pack(side="left", padx=4)
    tk.Label(ff, text="From:", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
    fr_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
    tk.Entry(ff, textvariable=fr_var, width=12, bg=ENTRY_BG,
             font=FONT_NORMAL, relief="sunken", bd=2).pack(side="left", padx=4)
    tk.Label(ff, text="To:", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
    to_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
    tk.Entry(ff, textvariable=to_var, width=12, bg=ENTRY_BG,
             font=FONT_NORMAL, relief="sunken", bd=2).pack(side="left", padx=4)

    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=6, pady=4)
    cols = [("dated","Date",80),("vno","Voucher#",70),("ac_code","A/C Code",70),
            ("ac_title","A/C Title",180),("debit","Debit",90),("credit","Credit",90)]
    gf, tree = make_grid(body, cols, height=18)
    gf.pack(fill="both", expand=True)

    status_var = tk.StringVar(value="Enter criteria and click Show")
    tk.Label(win, textvariable=status_var, bg=STATUS_BG, fg=LABEL_FG,
             font=FONT_SMALL).pack(fill="x", side="bottom", padx=4)
    tk.Frame(win, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")

    def show():
        try:
            from datetime import datetime
            fd = datetime.strptime(fr_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            td = datetime.strptime(to_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=win); return
        rows2 = db.get_general_ledger(fd, td)
        ac = ac_var.get().strip()
        if ac:
            rows2 = [r for r in rows2 if r["ac_code"] == ac]
        tree.delete(*tree.get_children())
        tot_d = tot_c = 0.0
        for i, r in enumerate(rows2):
            tag = "odd" if i % 2 else "even"
            tree.insert("", "end", values=(
                r["dated"], r["voucher_no"], r["ac_code"], r["ac_title"],
                f"{r['debit']:,.2f}", f"{r['credit']:,.2f}"
            ), tags=(tag,))
            tot_d += r["debit"]; tot_c += r["credit"]
        status_var.set(f"Records: {len(rows2)}    "
                       f"Total Debit: {tot_d:,.2f}    Total Credit: {tot_c:,.2f}")

    ac_e.bind("<F9>", lambda e: _f9_ac(ac_var, win))
    tk.Button(ff, text="Show",  bg=BTN_BG, font=FONT_NORMAL,
              relief="raised", command=show).pack(side="left", padx=8)
    tk.Button(ff, text="Close", bg=BTN_BG, font=FONT_NORMAL,
              relief="raised", command=win.destroy).pack(side="left", padx=4)


def _f9_ac(ac_var, parent):
    dlg = AccountLOVDialog(parent, ac_var.get())
    if dlg.result:
        ac_var.set(dlg.result[0])


# ── Generic report window ─────────────────────────────────────────────────────

def _report_window(master, title, sidebar_text, columns, rows, totals=None):
    win = tk.Toplevel(master)
    win.title(title)
    win.configure(bg=BG)
    win.geometry("940x560")
    win.grab_set()

    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text=title, bg=GRID_HDR_BG, fg="white",
             font=FONT_TITLE, pady=6).pack(side="left", padx=10)
    tk.Button(hdr, text="Close", bg=BTN_BG, font=FONT_SMALL,
              relief="raised", command=win.destroy).pack(side="right", padx=10, pady=4)

    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=6, pady=6)

    sb = tk.Frame(body, bg=SIDEBAR_BG, width=28)
    sb.pack(side="left", fill="y")
    sb.pack_propagate(False)
    tk.Label(sb, text="\n".join(sidebar_text), bg=SIDEBAR_BG, fg=SIDEBAR_FG,
             font=FONT_SIDEBAR).pack(expand=True)

    gf, tree = make_grid(body, columns, height=24)
    gf.pack(side="left", fill="both", expand=True)

    for i, r in enumerate(rows):
        tag = "odd" if i % 2 else "even"
        tree.insert("", "end", values=r, tags=(tag,))

    if totals:
        tk.Label(win, text=totals, bg=STATUS_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(fill="x", side="bottom", padx=8, pady=2)
    tk.Frame(win, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")
