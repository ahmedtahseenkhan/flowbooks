"""
Inventory Reports: ISR, ILR, IAR, DDIT, DITS, IWAA
All dialogs match design images exactly.
"""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import DateRangeDialog, make_grid, InventoryLOVDialog, lov_button
import database as db
from datetime import date


# ── Inventory Stock Report / ISR ───────────────────────────────────────────────

def open_inventory_stock(master):
    dlg = DateRangeDialog(master, "Inventory Stock Report Parameters", show_period=False)
    if not dlg.result:
        return
    dated, _ = dlg.result
    rows = db.get_inventory_stock(dated)
    cols = [("code","Code",70),("name","Item Name",200),("unit","Unit",50),
            ("qty","Quantity",80),("rate","Pur Rate",80),
            ("stock_val","Stock Value",100),("ledger_val","Ledger Value",100)]
    data = [(r["code"], r["name"], r["unit"] or "",
             f"{r['quantity']:,.2f}", f"{r['last_purchase_rate']:,.2f}",
             f"{r['stock_value']:,.2f}", f"{r['value']:,.2f}") for r in rows]
    total_sv = sum(r["stock_value"] for r in rows)
    total_lv = sum(r["value"] for r in rows)
    _inv_report_window(master, "Inventory Stock Report / ISR",
                       "INVENTORY STOCK REPORT", cols, data,
                       f"Total Stock Value: {total_sv:,.2f}    "
                       f"Total Ledger Value: {total_lv:,.2f}")


# ── Inventory Ledger Reports / ILR ────────────────────────────────────────────

def open_inventory_ledger(master):
    """Dialog matches design: COMBINED/QUANTITATIVE/ON VALUE + Inventory filter."""
    dlg = _ILRDialog(master)
    if not dlg.result:
        return
    from_d, to_d, inv_code, inv_name, report_type = dlg.result
    rows = db.get_inventory_ledger(from_d, to_d, inv_code or None)

    if report_type == "combined":
        _show_inv_ledger_combined(master, rows, from_d, to_d, inv_code, inv_name)
    else:
        _show_inv_ledger_simple(master, rows, from_d, to_d, report_type)


def _show_inv_ledger_combined(master, rows, from_d, to_d, inv_code, inv_name):
    """Running balance ledger – matches acd:Previewer design image."""
    win = tk.Toplevel(master)
    win.title("Inventory Ledger / ILR")
    win.configure(bg="white")
    win.geometry("1000x560")
    win.grab_set()

    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text="INVENTORY LEDGER", bg=GRID_HDR_BG, fg="white",
             font=("Arial", 11, "bold"), pady=6).pack(side="left", padx=10)
    info_txt = f"FROM: {from_d}    TO: {to_d}"
    if inv_code:
        info_txt = f"[ {inv_code} ] {inv_name}    {info_txt}"
    tk.Label(hdr, text=info_txt, bg=GRID_HDR_BG, fg="white",
             font=FONT_NORMAL, pady=6).pack(side="right", padx=10)

    # Sub-header: column groups
    sub = tk.Frame(win, bg="#4A6080")
    sub.pack(fill="x")
    for txt, w in [("DATE/ACCOUNT INFO/NARRATION", 280), ("VR REF", 80),
                   ("TRANSACTION DETAILS", 220), ("RUNNING BALANCE", 220)]:
        tk.Label(sub, text=txt, bg="#4A6080", fg="white",
                 font=FONT_GRID_H, width=w//8, anchor="center").pack(side="left", padx=2)

    cols = [("dated","DATE",80), ("acct","ACCOUNT INFO",160),
            ("ref","VR REF",80), ("t_qty","QTY",70), ("t_rate","RATE",60),
            ("t_val","VALUE",90), ("r_qty","QTY",70), ("r_rate","RATE",60),
            ("r_val","VALUE",90)]
    gf, tree = make_grid(win, cols, height=20)
    gf.pack(fill="both", expand=True, padx=6, pady=4)

    run_qty = 0.0; run_val = 0.0
    for i, r in enumerate(rows):
        qty  = r["quantity"] if r["type"] == "PURCHASE" else -r["quantity"]
        val  = r["value"]    if r["type"] == "PURCHASE" else -r["value"]
        run_qty += qty; run_val += val
        run_rate = run_val / run_qty if run_qty else 0
        tag = "odd" if i % 2 else "even"
        tree.insert("", "end", values=(
            r["dated"],
            f"[{r['inv_code']}] {r['inventory_name'][:18]}",
            r["invoice_no"],
            f"{r['quantity']:,.2f}", f"{r['rate']:,.4f}", f"{r['value']:,.2f}",
            f"{abs(run_qty):,.2f}", f"{abs(run_rate):,.4f}", f"{abs(run_val):,.2f}"
        ), tags=(tag,))

    tk.Button(win, text="Close", bg=BTN_BG, font=FONT_NORMAL,
              relief="raised", command=win.destroy).pack(side="bottom", pady=4)
    tk.Frame(win, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")


def _show_inv_ledger_simple(master, rows, from_d, to_d, report_type):
    cols = [("code","Inv Code",70),("name","Item Name",160),("dated","Date",90),
            ("inv_no","Ref#",80),("type","Type",70),
            ("qty","Quantity",80),("rate","Rate",80),("value","Value",90)]
    data = [(r["inv_code"], r["inventory_name"], r["dated"], r["invoice_no"],
             r["type"], f"{r['quantity']:,.2f}", f"{r['rate']:,.2f}", f"{r['value']:,.2f}")
            for r in rows]
    _inv_report_window(master, "Inventory Ledger Reports / ILR",
                       "INVENTORY LEDGER REPORTS", cols, data)


class _ILRDialog(tk.Toplevel):
    """Inventory Ledger Report Parameters – matches design exactly."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Inventory Ledger Report / ILR")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.result = None
        self.grab_set()

        from datetime import date as _date
        today = _date.today()

        hdr = tk.Frame(self, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Inventory Ledger Report Parameters",
                 bg=GRID_HDR_BG, fg="white",
                 font=("Arial", 11, "bold"), pady=8).pack()

        body = tk.Frame(self, bg=BG, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        # Period radio
        self._period = tk.StringVar(value="year")
        pr = tk.Frame(body, bg=BG)
        pr.pack(fill="x", pady=4)
        for v, t in [("month","Current Month"), ("year","Current Year"),
                     ("prev","Previous Year"), ("define","Define")]:
            tk.Radiobutton(pr, text=t, variable=self._period, value=v,
                           bg=BG, fg=LABEL_FG, font=FONT_NORMAL,
                           command=self._on_period).pack(side="left", padx=4)

        # Report type group
        rt_grp = tk.LabelFrame(body, text="Reports", bg=BG, fg=LABEL_FG,
                               font=FONT_BOLD, bd=2, relief="groove")
        rt_grp.pack(anchor="w", padx=10, pady=6)
        self._rtype = tk.StringVar(value="combined")
        for v, t in [("combined","COMBINED"),
                     ("quantitative","QUANTITATIVE"),
                     ("value","ON VALUE")]:
            tk.Radiobutton(rt_grp, text=t, variable=self._rtype, value=v,
                           bg=BG, fg=LABEL_FG, font=FONT_NORMAL).pack(anchor="w", padx=10)

        # Date range
        df = tk.Frame(body, bg=BG)
        df.pack(fill="x", pady=4)
        cur_year = today.year
        self._from_var = tk.StringVar(
            value=f"01/07/{cur_year-1}" if today.month < 7 else f"01/07/{cur_year}")
        self._to_var   = tk.StringVar(
            value=f"30/06/{cur_year}"   if today.month < 7 else f"30/06/{cur_year+1}")

        tk.Label(df, text="From", bg=BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=6, anchor="e").grid(row=0, column=0, padx=4, pady=4)
        tk.Entry(df, textvariable=self._from_var, width=14,
                 bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2).grid(
            row=0, column=1, padx=4, pady=4)
        tk.Label(df, text="DD/MM/YYYY", bg=BG, fg=LABEL_FG,
                 font=("Arial",7)).grid(row=0, column=2, sticky="w")

        tk.Label(df, text="To", bg=BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=6, anchor="e").grid(row=1, column=0, padx=4, pady=4)
        tk.Entry(df, textvariable=self._to_var, width=14,
                 bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2).grid(
            row=1, column=1, padx=4, pady=4)
        tk.Label(df, text="DD/MM/YYYY", bg=BG, fg=LABEL_FG,
                 font=("Arial",7)).grid(row=1, column=2, sticky="w")

        # Inventory filter
        inv_f = tk.Frame(body, bg=BG)
        inv_f.pack(fill="x", pady=6)
        tk.Label(inv_f, text="Inventory", bg=BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="left")
        self._inv_code_var = tk.StringVar()
        ic_e = tk.Entry(inv_f, textvariable=self._inv_code_var, width=10,
                        bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        ic_e.pack(side="left", padx=(6, 1))
        lov_button(inv_f, self._f9_inv).pack(side="left", padx=(0, 6))
        self._inv_name_var = tk.StringVar()
        tk.Entry(inv_f, textvariable=self._inv_name_var, width=28,
                 bg="#E8E8E8", font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).pack(side="left", padx=4)
        ic_e.bind("<F9>", self._f9_inv)
        ic_e.bind("<FocusOut>", self._lookup_inv)

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

    def _on_period(self):
        from datetime import date as _date
        today = _date.today()
        p = self._period.get()
        if p == "month":
            self._from_var.set(today.replace(day=1).strftime("%d/%m/%Y"))
            self._to_var.set(today.strftime("%d/%m/%Y"))
        elif p == "year":
            yr = today.year
            self._from_var.set(f"01/07/{yr-1}" if today.month < 7 else f"01/07/{yr}")
            self._to_var.set(f"30/06/{yr}"     if today.month < 7 else f"30/06/{yr+1}")
        elif p == "prev":
            yr = today.year - 1
            self._from_var.set(f"01/07/{yr-1}")
            self._to_var.set(f"30/06/{yr}")

    def _f9_inv(self, _event=None):
        dlg = InventoryLOVDialog(self, self._inv_code_var.get())
        if dlg.result:
            self._inv_code_var.set(dlg.result[0])
            self._inv_name_var.set(dlg.result[1])

    def _lookup_inv(self, _):
        code = self._inv_code_var.get().strip()
        if code:
            item = db.get_inventory_item(code)
            if item:
                self._inv_name_var.set(item["name"])

    def _ok(self):
        try:
            from datetime import datetime
            fd = datetime.strptime(self._from_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            td = datetime.strptime(self._to_var.get(),   "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self); return
        self.result = (fd, td,
                       self._inv_code_var.get().strip(),
                       self._inv_name_var.get(),
                       self._rtype.get())
        self.destroy()


# ── Inventory Activity Report / IAR ───────────────────────────────────────────

def open_inventory_activity(master):
    dlg = DateRangeDialog(master, "Inventory Activity Report")
    if not dlg.result:
        return
    from_d, to_d = dlg.result
    rows = db.get_inventory_ledger(from_d, to_d)
    summary = {}
    for r in rows:
        k = r["inv_code"]
        if k not in summary:
            summary[k] = {"name": r["inventory_name"], "purchases": 0.0,
                          "sales": 0.0, "value": 0.0}
        if r["type"] == "PURCHASE":
            summary[k]["purchases"] += r["quantity"]
        else:
            summary[k]["sales"] += r["quantity"]
        summary[k]["value"] += r["value"]
    cols = [("code","Inv Code",70),("name","Item Name",200),
            ("purchases","Purchases",90),("sales","Sales",90),
            ("net","Net Qty",90),("value","Value",100)]
    data = [(k, v["name"],
             f"{v['purchases']:,.2f}", f"{v['sales']:,.2f}",
             f"{v['purchases']-v['sales']:,.2f}", f"{v['value']:,.2f}")
            for k, v in sorted(summary.items())]
    _inv_report_window(master, "Inventory Activity Report / IAR",
                       "INVENTORY ACTIVITY REPORT", cols, data)


# ── Inv. Wise Account Activity / IWAA ─────────────────────────────────────────

def open_inv_wise_account(master):
    dlg = DateRangeDialog(master, "Inv. Wise Account Activity")
    if not dlg.result:
        return
    from_d, to_d = dlg.result
    rows = db.get_inventory_ledger(from_d, to_d)
    cols = [("code","Inv Code",70),("name","Item Name",160),("dated","Date",90),
            ("inv_no","Invoice#",80),("type","Type",70),
            ("qty","Qty",70),("value","Value",90)]
    data = [(r["inv_code"], r["inventory_name"], r["dated"], r["invoice_no"],
             r["type"], f"{r['quantity']:,.2f}", f"{r['value']:,.2f}")
            for r in rows]
    _inv_report_window(master, "Inv. Wise Account Activity / IWAA",
                       "INV WISE ACCOUNT ACTIVITY", cols, data)


# ── Daily Detail Inv Transactions / DDIT ──────────────────────────────────────

def open_daily_detail_inv(master):
    dlg = DateRangeDialog(master, "Daily Detail Inv Transactions", show_period=False)
    if not dlg.result:
        return
    from_d, _ = dlg.result
    rows = db.get_inventory_ledger(from_d, from_d)
    cols = [("code","Inv Code",70),("name","Item Name",160),
            ("inv_no","Invoice#",80),("type","Type",70),
            ("qty","Quantity",80),("rate","Rate",80),("value","Value",90)]
    data = [(r["inv_code"], r["inventory_name"], r["invoice_no"],
             r["type"], f"{r['quantity']:,.2f}",
             f"{r['rate']:,.2f}", f"{r['value']:,.2f}") for r in rows]
    _inv_report_window(master, "Daily Detail Inv Transactions / DDIT",
                       "DAILY DETAIL INV TRANSACTIONS", cols, data)


# ── Daily Inv Transactions Summary / DITS ─────────────────────────────────────

def open_daily_inv_summary(master):
    dlg = DateRangeDialog(master, "Daily Inv Transactions Summary", show_period=False)
    if not dlg.result:
        return
    from_d, _ = dlg.result
    rows = db.get_inventory_ledger(from_d, from_d)
    summary = {}
    for r in rows:
        k = r["inv_code"]
        if k not in summary:
            summary[k] = {"name": r["inventory_name"], "qty_in": 0.0,
                          "qty_out": 0.0, "value": 0.0}
        if r["type"] == "PURCHASE":
            summary[k]["qty_in"] += r["quantity"]
        else:
            summary[k]["qty_out"] += r["quantity"]
        summary[k]["value"] += r["value"]
    cols = [("code","Inv Code",70),("name","Item Name",200),
            ("in","Qty In",80),("out","Qty Out",80),
            ("net","Net",80),("value","Value",100)]
    data = [(k, v["name"],
             f"{v['qty_in']:,.2f}", f"{v['qty_out']:,.2f}",
             f"{v['qty_in']-v['qty_out']:,.2f}", f"{v['value']:,.2f}")
            for k, v in sorted(summary.items())]
    _inv_report_window(master, "Daily Inv Transactions Smry / DITS",
                       "DAILY INV TRANSACTIONS SUMMARY", cols, data)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _inv_report_window(master, title, sidebar_text, columns, rows, totals=None):
    win = tk.Toplevel(master)
    win.title(title)
    win.configure(bg=BG)
    win.geometry("940x520")
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

    gf, tree = make_grid(body, columns, height=22)
    gf.pack(side="left", fill="both", expand=True)

    for i, r in enumerate(rows):
        tag = "odd" if i % 2 else "even"
        tree.insert("", "end", values=r, tags=(tag,))

    if totals:
        tk.Label(win, text=totals, bg=STATUS_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(fill="x", side="bottom", padx=8, pady=2)
    tk.Frame(win, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")
