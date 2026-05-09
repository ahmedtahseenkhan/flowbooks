"""Chart of Accounts – Special / General (CAS / CAG)  –  form-only, no grid."""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, AccountLOVDialog
import database as db
from forms.base_form import lov_button

SHORTCUTS = (
    "Alt+D : Delete Record    Alt+A : Add Record    Alt+E : Edit Record    "
    "Alt+F : Find/Search Record    Alt+S : Save the Record\n"
    "Alt+I : Ignore    Alt+P : Print    F-7 : Call Setup Forms    "
    "Alt+X : Exit    F-9 : List of Values[LOV]"
)


class ChartOfAccounts(BaseForm):

    def __init__(self, master, username="ADMIN", mode="special"):
        label = ("Chart of Account - Special" if mode == "special"
                 else "Chart of Account - General")
        super().__init__(master, label, "CHART OF ACCOUNT", username, SHORTCUTS)
        self.geometry("780x480")
        self._mode_type = mode
        self._current_code = None
        self._all_codes = []   # list of ac_codes in display order
        self._idx = -1
        self._build_form()
        self._load_all_codes()
        self._bind_keys()

    # ── Form layout ────────────────────────────────────────────────────────────

    def _build_form(self):
        c = self.content

        # Search-mode radio (shown at top, same as original)
        self._search_by = tk.StringVar(value="code")
        sf = tk.Frame(c, bg=FORM_BG)
        sf.pack(fill="x", padx=10, pady=(6, 0))
        tk.Radiobutton(sf, text="Search By Code", variable=self._search_by, value="code",
                       bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left")
        tk.Radiobutton(sf, text="Search By Name", variable=self._search_by, value="name",
                       bg=FORM_BG, fg=LABEL_FG, font=FONT_SMALL).pack(side="left", padx=8)

        # ── Main bordered form panel ───────────────────────────────────────────
        panel = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        panel.pack(fill="x", padx=10, pady=8)
        panel.columnconfigure(1, weight=1)
        panel.columnconfigure(3, weight=2)

        # Row 0: A/C Code | A/C Name
        tk.Label(panel, text="A/C Code",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=0, column=0, sticky="e", padx=(10,4), pady=6)
        self._ac_code_e = tk.Entry(panel, width=14, bg=ENTRY_BG, font=FONT_NORMAL,
                                   relief="sunken", bd=2)
        self._ac_code_e.grid(row=0, column=1, sticky="w", padx=4, pady=6)

        tk.Label(panel, text="A/C Name",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=0, column=2, sticky="e", padx=4, pady=6)
        self._ac_name_e = tk.Entry(panel, width=38, bg=ENTRY_BG, font=FONT_NORMAL,
                                   relief="sunken", bd=2)
        self._ac_name_e.grid(row=0, column=3, sticky="ew", padx=(4,10), pady=6)

        # Row 1: Head Code | Head Name
        tk.Label(panel, text="Head Code", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=1, column=0, sticky="e", padx=(10,4), pady=6)
        self._head_code_e = tk.Entry(panel, width=14, bg=ENTRY_BG, font=FONT_NORMAL,
                                     relief="sunken", bd=2)
        self._head_code_e.grid(row=1, column=1, sticky="w", padx=4, pady=6)

        tk.Label(panel, text="Head Name", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=1, column=2, sticky="e", padx=4, pady=6)
        self._head_name_e = tk.Entry(panel, width=38, bg=ENTRY_BG, font=FONT_NORMAL,
                                     relief="sunken", bd=2)
        self._head_name_e.grid(row=1, column=3, sticky="ew", padx=(4,10), pady=6)

        # Row 2: A/C Path
        tk.Label(panel, text="A/C Path",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=2, column=0, sticky="e", padx=(10,4), pady=6)
        self._path_e = tk.Entry(panel, width=58, bg=ENTRY_BG, font=FONT_NORMAL,
                                relief="sunken", bd=2)
        self._path_e.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(4,10), pady=6)

        # Row 2b: A/C Type (for Balance Sheet / P&L classification)
        tk.Label(panel, text="A/C Type", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=2, column=2, sticky="e", padx=4, pady=6)
        self._ac_type_var = tk.StringVar(value="EXPENSE")
        type_opts = db.get_account_types()
        self._ac_type_om = tk.OptionMenu(panel, self._ac_type_var, *type_opts)
        self._ac_type_om.config(bg=ENTRY_BG, font=FONT_SMALL, anchor="w")
        self._ac_type_om.grid(row=2, column=3, sticky="ew", padx=(4,10), pady=6)

        # Row 3: Opening | Balance
        inner = tk.Frame(panel, bg=FORM_BG, bd=1, relief="groove")
        inner.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=(4,10))

        tk.Label(inner, text="Opening", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=0, column=0, sticky="e", padx=(10,4), pady=8)
        self._opening_e = tk.Entry(inner, width=20, bg=ENTRY_BG, font=FONT_NORMAL,
                                   relief="sunken", bd=2)
        self._opening_e.grid(row=0, column=1, sticky="w", padx=4, pady=8)

        tk.Label(inner, text="Balance",  bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD,
                 width=10, anchor="e").grid(row=0, column=2, sticky="e", padx=4, pady=8)
        self._balance_e = tk.Entry(inner, width=20, bg="#E8E8E8", font=FONT_NORMAL,
                                   relief="sunken", bd=2, state="readonly")
        self._balance_e.grid(row=0, column=3, sticky="w", padx=(4,10), pady=8)

        # ── Navigation info label ──────────────────────────────────────────────
        self._nav_var = tk.StringVar(value="Press F9 or Search to find an account")
        tk.Label(c, textvariable=self._nav_var, bg=STATUS_BG, fg=LABEL_FG,
                 font=FONT_SMALL, anchor="w", relief="sunken",
                 bd=1).pack(fill="x", padx=10, pady=2)

        # ── Keyboard shortcuts box (matches original exactly) ──────────────────
        sbox = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        sbox.pack(fill="x", padx=10, pady=8)
        tk.Label(sbox, text=SHORTCUTS, bg=FORM_BG, fg=SHORTCUT_FG,
                 font=("Arial", 7), justify="left",
                 wraplength=700).pack(anchor="w", padx=6, pady=4)

        self._all_entries = [self._ac_code_e, self._ac_name_e,
                             self._head_code_e, self._head_name_e,
                             self._path_e, self._opening_e]
        self._set_fields_state("disabled")

    # ── Data helpers ───────────────────────────────────────────────────────────

    def _load_all_codes(self):
        rows = db.get_all_accounts()
        self._all_codes = [r["ac_code"] for r in rows]

    def _set_fields_state(self, state):
        for e in self._all_entries:
            e.configure(state=state)

    def _clear_fields(self):
        self._ac_code_e.configure(state="normal"); self._ac_code_e.delete(0, "end")
        self._ac_name_e.configure(state="normal"); self._ac_name_e.delete(0, "end")
        self._head_code_e.configure(state="normal"); self._head_code_e.delete(0, "end")
        self._head_name_e.configure(state="normal"); self._head_name_e.delete(0, "end")
        self._path_e.configure(state="normal");     self._path_e.delete(0, "end")
        self._opening_e.configure(state="normal");  self._opening_e.delete(0, "end")
        self._balance_e.configure(state="normal");  self._balance_e.delete(0, "end")
        self._balance_e.configure(state="readonly")

    def _load_record(self, code):
        row = db.get_account(str(code))
        if not row:
            return
        self._current_code = str(row["ac_code"])
        self._clear_fields()
        self._set_fields_state("normal")
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
        self._ac_type_var.set(row["ac_type"] or "EXPENSE")
        self._ac_type_om.configure(state="disabled")
        self._ac_code_e.configure(state="disabled")
        self._set_fields_state("disabled")
        try:
            self._idx = self._all_codes.index(self._current_code)
        except ValueError:
            self._idx = -1
        total = len(self._all_codes)
        self._nav_var.set(f"Record {self._idx+1} of {total}   |   Code: {self._current_code}")

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_code = None
        self._idx = -1
        self._clear_fields()
        self._set_fields_state("normal")
        self._ac_type_om.configure(state="normal")
        self._balance_e.configure(state="readonly")
        self._ac_code_e.focus_set()
        self._mode = "add"
        self._nav_var.set("Adding new account — fill fields then Save")

    def on_edit(self):
        if not self._current_code:
            messagebox.showwarning("Edit", "Search and load a record first.", parent=self)
            return
        self._set_fields_state("normal")
        self._ac_type_om.configure(state="normal")
        self._ac_code_e.configure(state="disabled")
        self._balance_e.configure(state="readonly")
        self._mode = "edit"
        self._nav_var.set(f"Editing: {self._current_code}")

    def on_delete(self):
        if not self._current_code:
            messagebox.showwarning("Delete", "Load a record first.", parent=self)
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete account {self._current_code}?", parent=self):
            db.delete_account(self._current_code)
            self._current_code = None
            self._load_all_codes()
            self._clear_fields()
            self._set_fields_state("disabled")
            self._nav_var.set("Record deleted. Press F9 to search.")

    def on_search(self):
        self._open_lov()

    def on_save(self):
        code = self._ac_code_e.get().strip()
        name = self._ac_name_e.get().strip()
        if not code or not name:
            messagebox.showwarning("Validation", "A/C Code and Name are required.", parent=self)
            return
        try:
            opening = float(self._opening_e.get().replace(",", "") or 0)
        except ValueError:
            opening = 0.0
        data = (code, name,
                self._head_code_e.get().strip(),
                self._head_name_e.get().strip(),
                self._path_e.get().strip(),
                opening, opening,
                self._ac_type_var.get())
        db.save_account(data)
        self._ac_type_om.configure(state="disabled")
        self._current_code = code
        self._load_all_codes()
        self._load_record(code)
        self._mode = "view"
        messagebox.showinfo("Saved", f"Account {code} saved successfully.", parent=self)

    def on_ignore(self):
        if self._current_code:
            self._load_record(self._current_code)
        else:
            self._clear_fields()
            self._set_fields_state("disabled")
            self._nav_var.set("Cancelled. Press F9 or Search to find an account.")
        self._mode = "view"

    # ── LOV / F9 ───────────────────────────────────────────────────────────────

    def _open_lov(self):
        term = self._ac_code_e.get().strip() or self._ac_name_e.get().strip()
        dlg  = AccountLOVDialog(self, term)
        if dlg.result:
            code, _name = dlg.result
            self._load_record(code)

    # ── Keyboard navigation ────────────────────────────────────────────────────

    def _bind_keys(self):
        self._ac_code_e.bind("<F9>",    lambda e: self._open_lov())
        self._ac_code_e.bind("<Return>", self._on_code_enter)
        self.bind("<Alt-d>",  lambda e: self.on_delete())
        self.bind("<Alt-a>",  lambda e: self.on_add())
        self.bind("<Alt-e>",  lambda e: self.on_edit())
        self.bind("<Alt-f>",  lambda e: self._open_lov())
        self.bind("<Alt-s>",  lambda e: self.on_save())
        self.bind("<Alt-i>",  lambda e: self.on_ignore())
        self.bind("<Alt-x>",  lambda e: self.on_exit())
        self.bind("<F9>",     lambda e: self._open_lov())
        # Arrow navigation through records
        self.bind("<Prior>",  lambda e: self._nav(-1))   # Page Up = previous
        self.bind("<Next>",   lambda e: self._nav(+1))   # Page Down = next

    def _on_code_enter(self, _):
        code = self._ac_code_e.get().strip()
        if code:
            row = db.get_account(code)
            if row:
                self._load_record(code)
            else:
                self._open_lov()

    def _nav(self, direction):
        if not self._all_codes:
            return
        self._idx = max(0, min(len(self._all_codes)-1, self._idx + direction))
        self._load_record(self._all_codes[self._idx])


# ── Define Heading Accounts ────────────────────────────────────────────────────

class DefineHeadingAccounts(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "Define Heading Accounts", "DEFINE HEADING ACCOUNTS",
                         username,
                         "Alt+A : Add    Alt+D : Delete    Alt+S : Save    Alt+X : Exit")
        self.geometry("600x460")
        self._current = None
        self._build_form()
        self._refresh()

    def _build_form(self):
        from forms.base_form import make_grid
        c = self.content

        ef = tk.Frame(c, bg=FORM_BG)
        ef.pack(fill="x", padx=10, pady=8)

        tk.Label(ef, text="Head Code", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._code_e = tk.Entry(ef, width=14, bg=ENTRY_BG, font=FONT_NORMAL,
                                relief="sunken", bd=2)
        self._code_e.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        tk.Label(ef, text="Head Name", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self._name_e = tk.Entry(ef, width=36, bg=ENTRY_BG, font=FONT_NORMAL,
                                relief="sunken", bd=2)
        self._name_e.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        cols = [("code","Head Code",100), ("name","Head Name",320)]
        gf, self._tree = make_grid(c, cols, height=14)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_sel)

        self._entries = [self._code_e, self._name_e]
        self._set_state("disabled")

    def _set_state(self, state):
        for e in self._entries:
            e.configure(state=state)

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_all_heads()):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=(r["head_code"], r["head_name"]),
                              tags=(tag,))

    def _on_sel(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        v = self._tree.item(sel[0])["values"]
        self._current = str(v[0])
        self._set_state("normal")
        self._code_e.delete(0, "end"); self._code_e.insert(0, v[0])
        self._name_e.delete(0, "end"); self._name_e.insert(0, v[1])
        self._code_e.configure(state="disabled")

    def on_add(self):
        self._current = None
        self._set_state("normal")
        self._code_e.delete(0, "end"); self._name_e.delete(0, "end")
        self._code_e.focus_set()

    def on_save(self):
        code = self._code_e.get().strip()
        name = self._name_e.get().strip()
        if not code or not name:
            messagebox.showwarning("Validation", "Both fields required.", parent=self)
            return
        db.save_head(code, name)
        self._refresh()
        self._set_state("disabled")

    def on_delete(self):
        if not self._current:
            messagebox.showwarning("Delete", "Select a record first.", parent=self)
            return
        if messagebox.askyesno("Confirm", f"Delete head {self._current}?", parent=self):
            db.delete_head(self._current)
            self._current = None
            self._set_state("disabled")
            self._refresh()

    def on_ignore(self):
        self._set_state("disabled")
        self._code_e.delete(0, "end")
        self._name_e.delete(0, "end")
