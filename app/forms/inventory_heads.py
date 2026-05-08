"""Inventory Heads form – matches design image exactly."""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, make_grid
import database as db


class InventoryHeads(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "Inventory Heads", "INVENTORY HEADS", username,
                         "Alt+A : Add    Alt+D : Delete    Alt+S : Save    Alt+X : Exit")
        self.geometry("640x520")
        self._current = None
        self._build_form()
        self._refresh()

    def _build_form(self):
        c = self.content

        # ── Group box ──────────────────────────────────────────────────────────
        grp = tk.LabelFrame(c, text="INVENTORY HEADS", bg=GROUP_BG, fg=LABEL_FG,
                            font=FONT_BOLD, bd=2, relief="groove")
        grp.pack(fill="both", expand=True, padx=16, pady=12)

        # Inline-editable grid (Head | Name)
        cols = [("head","Head",100), ("name","Name",340)]
        gf, self._tree = make_grid(grp, cols, height=18)
        gf.pack(fill="both", expand=True, padx=6, pady=6)
        self._tree.bind("<<TreeviewSelect>>", self._on_sel)

        # ── Entry strip below grid ─────────────────────────────────────────────
        ef = tk.Frame(c, bg=FORM_BG)
        ef.pack(fill="x", padx=16, pady=4)

        tk.Label(ef, text="Head :", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
        self._head_e = tk.Entry(ef, width=10, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._head_e.pack(side="left", padx=4)

        tk.Label(ef, text="Name :", bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD).pack(side="left", padx=4)
        self._name_e = tk.Entry(ef, width=30, bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)
        self._name_e.pack(side="left", padx=4)

        tk.Button(ef, text="Add / Update", bg=BTN_BG, font=FONT_SMALL, relief="raised",
                  bd=2, command=self.on_save).pack(side="left", padx=8)

    # ── Data ───────────────────────────────────────────────────────────────────

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(db.get_all_heads()):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(r["head_code"]),
                              values=(r["head_code"], r["head_name"]), tags=(tag,))

    def _on_sel(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        self._current = str(vals[0])
        self._head_e.delete(0, "end"); self._head_e.insert(0, vals[0])
        self._name_e.delete(0, "end"); self._name_e.insert(0, vals[1])

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def on_add(self):
        self._current = None
        self._head_e.delete(0, "end")
        self._name_e.delete(0, "end")
        self._head_e.focus_set()

    def on_save(self):
        code = self._head_e.get().strip()
        name = self._name_e.get().strip()
        if not code or not name:
            messagebox.showwarning("Validation", "Head Code and Name required.", parent=self)
            return
        db.save_head(code, name)
        self._refresh()
        self._head_e.delete(0, "end")
        self._name_e.delete(0, "end")
        self._head_e.focus_set()

    def on_delete(self):
        if not self._current:
            messagebox.showwarning("Delete", "Select a record first.", parent=self)
            return
        if messagebox.askyesno("Confirm", f"Delete head '{self._current}'?", parent=self):
            db.delete_head(self._current)
            self._current = None
            self._head_e.delete(0, "end")
            self._name_e.delete(0, "end")
            self._refresh()

    def on_ignore(self):
        self._head_e.delete(0, "end")
        self._name_e.delete(0, "end")
        self._current = None
