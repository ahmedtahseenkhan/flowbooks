"""Journal Voucher Form"""

import tkinter as tk
from tkinter import messagebox, ttk
from config import *
from forms.base_form import BaseForm, make_grid, stripe_tree
import database as db
from datetime import date

SIDEBAR = "JOURNAL VOUCHER"
SHORTCUTS = "Alt+D : Delete    Alt+A : Add    Alt+E : Edit    Alt+S : Save    Alt+X : Exit"


class JournalVoucher(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "JOURNAL VOUCHER", SIDEBAR, username, SHORTCUTS)
        self.geometry("860x600")
        self._current_voucher = None
        self._line_data = []   # list of [ac_code, ac_title, debit, credit]
        self._build_form()
        self._refresh_voucher_list()
        self._bind_keys()

    def _build_form(self):
        c = self.content

        # ── Header fields ──────────────────────────────────────────────────────
        hf = tk.Frame(c, bg=FORM_BG)
        hf.pack(fill="x", padx=10, pady=6)

        tk.Label(hf, text="Voucher#",       bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._vno_e = tk.Entry(hf, width=12, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._vno_e.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        tk.Label(hf, text="* Prepare Date", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self._date_e = tk.Entry(hf, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._date_e.grid(row=1, column=1, sticky="w", padx=4, pady=4)
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hf, text="Description",    bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=2, column=0, sticky="e", padx=4, pady=4)
        self._desc_e = tk.Entry(hf, width=52, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._desc_e.grid(row=2, column=1, columnspan=5, sticky="ew", padx=4, pady=4)

        # Totals row
        tk.Label(hf, text="Debit",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=3, column=0, sticky="e", padx=4, pady=4)
        self._debit_var = tk.StringVar(value="0.00")
        tk.Entry(hf, textvariable=self._debit_var, width=16, bg="#E8E8E8",
                 font=FONT_NORMAL, state="readonly", relief="sunken", bd=2).grid(row=3, column=1, sticky="w", padx=4, pady=4)
        tk.Label(hf, text="Credit", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=3, column=2, sticky="e", padx=4, pady=4)
        self._credit_var = tk.StringVar(value="0.00")
        tk.Entry(hf, textvariable=self._credit_var, width=16, bg="#E8E8E8",
                 font=FONT_NORMAL, state="readonly", relief="sunken", bd=2).grid(row=3, column=3, sticky="w", padx=4, pady=4)

        # ── Line-entry grid ────────────────────────────────────────────────────
        vcols = [("ac_code","A/C Code",80), ("ac_title","A/C Title",220),
                 ("debit","Debit",100), ("credit","Credit",100)]
        gf, self._tree = make_grid(c, vcols, height=10)
        gf.pack(fill="both", expand=True, padx=10, pady=2)
        self._tree.bind("<<TreeviewSelect>>", self._on_line_select)

        # ── Line-entry row ─────────────────────────────────────────────────────
        lef = tk.Frame(c, bg=FORM_BG)
        lef.pack(fill="x", padx=10, pady=4)

        for col, txt, w in [("_le_ac_code","A/C Code",10), ("_le_ac_title","A/C Title",28),
                             ("_le_debit","Debit",12), ("_le_credit","Credit",12)]:
            tk.Label(lef, text=txt, bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=2)
            e = tk.Entry(lef, width=w, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
            e.pack(side="left", padx=2)
            setattr(self, col, e)

        tk.Button(lef, text="Add Line", bg=BTN_BG, font=FONT_SMALL,
                  relief="raised", bd=2, command=self._add_line).pack(side="left", padx=6)
        tk.Button(lef, text="Delete Transaction", bg=BTN_BG, font=FONT_SMALL,
                  relief="raised", bd=2, command=self._del_line).pack(side="left", padx=4)

        # ── Voucher list ───────────────────────────────────────────────────────
        vcols2 = [("vno","Voucher#",80),("date","Date",90),("desc","Description",220),
                  ("debit","Debit",90),("credit","Credit",90)]
        gf2, self._vlist = make_grid(c, vcols2, height=5)
        gf2.pack(fill="x", padx=10, pady=4)
        self._vlist.bind("<<TreeviewSelect>>", self._on_voucher_select)

        self._header_entries = [self._vno_e, self._date_e, self._desc_e]
        self._set_header_state("disabled")

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_voucher = None
        self._clear_form()
        self._set_header_state("normal")
        self._vno_e.configure(state="normal")
        next_no = db.next_voucher_no()
        self._vno_e.delete(0,"end"); self._vno_e.insert(0, next_no)
        self._vno_e.configure(state="readonly")
        self._date_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_voucher:
            messagebox.showwarning("Edit","Select a voucher first.", parent=self); return
        self._set_header_state("normal")
        self._vno_e.configure(state="readonly")
        self._mode = "edit"

    def on_delete(self):
        if not self._current_voucher:
            messagebox.showwarning("Delete","Select a voucher first.", parent=self); return
        if messagebox.askyesno("Confirm",f"Delete voucher {self._current_voucher}?", parent=self):
            db.delete_voucher(self._current_voucher)
            self._current_voucher = None
            self._clear_form()
            self._refresh_voucher_list()

    def on_save(self):
        vno  = self._vno_e.get().strip()
        dstr = self._date_e.get().strip()
        if not vno or not dstr:
            messagebox.showwarning("Validation","Voucher# and Date required.", parent=self); return
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date Error","Use DD/MM/YYYY format.", parent=self); return

        td = sum(r[2] for r in self._line_data)
        tc = sum(r[3] for r in self._line_data)
        header = (vno, dt, self._desc_e.get().strip(), td, tc)
        lines  = [(vno, r[0], r[1], r[2], r[3]) for r in self._line_data]
        db.save_voucher(header, lines)
        self._current_voucher = vno
        self._refresh_voucher_list()
        self._set_header_state("disabled")
        self._mode = "view"

    def on_ignore(self):
        if self._current_voucher:
            self._load_voucher(self._current_voucher)
        else:
            self._clear_form()
        self._set_header_state("disabled")
        self._mode = "view"

    # ── Line management ────────────────────────────────────────────────────────

    def _add_line(self):
        ac   = self._le_ac_code.get().strip()
        titl = self._le_ac_title.get().strip()
        try:
            dbt = float(self._le_debit.get() or 0)
            crd = float(self._le_credit.get() or 0)
        except ValueError:
            messagebox.showwarning("Input","Enter numeric Debit/Credit values.", parent=self); return
        if not ac:
            messagebox.showwarning("Input","A/C Code is required.", parent=self); return

        # If ac_title blank, try lookup
        if not titl:
            row = db.get_account(ac)
            titl = row["ac_name"] if row else ac

        self._line_data.append([ac, titl, dbt, crd])
        self._render_lines()
        self._clear_line_entry()

    def _del_line(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Delete","Select a line first.", parent=self); return
        idx = self._tree.index(sel[0])
        del self._line_data[idx]
        self._render_lines()

    def _on_line_select(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        r = self._line_data[idx]
        self._le_ac_code.delete(0,"end");  self._le_ac_code.insert(0, r[0])
        self._le_ac_title.delete(0,"end"); self._le_ac_title.insert(0, r[1])
        self._le_debit.delete(0,"end");    self._le_debit.insert(0, f"{r[2]:.2f}")
        self._le_credit.delete(0,"end");   self._le_credit.insert(0, f"{r[3]:.2f}")

    def _render_lines(self):
        self._tree.delete(*self._tree.get_children())
        td = tc = 0.0
        for i, r in enumerate(self._line_data):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=(r[0], r[1], f"{r[2]:,.2f}", f"{r[3]:,.2f}"), tags=(tag,))
            td += r[2]; tc += r[3]
        self._debit_var.set(f"{td:,.2f}")
        self._credit_var.set(f"{tc:,.2f}")

    def _clear_line_entry(self):
        for e in [self._le_ac_code, self._le_ac_title, self._le_debit, self._le_credit]:
            e.delete(0,"end")

    # ── Voucher list ───────────────────────────────────────────────────────────

    def _refresh_voucher_list(self):
        self._vlist.delete(*self._vlist.get_children())
        for i, r in enumerate(db.get_all_vouchers()):
            tag = "odd" if i % 2 else "even"
            self._vlist.insert("", "end", values=(
                r["voucher_no"], r["prepare_date"], r["description"] or "",
                f"{r['total_debit']:,.2f}", f"{r['total_credit']:,.2f}"
            ), tags=(tag,))

    def _on_voucher_select(self, _):
        sel = self._vlist.selection()
        if not sel:
            return
        vno = str(self._vlist.item(sel[0])["values"][0])
        self._current_voucher = vno
        self._load_voucher(vno)

    def _load_voucher(self, vno):
        hdr, lines = db.get_voucher(vno)
        if not hdr:
            return
        self._clear_form(True)
        self._set_header_state("normal")
        self._vno_e.delete(0,"end"); self._vno_e.insert(0, hdr["voucher_no"])
        self._date_e.delete(0,"end")
        try:
            from datetime import datetime
            self._date_e.insert(0, datetime.strptime(hdr["prepare_date"],"%Y-%m-%d").strftime("%d/%m/%Y"))
        except Exception:
            self._date_e.insert(0, hdr["prepare_date"])
        self._desc_e.delete(0,"end"); self._desc_e.insert(0, hdr["description"] or "")
        self._vno_e.configure(state="readonly")
        self._set_header_state("disabled")
        self._line_data = [[r["ac_code"], r["ac_title"], r["debit"], r["credit"]] for r in lines]
        self._render_lines()

    def _clear_form(self, keep=False):
        self._line_data = []
        self._tree.delete(*self._tree.get_children())
        self._debit_var.set("0.00"); self._credit_var.set("0.00")
        for e in [self._vno_e, self._date_e, self._desc_e]:
            s = e.cget("state")
            e.configure(state="normal")
            e.delete(0,"end")
            if keep:
                e.configure(state=s)
        if not keep:
            self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._clear_line_entry()

    def _set_header_state(self, state):
        for e in [self._date_e, self._desc_e]:
            e.configure(state=state)

    def _bind_keys(self):
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-e>", lambda e: self.on_edit())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())
