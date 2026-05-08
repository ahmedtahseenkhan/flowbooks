"""Journal Voucher Form  –  matches design images exactly."""

import tkinter as tk
from tkinter import messagebox, ttk
from config import *
from forms.base_form import BaseForm, make_grid, AccountLOVDialog
import database as db
from datetime import date

SIDEBAR   = "JOURNAL VOUCHER"
SHORTCUTS = ("Alt+D : Delete    Alt+A : Add    Alt+E : Edit    "
             "Alt+S : Save    Alt+X : Exit    F9 : List of Values[LOV]")


class JournalVoucher(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "JOURNAL VOUCHER", SIDEBAR, username, SHORTCUTS)
        self.geometry("860x640")
        self._current_voucher = None
        self._line_data = []   # [[ac_code, ac_title, debit, credit], ...]
        self._build_form()
        self._refresh_voucher_list()
        self._bind_keys()

    # ── Form layout ────────────────────────────────────────────────────────────

    def _build_form(self):
        c = self.content

        # ── Header fields ──────────────────────────────────────────────────────
        outer = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        outer.pack(fill="x", padx=10, pady=6)

        hf = tk.Frame(outer, bg=FORM_BG)
        hf.pack(fill="x", padx=8, pady=4)

        tk.Label(hf, text="Voucher#",       bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD, width=13, anchor="e").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        self._vno_e = tk.Entry(hf, width=12, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._vno_e.grid(row=0, column=1, sticky="w", padx=4, pady=3)

        tk.Label(hf, text="* Prepare Date", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD, width=13, anchor="e").grid(row=1, column=0, sticky="e", padx=4, pady=3)
        self._date_e = tk.Entry(hf, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._date_e.grid(row=1, column=1, sticky="w", padx=4, pady=3)
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hf, text="Description",    bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD, width=13, anchor="e").grid(row=2, column=0, sticky="e", padx=4, pady=3)
        self._desc_e = tk.Entry(hf, width=56, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._desc_e.grid(row=2, column=1, columnspan=5, sticky="ew", padx=4, pady=3)

        # Debit / Credit totals row
        tk.Label(hf, text="Dabit", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=3, column=0, sticky="e", padx=4, pady=3)
        self._debit_var  = tk.StringVar(value="0.00")
        tk.Entry(hf, textvariable=self._debit_var,  width=18, bg="#EEF4FF",
                 font=("Arial", 10, "bold"), fg="#000080", state="readonly",
                 relief="sunken", bd=2).grid(row=3, column=1, sticky="w", padx=4, pady=3)
        tk.Label(hf, text="Credit", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=3, column=2, sticky="e", padx=4)
        self._credit_var = tk.StringVar(value="0.00")
        tk.Entry(hf, textvariable=self._credit_var, width=18, bg="#EEF4FF",
                 font=("Arial", 10, "bold"), fg="#000080", state="readonly",
                 relief="sunken", bd=2).grid(row=3, column=3, sticky="w", padx=4, pady=3)

        # ── Line display grid ──────────────────────────────────────────────────
        vcols = [("ac_code","A/C Code",90), ("ac_title","A/C Title",260),
                 ("debit","Debit",110), ("credit","Credit",110)]
        gf, self._tree = make_grid(c, vcols, height=10)
        gf.pack(fill="both", expand=True, padx=10, pady=2)
        self._tree.bind("<<TreeviewSelect>>", self._on_line_select)
        self._tree.bind("<Delete>", lambda e: self._del_line())

        # ── Status bar (description echo) + totals ─────────────────────────────
        self._status_var = tk.StringVar(value="")
        tk.Label(c, textvariable=self._status_var, bg="#D0D4E0", fg=LABEL_FG,
                 font=FONT_SMALL, anchor="w", relief="sunken",
                 bd=1).pack(fill="x", padx=10)

        # Blue totals bar (matches image)
        tot_bar = tk.Frame(c, bg="#0000A0")
        tot_bar.pack(fill="x", padx=10, pady=0)
        self._bar_d = tk.Label(tot_bar, text="0.00", bg="#0000A0", fg="white",
                                font=("Arial", 9, "bold"), width=16, anchor="e")
        self._bar_d.pack(side="left", padx=(200, 4), pady=2)
        self._bar_c = tk.Label(tot_bar, text="0.00", bg="#0000A0", fg="white",
                                font=("Arial", 9, "bold"), width=16, anchor="e")
        self._bar_c.pack(side="left", padx=4, pady=2)

        # ── Line entry strip ───────────────────────────────────────────────────
        le = tk.Frame(c, bg=FORM_BG)
        le.pack(fill="x", padx=10, pady=4)

        tk.Label(le, text="A/C Code",  bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=2)
        self._le_ac  = tk.Entry(le, width=10, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._le_ac.pack(side="left", padx=2)

        tk.Label(le, text="A/C Title", bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=2)
        self._le_title = tk.Entry(le, width=28, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._le_title.pack(side="left", padx=2)

        tk.Label(le, text="Debit",     bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=2)
        self._le_debit  = tk.Entry(le, width=12, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._le_debit.pack(side="left", padx=2)

        tk.Label(le, text="Credit",    bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=2)
        self._le_credit = tk.Entry(le, width=12, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._le_credit.pack(side="left", padx=2)

        tk.Button(le, text="Add Line",          bg=BTN_BG, font=FONT_SMALL, relief="raised",
                  bd=2, command=self._add_line).pack(side="left", padx=6)
        tk.Button(le, text="Delete Transaction", bg=BTN_BG, font=FONT_SMALL, relief="raised",
                  bd=2, command=self._del_line).pack(side="left", padx=2)

        # F9 on A/C Code field
        self._le_ac.bind("<F9>",       self._f9_ac)
        self._le_ac.bind("<FocusOut>", self._lookup_ac)
        self._le_ac.bind("<Return>",   lambda e: self._le_title.focus_set())

        # ── Previous vouchers list ─────────────────────────────────────────────
        vcols2 = [("vno","Voucher#",70), ("date","Date",90),
                  ("desc","Description",240), ("debit","Debit",90), ("credit","Credit",90)]
        gf2, self._vlist = make_grid(c, vcols2, height=4)
        gf2.pack(fill="x", padx=10, pady=4)
        self._vlist.bind("<<TreeviewSelect>>", self._on_voucher_select)

        self._set_header_state("disabled")

    # ── F9 LOV ─────────────────────────────────────────────────────────────────

    def _f9_ac(self, _event):
        term = self._le_ac.get().strip()
        dlg  = AccountLOVDialog(self, term)
        if dlg.result:
            code, name = dlg.result
            self._le_ac.delete(0, "end");    self._le_ac.insert(0, code)
            self._le_title.delete(0, "end"); self._le_title.insert(0, name)
            self._le_debit.focus_set()

    def _lookup_ac(self, _event):
        code = self._le_ac.get().strip()
        if not code or self._le_title.get().strip():
            return
        row = db.get_account(code)
        if row:
            self._le_title.delete(0, "end")
            self._le_title.insert(0, row["ac_name"])

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_voucher = None
        self._clear_form()
        self._set_header_state("normal")
        self._vno_e.configure(state="normal")
        self._vno_e.delete(0, "end")
        self._vno_e.insert(0, db.next_voucher_no())
        self._vno_e.configure(state="readonly")
        self._date_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_voucher:
            messagebox.showwarning("Edit", "Select a voucher first.", parent=self); return
        self._set_header_state("normal")
        self._vno_e.configure(state="readonly")
        self._mode = "edit"

    def on_delete(self):
        if not self._current_voucher:
            messagebox.showwarning("Delete", "Select a voucher first.", parent=self); return
        if messagebox.askyesno("Confirm", f"Delete voucher {self._current_voucher}?", parent=self):
            db.delete_voucher(self._current_voucher)
            self._current_voucher = None
            self._clear_form()
            self._refresh_voucher_list()

    def on_save(self):
        vno  = self._vno_e.get().strip()
        dstr = self._date_e.get().strip()
        if not vno or not dstr:
            messagebox.showwarning("Validation", "Voucher# and Date required.", parent=self); return
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date Error", "Use DD/MM/YYYY format.", parent=self); return
        if not self._line_data:
            messagebox.showwarning("Validation", "Add at least one transaction line.", parent=self); return

        td = sum(r[2] for r in self._line_data)
        tc = sum(r[3] for r in self._line_data)
        header = (vno, dt, self._desc_e.get().strip(), td, tc)
        lines  = [(vno, r[0], r[1], r[2], r[3]) for r in self._line_data]
        db.save_voucher(header, lines)
        self._current_voucher = vno
        self._refresh_voucher_list()
        self._set_header_state("disabled")
        self._mode = "view"
        messagebox.showinfo("Saved", f"Voucher {vno} saved successfully.", parent=self)

    def on_ignore(self):
        if self._current_voucher:
            self._load_voucher(self._current_voucher)
        else:
            self._clear_form()
        self._set_header_state("disabled")
        self._mode = "view"

    # ── Line management ────────────────────────────────────────────────────────

    def _add_line(self):
        ac    = self._le_ac.get().strip()
        title = self._le_title.get().strip() or ac
        try:
            dbt = float(self._le_debit.get()  or 0)
            crd = float(self._le_credit.get() or 0)
        except ValueError:
            messagebox.showwarning("Input", "Enter numeric Debit/Credit values.", parent=self); return
        if not ac:
            messagebox.showwarning("Input", "A/C Code is required.", parent=self); return
        if dbt == 0 and crd == 0:
            messagebox.showwarning("Input", "Enter Debit or Credit amount.", parent=self); return
        if not title:
            row = db.get_account(ac)
            title = row["ac_name"] if row else ac

        self._line_data.append([ac, title, dbt, crd])
        self._render_lines()
        self._clear_line_entry()
        self._le_ac.focus_set()

    def _del_line(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Delete", "Select a line to delete.", parent=self); return
        idx = self._tree.index(sel[0])
        del self._line_data[idx]
        self._render_lines()

    def _on_line_select(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        r   = self._line_data[idx]
        self._le_ac.delete(0, "end");     self._le_ac.insert(0, r[0])
        self._le_title.delete(0, "end");  self._le_title.insert(0, r[1])
        self._le_debit.delete(0, "end");  self._le_debit.insert(0, f"{r[2]:.2f}")
        self._le_credit.delete(0, "end"); self._le_credit.insert(0, f"{r[3]:.2f}")

    def _render_lines(self):
        self._tree.delete(*self._tree.get_children())
        td = tc = 0.0
        for i, r in enumerate(self._line_data):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=(
                r[0], r[1],
                f"{r[2]:,.2f}" if r[2] else "",
                f"{r[3]:,.2f}" if r[3] else ""
            ), tags=(tag,))
            td += r[2]; tc += r[3]
        self._debit_var.set(f"{td:,.2f}")
        self._credit_var.set(f"{tc:,.2f}")
        self._bar_d.config(text=f"{td:,.2f}")
        self._bar_c.config(text=f"{tc:,.2f}")
        self._status_var.set(self._desc_e.get().strip())

    def _clear_line_entry(self):
        for e in [self._le_ac, self._le_title, self._le_debit, self._le_credit]:
            e.delete(0, "end")

    # ── Voucher list ───────────────────────────────────────────────────────────

    def _refresh_voucher_list(self):
        self._vlist.delete(*self._vlist.get_children())
        for i, r in enumerate(db.get_all_vouchers()):
            tag = "odd" if i % 2 else "even"
            self._vlist.insert("", "end", iid=str(r["voucher_no"]), values=(
                r["voucher_no"], r["prepare_date"],
                r["description"] or "",
                f"{r['total_debit']:,.2f}", f"{r['total_credit']:,.2f}"
            ), tags=(tag,))

    def _on_voucher_select(self, _):
        sel = self._vlist.selection()
        if not sel:
            return
        self._current_voucher = str(self._vlist.item(sel[0])["values"][0])
        self._load_voucher(self._current_voucher)

    def _load_voucher(self, vno):
        hdr, lines = db.get_voucher(vno)
        if not hdr:
            return
        self._clear_form(keep=True)
        self._set_header_state("normal")
        self._vno_e.configure(state="normal")
        self._vno_e.delete(0, "end"); self._vno_e.insert(0, hdr["voucher_no"])
        self._vno_e.configure(state="readonly")
        self._date_e.delete(0, "end")
        try:
            from datetime import datetime
            self._date_e.insert(0, datetime.strptime(hdr["prepare_date"], "%Y-%m-%d").strftime("%d/%m/%Y"))
        except Exception:
            self._date_e.insert(0, hdr["prepare_date"])
        self._desc_e.delete(0, "end"); self._desc_e.insert(0, hdr["description"] or "")
        self._set_header_state("disabled")
        self._line_data = [[r["ac_code"], r["ac_title"], r["debit"], r["credit"]] for r in lines]
        self._render_lines()

    def _clear_form(self, keep=False):
        self._line_data = []
        self._tree.delete(*self._tree.get_children())
        self._debit_var.set("0.00"); self._credit_var.set("0.00")
        self._bar_d.config(text="0.00"); self._bar_c.config(text="0.00")
        self._status_var.set("")
        for e in [self._vno_e, self._date_e, self._desc_e]:
            s = e.cget("state")
            e.configure(state="normal"); e.delete(0, "end")
            if keep:
                e.configure(state=s)
        if not keep:
            self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._clear_line_entry()

    def _set_header_state(self, state):
        for e in [self._date_e, self._desc_e]:
            e.configure(state=state)

    # ── Key bindings ───────────────────────────────────────────────────────────

    def _bind_keys(self):
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-e>", lambda e: self.on_edit())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())
