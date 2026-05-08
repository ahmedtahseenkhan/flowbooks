"""Chart of Accounts – Special / General (CAS / CAG)"""

import tkinter as tk
from tkinter import messagebox, ttk
from config import *
from forms.base_form import BaseForm, make_grid, stripe_tree
import database as db

SHORTCUTS = (
    "Alt+D : Delete Record    Alt+A : Add Record    Alt+E : Edit Record    "
    "Alt+F : Find/Search Record    Alt+S : Save the Record\n"
    "Alt+I : Ignore    Alt+P : Print    F-7 : Call Setup Forms    "
    "Alt+X : Exit    F-9 : List of Values[LOV]"
)

SIDEBAR = "CHART OF ACCOUNT"


class ChartOfAccounts(BaseForm):

    def __init__(self, master, username="ADMIN", mode="special"):
        label = "Chart of Account - Special" if mode == "special" else "Chart of Account - General"
        super().__init__(master, label, SIDEBAR, username, SHORTCUTS)
        self.geometry("800x560")
        self._mode_type = mode
        self._current_code = None
        self._entries = []
        self._build_form()
        self._refresh_list()
        self._bind_keys()

    # ── Form layout ────────────────────────────────────────────────────────────

    def _build_form(self):
        c = self.content
        c.columnconfigure(1, weight=1)

        # Search-mode radio (hidden row, shown during search)
        self._search_by = tk.StringVar(value="code")
        sf = tk.Frame(c, bg=FORM_BG)
        sf.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 0))
        tk.Radiobutton(sf, text="Search By Code", variable=self._search_by, value="code",
                       bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left")
        tk.Radiobutton(sf, text="Search By Name", variable=self._search_by, value="name",
                       bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=8)

        # ── Fields ─────────────────────────────────────────────────────────────
        fields = tk.Frame(c, bg=FORM_BG)
        fields.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=4)
        fields.columnconfigure(1, weight=1)
        fields.columnconfigure(3, weight=2)

        tk.Label(fields, text="A/C Code",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._ac_code_e = tk.Entry(fields, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._ac_code_e.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        tk.Label(fields, text="A/C Name",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self._ac_name_e = tk.Entry(fields, width=38, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._ac_name_e.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        tk.Label(fields, text="Head Code", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self._head_code_e = tk.Entry(fields, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._head_code_e.grid(row=1, column=1, sticky="w", padx=4, pady=4)

        tk.Label(fields, text="Head Name", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=1, column=2, sticky="e", padx=4, pady=4)
        self._head_name_e = tk.Entry(fields, width=38, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._head_name_e.grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        tk.Label(fields, text="A/C Path",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=2, column=0, sticky="e", padx=4, pady=4)
        self._path_e = tk.Entry(fields, width=54, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._path_e.grid(row=2, column=1, columnspan=3, sticky="ew", padx=4, pady=4)

        tk.Label(fields, text="Opening",   bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=3, column=0, sticky="e", padx=4, pady=4)
        self._opening_e = tk.Entry(fields, width=18, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._opening_e.grid(row=3, column=1, sticky="w", padx=4, pady=4)

        tk.Label(fields, text="Balance",   bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=3, column=2, sticky="e", padx=4, pady=4)
        self._balance_e = tk.Entry(fields, width=18, bg="#E8E8E8", font=FONT_NORMAL, relief="sunken", bd=2, state="readonly")
        self._balance_e.grid(row=3, column=3, sticky="w", padx=4, pady=4)

        self._entries = [self._ac_code_e, self._ac_name_e, self._head_code_e,
                         self._head_name_e, self._path_e, self._opening_e]

        # ── Accounts list grid ─────────────────────────────────────────────────
        cols = [("code","A/C Code",90), ("name","A/C Name",200),
                ("head","Head",70), ("opening","Opening",90), ("balance","Balance",90)]
        gf, self._tree = make_grid(c, cols, height=9)
        gf.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=10, pady=6)
        c.rowconfigure(2, weight=1)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._set_fields_state("disabled")

    def _set_fields_state(self, state):
        for e in self._entries:
            e.configure(state=state)

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_code = None
        self._clear_fields()
        self._set_fields_state("normal")
        self._ac_code_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_code:
            messagebox.showwarning("Edit", "Select a record first.", parent=self)
            return
        self._set_fields_state("normal")
        self._ac_code_e.configure(state="disabled")
        self._mode = "edit"

    def on_delete(self):
        if not self._current_code:
            messagebox.showwarning("Delete", "Select a record first.", parent=self)
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete account {self._current_code}?", parent=self):
            db.delete_account(self._current_code)
            self._current_code = None
            self._clear_fields()
            self._refresh_list()

    def on_search(self):
        self._set_fields_state("normal")
        self._clear_fields()
        self._ac_code_e.focus_set()
        self._mode = "search"

    def on_save(self):
        code = self._ac_code_e.get().strip()
        name = self._ac_name_e.get().strip()
        if not code or not name:
            messagebox.showwarning("Validation", "A/C Code and Name are required.", parent=self)
            return
        try:
            opening = float(self._opening_e.get() or 0)
        except ValueError:
            opening = 0.0

        data = (code, name,
                self._head_code_e.get().strip(),
                self._head_name_e.get().strip(),
                self._path_e.get().strip(),
                opening, opening)
        db.save_account(data)
        self._current_code = code
        self._refresh_list()
        self._set_fields_state("disabled")
        self._mode = "view"

    def on_ignore(self):
        if self._current_code:
            self._load_record(self._current_code)
        else:
            self._clear_fields()
        self._set_fields_state("disabled")
        self._mode = "view"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _refresh_list(self, rows=None):
        self._tree.delete(*self._tree.get_children())
        data = rows if rows is not None else db.get_all_accounts()
        for i, r in enumerate(data):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=(
                r["ac_code"], r["ac_name"], r["head_code"],
                f"{r['opening']:,.2f}", f"{r['balance']:,.2f}"
            ), tags=(tag,))

    def _on_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        code = self._tree.item(sel[0])["values"][0]
        self._current_code = str(code)
        self._load_record(self._current_code)

    def _load_record(self, code):
        row = db.get_account(code)
        if not row:
            return
        self._clear_fields(keep_state=True)
        self._ac_code_e.configure(state="normal")
        self._ac_code_e.insert(0, row["ac_code"])
        self._ac_name_e.insert(0, row["ac_name"])
        self._head_code_e.insert(0, row["head_code"] or "")
        self._head_name_e.insert(0, row["head_name"] or "")
        self._path_e.insert(0, row["ac_path"] or "")
        self._opening_e.insert(0, f"{row['opening']:,.2f}")
        self._balance_e.configure(state="normal")
        self._balance_e.delete(0, "end")
        self._balance_e.insert(0, f"{row['balance']:,.2f}")
        self._balance_e.configure(state="readonly")
        self._ac_code_e.configure(state="disabled")

    def _clear_fields(self, keep_state=False):
        state = None
        for e in self._entries:
            if not keep_state:
                state = e.cget("state")
                e.configure(state="normal")
            e.delete(0, "end")
            if not keep_state and state:
                e.configure(state=state)
        self._balance_e.configure(state="normal")
        self._balance_e.delete(0, "end")
        self._balance_e.configure(state="readonly")

    def _bind_keys(self):
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-e>", lambda e: self.on_edit())
        self.bind("<Alt-f>", lambda e: self.on_search())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())
        self.bind("<Return>", self._on_return_search)

    def _on_return_search(self, _event):
        if self._mode != "search":
            return
        term = self._ac_code_e.get().strip() or self._ac_name_e.get().strip()
        by = self._search_by.get()
        results = db.search_accounts(term, by)
        self._refresh_list(results)
        self._mode = "view"
        self._set_fields_state("disabled")


# ── Define Heading Accounts ────────────────────────────────────────────────────

class DefineHeadingAccounts(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "Define Heading Accounts", "DEFINE HEADING ACCOUNTS", username,
                         "Alt+A : Add    Alt+D : Delete    Alt+S : Save    Alt+X : Exit")
        self.geometry("600x480")
        self._current = None
        self._build_form()
        self._refresh()

    def _build_form(self):
        c = self.content
        c.columnconfigure(1, weight=1)

        row0 = tk.Frame(c, bg=FORM_BG)
        row0.pack(fill="x", padx=10, pady=8)

        tk.Label(row0, text="Head Code", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._code_e = tk.Entry(row0, width=14, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._code_e.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        tk.Label(row0, text="Head Name", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self._name_e = tk.Entry(row0, width=36, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._name_e.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        cols = [("code","Head Code",100), ("name","Head Name",300)]
        gf, self._tree = make_grid(c, cols, height=12)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_sel)

        self._entries = [self._code_e, self._name_e]
        self._set_fields_state("disabled")

    def _set_fields_state(self, state):
        for e in self._entries:
            e.configure(state=state)

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_all_heads()):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=(r["head_code"], r["head_name"]), tags=(tag,))

    def _on_sel(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        self._current = str(vals[0])
        self._code_e.configure(state="normal"); self._code_e.delete(0,"end"); self._code_e.insert(0, vals[0])
        self._name_e.configure(state="normal"); self._name_e.delete(0,"end"); self._name_e.insert(0, vals[1])
        self._code_e.configure(state="disabled")

    def on_add(self):
        self._current = None
        self._code_e.configure(state="normal"); self._code_e.delete(0,"end")
        self._name_e.configure(state="normal"); self._name_e.delete(0,"end")
        self._code_e.focus_set()

    def on_save(self):
        code = self._code_e.get().strip(); name = self._name_e.get().strip()
        if not code or not name:
            messagebox.showwarning("Validation", "Head Code and Name required.", parent=self); return
        db.save_head(code, name)
        self._refresh()
        self._set_fields_state("disabled")

    def on_delete(self):
        if not self._current:
            messagebox.showwarning("Delete", "Select a record first.", parent=self); return
        if messagebox.askyesno("Confirm", f"Delete head {self._current}?", parent=self):
            db.delete_head(self._current)
            self._current = None
            self._set_fields_state("disabled")
            self._refresh()

    def on_ignore(self):
        self._set_fields_state("disabled")
