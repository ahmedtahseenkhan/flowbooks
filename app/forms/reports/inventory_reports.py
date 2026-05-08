"""Inventory Reports: ISR, ILR, IAR, DDIT, DITS, IWAA"""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import DateRangeDialog, make_grid
import database as db
from datetime import date


# ── Inventory Stock Report / ISR ───────────────────────────────────────────────

def open_inventory_stock(master):
    """Matches the 'Inventory Stock Report Parameters' dialog in the images."""
    dlg = DateRangeDialog(master, "Inventory Stock Report Parameters", show_period=False)
    if not dlg.result:
        return
    dated, _ = dlg.result
    rows = db.get_inventory_stock(dated)

    cols = [("code","Code",70),("name","Item Name",200),("unit","Unit",50),
            ("qty","Quantity",80),("rate","Pur Rate",80),("stock_val","Stock Value",100),
            ("ledger_val","Ledger Value",100)]
    data = [(r["code"], r["name"], r["unit"] or "",
             f"{r['quantity']:,.2f}", f"{r['last_purchase_rate']:,.2f}",
             f"{r['stock_value']:,.2f}", f"{r['value']:,.2f}")
            for r in rows]

    total_sv = sum(r["stock_value"] for r in rows)
    total_lv = sum(r["value"] for r in rows)
    totals = f"Total Stock Value: {total_sv:,.2f}    Total Ledger Value: {total_lv:,.2f}"

    _inv_report_window(master, "Inventory Stock Report / ISR",
                       "INVENTORY STOCK REPORT", cols, data, totals)


# ── Inventory Ledger Reports / ILR ────────────────────────────────────────────

def open_inventory_ledger(master):
    dlg = DateRangeDialog(master, "Inventory Ledger Report")
    if not dlg.result:
        return
    from_d, to_d = dlg.result
    rows = db.get_inventory_ledger(from_d, to_d)

    cols = [("code","Inv Code",70),("name","Item Name",160),("dated","Date",90),
            ("inv_no","Ref#",80),("type","Type",70),
            ("qty","Quantity",80),("rate","Rate",80),("value","Value",90)]
    data = [(r["inv_code"], r["inventory_name"], r["dated"], r["invoice_no"],
             r["type"], f"{r['quantity']:,.2f}", f"{r['rate']:,.2f}", f"{r['value']:,.2f}")
            for r in rows]

    _inv_report_window(master, "Inventory Ledger Reports / ILR",
                       "INVENTORY LEDGER REPORTS", cols, data)


# ── Inventory Activity Report / IAR ───────────────────────────────────────────

def open_inventory_activity(master):
    dlg = DateRangeDialog(master, "Inventory Activity Report")
    if not dlg.result:
        return
    from_d, to_d = dlg.result
    rows = db.get_inventory_ledger(from_d, to_d)

    # Group by inventory code
    summary = {}
    for r in rows:
        k = r["inv_code"]
        if k not in summary:
            summary[k] = {"name": r["inventory_name"], "purchases": 0.0, "sales": 0.0, "value": 0.0}
        if r["type"] == "PURCHASE":
            summary[k]["purchases"] += r["quantity"]
        else:
            summary[k]["sales"] += r["quantity"]
        summary[k]["value"] += r["value"]

    cols = [("code","Inv Code",70),("name","Item Name",200),
            ("purchases","Purchases",90),("sales","Sales",90),("net","Net Qty",90),("value","Value",100)]
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
            ("inv_no","Invoice#",80),("type","Type",70),("ac","A/C",80),
            ("qty","Qty",70),("value","Value",90)]
    data = [(r["inv_code"], r["inventory_name"], r["dated"], r["invoice_no"],
             r["type"], "", f"{r['quantity']:,.2f}", f"{r['value']:,.2f}")
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

    cols = [("code","Inv Code",70),("name","Item Name",160),("inv_no","Invoice#",80),
            ("type","Type",70),("qty","Quantity",80),("rate","Rate",80),("value","Value",90)]
    data = [(r["inv_code"], r["inventory_name"], r["invoice_no"],
             r["type"], f"{r['quantity']:,.2f}", f"{r['rate']:,.2f}", f"{r['value']:,.2f}")
            for r in rows]

    _inv_report_window(master, "Daily Detail Inv Transactions / DDIT",
                       "DAILY DETAIL INV TRANSACTIONS", cols, data)


# ── Daily Inv Transactions Summary / DITS ─────────────────────────────────────

def open_daily_inv_summary(master):
    dlg = DateRangeDialog(master, "Daily Inv Transactions Summary", show_period=False)
    if not dlg.result:
        return
    from_d, _ = dlg.result
    rows = db.get_inventory_ledger(from_d, from_d)

    # Summarise
    summary = {}
    for r in rows:
        k = r["inv_code"]
        if k not in summary:
            summary[k] = {"name": r["inventory_name"], "qty_in": 0.0, "qty_out": 0.0, "value": 0.0}
        if r["type"] == "PURCHASE":
            summary[k]["qty_in"] += r["quantity"]
        else:
            summary[k]["qty_out"] += r["quantity"]
        summary[k]["value"] += r["value"]

    cols = [("code","Inv Code",70),("name","Item Name",200),
            ("in","Qty In",80),("out","Qty Out",80),("net","Net",80),("value","Value",100)]
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
    win.geometry("900x520")
    win.grab_set()

    hdr = tk.Frame(win, bg=GRID_HDR_BG)
    hdr.pack(fill="x")
    tk.Label(hdr, text=title, bg=GRID_HDR_BG, fg="white",
             font=FONT_TITLE, pady=6).pack(side="left", padx=10)
    tk.Button(hdr, text="Close", bg=BTN_BG, font=FONT_SMALL, relief="raised",
              command=win.destroy).pack(side="right", padx=10, pady=4)

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

    tk.Frame(win, bg=BOTTOM_BAR, height=6).pack(fill="x", side="bottom")
