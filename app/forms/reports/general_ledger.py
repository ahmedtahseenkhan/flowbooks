"""General Ledger Report / GLR  and related report windows."""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import DateRangeDialog, make_grid
import database as db
from datetime import date


def _report_window(master, title, sidebar_text, columns, rows, totals=None):
    """Generic read-only report viewer."""
    win = tk.Toplevel(master)
    win.title(title)
    win.configure(bg=BG)
    win.geometry("900x560")

    # Header bar
    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text=title, bg=GRID_HDR_BG, fg="white",
             font=FONT_TITLE, pady=6).pack(side="left", padx=10)
    tk.Button(hdr, text="Close", bg=BTN_BG, font=FONT_SMALL, relief="raised",
              command=win.destroy).pack(side="right", padx=10, pady=4)

    # Body
    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=6, pady=6)

    # Sidebar
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

    tk.Frame(win, bg=BOTTOM_BAR, height=6).pack(fill="x", side="bottom")
    win.grab_set()


# ── General Ledger Report ─────────────────────────────────────────────────────

def open_general_ledger(master, username="ADMIN"):
    dlg = DateRangeDialog(master, "General Transactions")
    if not dlg.result:
        return
    from_d, to_d = dlg.result
    rows = db.get_general_ledger(from_d, to_d)

    cols = [("dated","Date",90),("vno","Voucher#",80),("ac_code","A/C Code",80),
            ("ac_title","A/C Title",180),("debit","Debit",90),("credit","Credit",90),
            ("desc","Description",150)]
    data = [(r["dated"], r["voucher_no"], r["ac_code"], r["ac_title"],
             f"{r['debit']:,.2f}", f"{r['credit']:,.2f}", r["description"] or "")
            for r in rows]

    td = sum(r["debit"] for r in rows)
    tc = sum(r["credit"] for r in rows)
    totals = f"Total Debit: {td:,.2f}    Total Credit: {tc:,.2f}"

    _report_window(master, "General Ledger Report / GLR",
                   "GENERAL LEDGER REPORT", cols, data, totals)


# ── Daily General Transactions ─────────────────────────────────────────────────

def open_daily_transactions(master, username="ADMIN"):
    dlg = DateRangeDialog(master, "Daily General Transactions", show_period=False)
    if not dlg.result:
        return
    from_d, _ = dlg.result
    rows = db.get_daily_general_transactions(from_d)

    cols = [("dated","Date",90),("vno","Voucher#",80),("ac_code","A/C Code",80),
            ("ac_title","A/C Title",180),("debit","Debit",90),("credit","Credit",90),
            ("desc","Description",150)]
    data = [(r["dated"], r["voucher_no"], r["ac_code"], r["ac_title"],
             f"{r['debit']:,.2f}", f"{r['credit']:,.2f}", r["description"] or "")
            for r in rows]

    td = sum(r["debit"] for r in rows)
    tc = sum(r["credit"] for r in rows)
    totals = f"Total Debit: {td:,.2f}    Total Credit: {tc:,.2f}"
    _report_window(master, "Daily General Transactions / DGT",
                   "DAILY GENERAL TRANSACTIONS", cols, data, totals)


# ── Trial Balance ─────────────────────────────────────────────────────────────

def open_trial_balance(master, username="ADMIN"):
    rows = db.get_trial_balance()

    cols = [("ac_code","A/C Code",80),("ac_name","Account Name",200),
            ("opening","Opening",90),("total_debit","Total Debit",100),
            ("total_credit","Total Credit",100),("balance","Balance",100)]
    data = [(r["ac_code"], r["ac_name"],
             f"{r['opening']:,.2f}", f"{r['total_debit']:,.2f}",
             f"{r['total_credit']:,.2f}", f"{r['balance']:,.2f}")
            for r in rows]

    td = sum(r["total_debit"] for r in rows)
    tc = sum(r["total_credit"] for r in rows)
    totals = f"Total Debit: {td:,.2f}    Total Credit: {tc:,.2f}"
    _report_window(master, "Trial Balance / TB",
                   "TRIAL BALANCE", cols, data, totals)


# ── General Ledger Detail / Screen Ledger ─────────────────────────────────────

def open_screen_ledger(master, username="ADMIN"):
    """Detailed account activity filtered by account."""
    win = tk.Toplevel(master)
    win.title("Screen Ledger / SCR_LGR")
    win.configure(bg=BG)
    win.geometry("860x500")
    win.grab_set()

    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text="Screen Ledger / SCR_LGR", bg=GRID_HDR_BG, fg="white",
             font=FONT_TITLE, pady=6).pack(side="left", padx=10)

    filter_f = tk.Frame(win, bg=BG, pady=6)
    filter_f.pack(fill="x", padx=10)
    tk.Label(filter_f, text="A/C Code:", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
    ac_var = tk.StringVar()
    tk.Entry(filter_f, textvariable=ac_var, width=12, bg=ENTRY_BG,
             font=FONT_NORMAL, relief="sunken", bd=2).pack(side="left", padx=4)
    tk.Label(filter_f, text="From:", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
    fr_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
    tk.Entry(filter_f, textvariable=fr_var, width=12, bg=ENTRY_BG,
             font=FONT_NORMAL, relief="sunken", bd=2).pack(side="left", padx=4)
    tk.Label(filter_f, text="To:", bg=BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
    to_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
    tk.Entry(filter_f, textvariable=to_var, width=12, bg=ENTRY_BG,
             font=FONT_NORMAL, relief="sunken", bd=2).pack(side="left", padx=4)

    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=6, pady=4)
    cols = [("dated","Date",90),("vno","Voucher#",80),("ac_code","A/C Code",80),
            ("ac_title","A/C Title",180),("debit","Debit",90),("credit","Credit",90)]
    gf, tree = make_grid(body, cols, height=16)
    gf.pack(fill="both", expand=True)

    status_var = tk.StringVar(value="Enter criteria and click Show.")
    tk.Label(win, textvariable=status_var, bg=STATUS_BG, fg=LABEL_FG,
             font=FONT_SMALL).pack(fill="x", side="bottom", padx=4)
    tk.Frame(win, bg=BOTTOM_BAR, height=6).pack(fill="x", side="bottom")

    def show():
        try:
            from datetime import datetime
            fd = datetime.strptime(fr_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            td = datetime.strptime(to_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date","Use DD/MM/YYYY.", parent=win); return
        rows2 = db.get_general_ledger(fd, td)
        ac = ac_var.get().strip()
        if ac:
            rows2 = [r for r in rows2 if r["ac_code"] == ac]
        tree.delete(*tree.get_children())
        tot_d = tot_c = 0.0
        for i, r in enumerate(rows2):
            tag = "odd" if i % 2 else "even"
            tree.insert("", "end", values=(r["dated"], r["voucher_no"], r["ac_code"],
                                           r["ac_title"], f"{r['debit']:,.2f}", f"{r['credit']:,.2f}"
                                           ), tags=(tag,))
            tot_d += r["debit"]; tot_c += r["credit"]
        status_var.set(f"Records: {len(rows2)}    Total Debit: {tot_d:,.2f}    Total Credit: {tot_c:,.2f}")

    tk.Button(filter_f, text="Show", bg=BTN_BG, font=FONT_NORMAL, relief="raised",
              command=show).pack(side="left", padx=8)
    tk.Button(filter_f, text="Close", bg=BTN_BG, font=FONT_NORMAL, relief="raised",
              command=win.destroy).pack(side="left", padx=4)
