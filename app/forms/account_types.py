"""Account Types CRUD – manage the list of account types used in Chart of Accounts."""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, make_grid
import database as db


class AccountTypesForm(BaseForm):
    """Simple CRUD for the account_types table."""

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "Account Types / ATM", "ACCOUNT\nTYPES", username,
                         shortcuts="Add : add new type    Edit : rename selected    Delete : remove selected    F9 / Search : refresh list")
        self._selected_id   = None
        self._selected_name = None
        self._build_ui()
        self._load()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        c = self.content

        # ── Header row ────────────────────────────────────────────────────────
        hdr = tk.Frame(c, bg=GRID_HDR_BG)
        hdr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(hdr, text="Account Types", bg=GRID_HDR_BG, fg="white",
                 font=FONT_TITLE, pady=6).pack(side="left", padx=10)

        # ── Entry area ────────────────────────────────────────────────────────
        ef = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        ef.pack(fill="x", padx=10, pady=4)

        tk.Label(ef, text="Type Name", bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD, width=12, anchor="e").grid(row=0, column=0, padx=(10, 4), pady=10)
        self._name_var = tk.StringVar()
        self._name_e = tk.Entry(ef, textvariable=self._name_var, width=34,
                                bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2,
                                state="disabled")
        self._name_e.grid(row=0, column=1, sticky="w", padx=4, pady=10)
        self._name_e.bind("<Return>", lambda e: self.on_save())

        self._status_var = tk.StringVar(value="Select a type or click Add to create new.")
        tk.Label(c, textvariable=self._status_var, bg=STATUS_BG, fg=LABEL_FG,
                 font=FONT_SMALL, anchor="w", relief="sunken", bd=1).pack(
            fill="x", padx=10, pady=2)

        # ── Grid list ─────────────────────────────────────────────────────────
        cols = [("id", "ID", 50), ("type_name", "Account Type Name", 380)]
        gf, self._tree = make_grid(c, cols, height=18)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-Button-1>",  self._on_double)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load(self):
        self._tree.delete(*self._tree.get_children())
        rows = db.get_all_account_types()
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(r["id"]),
                              values=(r["id"], r["type_name"]), tags=(tag,))
        self._status_var.set(f"{len(rows)} account type(s) loaded.")

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0], "values")
        self._selected_id   = int(vals[0])
        self._selected_name = vals[1]

    def _on_double(self, _=None):
        self._on_select()
        if self._selected_id:
            self.on_edit()

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def on_add(self):
        self._selected_id = None
        self._name_var.set("")
        self._name_e.configure(state="normal")
        self._name_e.focus_set()
        self._status_var.set("Enter the new account type name and press Save.")

    def on_edit(self):
        if not self._selected_id:
            messagebox.showwarning("Edit", "Select a type from the list first.", parent=self)
            return
        self._name_var.set(self._selected_name)
        self._name_e.configure(state="normal")
        self._name_e.focus_set()
        self._name_e.select_range(0, "end")
        self._status_var.set(f"Editing: {self._selected_name} — change name and press Save.")

    def on_save(self):
        name = self._name_var.get().strip().upper()
        if not name:
            messagebox.showwarning("Validation", "Type name cannot be empty.", parent=self)
            return
        ok, msg = db.save_account_type(name, self._selected_id)
        if ok:
            self._name_e.configure(state="disabled")
            self._name_var.set("")
            self._selected_id = None
            self._load()
            self._status_var.set(f"Saved: {name}")
        else:
            messagebox.showerror("Error", msg, parent=self)

    def on_ignore(self):
        self._name_e.configure(state="disabled")
        self._name_var.set("")
        self._status_var.set("Cancelled.")

    def on_delete(self):
        if not self._selected_id:
            messagebox.showwarning("Delete", "Select a type from the list first.", parent=self)
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete account type '{self._selected_name}'?\n\n"
                               "Accounts already using this type will keep their current value.",
                               parent=self):
            db.delete_account_type(self._selected_id)
            self._selected_id   = None
            self._selected_name = None
            self._name_var.set("")
            self._name_e.configure(state="disabled")
            self._load()

    def on_search(self):
        self._load()

    def on_print(self):
        messagebox.showinfo("Print", "Print not available for this form.", parent=self)
