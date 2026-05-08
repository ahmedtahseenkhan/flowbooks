"""User Management form under Administration."""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, make_grid
import database as db


class UserManagementForm(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "USER MANAGEMENT", "USER MANAGEMENT", username,
                         "Alt+A : Add    Alt+E : Edit    Alt+D : Delete    "
                         "Alt+S : Save    Alt+X : Exit")
        self.geometry("720x520")
        self._current_id = None
        self._build_form()
        self._refresh()
        self._bind_keys()

    def _build_form(self):
        c = self.content
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)
        tkw = dict(bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)

        panel = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        panel.pack(fill="x", padx=10, pady=8)
        panel.columnconfigure(1, weight=1)
        panel.columnconfigure(3, weight=1)

        fields = [
            (0, 0, "Username",    "_user_e",   18),
            (0, 2, "Password",    "_pass_e",   18),
            (1, 0, "Full Name",   "_name_e",   36),
            (2, 0, "Designation", "_desig_e",  18),
            (2, 2, "Department",  "_dept_e",   18),
            (3, 0, "Section",     "_sect_e",   36),
        ]
        for row, col, lbl, attr, w in fields:
            tk.Label(panel, text=lbl, **lkw, anchor="e", width=12).grid(
                row=row, column=col, sticky="e", padx=(8,2), pady=4)
            e = tk.Entry(panel, width=w, **tkw,
                         show="*" if attr == "_pass_e" else "")
            e.grid(row=row, column=col+1, sticky="ew", padx=(2,6), pady=4)
            setattr(self, attr, e)

        # Change Password section
        cpf = tk.LabelFrame(c, text="Change Password", bg=GROUP_BG, fg=LABEL_FG,
                            font=FONT_BOLD, bd=2, relief="groove")
        cpf.pack(fill="x", padx=10, pady=4)

        tk.Label(cpf, text="New Password", bg=GROUP_BG, fg=LABEL_FG,
                 font=FONT_BOLD).grid(row=0, column=0, sticky="e", padx=4, pady=6)
        self._new_pass = tk.Entry(cpf, width=20, bg=ENTRY_BG, font=FONT_NORMAL,
                                  relief="sunken", bd=2, show="*")
        self._new_pass.grid(row=0, column=1, sticky="w", padx=4, pady=6)
        tk.Label(cpf, text="Confirm", bg=GROUP_BG, fg=LABEL_FG,
                 font=FONT_BOLD).grid(row=0, column=2, sticky="e", padx=4, pady=6)
        self._confirm_pass = tk.Entry(cpf, width=20, bg=ENTRY_BG, font=FONT_NORMAL,
                                      relief="sunken", bd=2, show="*")
        self._confirm_pass.grid(row=0, column=3, sticky="w", padx=4, pady=6)
        tk.Button(cpf, text="Change Password", bg=BTN_BG, font=FONT_NORMAL,
                  relief="raised", bd=2, command=self._change_password).grid(
            row=0, column=4, padx=8, pady=6)

        # User list
        cols = [("id","ID",40),("username","Username",100),("name","Full Name",160),
                ("desig","Designation",100),("dept","Department",100),("sect","Section",90)]
        gf, self._tree = make_grid(c, cols, height=10)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_sel)

        self._entries = [self._user_e, self._pass_e, self._name_e,
                         self._desig_e, self._dept_e, self._sect_e]
        self._set_fields("disabled")

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current_id = None
        self._clear_fields()
        self._set_fields("normal")
        self._user_e.focus_set()
        self._mode = "add"

    def on_edit(self):
        if not self._current_id:
            messagebox.showwarning("Edit", "Select a user first.", parent=self)
            return
        self._set_fields("normal")
        self._mode = "edit"

    def on_delete(self):
        if not self._current_id:
            messagebox.showwarning("Delete", "Select a user first.", parent=self)
            return
        uname = self._user_e.get()
        if uname == "admin":
            messagebox.showwarning("Delete", "Cannot delete the admin user.", parent=self)
            return
        if messagebox.askyesno("Confirm", f"Delete user '{uname}'?", parent=self):
            db.delete_user(self._current_id)
            self._current_id = None
            self._clear_fields()
            self._set_fields("disabled")
            self._refresh()

    def on_save(self):
        uname = self._user_e.get().strip()
        pwd   = self._pass_e.get().strip()
        if not uname or not pwd:
            messagebox.showwarning("Validation", "Username and Password required.", parent=self)
            return
        data = (uname, pwd,
                self._name_e.get().strip(),
                self._desig_e.get().strip() or "MANAGER",
                self._dept_e.get().strip()  or "ACCOUNTS",
                self._sect_e.get().strip()  or "HEAD OFFICE",
                self._current_id)
        db.save_user(data)
        self._refresh()
        self._set_fields("disabled")
        self._mode = "view"
        messagebox.showinfo("Saved", f"User '{uname}' saved.", parent=self)

    def on_ignore(self):
        if self._current_id:
            self._load(self._current_id)
        else:
            self._clear_fields()
        self._set_fields("disabled")
        self._mode = "view"

    def _change_password(self):
        if not self._current_id:
            messagebox.showwarning("Change Password", "Select a user first.", parent=self)
            return
        new  = self._new_pass.get().strip()
        conf = self._confirm_pass.get().strip()
        if not new:
            messagebox.showwarning("Password", "Enter a new password.", parent=self)
            return
        if new != conf:
            messagebox.showerror("Password", "Passwords do not match.", parent=self)
            return
        db.change_password(self._current_id, new)
        self._new_pass.delete(0, "end")
        self._confirm_pass.delete(0, "end")
        messagebox.showinfo("Done", "Password changed successfully.", parent=self)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_all_users()):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(r["id"]), values=(
                r["id"], r["username"], r["full_name"] or "",
                r["designation"] or "", r["department"] or "", r["section"] or ""
            ), tags=(tag,))

    def _on_sel(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        uid = int(self._tree.item(sel[0])["values"][0])
        self._current_id = uid
        self._load(uid)

    def _load(self, uid):
        rows = db.get_all_users()
        row  = next((r for r in rows if r["id"] == uid), None)
        if not row:
            return
        self._clear_fields()
        self._set_fields("normal")
        self._user_e.insert(0,  row["username"])
        self._pass_e.insert(0,  row["password"])
        self._name_e.insert(0,  row["full_name"]   or "")
        self._desig_e.insert(0, row["designation"] or "")
        self._dept_e.insert(0,  row["department"]  or "")
        self._sect_e.insert(0,  row["section"]     or "")
        self._set_fields("disabled")

    def _clear_fields(self):
        for e in self._entries:
            s = e.cget("state")
            e.configure(state="normal")
            e.delete(0, "end")
            e.configure(state=s)

    def _set_fields(self, state):
        for e in self._entries:
            e.configure(state=state)

    def _bind_keys(self):
        self.bind("<Alt-a>", lambda e: self.on_add())
        self.bind("<Alt-e>", lambda e: self.on_edit())
        self.bind("<Alt-d>", lambda e: self.on_delete())
        self.bind("<Alt-s>", lambda e: self.on_save())
        self.bind("<Alt-i>", lambda e: self.on_ignore())
        self.bind("<Alt-x>", lambda e: self.on_exit())
