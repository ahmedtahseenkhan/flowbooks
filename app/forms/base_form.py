"""
BaseForm – the standard Oracle-Forms-style window that every data-entry screen
inherits from.  It provides:
  • Top toolbar  (Delete / Add / Edit / Search / Save / Ignore / Print / Exit)
  • Left sidebar with vertical title text
  • Inner content area (self.content) for child widgets
  • Bottom status / shortcut bar
  • Standard CRUD state machine (view → edit/add → save/ignore)
"""

import tkinter as tk
from tkinter import messagebox, ttk
from config import *


class BaseForm(tk.Toplevel):

    TOOLBAR_BTNS = ["Delete", "Add", "Edit", "Search", "Save", "Ignore", "Print", "Exit"]

    def __init__(self, master, title: str, sidebar_text: str, username: str = "ADMIN", shortcuts: str = ""):
        super().__init__(master)
        self.title(title)
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(750, 520)

        self._username  = username
        self._sidebar_t = sidebar_text
        self._shortcuts = shortcuts
        self._mode      = "view"   # view | add | edit | search

        self._btn_refs  = {}
        self._build_chrome()
        self.grab_set()

    # ── Layout skeleton ────────────────────────────────────────────────────────

    def _build_chrome(self):
        # ── Title bar label (window-level title is set, but also add an inner one)
        tk.Label(self, text=self.title(), bg=BG, fg=LABEL_FG,
                 font=FONT_BOLD, anchor="w").pack(fill="x", padx=4, pady=(4, 0))

        # ── Toolbar ────────────────────────────────────────────────────────────
        tb = tk.Frame(self, bg=TOOLBAR_BG, bd=1, relief="flat")
        tb.pack(fill="x", padx=2, pady=2)

        for name in self.TOOLBAR_BTNS:
            b = tk.Button(tb, text=name, font=FONT_SMALL, bg=BTN_BG,
                          relief="raised", bd=2, padx=6, pady=1,
                          command=lambda n=name: self._toolbar_cmd(n))
            b.pack(side="left", padx=2, pady=2)
            self._btn_refs[name] = b

        tk.Label(tb, text=f"USER NAME :\n{self._username}",
                 bg=TOOLBAR_BG, fg=LABEL_FG, font=FONT_SMALL,
                 justify="left").pack(side="right", padx=8)

        # ── Body row: sidebar + content ────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=4, pady=2)

        # Sidebar
        sb = tk.Frame(body, bg=SIDEBAR_BG, width=28)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        lbl = tk.Label(sb, text="\n".join(self._sidebar_t),
                       bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                       font=FONT_SIDEBAR, justify="center")
        lbl.pack(expand=True)

        # Content area (child classes place their widgets here)
        self.content = tk.Frame(body, bg=FORM_BG, bd=1, relief="sunken")
        self.content.pack(side="left", fill="both", expand=True)

        # ── Bottom status / shortcut bar ───────────────────────────────────────
        bot = tk.Frame(self, bg=STATUS_BG, bd=1, relief="sunken")
        bot.pack(fill="x", side="bottom")

        if self._shortcuts:
            tk.Label(bot, text=self._shortcuts, bg=STATUS_BG, fg=SHORTCUT_FG,
                     font=("Arial", 7), justify="left", wraplength=900).pack(
                anchor="w", padx=6, pady=2)

        # Bottom blue progress bar (cosmetic)
        bar = tk.Frame(self, bg=BOTTOM_BAR, height=6)
        bar.pack(fill="x", side="bottom")

    # ── Toolbar dispatcher ─────────────────────────────────────────────────────

    def _toolbar_cmd(self, name):
        dispatch = {
            "Add":    self.on_add,
            "Edit":   self.on_edit,
            "Delete": self.on_delete,
            "Search": self.on_search,
            "Save":   self.on_save,
            "Ignore": self.on_ignore,
            "Print":  self.on_print,
            "Exit":   self.on_exit,
        }
        dispatch.get(name, lambda: None)()

    # ── Override these in child classes ───────────────────────────────────────

    def on_add(self):    self._set_mode("add")
    def on_edit(self):   self._set_mode("edit")
    def on_delete(self): messagebox.showwarning("Delete", "Nothing selected.", parent=self)
    def on_search(self): self._set_mode("search")
    def on_save(self):   messagebox.showinfo("Save", "Nothing to save.", parent=self)
    def on_ignore(self): self._set_mode("view")
    def on_print(self):  messagebox.showinfo("Print", "Print feature coming soon.", parent=self)
    def on_exit(self):   self.destroy()

    # ── Mode helpers ───────────────────────────────────────────────────────────

    def _set_mode(self, mode):
        self._mode = mode

    def _set_entries_state(self, state, entries):
        for e in entries:
            try:
                e.configure(state=state)
            except Exception:
                pass

    # ── Convenience widget builders ────────────────────────────────────────────

    @staticmethod
    def lf(parent, text, row, col, colspan=1, padx=(4, 2), pady=3):
        """Label + Frame group-box convenience."""
        tk.Label(parent, text=text, bg=FORM_BG, fg=LABEL_FG,
                 font=FONT_BOLD).grid(row=row, column=col, sticky="w",
                                      padx=padx, pady=pady)

    @staticmethod
    def mk_entry(parent, row, col, width=20, colspan=1, state="normal"):
        var = tk.StringVar()
        e = tk.Entry(parent, textvariable=var, width=width, bg=ENTRY_BG,
                     font=FONT_NORMAL, relief="sunken", bd=2, state=state)
        e.grid(row=row, column=col, columnspan=colspan,
               sticky="w", padx=4, pady=2)
        return e, var

    @staticmethod
    def mk_label(parent, text, row, col, fg=LABEL_FG, font=None):
        font = font or FONT_NORMAL
        tk.Label(parent, text=text, bg=FORM_BG, fg=fg,
                 font=font).grid(row=row, column=col, sticky="w", padx=4, pady=2)

    @staticmethod
    def group_box(parent, text, row, col, colspan, rowspan=1):
        """Return a labelled LabelFrame group box."""
        f = tk.LabelFrame(parent, text=text, bg=GROUP_BG, fg=LABEL_FG,
                          font=FONT_BOLD, bd=2, relief="groove")
        f.grid(row=row, column=col, columnspan=colspan, rowspan=rowspan,
               sticky="nsew", padx=8, pady=4)
        return f


# ── Reusable date-range dialog ─────────────────────────────────────────────────

class DateRangeDialog(tk.Toplevel):
    """
    A small dialog that lets the user pick a date range (From / To)
    plus optionally a period radio button (Current Month / Current Year / Previous Year / Define).
    Returns None or (from_date, to_date) strings in DD/MM/YYYY.
    """

    def __init__(self, master, title="Date Range", show_period=True):
        super().__init__(master)
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.result = None
        self.grab_set()

        from datetime import date, timedelta
        today = date.today()

        # Header
        hdr = tk.Frame(self, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, bg=GRID_HDR_BG, fg="white",
                 font=FONT_TITLE, pady=6).pack()

        body = tk.Frame(self, bg=BG, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        self._period = tk.StringVar(value="define")

        if show_period:
            for val, txt in [("month", "Current Month"), ("year", "Current Year"),
                             ("prev", "Previous Year"), ("define", "Define")]:
                tk.Radiobutton(body, text=txt, variable=self._period, value=val,
                               bg=BG, fg=LABEL_FG, font=FONT_NORMAL,
                               command=self._on_period).pack(side="left", padx=4)
            tk.Frame(body, bg=BG, height=6).pack(fill="x")

        row2 = tk.Frame(self, bg=BG, padx=20)
        row2.pack(fill="x")

        tk.Label(row2, text="From", bg=BG, fg=LABEL_FG, font=FONT_BOLD, width=6).grid(row=0, column=0, sticky="e")
        self._from_var = tk.StringVar(value=today.strftime("%d/%m/%Y"))
        self._from_e = tk.Entry(row2, textvariable=self._from_var, width=14, bg=ENTRY_BG, font=FONT_NORMAL)
        self._from_e.grid(row=0, column=1, padx=4, pady=4)
        tk.Label(row2, text="DD/MM/YYYY", bg=BG, fg=LABEL_FG, font=("Arial", 7)).grid(row=0, column=2, sticky="w")

        if show_period:
            tk.Label(row2, text="To", bg=BG, fg=LABEL_FG, font=FONT_BOLD, width=6).grid(row=1, column=0, sticky="e")
            self._to_var = tk.StringVar(value=today.strftime("%d/%m/%Y"))
            self._to_e = tk.Entry(row2, textvariable=self._to_var, width=14, bg=ENTRY_BG, font=FONT_NORMAL)
            self._to_e.grid(row=1, column=1, padx=4, pady=4)
            tk.Label(row2, text="DD/MM/YYYY", bg=BG, fg=LABEL_FG, font=("Arial", 7)).grid(row=1, column=2, sticky="w")
        else:
            self._to_var = self._from_var  # single-date mode

        # Buttons
        bf = tk.Frame(self, bg=BG, pady=8)
        bf.pack()
        tk.Button(bf, text="OK", width=8, bg=BTN_BG, font=FONT_NORMAL,
                  command=self._ok).pack(side="left", padx=6)
        tk.Button(bf, text="Cancel", width=8, bg=BTN_BG, font=FONT_NORMAL,
                  command=self.destroy).pack(side="left", padx=6)

        self.transient(master)
        self.wait_window(self)

    def _on_period(self):
        from datetime import date
        today = date.today()
        p = self._period.get()
        if p == "month":
            self._from_var.set(today.replace(day=1).strftime("%d/%m/%Y"))
            self._to_var.set(today.strftime("%d/%m/%Y"))
        elif p == "year":
            self._from_var.set(today.replace(month=1, day=1).strftime("%d/%m/%Y"))
            self._to_var.set(today.strftime("%d/%m/%Y"))
        elif p == "prev":
            self._from_var.set(today.replace(year=today.year - 1, month=1, day=1).strftime("%d/%m/%Y"))
            self._to_var.set(today.replace(year=today.year - 1, month=12, day=31).strftime("%d/%m/%Y"))

    def _ok(self):
        # Convert DD/MM/YYYY → YYYY-MM-DD for SQLite
        try:
            from datetime import datetime
            fd = datetime.strptime(self._from_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            td = datetime.strptime(self._to_var.get(),   "%d/%m/%Y").strftime("%Y-%m-%d")
            self.result = (fd, td)
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter dates as DD/MM/YYYY", parent=self)


# ── Reusable grid (Treeview wrapper) ──────────────────────────────────────────

def make_grid(parent, columns, height=12, selectmode="browse"):
    """
    columns = list of (id, header, width) tuples
    Returns (frame, tree).
    """
    frame = tk.Frame(parent, bg=FORM_BG)

    style = ttk.Style()
    style.configure("Acct.Treeview.Heading", background=GRID_HDR_BG,
                    foreground=GRID_HDR_FG, font=FONT_GRID_H, relief="flat")
    style.configure("Acct.Treeview", background=GRID_ROW1, foreground="black",
                    fieldbackground=GRID_ROW1, font=FONT_GRID, rowheight=18)
    style.map("Acct.Treeview", background=[("selected", GRID_SEL)],
              foreground=[("selected", "white")])

    ids = [c[0] for c in columns]
    tree = ttk.Treeview(frame, columns=ids, show="headings",
                        height=height, style="Acct.Treeview",
                        selectmode=selectmode)

    for cid, hdr, w in columns:
        tree.heading(cid, text=hdr)
        tree.column(cid, width=w, minwidth=40, stretch=False)

    vsb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    # Stripe rows on insert (tag "odd")
    tree.tag_configure("odd",  background=GRID_ROW1)
    tree.tag_configure("even", background=GRID_ROW2)

    return frame, tree


def stripe_tree(tree):
    for i, item in enumerate(tree.get_children()):
        tree.item(item, tags=("odd" if i % 2 else "even",))
