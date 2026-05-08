"""Inventory Master Form"""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, make_grid
import database as db
from datetime import date

SIDEBAR = "INVENTORY MASTER FORM"
SHORTCUTS = "Alt+D : Delete    Alt+A : Add    Alt+E : Edit    Alt+F : Search    Alt+S : Save    Alt+X : Exit"


class InventoryMaster(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "INVENTORY MASTER", SIDEBAR, username, SHORTCUTS)
        self.geometry("820x580")
        self._current_code = None
        self._entries = []
        self._build_form()
        self._refresh_list()
        self._bind_keys()

    def _build_form(self):
        c = self.content

        # ── Search radio ───────────────────────────────────────────────────────
        self._search_by = tk.StringVar(value="code")
        sr = tk.Frame(c, bg=FORM_BG)
        sr.pack(fill="x", padx=10, pady=(4, 0))
        tk.Radiobutton(sr, text="Search By Code", variable=self._search_by, value="code",
                       bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left")
        tk.Radiobutton(sr, text="Search By Name", variable=self._search_by, value="name",
                       bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=10)

        # ── Main form section ──────────────────────────────────────────────────
        mf = tk.LabelFrame(c, text="INVENTORY MASTER FORM", bg=GROUP_BG, fg=LABEL_FG,
                           font=FONT_BOLD, bd=2, relief="groove")
        mf.pack(fill="x", padx=10, pady=6)
        mf.columnconfigure(1, weight=1)
        mf.columnconfigure(3, weight=0)

        # Row 0
        tk.Label(mf, text="Code",   bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._code_e = tk.Entry(mf, width=12, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._code_e.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        tk.Label(mf, text="Symbol", bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self._symbol_e = tk.Entry(mf, width=12, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._symbol_e.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        # Row 1
        tk.Label(mf, text="Name",   bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self._name_e = tk.Entry(mf, width=46, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._name_e.grid(row=1, column=1, columnspan=3, sticky="ew", padx=4, pady=4)

        # Row 2
        tk.Label(mf, text="Head",      bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=2, column=0, sticky="e", padx=4, pady=4)
        self._head_e = tk.Entry(mf, width=10, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._head_e.grid(row=2, column=1, sticky="w", padx=4, pady=4)
        tk.Label(mf, text="Head Name", bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=2, column=2, sticky="e", padx=4, pady=4)
        self._head_name_e = tk.Entry(mf, width=24, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._head_name_e.grid(row=2, column=3, sticky="w", padx=4, pady=4)
        tk.Label(mf, text="Unit",      bg=GROUP_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=2, column=4, sticky="e", padx=4, pady=4)
        self._unit_e = tk.Entry(mf, width=8, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._unit_e.grid(row=2, column=5, sticky="w", padx=4, pady=4)

        # ── Last Updates ───────────────────────────────────────────────────────
        lu = tk.LabelFrame(c, text="Last Updates", bg=GROUP_BG, fg=LABEL_FG,
                           font=FONT_BOLD, bd=2, relief="groove")
        lu.pack(fill="x", padx=10, pady=4)

        tk.Label(lu, text="Last Saling Rates",   bg=GROUP_BG, fg=LABEL_FG, font=FONT_NORMAL).grid(row=0, column=0, sticky="e", padx=4, pady=3)
        self._lsr_e = tk.Entry(lu, width=18, bg="#E8E8E8", font=FONT_NORMAL, relief="sunken", bd=2, state="readonly")
        self._lsr_e.grid(row=0, column=1, sticky="w", padx=4, pady=3)
        tk.Label(lu, text="Last Saling Date",    bg=GROUP_BG, fg=LABEL_FG, font=FONT_NORMAL).grid(row=0, column=2, sticky="e", padx=4, pady=3)
        self._lsd_e = tk.Entry(lu, width=14, bg="#E8E8E8", font=FONT_NORMAL, relief="sunken", bd=2, state="readonly")
        self._lsd_e.grid(row=0, column=3, sticky="w", padx=4, pady=3)

        tk.Label(lu, text="Last Purchase Rates", bg=GROUP_BG, fg=LABEL_FG, font=FONT_NORMAL).grid(row=1, column=0, sticky="e", padx=4, pady=3)
        self._lpr_e = tk.Entry(lu, width=18, bg="#E8E8E8", font=FONT_NORMAL, relief="sunken", bd=2, state="readonly")
        self._lpr_e.grid(row=1, column=1, sticky="w", padx=4, pady=3)
        tk.Label(lu, text="Last Purchase Date",  bg=GROUP_BG, fg=LABEL_FG, font=FONT_NORMAL).grid(row=1, column=2, sticky="e", padx=4, pady=3)
        self._lpd_e = tk.Entry(lu, width=14, bg="#E8E8E8", font=FONT_NORMAL, relief="sunken", bd=2, state="readonly")
        self._lpd_e.grid(row=1, column=3, sticky="w", padx=4, pady=3)

        # ── Current Balances ───────────────────────────────────────────────────
        cb = tk.LabelFrame(c, text="CURRENT BALANCES", bg=GROUP_BG, fg=LABEL_FG,
                           font=FONT_BOLD, bd=2, relief="groove")
        cb.pack(fill="x", padx=10, pady=4)

        tk.Label(cb, text="Quantity", bg=GROUP_BG, fg=LABEL_FG, font=FONT_NORMAL).grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._qty_e = tk.Entry(cb, width=18, bg="#E8E8E8", font=FONT_NORMAL, relief="sunken", bd=2, state="readonly")
        self._qty_e.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        tk.Label(cb, text="Value",    bg=GROUP_BG, fg=LABEL_FG, font=FONT_NORMAL).grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self._val_e = tk.Entry(cb, width=18, bg="#E8E8E8", font=FONT_NORMAL, relief="sunken", bd=2, state="readonly")
        self._val_e.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        # ── Grid ───────────────────────────────────────────────────────────────
        cols = [("code","Code",70),("name","Item Name",200),("unit","Unit",50),
                ("qty","Quantity",80),("lpr","Last Pur Rate",100),("val","Value",90)]
        gf, self._tree = make_grid(c, cols, height=7)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._editable = [self._code_e, self._name_e, self._symbol_e,
                          self._head_e, self._head_name_e, self._unit_e]
        self._set_editable("disabled")

    def _set_editable(self, state):
        for e in self._editable:
            e.configure(state=state)

    def _refresh_list(self, rows=None):
        self._tree.delete(*self._tree.get_children())
        data = rows or db.get_all_inventory()
        for i, r in enumerate(data):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=(
                r["code"], r["name"], r["unit"] or "",
                f"{r['quantity']:,.2f}", f"{r['last_purchase_rate']:,.2f}", f"{r['value']:,.2f}"
            ), tags=(tag,))

    def _on_select(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        code = str(self._tree.item(sel[0])["values"][0])
        self._current_code = code
        self._load_record(code)

    def _load_record(self, code):
        r = db.get_inventory_item(code)
        if not r:
            return
        self._clear_fields(True)
        self._set_editable("normal")
        self._code_e.delete(0,"end"); self._code_e.insert(0, r["code"])
        self._name_e.delete(0,"end"); self._name_e.insert(0, r["name"])
        self._symbol_e.delete(0,"end"); self._symbol_e.insert(0, r["symbol"] or "")
        self._head_e.delete(0,"end"); self._head_e.insert(0, r["head"] or "")
        self._head_name_e.delete(0,"end"); self._head_name_e.insert(0, r["head_name"] or "")
        self._unit_e.delete(0,"end"); self._unit_e.insert(0, r["unit"] or "")
        self._code_e.configure(state="disabled")
        self._set_readonly("normal")
        for (e, v) in [
            (self._lsr_e, f"{r['last_sale_rate']:,.2f}"),
            (self._lsd_e, r["last_sale_date"] or ""),
            (self._lpr_e, f"{r['last_purchase_rate']:,.2f}"),
            (self._lpd_e, r["last_purchase_date"] or ""),
            (self._qty_e, f"{r['quantity']:,.2f}"),
            (self._val_e, f"{r['value']:,.2f}"),
        ]:
            e.delete(0,"end"); e.insert(0, v)
        self._set_readonly("readonly")

    def _set_readonly(self, state):
        for e in [self._lsr_e, self._lsd_e, self._lpr_e, self._lpd_e, self._qty_e, self._val_e]:
            e.configure(state=state)

    def _clear_fields(self, keep=False):
        for e in self._editable:
            s = e.cget("state")
            e.configure(state="normal")
            e.delete(0,"end")
            if keep:
                e.configure(state=s)
        self._set_readonly("normal")
        for e in [self._lsr_e, self._lsd_e, self._lpr_e, self._lpd_e, self._qty_e, self._val_e]:
            e.delete(0,"end")
        self._set_readonly("readonly")

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_code = None
        self._clear_fields()
        self._set_editable("normal")
        self._code_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_code:
            messagebox.showwarning("Edit","Select a record first.", parent=self); return
        self._set_editable("normal")
        self._code_e.configure(state="disabled")
        self._mode = "edit"

    def on_delete(self):
        if not self._current_code:
            messagebox.showwarning("Delete","Select a record first.", parent=self); return
        if messagebox.askyesno("Confirm",f"Delete item {self._current_code}?", parent=self):
            db.delete_inventory_item(self._current_code)
            self._current_code = None
            self._clear_fields()
            self._refresh_list()

    def on_search(self):
        self._set_editable("normal")
        self._clear_fields()
        self._code_e.focus_set()
        self._mode = "search"

    def on_save(self):
        code = self._code_e.get().strip()
        name = self._name_e.get().strip()
        if not code or not name:
            messagebox.showwarning("Validation","Code and Name are required.", parent=self); return
        today = date.today().strftime("%Y-%m-%d")
        existing = db.get_inventory_item(code)
        qty   = float(existing["quantity"])          if existing else 0.0
        value = float(existing["value"])             if existing else 0.0
        lsr   = float(existing["last_sale_rate"])    if existing else 0.0
        lsd   = existing["last_sale_date"]           if existing else today
        lpr   = float(existing["last_purchase_rate"]) if existing else 0.0
        lpd   = existing["last_purchase_date"]       if existing else today

        data = (code, name, self._symbol_e.get().strip(),
                self._head_e.get().strip(), self._head_name_e.get().strip(),
                self._unit_e.get().strip(),
                lsr, lsd, lpr, lpd, qty, value)
        db.save_inventory_item(data)
        self._current_code = code
        self._refresh_list()
        self._set_editable("disabled")
        self._mode = "view"

    def on_ignore(self):
        if self._current_code:
            self._load_record(self._current_code)
        else:
            self._clear_fields()
        self._set_editable("disabled")
        self._mode = "view"

    def _bind_keys(self):
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-e>", lambda e: self.on_edit())
        self.bind("<Alt-f>", lambda e: self.on_search())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())
        self.bind("<Return>", self._enter_search)

    def _enter_search(self, _):
        if self._mode != "search":
            return
        term = self._code_e.get().strip() or self._name_e.get().strip()
        by   = self._search_by.get()
        self._refresh_list(db.search_inventory(term, by))
        self._set_editable("disabled")
        self._mode = "view"
