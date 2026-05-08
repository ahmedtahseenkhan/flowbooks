"""Opening Balances Form / OBF"""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, make_grid
import database as db
from datetime import date

SIDEBAR = "OPENING BALANCES FORM"


class OpeningBalancesForm(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "OPENING BALANCES FORM / OBF", SIDEBAR, username,
                         "Alt+A : Add Line    Alt+D : Delete Line    Alt+S : Save    Alt+X : Exit")
        self.geometry("800x560")
        self._build_form()
        self._refresh()

    def _build_form(self):
        c = self.content

        # ── Header ─────────────────────────────────────────────────────────────
        hf = tk.Frame(c, bg=FORM_BG)
        hf.pack(fill="x", padx=10, pady=8)

        tk.Label(hf, text="Date", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._date_e = tk.Entry(hf, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._date_e.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))

        # ── Line entry ─────────────────────────────────────────────────────────
        lf = tk.Frame(c, bg=FORM_BG)
        lf.pack(fill="x", padx=10, pady=4)

        for attr, lbl, w in [("_le_code","A/C Code",12),("_le_name","A/C Name",28),
                              ("_le_debit","Debit",12),("_le_credit","Credit",12)]:
            tk.Label(lf, text=lbl, bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=2)
            e = tk.Entry(lf, width=w, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
            e.pack(side="left", padx=2)
            setattr(self, attr, e)

        self._le_code.bind("<FocusOut>", self._lookup_ac)
        tk.Button(lf, text="Add Line",    bg=BTN_BG, font=FONT_SMALL, relief="raised", bd=2,
                  command=self._add_line).pack(side="left", padx=6)
        tk.Button(lf, text="Remove Line", bg=BTN_BG, font=FONT_SMALL, relief="raised", bd=2,
                  command=self._del_line).pack(side="left", padx=4)

        # ── Grid ───────────────────────────────────────────────────────────────
        cols = [("ac_code","A/C Code",90),("ac_name","A/C Name",220),
                ("debit","Debit",100),("credit","Credit",100),("dated","Date",100)]
        gf, self._tree = make_grid(c, cols, height=14)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_sel)

        # Totals
        tf = tk.Frame(c, bg=FORM_BG)
        tf.pack(fill="x", padx=10, pady=2)
        tk.Label(tf, text="Total Debit",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
        self._total_d = tk.StringVar(value="0.00")
        tk.Entry(tf, textvariable=self._total_d, width=14, bg="#E8E8E8",
                 font=FONT_NORMAL, state="readonly", relief="sunken", bd=2).pack(side="left", padx=4)
        tk.Label(tf, text="Total Credit", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=8)
        self._total_c = tk.StringVar(value="0.00")
        tk.Entry(tf, textvariable=self._total_c, width=14, bg="#E8E8E8",
                 font=FONT_NORMAL, state="readonly", relief="sunken", bd=2).pack(side="left", padx=4)

    # ── Lookup ─────────────────────────────────────────────────────────────────

    def _lookup_ac(self, _):
        code = self._le_code.get().strip()
        if not code:
            return
        row = db.get_account(code)
        if row:
            self._le_name.delete(0,"end")
            self._le_name.insert(0, row["ac_name"])

    # ── Line management ────────────────────────────────────────────────────────

    def _add_line(self):
        code  = self._le_code.get().strip()
        name  = self._le_name.get().strip() or code
        dated = self._date_e.get().strip()
        try:
            from datetime import datetime
            dt = datetime.strptime(dated, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date","Use DD/MM/YYYY format.", parent=self); return
        try:
            dbt = float(self._le_debit.get() or 0)
            crd = float(self._le_credit.get() or 0)
        except ValueError:
            messagebox.showwarning("Input","Enter numeric values.", parent=self); return
        if not code:
            messagebox.showwarning("Input","A/C Code required.", parent=self); return

        db.save_opening_balance((code, name, dbt, crd, dt))
        self._refresh()
        for e in [self._le_code, self._le_name, self._le_debit, self._le_credit]:
            e.delete(0,"end")

    def _del_line(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Delete","Select a record first.", parent=self); return
        # The tree iid is the database row id (set in _refresh). The previous
        # implementation read values[4] which is the date, so the DELETE
        # silently matched no rows.
        try:
            row_id = int(sel[0])
        except (TypeError, ValueError):
            messagebox.showerror("Delete","Could not resolve row id.", parent=self); return
        if messagebox.askyesno("Confirm","Delete this opening balance entry?", parent=self):
            db.delete_opening_balance(row_id)
            self._refresh()

    def _on_sel(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        self._le_code.delete(0,"end");   self._le_code.insert(0, vals[0])
        self._le_name.delete(0,"end");   self._le_name.insert(0, vals[1])
        self._le_debit.delete(0,"end");  self._le_debit.insert(0, vals[2])
        self._le_credit.delete(0,"end"); self._le_credit.insert(0, vals[3])

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        rows = db.get_opening_balances()
        td = tc = 0.0
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(r["id"]), values=(
                r["ac_code"], r["ac_name"],
                f"{r['debit']:,.2f}", f"{r['credit']:,.2f}", r["dated"]
            ), tags=(tag,))
            td += r["debit"]; tc += r["credit"]
        self._total_d.set(f"{td:,.2f}")
        self._total_c.set(f"{tc:,.2f}")

    def on_add(self):
        for e in [self._le_code, self._le_name, self._le_debit, self._le_credit]:
            e.delete(0,"end")
        self._le_code.focus_set()
