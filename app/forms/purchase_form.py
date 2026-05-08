"""
Purchase Transactions Form / PTF  &  Sales Transactions Form / STF
Layout matches design images exactly – no bottom transaction list.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from config import *
from forms.base_form import (BaseForm, make_grid,
                              AccountLOVDialog, InventoryLOVDialog,
                              TransactionSearchDialog)
import database as db
from datetime import date


def _num(s):
    try:
        return float(str(s).replace(",", "") or 0)
    except ValueError:
        return 0.0


class _TransactionBase(BaseForm):
    """Shared skeleton for Purchase and Sales transaction forms."""

    _TITLE    = "PURCHASE TRANSACTIONS FORM / PTF"
    _SIDEBAR  = "PURCHASE TRANSACTIONS FORM"
    _DB_SAVE  = staticmethod(db.save_purchase)
    _DB_DEL   = staticmethod(db.delete_purchase)
    _DB_GET   = staticmethod(db.get_purchase)
    _DB_ALL   = staticmethod(db.get_all_purchases)
    _DB_NEXT  = "purchase_transactions"

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, self._TITLE, self._SIDEBAR, username,
                         "Alt+A : Add    Alt+E : Edit    Alt+D : Delete    "
                         "Alt+S : Save    Alt+X : Exit    F9 : LOV")
        self.geometry("860x640")
        self._current_inv = None
        self._lines = []
        self._build_form()
        self._bind_keys()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_form(self):
        c = self.content

        # ── Header panel ───────────────────────────────────────────────────────
        hp = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hp.pack(fill="x", padx=8, pady=6)
        hp.columnconfigure(3, weight=1)
        hp.columnconfigure(6, weight=1)

        # Row 0 – Invoice# | Dated | A/C | Name
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)
        tkw = dict(bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)

        tk.Label(hp, text="Invoice #", **lkw).grid(row=0, column=0, sticky="e", padx=(8,2), pady=4)
        self._inv_e = tk.Entry(hp, width=12, **tkw)
        self._inv_e.grid(row=0, column=1, sticky="w", padx=2, pady=4)

        tk.Label(hp, text="Dated", **lkw).grid(row=0, column=2, sticky="e", padx=(6,2), pady=4)
        self._dated_e = tk.Entry(hp, width=12, bg="#D0DCF0", font=FONT_NORMAL,
                                 relief="sunken", bd=2)
        self._dated_e.grid(row=0, column=3, sticky="w", padx=2, pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hp, text="A/C", **lkw).grid(row=0, column=4, sticky="e", padx=(6,2), pady=4)
        self._ac_e = tk.Entry(hp, width=9, **tkw)
        self._ac_e.grid(row=0, column=5, sticky="w", padx=2, pady=4)

        tk.Label(hp, text="Name", **lkw).grid(row=0, column=6, sticky="e", padx=(4,2), pady=4)
        self._ac_name_var = tk.StringVar()
        tk.Entry(hp, textvariable=self._ac_name_var, width=26,
                 bg="#E8E8E8", font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).grid(row=0, column=7, sticky="ew", padx=(2,8), pady=4)

        # Row 1 – Term | Party | Amount
        tk.Label(hp, text="Term", **lkw).grid(row=1, column=0, sticky="e", padx=(8,2), pady=4)
        self._term_var = tk.StringVar(value="CREDIT")
        tk.OptionMenu(hp, self._term_var, "CREDIT", "CASH").grid(
            row=1, column=1, sticky="w", padx=2, pady=4)

        tk.Label(hp, text="Party", **lkw).grid(row=1, column=2, sticky="e", padx=(6,2), pady=4)
        self._party_e = tk.Entry(hp, width=30, **tkw)
        self._party_e.grid(row=1, column=3, columnspan=3, sticky="ew", padx=2, pady=4)

        tk.Label(hp, text="Amount", **lkw).grid(row=1, column=6, sticky="e", padx=(4,2), pady=4)
        self._amt_var = tk.StringVar(value="")
        tk.Entry(hp, textvariable=self._amt_var, width=16,
                 bg="#E8E8E8", font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).grid(row=1, column=7, sticky="ew", padx=(2,8), pady=4)

        # Row 2 – In Words
        tk.Label(hp, text="In Words", **lkw).grid(row=2, column=0, sticky="e", padx=(8,2), pady=4)
        self._words_e = tk.Entry(hp, width=72, **tkw)
        self._words_e.grid(row=2, column=1, columnspan=7, sticky="ew", padx=(2,8), pady=4)

        # Row 3 – Description
        tk.Label(hp, text="Description", **lkw).grid(row=3, column=0, sticky="e", padx=(8,2), pady=4)
        self._desc_e = tk.Entry(hp, width=72, **tkw)
        self._desc_e.grid(row=3, column=1, columnspan=7, sticky="ew", padx=(2,8), pady=4)

        # ── Inventory lines grid ───────────────────────────────────────────────
        lcols = [("serial","Seial",45), ("inv_code","InvCode",70),
                 ("inv_name","Inventory Name",230),
                 ("qty","Quantity",80), ("rate","Rate",80), ("value","Value",90)]
        gf, self._ltree = make_grid(c, lcols, height=10)
        gf.pack(fill="both", expand=True, padx=8, pady=2)
        self._ltree.bind("<<TreeviewSelect>>", self._on_line_sel)
        self._ltree.bind("<Delete>", lambda e: self._del_line())

        # ── Status / description echo ──────────────────────────────────────────
        self._status_var = tk.StringVar(value="")
        tk.Label(c, textvariable=self._status_var, bg="#C8D0DC", fg=LABEL_FG,
                 font=FONT_SMALL, anchor="w", relief="sunken",
                 bd=1).pack(fill="x", padx=8)

        # ── Total Value row ────────────────────────────────────────────────────
        tvf = tk.Frame(c, bg=FORM_BG)
        tvf.pack(fill="x", padx=8, pady=2)
        tk.Label(tvf, text="Total Value", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).pack(side="right", padx=4)
        self._total_var = tk.StringVar(value="")
        tk.Entry(tvf, textvariable=self._total_var, width=16, bg="#E8E8E8",
                 font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).pack(side="right", padx=4)

        # ── Line-entry strip ───────────────────────────────────────────────────
        ler = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        ler.pack(fill="x", padx=8, pady=2)

        for attr, lbl, w in [("_le_code","InvCode",9),
                              ("_le_name","Inventory Name",26),
                              ("_le_qty", "Quantity",9),
                              ("_le_rate","Rate",9),
                              ("_le_val", "Value",10)]:
            tk.Label(ler, text=lbl, bg=FORM_BG, fg=LABEL_FG,
                     font=FONT_SMALL).pack(side="left", padx=(6,2))
            e = tk.Entry(ler, width=w, bg=ENTRY_BG, font=FONT_NORMAL,
                         relief="sunken", bd=2)
            e.pack(side="left", padx=2)
            setattr(self, attr, e)

        self._le_code.bind("<F9>",       self._f9_inv)
        self._le_code.bind("<FocusOut>", self._lookup_inv)
        self._le_qty.bind("<FocusOut>",  self._calc_value)
        self._le_rate.bind("<FocusOut>", self._calc_value)

        tk.Button(ler, text="Add Line",    bg=BTN_BG, font=FONT_SMALL,
                  relief="raised", bd=2,
                  command=self._add_line).pack(side="left", padx=6, pady=3)
        tk.Button(ler, text="Remove Line", bg=BTN_BG, font=FONT_SMALL,
                  relief="raised", bd=2,
                  command=self._del_line).pack(side="left", padx=2, pady=3)

        # ── General Ledger Transactions section ───────────────────────────────
        glf = tk.LabelFrame(c, text="GENERAL LEDGER TRANSACTIONS",
                            bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD,
                            bd=2, relief="groove")
        glf.pack(fill="x", padx=8, pady=4)

        glcols = [("ac_code","A/c Code",80), ("ac_name","A/c Name",280),
                  ("debit","Debit",110), ("credit","Credit",110)]
        gf2, self._gltree = make_grid(glf, glcols, height=3)
        gf2.pack(fill="x", padx=4, pady=4)

        # F9 and FocusOut on A/C field
        self._ac_e.bind("<F9>",       self._f9_ac)
        self._ac_e.bind("<FocusOut>", self._lookup_ac)

        self._hdr_entries = [self._dated_e, self._ac_e, self._party_e,
                             self._words_e, self._desc_e]
        self._set_hdr_state("disabled")

    # ── F9 LOV handlers ────────────────────────────────────────────────────────

    def _f9_ac(self, _event):
        dlg = AccountLOVDialog(self, self._ac_e.get().strip())
        if dlg.result:
            code, name = dlg.result
            self._ac_e.delete(0, "end");   self._ac_e.insert(0, code)
            self._ac_name_var.set(name)
            self._party_e.focus_set()

    def _f9_inv(self, _event):
        dlg = InventoryLOVDialog(self, self._le_code.get().strip())
        if dlg.result:
            code, name, unit, rate = dlg.result
            self._le_code.delete(0, "end"); self._le_code.insert(0, code)
            self._le_name.delete(0, "end"); self._le_name.insert(0, name)
            self._le_rate.delete(0, "end"); self._le_rate.insert(0, f"{rate:.2f}")
            self._le_qty.focus_set()

    def _lookup_ac(self, _):
        code = self._ac_e.get().strip()
        if not code:
            return
        row = db.get_account(code)
        if row:
            self._ac_name_var.set(row["ac_name"])

    def _lookup_inv(self, _):
        code = self._le_code.get().strip()
        if not code:
            return
        item = db.get_inventory_item(code)
        if item:
            self._le_name.delete(0, "end"); self._le_name.insert(0, item["name"])
            if not self._le_rate.get().strip():
                self._le_rate.delete(0, "end")
                self._le_rate.insert(0, f"{item['last_purchase_rate']:.2f}")

    def _calc_value(self, _):
        val = _num(self._le_qty.get()) * _num(self._le_rate.get())
        self._le_val.delete(0, "end")
        self._le_val.insert(0, f"{val:.2f}")

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_inv = None
        self._clear_form()
        self._set_hdr_state("normal")
        self._inv_e.configure(state="normal")
        self._inv_e.delete(0, "end")
        self._inv_e.insert(0, db.next_invoice_no(self._DB_NEXT))
        self._inv_e.configure(state="readonly")
        self._dated_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_inv:
            messagebox.showwarning("Edit", "Search and load a record first.", parent=self)
            return
        self._set_hdr_state("normal")
        self._inv_e.configure(state="readonly")
        self._mode = "edit"

    def on_delete(self):
        if not self._current_inv:
            messagebox.showwarning("Delete", "Load a record first.", parent=self)
            return
        if messagebox.askyesno("Confirm",
                               f"Delete invoice {self._current_inv}?", parent=self):
            self._DB_DEL(self._current_inv)
            self._current_inv = None
            self._clear_form()

    def on_search(self):
        src = "purchase" if "PURCHASE" in self._TITLE else "sale"
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
            messagebox.showerror("Date", "Use DD/MM/YYYY format.", parent=self)
            return
        if not self._lines:
            messagebox.showwarning("Validation",
                                   "Add at least one inventory line.", parent=self)
            return

        total  = sum(r[5] for r in self._lines)
        header = (inv_no, dt,
                  self._ac_e.get().strip(), self._ac_name_var.get(),
                  self._term_var.get(), self._party_e.get().strip(),
                  total, self._words_e.get().strip(),
                  self._desc_e.get().strip(), total)
        lines  = [(inv_no, r[0], r[1], r[2], r[3], r[4], r[5])
                  for r in self._lines]
        self._DB_SAVE(header, lines)
        self._current_inv = inv_no
        self._set_hdr_state("disabled")
        self._mode = "view"
        messagebox.showinfo("Saved", f"Invoice {inv_no} saved.", parent=self)

    def on_ignore(self):
        if self._current_inv:
            self._load_record(self._current_inv)
        else:
            self._clear_form()
        self._set_hdr_state("disabled")
        self._mode = "view"

    # ── Lines ──────────────────────────────────────────────────────────────────

    def _add_line(self):
        code = self._le_code.get().strip()
        name = self._le_name.get().strip() or code
        qty  = _num(self._le_qty.get())
        rate = _num(self._le_rate.get())
        val  = _num(self._le_val.get()) or qty * rate
        if not code:
            messagebox.showwarning("Input", "Inventory Code required.", parent=self)
            return
        serial = len(self._lines) + 1
        self._lines.append([serial, code, name, qty, rate, val])
        self._render_lines()
        for e in [self._le_code, self._le_name, self._le_qty,
                  self._le_rate, self._le_val]:
            e.delete(0, "end")
        self._le_code.focus_set()

    def _del_line(self):
        sel = self._ltree.selection()
        if not sel:
            messagebox.showwarning("Delete", "Select a line first.", parent=self)
            return
        idx = self._ltree.index(sel[0])
        del self._lines[idx]
        for i, r in enumerate(self._lines):
            r[0] = i + 1
        self._render_lines()

    def _on_line_sel(self, _):
        sel = self._ltree.selection()
        if not sel:
            return
        r = self._lines[self._ltree.index(sel[0])]
        self._le_code.delete(0, "end");  self._le_code.insert(0, r[1])
        self._le_name.delete(0, "end");  self._le_name.insert(0, r[2])
        self._le_qty.delete(0, "end");   self._le_qty.insert(0, f"{r[3]:.2f}")
        self._le_rate.delete(0, "end");  self._le_rate.insert(0, f"{r[4]:.2f}")
        self._le_val.delete(0, "end");   self._le_val.insert(0, f"{r[5]:.2f}")

    def _render_lines(self):
        self._ltree.delete(*self._ltree.get_children())
        total = 0.0
        for i, r in enumerate(self._lines):
            tag = "odd" if i % 2 else "even"
            self._ltree.insert("", "end", values=(
                r[0], r[1], r[2],
                f"{r[3]:,.2f}", f"{r[4]:,.2f}", f"{r[5]:,.2f}"
            ), tags=(tag,))
            total += r[5]
        self._total_var.set(f"{total:,.2f}")
        self._amt_var.set(f"{total:,.2f}")
        self._status_var.set(self._desc_e.get().strip())
        self._update_gl(total)

    def _update_gl(self, total):
        self._gltree.delete(*self._gltree.get_children())
        ac_code = self._ac_e.get().strip()
        ac_name = self._ac_name_var.get()
        party   = self._party_e.get().strip()
        self._gltree.insert("", "end", values=(
            "INV", "Inventory / Stock",
            f"{total:,.2f}", ""), tags=("odd",))
        self._gltree.insert("", "end", values=(
            ac_code, ac_name or party, "",
            f"{total:,.2f}"), tags=("even",))

    # ── Load / Clear ───────────────────────────────────────────────────────────

    def _load_record(self, inv_no):
        hdr, lines = self._DB_GET(inv_no)
        if not hdr:
            return
        self._clear_form(keep=True)
        self._set_hdr_state("normal")
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
        self._set_hdr_state("disabled")
        self._lines = [[r["serial"], r["inv_code"], r["inventory_name"],
                        r["quantity"], r["rate"], r["value"]] for r in lines]
        self._render_lines()

    def _clear_form(self, keep=False):
        self._lines = []
        self._ltree.delete(*self._ltree.get_children())
        self._gltree.delete(*self._gltree.get_children())
        self._total_var.set(""); self._amt_var.set("")
        self._status_var.set("")
        for e in [self._inv_e, self._dated_e, self._ac_e,
                  self._party_e, self._words_e, self._desc_e]:
            s = e.cget("state")
            e.configure(state="normal"); e.delete(0, "end")
            if keep:
                e.configure(state=s)
        if not keep:
            self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._ac_name_var.set("")
        self._term_var.set("CREDIT")
        for e in [self._le_code, self._le_name, self._le_qty,
                  self._le_rate, self._le_val]:
            e.delete(0, "end")

    def _set_hdr_state(self, state):
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

    def _update_gl(self, total):
        self._gltree.delete(*self._gltree.get_children())
        ac_code = self._ac_e.get().strip()
        ac_name = self._ac_name_var.get()
        party   = self._party_e.get().strip()
        self._gltree.insert("", "end", values=(
            ac_code, ac_name or party,
            f"{total:,.2f}", ""), tags=("odd",))
        self._gltree.insert("", "end", values=(
            "SALES", "Sales Revenue", "",
            f"{total:,.2f}"), tags=("even",))
