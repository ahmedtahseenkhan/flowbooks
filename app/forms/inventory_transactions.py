"""
All inventory transaction forms using InlineEntryGrid:
  • Opening Transactions Form / OTF  — inventory opening stock
  • Carry Transaction Form / CHF     — carry forward inventory
  • Currency Transaction Form / CTF  — currency/forex inventory
  • Value Adjustment Form / VAF      — manual value adjustment
  • Auto Value Adjustment / AVADJ    — revalue at current purchase rate
  • Value Addition/Deletion / VADF   — add or remove stock quantities

All forms are keyboard-driven (Tab navigates, F9 opens LOV, auto-calc).
"""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, InlineEntryGrid, make_grid, lov_button, \
    InventoryLOVDialog, AccountLOVDialog
import database as db
from datetime import date


# ─────────────────────────────────────────────────────────────────────────────
# Opening Transactions Form / OTF  (inventory opening stock)
# ─────────────────────────────────────────────────────────────────────────────

OTF_COLS = [
    {"id": "inv_code",  "header": "InvCode",        "width": 9,  "editable": True,  "align": "left"},
    {"id": "inv_name",  "header": "Inventory Name",  "width": 26, "editable": False, "align": "left"},
    {"id": "quantity",  "header": "Quantity",        "width": 11, "editable": True,  "align": "right"},
    {"id": "rate",      "header": "Rate",            "width": 11, "editable": True,  "align": "right"},
    {"id": "value",     "header": "Value",           "width": 12, "editable": False, "align": "right", "bold": True},
]


class OpeningTransactionsForm(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "OPENING TRANSACTIONS FORM / OTF",
                         "OPENING TRANSACTIONS FORM", username,
                         "Alt+A : Add    Alt+D : Delete    Alt+S : Save    "
                         "Alt+X : Exit    F9 : LOV")
        self.geometry("820x560")
        self._build_form()
        self._refresh_list()
        self._bind_keys()

    def _build_form(self):
        c = self.content

        # Date header
        hf = tk.Frame(c, bg=FORM_BG)
        hf.pack(fill="x", padx=10, pady=6)
        tk.Label(hf, text="Dated", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="left", padx=4)
        self._date_e = tk.Entry(hf, width=14, bg="#D0DCF0",
                                font=FONT_NORMAL, relief="sunken", bd=2)
        self._date_e.pack(side="left", padx=4)
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._date_e.bind("<Tab>", lambda e: (self._grid.focus_first(), "break")[1])

        tk.Label(hf, text="Description", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="left", padx=(16, 4))
        self._desc_e = tk.Entry(hf, width=36, bg=ENTRY_BG,
                                font=FONT_NORMAL, relief="sunken", bd=2)
        self._desc_e.pack(side="left", padx=4)
        self._desc_e.bind("<Tab>", lambda e: (self._grid.focus_first(), "break")[1])

        # Inline grid
        gh = tk.Frame(c, bg="#DDE4EE")
        gh.pack(fill="x", padx=10)
        tk.Label(gh, text="💡 InvCode: double-click or F9 to search",
                 bg="#DDE4EE", fg="#334466", font=("Arial", 8)).pack(side="left", padx=6, pady=2)
        lov_button(gh, self._open_inv_lov).pack(side="left", padx=4)
        self._grid = InlineEntryGrid(c, OTF_COLS, start_rows=10)
        self._grid.pack(fill="both", expand=True, padx=10, pady=2)
        self._grid.on_focus_out  = self._grid_fo
        self._grid.on_f9         = self._grid_f9
        self._grid.on_change     = self._grid_changed

        # Total
        tf = tk.Frame(c, bg=FORM_BG)
        tf.pack(fill="x", padx=10, pady=2)
        tk.Label(tf, text="Total Value", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="right", padx=4)
        self._total_var = tk.StringVar(value="")
        tk.Entry(tf, textvariable=self._total_var, width=16,
                 bg="#EEF4FF", fg="#000080", font=("Arial", 9, "bold"),
                 state="readonly", relief="sunken", bd=2,
                 justify="right").pack(side="right", padx=4)

        # Existing records list
        cols = [("inv_code","InvCode",80), ("inv_name","Inventory Name",200),
                ("qty","Quantity",90), ("rate","Rate",90),
                ("value","Value",100), ("dated","Date",90)]
        gf, self._tree = make_grid(c, cols, height=5)
        gf.pack(fill="x", padx=10, pady=4)
        self._tree.bind("<Delete>", lambda e: self._delete_selected())

    def _open_inv_lov(self):
        """Open inventory LOV for the focused/first grid row."""
        focused = self.focus_get()
        row_idx = 0
        for i, row in enumerate(self._grid._widgets):
            if focused in row.values():
                row_idx = i
                break
        self._grid_f9(row_idx, "inv_code",
                      self._grid.get_value(row_idx, "inv_code"))

    def _grid_fo(self, row_idx, col_id, value):
        if col_id == "inv_code" and value:
            item = db.get_inventory_item(value)
            if item:
                self._grid.set_value(row_idx, "inv_name", item["name"])
                if not self._grid.get_value(row_idx, "rate"):
                    self._grid.set_value(row_idx, "rate",
                                         f"{item['last_purchase_rate']:.2f}" if item["last_purchase_rate"] else "")
        elif col_id in ("quantity", "rate") and value:
            try:
                n = float(value.replace(",", ""))
                self._grid.set_value(row_idx, col_id, f"{n:,.2f}")
            except ValueError:
                pass
        qty  = _n(self._grid.get_value(row_idx, "quantity"))
        rate = _n(self._grid.get_value(row_idx, "rate"))
        if qty and rate:
            self._grid.set_value(row_idx, "value", f"{qty*rate:,.2f}")
        self._update_total()

    def _grid_f9(self, row_idx, col_id, value):
        if col_id == "inv_code":
            dlg = InventoryLOVDialog(self, value)
            if dlg.result:
                code, name, unit, rate = dlg.result
                self._grid.set_value(row_idx, "inv_code", code)
                self._grid.set_value(row_idx, "inv_name", name)
                if rate:
                    self._grid.set_value(row_idx, "rate", f"{rate:.2f}")
                self._grid._widgets[row_idx]["quantity"].focus_set()

    def _grid_changed(self, rows):
        self._update_total()

    def _update_total(self):
        rows  = self._grid.get_all_rows()
        total = sum(_n(r.get("value", 0)) for r in rows)
        self._total_var.set(f"{total:,.2f}" if total else "")

    def on_add(self):
        self._grid.reset()
        self._date_e.delete(0, "end")
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._desc_e.delete(0, "end")
        self._total_var.set("")
        self._date_e.focus_set()
        self._mode = "add"

    def on_save(self):
        dstr = self._date_e.get().strip()
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self)
            return
        rows = [r for r in self._grid.get_all_rows() if r.get("inv_code")]
        if not rows:
            messagebox.showwarning("Validation", "Enter at least one item.", parent=self)
            return
        for r in rows:
            db.save_opening_stock(
                r["inv_code"], r.get("inv_name", ""),
                _n(r.get("quantity", 0)), _n(r.get("rate", 0)),
                _n(r.get("value", 0)), dt)
        self._refresh_list()
        self._grid.reset()
        self._total_var.set("")
        self._mode = "view"
        messagebox.showinfo("Saved", f"Opening stock saved — {len(rows)} item(s).", parent=self)

    def on_delete(self):
        self._delete_selected()

    def _delete_selected(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Delete", "Select a record to delete.", parent=self)
            return
        vals = self._tree.item(sel[0])["values"]
        row_id  = int(self._tree.item(sel[0], "tags")[0])
        inv_code = str(vals[0])
        if messagebox.askyesno("Confirm", f"Delete opening stock for {inv_code}?", parent=self):
            db.delete_opening_stock(row_id, inv_code)
            self._refresh_list()

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_opening_stock()):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(i),
                              values=(r["inv_code"], r["inventory_name"],
                                      f"{r['quantity']:,.2f}", f"{r['rate']:,.2f}",
                                      f"{r['value']:,.2f}", r["dated"]),
                              tags=(str(r["id"]), tag))

    def on_ignore(self):
        self._grid.reset()
        self._total_var.set("")
        self._mode = "view"

    def _bind_keys(self):
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-x>", lambda e: self.on_exit())


# ─────────────────────────────────────────────────────────────────────────────
# Carry Transaction Form / CHF
# ─────────────────────────────────────────────────────────────────────────────

CHF_COLS = [
    {"id": "inv_code",  "header": "InvCode",        "width": 9,  "editable": True,  "align": "left"},
    {"id": "inv_name",  "header": "Inventory Name",  "width": 26, "editable": False, "align": "left"},
    {"id": "quantity",  "header": "Quantity",        "width": 11, "editable": True,  "align": "right"},
    {"id": "rate",      "header": "Rate",            "width": 11, "editable": True,  "align": "right"},
    {"id": "value",     "header": "Value",           "width": 12, "editable": False, "align": "right", "bold": True},
]


class CarryTransactionForm(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "CARRY TRANSACTION FORM / CHF",
                         "CARRY TRANSACTION FORM", username,
                         "Alt+A : Add    Alt+D : Delete    Alt+S : Save    "
                         "Alt+X : Exit    F9 : LOV")
        self.geometry("820x580")
        self._current = None
        self._build_form()
        self._refresh_list()
        self._bind_keys()

    def _build_form(self):
        c = self.content
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)
        tkw = dict(bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)

        hp = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hp.pack(fill="x", padx=10, pady=6)

        tk.Label(hp, text="Invoice #", **lkw).grid(row=0,column=0,sticky="e",padx=(8,2),pady=4)
        self._inv_e = tk.Entry(hp, width=12, **tkw)
        self._inv_e.grid(row=0,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hp, text="Dated", **lkw).grid(row=0,column=2,sticky="e",padx=(6,2),pady=4)
        self._dated_e = tk.Entry(hp, width=12, bg="#D0DCF0",
                                 font=FONT_NORMAL, relief="sunken", bd=2)
        self._dated_e.grid(row=0,column=3,sticky="w",padx=2,pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._dated_e.bind("<Tab>", lambda e: (self._grid.focus_first(), "break")[1])

        tk.Label(hp, text="Description", **lkw).grid(row=1,column=0,sticky="e",padx=(8,2),pady=4)
        self._desc_e = tk.Entry(hp, width=52, **tkw)
        self._desc_e.grid(row=1,column=1,columnspan=4,sticky="ew",padx=(2,8),pady=4)
        self._desc_e.bind("<Tab>", lambda e: (self._grid.focus_first(), "break")[1])

        gh = tk.Frame(c, bg="#DDE4EE")
        gh.pack(fill="x", padx=10)
        tk.Label(gh, text="💡 InvCode: double-click or F9 to search",
                 bg="#DDE4EE", fg="#334466", font=("Arial", 8)).pack(side="left", padx=6, pady=2)
        lov_button(gh, self._open_inv_lov).pack(side="left", padx=4)
        self._grid = InlineEntryGrid(c, CHF_COLS, start_rows=10)
        self._grid.pack(fill="both", expand=True, padx=10, pady=2)
        self._grid.on_focus_out = self._grid_fo
        self._grid.on_f9        = self._grid_f9
        self._grid.on_change    = lambda rows: self._update_total()

        tf = tk.Frame(c, bg=FORM_BG)
        tf.pack(fill="x", padx=10, pady=2)
        self._total_var = tk.StringVar(value="")
        tk.Label(tf, text="Total Value", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="right", padx=4)
        tk.Entry(tf, textvariable=self._total_var, width=16, bg="#EEF4FF",
                 fg="#000080", font=("Arial", 9, "bold"), state="readonly",
                 relief="sunken", bd=2, justify="right").pack(side="right", padx=4)

        cols = [("inv","Invoice#",80),("dated","Date",90),("desc","Description",200),("total","Total",90)]
        gf, self._prev = make_grid(c, cols, height=4)
        gf.pack(fill="x", padx=10, pady=4)
        self._prev.bind("<<TreeviewSelect>>", self._on_prev_sel)

        self._set_hdr("disabled")


    def _open_inv_lov(self):
        focused = self.focus_get()
        row_idx = 0
        for i, row in enumerate(self._grid._widgets):
            if focused in row.values():
                row_idx = i
                break
        self._grid_f9(row_idx, "inv_code",
                      self._grid.get_value(row_idx, "inv_code"))

    def _grid_fo(self, row_idx, col_id, value):
        if col_id == "inv_code" and value:
            item = db.get_inventory_item(value)
            if item:
                self._grid.set_value(row_idx, "inv_name", item["name"])
                if not self._grid.get_value(row_idx, "rate"):
                    self._grid.set_value(row_idx, "rate",
                                         f"{item['last_purchase_rate']:.2f}" if item["last_purchase_rate"] else "")
        elif col_id in ("quantity", "rate") and value:
            try:
                self._grid.set_value(row_idx, col_id, f"{float(value.replace(',','')):,.2f}")
            except ValueError:
                pass
        qty  = _n(self._grid.get_value(row_idx, "quantity"))
        rate = _n(self._grid.get_value(row_idx, "rate"))
        if qty and rate:
            self._grid.set_value(row_idx, "value", f"{qty*rate:,.2f}")
        self._update_total()

    def _grid_f9(self, row_idx, col_id, value):
        if col_id == "inv_code":
            dlg = InventoryLOVDialog(self, value)
            if dlg.result:
                code, name, unit, rate = dlg.result
                self._grid.set_value(row_idx, "inv_code", code)
                self._grid.set_value(row_idx, "inv_name", name)
                if rate:
                    self._grid.set_value(row_idx, "rate", f"{rate:.2f}")
                self._grid._widgets[row_idx]["quantity"].focus_set()

    def _update_total(self):
        total = sum(_n(r.get("value", 0)) for r in self._grid.get_all_rows())
        self._total_var.set(f"{total:,.2f}" if total else "")

    def on_add(self):
        self._current = None
        self._grid.reset()
        self._set_hdr("normal")
        self._inv_e.configure(state="normal")
        self._inv_e.delete(0, "end"); self._inv_e.insert(0, db.next_carry_no())
        self._inv_e.configure(state="readonly")
        self._dated_e.delete(0, "end")
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._desc_e.delete(0, "end")
        self._total_var.set("")
        self._dated_e.focus_set()
        self._mode = "add"

    def on_save(self):
        inv_no = self._inv_e.get().strip()
        dstr   = self._dated_e.get().strip()
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self); return
        rows = [r for r in self._grid.get_all_rows() if r.get("inv_code")]
        if not rows:
            messagebox.showwarning("Validation", "Add at least one line.", parent=self); return
        total = sum(_n(r.get("value", 0)) for r in rows)
        header = (inv_no, dt, self._desc_e.get().strip(), total)
        lines  = [(inv_no, r["inv_code"], r.get("inv_name",""),
                   _n(r.get("quantity",0)), _n(r.get("rate",0)), _n(r.get("value",0)))
                  for r in rows]
        db.save_carry(header, lines)
        self._current = inv_no
        self._refresh_list()
        self._set_hdr("disabled")
        self._mode = "view"
        messagebox.showinfo("Saved", f"CHF {inv_no} saved.", parent=self)

    def on_delete(self):
        if not self._current:
            messagebox.showwarning("Delete", "Select a record.", parent=self); return
        if messagebox.askyesno("Confirm", f"Delete {self._current}?", parent=self):
            db.delete_carry(self._current)
            self._current = None
            self._grid.reset()
            self._set_hdr("disabled")
            self._refresh_list()

    def on_ignore(self):
        if self._current:
            self._load(self._current)
        else:
            self._grid.reset()
            self._set_hdr("disabled")
        self._mode = "view"

    def _refresh_list(self):
        self._prev.delete(*self._prev.get_children())
        for i, r in enumerate(db.get_all_carry()):
            tag = "odd" if i % 2 else "even"
            self._prev.insert("", "end", iid=str(r["invoice_no"]), values=(
                r["invoice_no"], r["dated"], r["description"] or "",
                f"{r['total_value']:,.2f}"), tags=(tag,))

    def _on_prev_sel(self, _):
        sel = self._prev.selection()
        if not sel:
            return
        self._current = str(self._prev.item(sel[0])["values"][0])
        self._load(self._current)

    def _load(self, invoice_no):
        hdr, lines = db.get_carry(invoice_no)
        if not hdr:
            return
        self._set_hdr("normal")
        self._inv_e.configure(state="normal"); self._inv_e.delete(0,"end"); self._inv_e.insert(0, hdr["invoice_no"])
        self._inv_e.configure(state="readonly")
        self._dated_e.delete(0,"end")
        try:
            from datetime import datetime
            self._dated_e.insert(0, datetime.strptime(hdr["dated"],"%Y-%m-%d").strftime("%d/%m/%Y"))
        except Exception:
            self._dated_e.insert(0, hdr["dated"])
        self._desc_e.delete(0,"end"); self._desc_e.insert(0, hdr["description"] or "")
        self._set_hdr("disabled")
        row_data = [{"inv_code": r["inv_code"], "inv_name": r["inventory_name"],
                     "quantity": f"{r['quantity']:,.2f}", "rate": f"{r['rate']:,.2f}",
                     "value": f"{r['value']:,.2f}"} for r in lines]
        self._grid.load_rows(row_data)
        self._update_total()

    def _set_hdr(self, state):
        for e in [self._dated_e, self._desc_e]: e.configure(state=state)

    def _bind_keys(self):
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())


# ─────────────────────────────────────────────────────────────────────────────
# Value Adjustment Form / VAF + AVADJ + VADF
# ─────────────────────────────────────────────────────────────────────────────

class ValueAdjustmentForm(BaseForm):
    """Manual value adjustment (VAF) — change a stock item's value."""

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "VALUE ADJUSTMENT FORM / VAF",
                         "VALUE ADJUSTMENT FORM", username,
                         "Alt+A : Add    Alt+S : Save    Alt+X : Exit    F9 : LOV")
        self.geometry("800x520")
        self._build_form()
        self._refresh_list()
        self._bind_keys()

    def _build_form(self):
        c = self.content
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)

        hf = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hf.pack(fill="x", padx=10, pady=6)

        tk.Label(hf, text="Ref #",        **lkw).grid(row=0,column=0,sticky="e",padx=(8,2),pady=4)
        self._ref_e = tk.Entry(hf, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._ref_e.grid(row=0,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hf, text="Dated",        **lkw).grid(row=0,column=2,sticky="e",padx=(6,2),pady=4)
        self._dated_e = tk.Entry(hf, width=12, bg="#D0DCF0", font=FONT_NORMAL, relief="sunken", bd=2)
        self._dated_e.grid(row=0,column=3,sticky="w",padx=2,pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hf, text="Description",  **lkw).grid(row=1,column=0,sticky="e",padx=(8,2),pady=4)
        self._desc_e = tk.Entry(hf, width=50, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._desc_e.grid(row=1,column=1,columnspan=4,sticky="ew",padx=(2,8),pady=4)

        # Entry fields for one adjustment at a time
        ef = tk.Frame(c, bg=GROUP_BG, bd=1, relief="groove")
        ef.pack(fill="x", padx=10, pady=4)

        for col, (lbl, attr, w) in enumerate([
            ("Inv Code",  "_ec_code", 10), ("Inv Name",  "_ec_name", 24),
            ("Old Value", "_ec_old",  12), ("New Value", "_ec_new",  12),
        ]):
            tk.Label(ef, text=lbl, bg=GROUP_BG, fg=LABEL_FG, font=FONT_SMALL).grid(
                row=0, column=col*2, sticky="e", padx=(6,2), pady=4)
            e = tk.Entry(ef, width=w, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
            e.grid(row=0, column=col*2+1, sticky="w", padx=2, pady=4)
            setattr(self, attr, e)

        self._ec_code.bind("<F9>", self._f9)
        self._ec_code.bind("<FocusOut>", self._lookup)
        tk.Button(ef, text="Add Adjustment", bg=BTN_BG, font=FONT_SMALL,
                  relief="raised", bd=2, command=self._add_adj).grid(
            row=0, column=8, padx=8, pady=4)

        cols = [("inv_code","Inv Code",80),("inv_name","Inv Name",180),
                ("old","Old Value",100),("new","New Value",100),("adj","Adjustment",100),("dated","Date",90)]
        gf, self._tree = make_grid(c, cols, height=12)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<Delete>", lambda e: self._del_adj())

        self._set_hdr("disabled")

    def _f9(self, _):
        dlg = InventoryLOVDialog(self, self._ec_code.get())
        if dlg.result:
            self._ec_code.delete(0,"end"); self._ec_code.insert(0, dlg.result[0])
            self._ec_name.delete(0,"end"); self._ec_name.insert(0, dlg.result[1])
            item = db.get_inventory_item(dlg.result[0])
            if item:
                self._ec_old.delete(0,"end"); self._ec_old.insert(0, f"{item['value']:,.2f}")
            self._ec_new.focus_set()

    def _lookup(self, _):
        item = db.get_inventory_item(self._ec_code.get().strip())
        if item:
            self._ec_name.delete(0,"end"); self._ec_name.insert(0, item["name"])
            self._ec_old.delete(0,"end");  self._ec_old.insert(0, f"{item['value']:,.2f}")

    def _add_adj(self):
        code  = self._ec_code.get().strip()
        name  = self._ec_name.get().strip() or code
        dstr  = self._dated_e.get().strip()
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self); return
        try:
            old = _n(self._ec_old.get())
            new = _n(self._ec_new.get())
        except ValueError:
            messagebox.showwarning("Input", "Enter numeric values.", parent=self); return
        if not code:
            messagebox.showwarning("Input", "Inv Code required.", parent=self); return
        diff = new - old
        item = db.get_inventory_item(code)
        old_qty = item["quantity"] if item else 0
        db.save_value_adjustment(
            self._ref_e.get().strip() or f"VAF-{dt}", "VAF",
            code, name, old_qty, old_qty, old, new, dt,
            self._desc_e.get().strip())
        self._refresh_list()
        for e in [self._ec_code, self._ec_name, self._ec_old, self._ec_new]:
            e.delete(0,"end")
        self._ec_code.focus_set()

    def _del_adj(self):
        sel = self._tree.selection()
        if not sel:
            return
        tags = self._tree.item(sel[0], "tags")
        if tags:
            row_id  = int(tags[0])
            inv_code = str(self._tree.item(sel[0])["values"][0])
            if messagebox.askyesno("Confirm", "Delete this adjustment?", parent=self):
                db.delete_value_adjustment(row_id, inv_code)
                self._refresh_list()

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_value_adjustments("VAF")):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", tags=(str(r["id"]), tag),
                              values=(r["inv_code"], r["inventory_name"],
                                      f"{r['old_value']:,.2f}", f"{r['new_value']:,.2f}",
                                      f"{r['new_value']-r['old_value']:,.2f}", r["dated"]))

    def on_add(self):
        self._set_hdr("normal")
        self._ref_e.configure(state="normal"); self._ref_e.delete(0,"end")
        self._ref_e.insert(0, f"VAF-{date.today().strftime('%Y%m%d')}")
        self._dated_e.delete(0,"end"); self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._desc_e.delete(0,"end")
        self._ec_code.focus_set()
        self._mode = "add"

    def on_save(self):
        self._set_hdr("disabled"); self._mode = "view"

    def on_ignore(self):
        self._set_hdr("disabled"); self._mode = "view"

    def _set_hdr(self, state):
        for e in [self._dated_e, self._desc_e]:
            e.configure(state=state)

    def _bind_keys(self):
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-x>", lambda e: self.on_exit())


class AutoValueAdjustForm(BaseForm):
    """AVADJ — automatically revalue all inventory at current purchase rates."""

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "AUTO VALUE ADJUSTMENT / AVADJ",
                         "AUTO VALUE ADJUSTMENT", username, "Alt+X : Exit")
        self.geometry("720x460")
        self._build_form()

    def _build_form(self):
        c = self.content

        tk.Label(c, text="Auto Value Adjustment revalues all inventory items\n"
                          "at their current Last Purchase Rate.",
                 bg=FORM_BG, fg=LABEL_FG, font=FONT_NORMAL,
                 justify="center").pack(pady=20)

        hf = tk.Frame(c, bg=FORM_BG)
        hf.pack(pady=8)
        tk.Label(hf, text="Dated (DD/MM/YYYY)", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="left", padx=6)
        self._date_e = tk.Entry(hf, width=14, bg="#D0DCF0",
                                font=FONT_NORMAL, relief="sunken", bd=2)
        self._date_e.pack(side="left", padx=4)
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Button(c, text="Run Auto Value Adjustment", bg="#4C6890", fg="white",
                  font=FONT_BOLD, relief="raised", bd=2, padx=20, pady=6,
                  command=self._run).pack(pady=12)

        cols = [("inv_code","Inv Code",80),("inv_name","Inv Name",200),
                ("old","Old Value",100),("new","New Value",100),("adj","Diff",100),("dated","Date",90)]
        gf, self._tree = make_grid(c, cols, height=12)
        gf.pack(fill="both", expand=True, padx=10, pady=4)

        self._refresh_list()

    def _run(self):
        dstr = self._date_e.get().strip()
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self); return
        if not messagebox.askyesno("Confirm",
                                   "This will revalue ALL inventory at current purchase rates.\nContinue?",
                                   parent=self):
            return
        count = db.auto_value_adjust(dt)
        self._refresh_list()
        messagebox.showinfo("Done", f"Auto adjustment applied to {count} item(s).", parent=self)

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_value_adjustments("AVADJ")):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", tags=(tag,),
                              values=(r["inv_code"], r["inventory_name"],
                                      f"{r['old_value']:,.2f}", f"{r['new_value']:,.2f}",
                                      f"{r['new_value']-r['old_value']:,.2f}", r["dated"]))


VADF_COLS = [
    {"id": "inv_code",  "header": "InvCode",        "width": 9,  "editable": True,  "align": "left"},
    {"id": "inv_name",  "header": "Inventory Name",  "width": 22, "editable": False, "align": "left"},
    {"id": "old_qty",   "header": "Old Qty",         "width": 10, "editable": False, "align": "right"},
    {"id": "new_qty",   "header": "New Qty",         "width": 10, "editable": True,  "align": "right"},
    {"id": "old_value", "header": "Old Value",       "width": 11, "editable": False, "align": "right"},
    {"id": "new_value", "header": "New Value",       "width": 11, "editable": True,  "align": "right", "bold": True},
]


class ValueAdditionDeletionForm(BaseForm):
    """VADF — add or remove inventory quantities and values."""

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "VALUE ADDITION/DELETION FORM / VADF",
                         "VALUE ADDITION DELETION FORM", username,
                         "Alt+A : Add    Alt+S : Save    Alt+X : Exit    F9 : LOV")
        self.geometry("860x560")
        self._build_form()
        self._refresh_list()
        self._bind_keys()

    def _build_form(self):
        c = self.content
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)

        hf = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hf.pack(fill="x", padx=10, pady=6)

        tk.Label(hf, text="Ref #",    **lkw).grid(row=0,column=0,sticky="e",padx=(8,2),pady=4)
        self._ref_e = tk.Entry(hf, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._ref_e.grid(row=0,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hf, text="Dated",    **lkw).grid(row=0,column=2,sticky="e",padx=(6,2),pady=4)
        self._dated_e = tk.Entry(hf, width=12, bg="#D0DCF0", font=FONT_NORMAL, relief="sunken", bd=2)
        self._dated_e.grid(row=0,column=3,sticky="w",padx=2,pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hf, text="Type",     **lkw).grid(row=0,column=4,sticky="e",padx=(6,2),pady=4)
        self._type_var = tk.StringVar(value="VADF_ADD")
        tk.OptionMenu(hf, self._type_var, "VADF_ADD", "VADF_DEL").grid(
            row=0, column=5, sticky="w", padx=2, pady=4)

        tk.Label(hf, text="Description", **lkw).grid(row=1,column=0,sticky="e",padx=(8,2),pady=4)
        self._desc_e = tk.Entry(hf, width=52, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._desc_e.grid(row=1,column=1,columnspan=5,sticky="ew",padx=(2,8),pady=4)
        self._desc_e.bind("<Tab>", lambda e: (self._grid.focus_first(), "break")[1])

        self._grid = InlineEntryGrid(c, VADF_COLS, start_rows=8)
        self._grid.pack(fill="both", expand=True, padx=10, pady=2)
        self._grid.on_focus_out = self._grid_fo
        self._grid.on_f9        = self._grid_f9

        cols = [("ref","Ref#",90),("type","Type",70),("dated","Date",90),
                ("inv","Inv Code",80),("name","Inv Name",160),
                ("old_q","Old Qty",80),("new_q","New Qty",80),("desc","Description",130)]
        gf, self._tree = make_grid(c, cols, height=5)
        gf.pack(fill="x", padx=10, pady=4)

        self._set_hdr("disabled")

    def _grid_fo(self, row_idx, col_id, value):
        if col_id == "inv_code" and value:
            item = db.get_inventory_item(value)
            if item:
                self._grid.set_value(row_idx, "inv_name",  item["name"])
                self._grid.set_value(row_idx, "old_qty",   f"{item['quantity']:,.2f}")
                self._grid.set_value(row_idx, "old_value", f"{item['value']:,.2f}")

    def _grid_f9(self, row_idx, col_id, value):
        if col_id == "inv_code":
            dlg = InventoryLOVDialog(self, value)
            if dlg.result:
                code, name, unit, rate = dlg.result
                self._grid.set_value(row_idx, "inv_code", code)
                self._grid.set_value(row_idx, "inv_name", name)
                item = db.get_inventory_item(code)
                if item:
                    self._grid.set_value(row_idx, "old_qty",   f"{item['quantity']:,.2f}")
                    self._grid.set_value(row_idx, "old_value", f"{item['value']:,.2f}")
                self._grid._widgets[row_idx]["new_qty"].focus_set()

    def on_add(self):
        self._grid.reset()
        self._set_hdr("normal")
        self._ref_e.configure(state="normal"); self._ref_e.delete(0,"end")
        self._ref_e.insert(0, f"VADF-{date.today().strftime('%Y%m%d')}")
        self._ref_e.configure(state="readonly")
        self._dated_e.delete(0,"end"); self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._desc_e.delete(0,"end")
        self._dated_e.focus_set()
        self._mode = "add"

    def on_save(self):
        dstr = self._dated_e.get().strip()
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self); return
        rows = [r for r in self._grid.get_all_rows() if r.get("inv_code")]
        if not rows:
            messagebox.showwarning("Validation", "Add at least one line.", parent=self); return
        ref  = self._ref_e.get().strip()
        desc = self._desc_e.get().strip()
        adj_type = self._type_var.get()
        for r in rows:
            db.save_value_adjustment(
                ref, adj_type, r["inv_code"], r.get("inv_name",""),
                _n(r.get("old_qty",0)), _n(r.get("new_qty",0)),
                _n(r.get("old_value",0)), _n(r.get("new_value",0)),
                dt, desc)
        self._refresh_list()
        self._grid.reset()
        self._set_hdr("disabled")
        self._mode = "view"
        messagebox.showinfo("Saved", f"Saved {len(rows)} adjustment(s).", parent=self)

    def on_ignore(self):
        self._grid.reset()
        self._set_hdr("disabled"); self._mode = "view"

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_value_adjustments()):
            if r["adj_type"] not in ("VADF_ADD", "VADF_DEL"):
                continue
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", tags=(tag,),
                              values=(r["ref_no"], r["adj_type"], r["dated"],
                                      r["inv_code"], r["inventory_name"],
                                      f"{r['old_qty']:,.2f}", f"{r['new_qty']:,.2f}",
                                      r["description"] or ""))

    def _set_hdr(self, state):
        for e in [self._dated_e, self._desc_e]: e.configure(state=state)

    def _bind_keys(self):
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())


# ─────────────────────────────────────────────────────────────────────────────
# Currency Transaction Form / CTF  (rewritten with InlineEntryGrid)
# ─────────────────────────────────────────────────────────────────────────────

CTF_COLS = [
    {"id": "inv_code",  "header": "Inv Code",       "width": 9,  "editable": True,  "align": "left"},
    {"id": "inv_name",  "header": "Currency Name",   "width": 22, "editable": False, "align": "left"},
    {"id": "quantity",  "header": "Quantity",        "width": 11, "editable": True,  "align": "right"},
    {"id": "rate",      "header": "Rate",            "width": 11, "editable": True,  "align": "right"},
    {"id": "value",     "header": "Value",           "width": 12, "editable": False, "align": "right", "bold": True},
]


class CurrencyTransactionForm(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "CURRENCY TRANSACTION FORM / CTF",
                         "CURRENCY TRANSACTION FORM", username,
                         "Alt+A : Add    Alt+S : Save    Alt+X : Exit    F9 : LOV")
        self.geometry("820x560")
        self._current = None
        self._build_form()
        self._bind_keys()

    def _build_form(self):
        c = self.content
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)
        tkw = dict(bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)

        hp = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hp.pack(fill="x", padx=10, pady=6)

        tk.Label(hp, text="Invoice #",  **lkw).grid(row=0,column=0,sticky="e",padx=(8,2),pady=4)
        self._inv_e = tk.Entry(hp, width=12, **tkw)
        self._inv_e.grid(row=0,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hp, text="Dated",      **lkw).grid(row=0,column=2,sticky="e",padx=(6,2),pady=4)
        self._dated_e = tk.Entry(hp, width=12, bg="#D0DCF0", font=FONT_NORMAL, relief="sunken", bd=2)
        self._dated_e.grid(row=0,column=3,sticky="w",padx=2,pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hp, text="A/C",        **lkw).grid(row=0,column=4,sticky="e",padx=(6,2),pady=4)
        self._ac_e = tk.Entry(hp, width=9, **tkw)
        self._ac_e.grid(row=0,column=5,sticky="w",padx=2,pady=4)
        self._ac_e.bind("<F9>", self._f9_ac)
        self._ac_e.bind("<FocusOut>", self._lookup_ac)
        self._ac_name_var = tk.StringVar()
        tk.Entry(hp, textvariable=self._ac_name_var, width=20,
                 bg="#E8E8E8", font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).grid(row=0,column=6,sticky="ew",padx=(2,8),pady=4)

        tk.Label(hp, text="Type",       **lkw).grid(row=1,column=0,sticky="e",padx=(8,2),pady=4)
        self._type_var = tk.StringVar(value="BUY")
        tk.OptionMenu(hp, self._type_var, "BUY","SELL").grid(row=1,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hp, text="Party",      **lkw).grid(row=1,column=2,sticky="e",padx=(6,2),pady=4)
        self._party_e = tk.Entry(hp, width=30, **tkw)
        self._party_e.grid(row=1,column=3,columnspan=3,sticky="ew",padx=2,pady=4)

        tk.Label(hp, text="Description",**lkw).grid(row=2,column=0,sticky="e",padx=(8,2),pady=4)
        self._desc_e = tk.Entry(hp, width=52, **tkw)
        self._desc_e.grid(row=2,column=1,columnspan=6,sticky="ew",padx=(2,8),pady=4)
        self._desc_e.bind("<Tab>", lambda e: (self._grid.focus_first(), "break")[1])

        gh = tk.Frame(c, bg="#DDE4EE")
        gh.pack(fill="x", padx=10)
        tk.Label(gh, text="💡 Inv Code/Currency: double-click or F9 to search",
                 bg="#DDE4EE", fg="#334466", font=("Arial", 8)).pack(side="left", padx=6, pady=2)
        lov_button(gh, self._open_inv_lov).pack(side="left", padx=4)
        self._grid = InlineEntryGrid(c, CTF_COLS, start_rows=10)
        self._grid.pack(fill="both", expand=True, padx=10, pady=2)
        self._grid.on_focus_out = self._grid_fo
        self._grid.on_f9        = self._grid_f9
        self._grid.on_change    = lambda rows: self._update_total()

        tf = tk.Frame(c, bg=FORM_BG)
        tf.pack(fill="x", padx=10, pady=2)
        self._total_var = tk.StringVar(value="")
        tk.Label(tf, text="Total Value", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="right", padx=4)
        tk.Entry(tf, textvariable=self._total_var, width=16, bg="#EEF4FF",
                 fg="#000080", font=("Arial", 9, "bold"), state="readonly",
                 relief="sunken", bd=2, justify="right").pack(side="right", padx=4)

        self._set_hdr("disabled")

    def _f9_ac(self, _):
        dlg = AccountLOVDialog(self, self._ac_e.get())
        if dlg.result:
            self._ac_e.delete(0,"end"); self._ac_e.insert(0, dlg.result[0])
            self._ac_name_var.set(dlg.result[1])

    def _lookup_ac(self, _):
        row = db.get_account(self._ac_e.get().strip())
        if row:
            self._ac_name_var.set(row["ac_name"])

    def _grid_fo(self, row_idx, col_id, value):
        if col_id == "inv_code" and value:
            item = db.get_inventory_item(value)
            if item:
                self._grid.set_value(row_idx, "inv_name", item["name"])
                if not self._grid.get_value(row_idx, "rate"):
                    self._grid.set_value(row_idx, "rate",
                                         f"{item['last_purchase_rate']:.4f}" if item["last_purchase_rate"] else "")
        elif col_id in ("quantity", "rate") and value:
            try:
                self._grid.set_value(row_idx, col_id, f"{float(value.replace(',','')):,.4f}")
            except ValueError:
                pass
        qty  = _n(self._grid.get_value(row_idx, "quantity"))
        rate = _n(self._grid.get_value(row_idx, "rate"))
        if qty and rate:
            self._grid.set_value(row_idx, "value", f"{qty*rate:,.2f}")
        self._update_total()

    def _grid_f9(self, row_idx, col_id, value):
        if col_id == "inv_code":
            dlg = InventoryLOVDialog(self, value)
            if dlg.result:
                self._grid.set_value(row_idx, "inv_code", dlg.result[0])
                self._grid.set_value(row_idx, "inv_name", dlg.result[1])
                if dlg.result[3]:
                    self._grid.set_value(row_idx, "rate", f"{dlg.result[3]:.4f}")
                self._grid._widgets[row_idx]["quantity"].focus_set()

    def _update_total(self):
        total = sum(_n(r.get("value", 0)) for r in self._grid.get_all_rows())
        self._total_var.set(f"{total:,.2f}" if total else "")

    def on_add(self):
        self._current = None
        self._grid.reset()
        self._set_hdr("normal")
        self._inv_e.configure(state="normal"); self._inv_e.delete(0,"end")
        self._inv_e.insert(0, f"CTF-{db.next_invoice_no('purchase_transactions')}")
        self._inv_e.configure(state="readonly")
        self._dated_e.delete(0,"end"); self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        for e in [self._ac_e, self._party_e, self._desc_e]: e.delete(0,"end")
        self._ac_name_var.set("")
        self._total_var.set("")
        self._dated_e.focus_set()
        self._mode = "add"

    def on_save(self):
        rows = [r for r in self._grid.get_all_rows() if r.get("inv_code")]
        if not rows:
            messagebox.showwarning("Validation", "Add at least one line.", parent=self); return
        # Save as purchase transaction for accounting
        dstr = self._dated_e.get().strip()
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self); return
        inv_no = self._inv_e.get().strip()
        total  = sum(_n(r.get("value", 0)) for r in rows)
        header = (inv_no, dt, self._ac_e.get().strip(), self._ac_name_var.get(),
                  self._type_var.get(), self._party_e.get().strip(),
                  total, "", self._desc_e.get().strip(), total)
        lines  = [(inv_no, i+1, r["inv_code"], r.get("inv_name",""),
                   _n(r.get("quantity",0)), _n(r.get("rate",0)), _n(r.get("value",0)))
                  for i, r in enumerate(rows)]
        db.save_purchase(header, lines)
        self._current = inv_no
        self._set_hdr("disabled")
        self._mode = "view"
        messagebox.showinfo("Saved", f"CTF {inv_no} saved.", parent=self)

    def on_ignore(self):
        self._grid.reset()
        self._set_hdr("disabled"); self._mode = "view"

    def _set_hdr(self, state):
        for e in [self._dated_e, self._ac_e, self._party_e, self._desc_e]:
            e.configure(state=state)

    def _bind_keys(self):
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())


# ── Utility ───────────────────────────────────────────────────────────────────

def _n(v):
    try:
        return float(str(v).replace(",", "") or 0)
    except (ValueError, TypeError):
        return 0.0
