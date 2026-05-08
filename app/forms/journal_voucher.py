"""
Journal Voucher Form – keyboard-driven, matches Oracle Forms UX exactly.

Tab flow:
  Voucher# (auto) → Date → Description
  → [grid row 1] A/C Code → [auto: A/C Title] → Debit → Credit
  → [grid row 2] A/C Code → ...  (new row created automatically)

F9 on A/C Code  → SELECT THE ACCOUNT popup
Totals update live on every keystroke.
Delete Transaction button removes the focused grid row.
"""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, InlineEntryGrid, AccountLOVDialog, TransactionSearchDialog
import database as db
from datetime import date

SIDEBAR   = "JOURNAL VOUCHER"
SHORTCUTS = ("Alt+D : Delete    Alt+A : Add    Alt+E : Edit    "
             "Alt+S : Save    Alt+X : Exit    F9 : List of Values[LOV]")

JV_COLS = [
    {"id": "ac_code",  "header": "A/C Code",  "width": 10, "editable": True,  "align": "left"},
    {"id": "ac_title", "header": "A/C Title",  "width": 30, "editable": False, "align": "left"},
    {"id": "debit",    "header": "Debit",      "width": 13, "editable": True,  "align": "right"},
    {"id": "credit",   "header": "Credit",     "width": 13, "editable": True,  "align": "right"},
]


class JournalVoucher(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "JOURNAL VOUCHER", SIDEBAR, username, SHORTCUTS)
        self.geometry("820x600")
        self._current_voucher = None
        self._build_form()
        self._refresh_voucher_list()
        self._bind_keys()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_form(self):
        c = self.content

        # ── Header panel ───────────────────────────────────────────────────────
        hp = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hp.pack(fill="x", padx=10, pady=6)

        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)

        # Row 0: Voucher#
        tk.Label(hp, text="Voucher#", **lkw, width=14, anchor="e").grid(
            row=0, column=0, sticky="e", padx=(10, 4), pady=5)
        self._vno_e = tk.Entry(hp, width=10, bg=ENTRY_BG, font=FONT_NORMAL,
                               relief="sunken", bd=2)
        self._vno_e.grid(row=0, column=1, sticky="w", padx=4, pady=5)

        # Row 1: * Prepare Date
        tk.Label(hp, text="* Prepare Date", **lkw, width=14, anchor="e").grid(
            row=1, column=0, sticky="e", padx=(10, 4), pady=5)
        self._date_e = tk.Entry(hp, width=14, bg="#D0DCF0", font=FONT_NORMAL,
                                relief="sunken", bd=2)
        self._date_e.grid(row=1, column=1, sticky="w", padx=4, pady=5)
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))

        # Row 2: Description
        tk.Label(hp, text="Description", **lkw, width=14, anchor="e").grid(
            row=2, column=0, sticky="e", padx=(10, 4), pady=5)
        self._desc_e = tk.Entry(hp, width=52, bg=ENTRY_BG, font=FONT_NORMAL,
                                relief="sunken", bd=2)
        self._desc_e.grid(row=2, column=1, columnspan=5, sticky="ew",
                          padx=(4, 10), pady=5)

        # Row 3: Dabit / Credit totals (bold blue, readonly)
        tk.Label(hp, text="Dabit", **lkw).grid(row=3, column=0, sticky="e",
                                                padx=(10, 4), pady=5)
        self._debit_var  = tk.StringVar(value="")
        tk.Entry(hp, textvariable=self._debit_var, width=18,
                 bg="#EEF4FF", fg="#000080", font=("Arial", 10, "bold"),
                 state="readonly", relief="sunken", bd=2,
                 justify="right").grid(row=3, column=1, sticky="w", padx=4, pady=5)

        tk.Label(hp, text="Credit", **lkw).grid(row=3, column=2, sticky="e",
                                                 padx=(10, 4), pady=5)
        self._credit_var = tk.StringVar(value="")
        tk.Entry(hp, textvariable=self._credit_var, width=18,
                 bg="#EEF4FF", fg="#000080", font=("Arial", 10, "bold"),
                 state="readonly", relief="sunken", bd=2,
                 justify="right").grid(row=3, column=3, sticky="w", padx=4, pady=5)

        # ── Inline entry grid ──────────────────────────────────────────────────
        self._grid = InlineEntryGrid(c, JV_COLS, start_rows=15)
        self._grid.pack(fill="both", expand=True, padx=10, pady=2)
        self._grid.on_focus_out  = self._grid_focus_out
        self._grid.on_f9         = self._grid_f9
        self._grid.on_change     = self._grid_changed
        self._grid.on_delete_row = lambda _: self._update_totals()

        # ── Status echo + blue totals bar ─────────────────────────────────────
        self._echo_var = tk.StringVar(value="")
        tk.Label(c, textvariable=self._echo_var,
                 bg="#C8D0DC", fg=LABEL_FG, font=FONT_SMALL,
                 anchor="w", relief="sunken", bd=1).pack(fill="x", padx=10)

        bar = tk.Frame(c, bg="#0000A0")
        bar.pack(fill="x", padx=10)
        self._bar_d = tk.Label(bar, text="", bg="#0000A0", fg="white",
                               font=("Arial", 9, "bold"), anchor="e", width=18)
        self._bar_d.pack(side="left", padx=(220, 2), pady=2)
        self._bar_c = tk.Label(bar, text="", bg="#0000A0", fg="white",
                               font=("Arial", 9, "bold"), anchor="e", width=18)
        self._bar_c.pack(side="left", padx=2, pady=2)

        # ── Delete Transaction + voucher list ──────────────────────────────────
        bf = tk.Frame(c, bg=FORM_BG)
        bf.pack(fill="x", padx=10, pady=4)
        tk.Button(bf, text="Delete Transaction", bg=BTN_BG, font=FONT_SMALL,
                  relief="raised", bd=2,
                  command=self._grid.delete_focused_row).pack(side="left")

        # Voucher list (compact)
        from forms.base_form import make_grid
        vcols = [("vno","Voucher#",70), ("date","Date",90),
                 ("desc","Description",230), ("debit","Debit",90), ("credit","Credit",90)]
        gf, self._vlist = make_grid(c, vcols, height=4)
        gf.pack(fill="x", padx=10, pady=4)
        self._vlist.bind("<<TreeviewSelect>>", self._on_voucher_select)

        # Tab from Description → grid
        self._desc_e.bind("<Tab>", lambda e: (self._grid.focus_first(), "break")[1])
        self._desc_e.bind("<Return>", lambda e: self._grid.focus_first())

        self._set_header_state("disabled")

    # ── Grid callbacks ─────────────────────────────────────────────────────────

    def _grid_focus_out(self, row_idx, col_id, value):
        if col_id == "ac_code" and value:
            # Auto-fill title
            row = db.get_account(value)
            title = row["ac_name"] if row else value
            self._grid.set_value(row_idx, "ac_title", title)
        elif col_id in ("debit", "credit") and value:
            # Format as number
            try:
                n = float(value.replace(",", ""))
                self._grid.set_value(row_idx, col_id, f"{n:,.2f}")
            except ValueError:
                pass
        self._update_totals()

    def _grid_f9(self, row_idx, col_id, value):
        if col_id == "ac_code":
            dlg = AccountLOVDialog(self, value)
            if dlg.result:
                code, name = dlg.result
                self._grid.set_value(row_idx, "ac_code",  code)
                self._grid.set_value(row_idx, "ac_title", name)
                # Move focus to Debit
                self._grid._widgets[row_idx]["debit"].focus_set()
                self._update_totals()

    def _grid_changed(self, rows):
        self._update_totals()

    def _update_totals(self):
        rows = self._grid.get_all_rows()
        td = tc = 0.0
        for r in rows:
            try:
                td += float(r.get("debit",  "0").replace(",", "") or 0)
            except ValueError:
                pass
            try:
                tc += float(r.get("credit", "0").replace(",", "") or 0)
            except ValueError:
                pass
        self._debit_var.set(f"{td:,.2f}" if td else "")
        self._credit_var.set(f"{tc:,.2f}" if tc else "")
        self._bar_d.config(text=f"{td:,.2f}" if td else "0.00")
        self._bar_c.config(text=f"{tc:,.2f}" if tc else "0.00")
        self._echo_var.set(self._desc_e.get().strip())

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_voucher = None
        self._grid.reset()
        self._set_header_state("normal")
        self._vno_e.configure(state="normal")
        self._vno_e.delete(0, "end")
        self._vno_e.insert(0, db.next_voucher_no())
        self._vno_e.configure(state="readonly")
        self._date_e.delete(0, "end")
        self._date_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._desc_e.delete(0, "end")
        self._debit_var.set(""); self._credit_var.set("")
        self._bar_d.config(text=""); self._bar_c.config(text="")
        self._echo_var.set("")
        self._date_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_voucher:
            messagebox.showwarning("Edit", "Select a voucher first.", parent=self)
            return
        self._set_header_state("normal")
        self._vno_e.configure(state="readonly")
        self._grid.set_editable(True)
        self._mode = "edit"

    def on_delete(self):
        if not self._current_voucher:
            messagebox.showwarning("Delete", "Select a voucher first.", parent=self)
            return
        if messagebox.askyesno("Confirm",
                               f"Delete voucher {self._current_voucher}?", parent=self):
            db.delete_voucher(self._current_voucher)
            self._current_voucher = None
            self._grid.reset()
            self._set_header_state("disabled")
            self._refresh_voucher_list()

    def on_search(self):
        # Open a simple search by voucher number
        vno = self._vno_e.get().strip()
        if vno:
            self._load_voucher(vno)
        else:
            messagebox.showinfo("Search",
                                "Type a Voucher# in the field then press Search,\n"
                                "or select from the list below.", parent=self)

    def on_save(self):
        vno  = self._vno_e.get().strip()
        dstr = self._date_e.get().strip()
        if not vno or not dstr:
            messagebox.showwarning("Validation",
                                   "Voucher# and Date required.", parent=self)
            return
        try:
            from datetime import datetime
            dt = datetime.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use DD/MM/YYYY format.", parent=self)
            return

        rows = self._grid.get_all_rows()
        if not rows:
            messagebox.showwarning("Validation",
                                   "Enter at least one transaction line.", parent=self)
            return

        def _f(v):
            try:
                return float(str(v).replace(",", "") or 0)
            except ValueError:
                return 0.0

        td = sum(_f(r.get("debit",  0)) for r in rows)
        tc = sum(_f(r.get("credit", 0)) for r in rows)

        header = (vno, dt, self._desc_e.get().strip(), td, tc)
        lines  = [(vno,
                   r["ac_code"],
                   r.get("ac_title", ""),
                   _f(r.get("debit",  0)),
                   _f(r.get("credit", 0)))
                  for r in rows if r.get("ac_code")]

        db.save_voucher(header, lines)
        self._current_voucher = vno
        self._set_header_state("disabled")
        self._grid.set_editable(False)
        self._refresh_voucher_list()
        self._mode = "view"
        messagebox.showinfo("Saved", f"Voucher {vno} saved.", parent=self)

    def on_ignore(self):
        if self._current_voucher:
            self._load_voucher(self._current_voucher)
        else:
            self._grid.reset()
            self._set_header_state("disabled")
        self._mode = "view"

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
        vno = str(self._vlist.item(sel[0])["values"][0])
        self._current_voucher = vno
        self._load_voucher(vno)

    def _load_voucher(self, vno):
        hdr, lines = db.get_voucher(vno)
        if not hdr:
            return
        self._set_header_state("normal")
        self._vno_e.configure(state="normal")
        self._vno_e.delete(0, "end"); self._vno_e.insert(0, hdr["voucher_no"])
        self._vno_e.configure(state="readonly")
        self._date_e.delete(0, "end")
        try:
            from datetime import datetime
            self._date_e.insert(
                0, datetime.strptime(hdr["prepare_date"], "%Y-%m-%d").strftime("%d/%m/%Y"))
        except Exception:
            self._date_e.insert(0, hdr["prepare_date"])
        self._desc_e.delete(0, "end")
        self._desc_e.insert(0, hdr["description"] or "")
        self._set_header_state("disabled")

        row_data = [{"ac_code":  r["ac_code"],
                     "ac_title": r["ac_title"],
                     "debit":    f"{r['debit']:,.2f}" if r["debit"]  else "",
                     "credit":   f"{r['credit']:,.2f}" if r["credit"] else ""}
                    for r in lines]
        self._grid.load_rows(row_data)
        self._grid.set_editable(False)
        self._update_totals()

    # ── Helpers ────────────────────────────────────────────────────────────────

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
