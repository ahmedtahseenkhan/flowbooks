"""
Purchase Transactions Form / PTF  &  Sales Transactions Form / STF
Keyboard-driven UX – matches Oracle Forms design exactly.

Tab flow (header):
  Invoice# (auto) → Dated → A/C → [auto: Name] → Term → Party → Amount (auto)
  → In Words → Description → [Tab enters grid]

Tab flow (grid):
  InvCode → [auto: Inventory Name] → Quantity → Rate → [auto: Value] → next row

F9 on A/C field   → SELECT THE ACCOUNT popup
F9 on InvCode     → SEARCH BY CODE popup
Total Value updates live. GL section auto-fills on save.
Search button     → SEARCH BY DATE popup
"""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import (BaseForm, InlineEntryGrid, make_grid, lov_button,
                              AccountLOVDialog, InventoryLOVDialog,
                              TransactionSearchDialog)
import database as db
from datetime import date

PURCHASE_COLS = [
    {"id": "inv_code",  "header": "InvCode",        "width": 9,  "editable": True,  "align": "left"},
    {"id": "inv_name",  "header": "Inventory Name",  "width": 26, "editable": False, "align": "left"},
    {"id": "quantity",  "header": "Quantity",        "width": 10, "editable": True,  "align": "right"},
    {"id": "rate",      "header": "Rate",            "width": 10, "editable": True,  "align": "right"},
    {"id": "value",     "header": "Value",           "width": 11, "editable": False, "align": "right", "bold": True},
]


def _f(v):
    try:
        return float(str(v).replace(",", "") or 0)
    except ValueError:
        return 0.0


class _TransactionBase(BaseForm):

    _TITLE   = "PURCHASE TRANSACTIONS FORM / PTF"
    _SIDEBAR = "PURCHASE TRANSACTIONS FORM"
    _DB_SAVE = staticmethod(db.save_purchase)
    _DB_DEL  = staticmethod(db.delete_purchase)
    _DB_GET  = staticmethod(db.get_purchase)
    _DB_ALL  = staticmethod(db.get_all_purchases)
    _DB_NEXT = "purchase_transactions"

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, self._TITLE, self._SIDEBAR, username,
                         "Alt+A : Add    Alt+E : Edit    Alt+D : Delete    "
                         "Alt+S : Save    Alt+X : Exit    F9 : LOV")
        self.geometry("900x660")
        self._current_inv = None
        self._build_form()
        self._bind_keys()
        # Auto-start in Add mode so the form is immediately ready for input
        self.after(50, self.on_add)

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_form(self):
        c = self.content
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)
        tkw = dict(bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)

        # ── Header panel ───────────────────────────────────────────────────────
        hp = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hp.pack(fill="x", padx=8, pady=6)
        hp.columnconfigure(3, weight=1)
        hp.columnconfigure(7, weight=1)

        # Row 0: Invoice # | Dated | A/C | Name
        tk.Label(hp, text="Invoice #", **lkw).grid(
            row=0, column=0, sticky="e", padx=(8,2), pady=4)
        self._inv_e = tk.Entry(hp, width=12, **tkw)
        self._inv_e.grid(row=0, column=1, sticky="w", padx=2, pady=4)

        tk.Label(hp, text="Dated", **lkw).grid(
            row=0, column=2, sticky="e", padx=(6,2), pady=4)
        self._dated_e = tk.Entry(hp, width=12, bg="#D0DCF0",
                                 font=FONT_NORMAL, relief="sunken", bd=2)
        self._dated_e.grid(row=0, column=3, sticky="w", padx=2, pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hp, text="A/C", **lkw).grid(
            row=0, column=4, sticky="e", padx=(6,2), pady=4)
        self._ac_e = tk.Entry(hp, width=9, **tkw)
        self._ac_e.grid(row=0, column=5, sticky="w", padx=2, pady=4)

        tk.Label(hp, text="Name", **lkw).grid(
            row=0, column=6, sticky="e", padx=(4,2), pady=4)
        self._ac_name_var = tk.StringVar()
        tk.Entry(hp, textvariable=self._ac_name_var, width=26,
                 bg="#E8E8E8", font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).grid(
            row=0, column=7, sticky="ew", padx=(2,8), pady=4)

        # Row 1: Term | Party | Amount (auto)
        tk.Label(hp, text="Term", **lkw).grid(
            row=1, column=0, sticky="e", padx=(8,2), pady=4)
        self._term_var = tk.StringVar(value="CREDIT")
        tk.OptionMenu(hp, self._term_var, "CREDIT", "CASH").grid(
            row=1, column=1, sticky="w", padx=2, pady=4)

        tk.Label(hp, text="Party", **lkw).grid(
            row=1, column=2, sticky="e", padx=(6,2), pady=4)
        self._party_e = tk.Entry(hp, width=32, **tkw)
        self._party_e.grid(row=1, column=3, columnspan=3,
                           sticky="ew", padx=2, pady=4)

        tk.Label(hp, text="Amount", **lkw).grid(
            row=1, column=6, sticky="e", padx=(4,2), pady=4)
        self._amt_var = tk.StringVar(value="")
        tk.Entry(hp, textvariable=self._amt_var, width=16,
                 bg="#E8E8E8", fg="#000080", font=("Arial", 9, "bold"),
                 state="readonly", relief="sunken", bd=2,
                 justify="right").grid(row=1, column=7, sticky="ew",
                                       padx=(2,8), pady=4)

        # Row 2: In Words
        tk.Label(hp, text="In Words", **lkw).grid(
            row=2, column=0, sticky="e", padx=(8,2), pady=4)
        self._words_e = tk.Entry(hp, width=72, **tkw)
        self._words_e.grid(row=2, column=1, columnspan=7,
                           sticky="ew", padx=(2,8), pady=4)

        # Row 3: Description (Tab from here → grid)
        tk.Label(hp, text="Description", **lkw).grid(
            row=3, column=0, sticky="e", padx=(8,2), pady=4)
        self._desc_e = tk.Entry(hp, width=72, **tkw)
        self._desc_e.grid(row=3, column=1, columnspan=7,
                          sticky="ew", padx=(2,8), pady=4)
        self._desc_e.bind("<Tab>",
            lambda e: (self._grid.focus_first(), "break")[1])
        self._desc_e.bind("<Return>", lambda e: self._grid.focus_first())

        # F9 / FocusOut on A/C field
        self._ac_e.bind("<F9>",       self._f9_ac)
        self._ac_e.bind("<FocusOut>", self._lookup_ac)
        lov_button(hp, self._f9_ac).grid(row=0, column=6, padx=(0,2), pady=4)

        # ── Inventory grid hint + LOV button ──────────────────────────────────
        gh = tk.Frame(c, bg="#DDE4EE")
        gh.pack(fill="x", padx=8)
        tk.Label(gh, text="💡 InvCode: type code OR double-click/F9 to search",
                 bg="#DDE4EE", fg="#334466", font=("Arial", 8)).pack(side="left", padx=6, pady=2)
        lov_button(gh, lambda: self._open_inv_lov()).pack(side="left", padx=4)
        tk.Label(gh, text="Search Inventory", bg="#DDE4EE", fg="#334466",
                 font=("Arial", 8)).pack(side="left")

        # ── Inline inventory grid ──────────────────────────────────────────────
        self._grid = InlineEntryGrid(c, PURCHASE_COLS, start_rows=12)
        self._grid.pack(fill="both", expand=True, padx=8, pady=2)
        self._grid.on_focus_out  = self._grid_focus_out
        self._grid.on_f9         = self._grid_f9
        self._grid.on_change     = self._grid_changed
        self._grid.on_delete_row = lambda _: self._update_total()

        # ── Status echo ────────────────────────────────────────────────────────
        self._echo_var = tk.StringVar(value="")
        tk.Label(c, textvariable=self._echo_var,
                 bg="#C8D0DC", fg=LABEL_FG, font=FONT_SMALL,
                 anchor="w", relief="sunken", bd=1).pack(fill="x", padx=8)

        # ── Total Value ────────────────────────────────────────────────────────
        tvf = tk.Frame(c, bg=FORM_BG)
        tvf.pack(fill="x", padx=8, pady=2)
        tk.Label(tvf, text="Total Value", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="right", padx=4)
        self._total_var = tk.StringVar(value="")
        tk.Entry(tvf, textvariable=self._total_var, width=16,
                 bg="#EEF4FF", fg="#000080", font=("Arial", 9, "bold"),
                 state="readonly", relief="sunken", bd=2,
                 justify="right").pack(side="right", padx=4)

        # ── General Ledger Transactions ────────────────────────────────────────
        glf = tk.LabelFrame(c, text="GENERAL LEDGER TRANSACTIONS",
                            bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD,
                            bd=2, relief="groove")
        glf.pack(fill="x", padx=8, pady=4)
        glcols = [("ac_code","A/c Code",80), ("ac_name","A/c Name",300),
                  ("debit","Debit",110), ("credit","Credit",110)]
        gf, self._gltree = make_grid(glf, glcols, height=3)
        gf.pack(fill="x", padx=4, pady=4)

        self._hdr_entries = [self._dated_e, self._ac_e, self._party_e,
                             self._words_e, self._desc_e]
        self._set_hdr("disabled")

    # ── Grid callbacks ─────────────────────────────────────────────────────────

    def _grid_focus_out(self, row_idx, col_id, value):
        if col_id == "inv_code" and value:
            item = db.get_inventory_item(value)
            if item:
                self._grid.set_value(row_idx, "inv_name", item["name"])
                # Pre-fill rate if empty
                if not self._grid.get_value(row_idx, "rate"):
                    rate = item["last_purchase_rate"] or 0
                    self._grid.set_value(row_idx, "rate",
                                         f"{rate:.2f}" if rate else "")
            self._calc_value(row_idx)

        elif col_id in ("quantity", "rate"):
            # Format number
            if value:
                try:
                    n = float(value.replace(",", ""))
                    self._grid.set_value(row_idx, col_id, f"{n:,.2f}")
                except ValueError:
                    pass
            self._calc_value(row_idx)
        self._update_total()

    def _calc_value(self, row_idx):
        qty  = _f(self._grid.get_value(row_idx, "quantity"))
        rate = _f(self._grid.get_value(row_idx, "rate"))
        val  = qty * rate
        self._grid.set_value(row_idx, "value",
                              f"{val:,.2f}" if val else "")

    def _grid_f9(self, row_idx, col_id, value):
        if col_id == "inv_code":
            dlg = InventoryLOVDialog(self, value)
            if dlg.result:
                code, name, unit, rate = dlg.result
                self._grid.set_value(row_idx, "inv_code",  code)
                self._grid.set_value(row_idx, "inv_name",  name)
                self._grid.set_value(row_idx, "rate",
                                     f"{rate:.2f}" if rate else "")
                # Focus Quantity
                self._grid._widgets[row_idx]["quantity"].focus_set()
                self._calc_value(row_idx)
                self._update_total()

    def _open_inv_lov(self):
        """Open inventory LOV for the currently focused grid row (or row 0)."""
        focused = self.focus_get()
        row_idx = 0
        for i, row in enumerate(self._grid._widgets):
            if focused in row.values():
                row_idx = i
                break
        self._grid_f9(row_idx, "inv_code",
                      self._grid.get_value(row_idx, "inv_code"))

    def _grid_changed(self, rows):
        self._update_total()

    def _update_total(self):
        rows  = self._grid.get_all_rows()
        total = sum(_f(r.get("value", 0)) for r in rows)
        self._total_var.set(f"{total:,.2f}" if total else "")
        self._amt_var.set(f"{total:,.2f}" if total else "")
        self._echo_var.set(self._desc_e.get().strip())
        self._refresh_gl(total)

    def _refresh_gl(self, total):
        self._gltree.delete(*self._gltree.get_children())
        if not total:
            return
        ac_code = self._ac_e.get().strip()
        ac_name = self._ac_name_var.get()
        party   = self._party_e.get().strip()
        self._gl_rows(total, ac_code, ac_name or party)

    def _gl_rows(self, total, ac_code, ac_name):
        # Default (purchase): debit inventory, credit party
        self._gltree.insert("", "end", values=(
            "INV", "Inventory / Stock",
            f"{total:,.2f}", ""), tags=("odd",))
        self._gltree.insert("", "end", values=(
            ac_code, ac_name, "", f"{total:,.2f}"), tags=("even",))

    # ── F9 / FocusOut on A/C ──────────────────────────────────────────────────

    def _f9_ac(self, _event):
        dlg = AccountLOVDialog(self, self._ac_e.get().strip())
        if dlg.result:
            code, name = dlg.result
            self._ac_e.delete(0, "end");   self._ac_e.insert(0, code)
            self._ac_name_var.set(name)
            self._party_e.focus_set()

    def _lookup_ac(self, _):
        code = self._ac_e.get().strip()
        if code:
            row = db.get_account(code)
            if row:
                self._ac_name_var.set(row["ac_name"])

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_inv = None
        self._clear_header()
        self._grid.reset()
        self._set_hdr("normal")
        self._inv_e.configure(state="normal")
        self._inv_e.delete(0, "end")
        self._inv_e.insert(0, db.next_invoice_no(self._DB_NEXT))
        self._inv_e.configure(state="readonly")
        self._total_var.set(""); self._amt_var.set("")
        self._echo_var.set("")
        self._dated_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_inv:
            messagebox.showwarning("Edit", "Search a record first.", parent=self)
            return
        self._set_hdr("normal")
        self._inv_e.configure(state="readonly")
        self._grid.set_editable(True)
        self._mode = "edit"

    def on_delete(self):
        if not self._current_inv:
            messagebox.showwarning("Delete", "Load a record first.", parent=self)
            return
        if messagebox.askyesno("Confirm",
                               f"Delete invoice {self._current_inv}?", parent=self):
            self._DB_DEL(self._current_inv)
            self._current_inv = None
            self._clear_header()
            self._grid.reset()
            self._set_hdr("disabled")

    def on_search(self):
        src = "sale" if "SALES" in self._TITLE else "purchase"
        dlg = TransactionSearchDialog(self, source=src)
        if dlg.result:
            self._current_inv = dlg.result
            self._load_record(self._current_inv)

    def on_save(self):
        inv_no = self._inv_e.get().strip()
        dstr   = self._dated_e.get().strip()
        if not inv_no or not dstr:
            messagebox.showwarning("Validation",
                                   "Invoice# and Date required.", parent=self)
            return
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY.", parent=self)
            return

        rows = [r for r in self._grid.get_all_rows() if r.get("inv_code")]
        if not rows:
            messagebox.showwarning("Validation",
                                   "Enter at least one inventory line.", parent=self)
            return

        total  = sum(_f(r.get("value", 0)) for r in rows)
        header = (inv_no, dt,
                  self._ac_e.get().strip(), self._ac_name_var.get(),
                  self._term_var.get(), self._party_e.get().strip(),
                  total, self._words_e.get().strip(),
                  self._desc_e.get().strip(), total)
        lines  = [(inv_no, i+1,
                   r["inv_code"], r.get("inv_name", ""),
                   _f(r.get("quantity", 0)),
                   _f(r.get("rate", 0)),
                   _f(r.get("value", 0)))
                  for i, r in enumerate(rows)]
        self._DB_SAVE(header, lines)
        self._current_inv = inv_no
        self._set_hdr("disabled")
        self._grid.set_editable(False)
        self._mode = "view"
        messagebox.showinfo("Saved", f"Invoice {inv_no} saved.", parent=self)

    def on_ignore(self):
        if self._current_inv:
            self._load_record(self._current_inv)
        else:
            self._clear_header()
            self._grid.reset()
            self._set_hdr("disabled")
        self._mode = "view"

    # ── Load / Clear ───────────────────────────────────────────────────────────

    def _load_record(self, inv_no):
        hdr, lines = self._DB_GET(inv_no)
        if not hdr:
            return
        self._clear_header()
        self._set_hdr("normal")
        self._inv_e.configure(state="normal")
        self._inv_e.delete(0, "end"); self._inv_e.insert(0, hdr["invoice_no"])
        self._inv_e.configure(state="readonly")
        self._dated_e.delete(0, "end")
        try:
            from datetime import datetime
            self._dated_e.insert(
                0, datetime.strptime(hdr["dated"], "%Y-%m-%d").strftime("%d/%m/%Y"))
        except Exception:
            self._dated_e.insert(0, hdr["dated"])
        self._ac_e.delete(0, "end");   self._ac_e.insert(0, hdr["ac_code"] or "")
        self._ac_name_var.set(hdr["ac_name"] or "")
        self._term_var.set(hdr["term"] or "CREDIT")
        self._party_e.delete(0, "end"); self._party_e.insert(0, hdr["party"] or "")
        self._words_e.delete(0, "end"); self._words_e.insert(0, hdr["in_words"] or "")
        self._desc_e.delete(0, "end");  self._desc_e.insert(0, hdr["description"] or "")
        self._set_hdr("disabled")

        row_data = [{"inv_code": r["inv_code"],
                     "inv_name": r["inventory_name"],
                     "quantity": f"{r['quantity']:,.2f}" if r["quantity"] else "",
                     "rate":     f"{r['rate']:,.2f}" if r["rate"] else "",
                     "value":    f"{r['value']:,.2f}" if r["value"] else ""}
                    for r in lines]
        self._grid.load_rows(row_data)
        self._grid.set_editable(False)
        self._update_total()

    def _clear_header(self):
        for e in [self._dated_e, self._ac_e, self._party_e,
                  self._words_e, self._desc_e]:
            s = e.cget("state")
            e.configure(state="normal"); e.delete(0, "end")
            e.configure(state=s)
        self._ac_name_var.set("")
        self._term_var.set("CREDIT")
        self._dated_e.configure(state="normal")
        self._dated_e.delete(0, "end")
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

    def _set_hdr(self, state):
        for e in [self._dated_e, self._ac_e, self._party_e,
                  self._words_e, self._desc_e]:
            e.configure(state=state)

    def _bind_keys(self):
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-e>", lambda e: self.on_edit())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())
        self.bind("<F9>",    lambda e: self._f9_ac(e))


# ── Concrete forms ─────────────────────────────────────────────────────────────

class PurchaseTransactionsForm(_TransactionBase):
    _TITLE   = "PURCHASE TRANSACTIONS FORM / PTF"
    _SIDEBAR = "PURCHASE TRANSACTIONS FORM"
    _DB_SAVE = staticmethod(db.save_purchase)
    _DB_DEL  = staticmethod(db.delete_purchase)
    _DB_GET  = staticmethod(db.get_purchase)
    _DB_ALL  = staticmethod(db.get_all_purchases)
    _DB_NEXT = "purchase_transactions"


class SalesTransactionsForm(_TransactionBase):
    _TITLE   = "SALES TRANSACTIONS FORM / STF"
    _SIDEBAR = "SALES TRANSACTIONS FORM"
    _DB_SAVE = staticmethod(db.save_sale)
    _DB_DEL  = staticmethod(db.delete_sale)
    _DB_GET  = staticmethod(db.get_sale)
    _DB_ALL  = staticmethod(db.get_all_sales)
    _DB_NEXT = "sales_transactions"

    def _gl_rows(self, total, ac_code, ac_name):
        # Sales: debit party, credit sales revenue
        self._gltree.insert("", "end", values=(
            ac_code, ac_name,
            f"{total:,.2f}", ""), tags=("odd",))
        self._gltree.insert("", "end", values=(
            "SALES", "Sales Revenue", "",
            f"{total:,.2f}"), tags=("even",))
