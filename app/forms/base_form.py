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


# ── F9 Account LOV – "SELECT THE ACCOUNT" ─────────────────────────────────────

class AccountLOVDialog(tk.Toplevel):
    """
    Press F9 on any A/C Code field to open this popup.
    Columns: A/C Name | A/C Code | A/C Head | Balance
    Returns (ac_code, ac_name) or None.
    """

    def __init__(self, master, initial_term="%"):
        super().__init__(master)
        self.title("SELECT THE ACCOUNT")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.result = None
        self.grab_set()
        self.geometry("760x420")

        import database as db
        self._db = db

        # ── Header ─────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="SELECT THE ACCOUNT", bg=GRID_HDR_BG, fg="white",
                 font=FONT_TITLE, pady=5).pack(side="left", padx=10)
        tk.Button(hdr, text="✕", bg=GRID_HDR_BG, fg="white", relief="flat",
                  font=FONT_BOLD, command=self.destroy).pack(side="right", padx=6)

        # ── Find row ───────────────────────────────────────────────────────────
        fr = tk.Frame(self, bg=BG, pady=6)
        fr.pack(fill="x", padx=14)
        tk.Label(fr, text="Find", bg=BG, fg=LABEL_FG, font=FONT_BOLD, width=6).pack(side="left")
        self._find_var = tk.StringVar(value=initial_term if initial_term else "%")
        self._find_e = tk.Entry(fr, textvariable=self._find_var, width=36,
                                bg=ENTRY_BG, font=FONT_MONO, relief="sunken", bd=2)
        self._find_e.pack(side="left", padx=6)
        self._find_e.bind("<Return>", lambda e: self._do_find())

        # ── Grid ───────────────────────────────────────────────────────────────
        cols = [("name","A/C NAME",200), ("code","A/C CODE",70),
                ("head","A/C HEAD",100), ("hcode","HEAD CODE",80),
                ("bal","BALANCE",110)]
        gf, self._tree = make_grid(self, cols, height=14)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<Double-1>",   lambda e: self._ok())
        self._tree.bind("<Return>",     lambda e: self._ok())

        # ── Buttons ────────────────────────────────────────────────────────────
        bf = tk.Frame(self, bg=BG, pady=6)
        bf.pack()
        for txt, cmd in [("Find", self._do_find), ("OK", self._ok), ("Cancel", self.destroy)]:
            tk.Button(bf, text=txt, width=10, bg=BTN_BG, font=FONT_NORMAL,
                      relief="raised", bd=2, command=cmd).pack(side="left", padx=10)

        tk.Frame(self, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")

        self._do_find()
        self._find_e.focus_set()
        self.transient(master)
        self.wait_window(self)

    def _do_find(self):
        term = self._find_var.get().strip().replace("%", "")
        self._tree.delete(*self._tree.get_children())
        rows = self._db.get_all_accounts()
        if term:
            rows = [r for r in rows
                    if term.lower() in r["ac_name"].lower()
                    or term.lower() in r["ac_code"].lower()]
        for i, r in enumerate(rows):
            bal = r["balance"] or 0
            bal_str = f"DR  {bal:,.2f}" if bal >= 0 else f"CR  {abs(bal):,.2f}"
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(r["ac_code"]), values=(
                r["ac_name"], r["ac_code"],
                r["head_name"] or "", r["head_code"] or "",
                bal_str
            ), tags=(tag,))
        # Select first row
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._tree.see(children[0])

    def _ok(self):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        self.result = (str(vals[1]), str(vals[0]))  # (code, name)
        self.destroy()


# ── F9 Inventory LOV – "SEARCH BY CODE" ───────────────────────────────────────

class InventoryLOVDialog(tk.Toplevel):
    """
    Press F9 on any InvCode field to open this popup.
    Columns: Code | Name | Head | Unit | Quantity | Value
    Returns (code, name, unit, last_purchase_rate) or None.
    """

    def __init__(self, master, initial_term="%"):
        super().__init__(master)
        self.title("SEARCH BY CODE")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.result = None
        self.grab_set()
        self.geometry("780x420")

        import database as db
        self._db = db

        hdr = tk.Frame(self, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="SEARCH BY CODE", bg=GRID_HDR_BG, fg="white",
                 font=FONT_TITLE, pady=5).pack(side="left", padx=10)
        tk.Button(hdr, text="✕", bg=GRID_HDR_BG, fg="white", relief="flat",
                  font=FONT_BOLD, command=self.destroy).pack(side="right", padx=6)

        fr = tk.Frame(self, bg=BG, pady=6)
        fr.pack(fill="x", padx=14)
        tk.Label(fr, text="Find", bg=BG, fg=LABEL_FG, font=FONT_BOLD, width=6).pack(side="left")
        self._find_var = tk.StringVar(value=initial_term if initial_term else "%")
        self._find_e = tk.Entry(fr, textvariable=self._find_var, width=36,
                                bg=ENTRY_BG, font=FONT_MONO, relief="sunken", bd=2)
        self._find_e.pack(side="left", padx=6)
        self._find_e.bind("<Return>", lambda e: self._do_find())

        cols = [("code","CODE",70), ("name","NAME",220), ("head","HEAD",70),
                ("unit","UNIT",50), ("qty","QUANTITY",90), ("val","VALUE",110)]
        gf, self._tree = make_grid(self, cols, height=14)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<Double-1>", lambda e: self._ok())
        self._tree.bind("<Return>",   lambda e: self._ok())

        bf = tk.Frame(self, bg=BG, pady=6)
        bf.pack()
        for txt, cmd in [("Find", self._do_find), ("OK", self._ok), ("Cancel", self.destroy)]:
            tk.Button(bf, text=txt, width=10, bg=BTN_BG, font=FONT_NORMAL,
                      relief="raised", bd=2, command=cmd).pack(side="left", padx=10)

        tk.Frame(self, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")

        self._do_find()
        self._find_e.focus_set()
        self.transient(master)
        self.wait_window(self)

    def _do_find(self):
        term = self._find_var.get().strip().replace("%", "")
        self._tree.delete(*self._tree.get_children())
        rows = self._db.get_all_inventory()
        if term:
            rows = [r for r in rows
                    if term.lower() in r["name"].lower()
                    or term.lower() in r["code"].lower()]
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(r["code"]), values=(
                r["code"], r["name"], r["head"] or "",
                r["unit"] or "", f"{r['quantity']:,.2f}", f"{r['value']:,.2f}"
            ), tags=(tag,))
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._tree.see(children[0])

    def _ok(self):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        # (code, name, unit, last_purchase_rate)
        rows = self._db.get_all_inventory()
        match = next((r for r in rows if str(r["code"]) == str(vals[0])), None)
        rate = match["last_purchase_rate"] if match else 0.0
        self.result = (str(vals[0]), str(vals[1]), str(vals[2]), rate)
        self.destroy()


# ── Transaction Search Dialog (Search by Date) ─────────────────────────────────

class TransactionSearchDialog(tk.Toplevel):
    """
    Search existing purchase/sales transactions.
    Returns invoice_no or None.
    """

    def __init__(self, master, source="purchase"):
        super().__init__(master)
        self.title("SEARCH BY DATE")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.result = None
        self.grab_set()
        self.geometry("820x420")

        import database as db
        self._db    = db
        self._source = source

        hdr = tk.Frame(self, bg=GRID_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="SEARCH BY DATE", bg=GRID_HDR_BG, fg="white",
                 font=FONT_TITLE, pady=5).pack(side="left", padx=10)
        tk.Button(hdr, text="✕", bg=GRID_HDR_BG, fg="white", relief="flat",
                  font=FONT_BOLD, command=self.destroy).pack(side="right", padx=6)

        fr = tk.Frame(self, bg=BG, pady=6)
        fr.pack(fill="x", padx=14)
        tk.Label(fr, text="Find", bg=BG, fg=LABEL_FG, font=FONT_BOLD, width=6).pack(side="left")
        self._find_var = tk.StringVar(value="%")
        fe = tk.Entry(fr, textvariable=self._find_var, width=30,
                      bg=ENTRY_BG, font=FONT_MONO, relief="sunken", bd=2)
        fe.pack(side="left", padx=6)
        fe.bind("<Return>", lambda e: self._do_find())

        cols = [("dated","TRANDT",80), ("vno","VCHR",70),
                ("party","PARTY NAME",180), ("code","CODE",70),
                ("term","TERM",60), ("total","AMOUNT",100)]
        gf, self._tree = make_grid(self, cols, height=14)
        gf.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<Double-1>", lambda e: self._ok())
        self._tree.bind("<Return>",   lambda e: self._ok())

        bf = tk.Frame(self, bg=BG, pady=6)
        bf.pack()
        for txt, cmd in [("Find", self._do_find), ("OK", self._ok), ("Cancel", self.destroy)]:
            tk.Button(bf, text=txt, width=10, bg=BTN_BG, font=FONT_NORMAL,
                      relief="raised", bd=2, command=cmd).pack(side="left", padx=10)

        tk.Frame(self, bg=BOTTOM_BAR, height=5).pack(fill="x", side="bottom")

        self._do_find()
        self.transient(master)
        self.wait_window(self)

    def _do_find(self):
        term = self._find_var.get().strip().replace("%", "").lower()
        self._tree.delete(*self._tree.get_children())
        rows = (self._db.get_all_purchases() if self._source == "purchase"
                else self._db.get_all_sales())
        if term:
            rows = [r for r in rows
                    if term in (r["party"] or "").lower()
                    or term in r["invoice_no"].lower()
                    or term in r["dated"].lower()]
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(r["invoice_no"]), values=(
                r["dated"], r["invoice_no"],
                r["party"] or "", r["ac_code"] or "",
                r["term"], f"{r['total_value']:,.2f}"
            ), tags=(tag,))
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])

    def _ok(self):
        sel = self._tree.selection()
        if not sel:
            return
        self.result = str(self._tree.item(sel[0])["values"][1])  # invoice_no
        self.destroy()


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


# ─────────────────────────────────────────────────────────────────────────────
# InlineEntryGrid – keyboard-driven data entry grid (Tab navigates, auto-calc)
# ─────────────────────────────────────────────────────────────────────────────

class InlineEntryGrid(tk.Frame):
    """
    Scrollable inline entry grid that works exactly like the original Oracle
    Forms blocks:
      • Tab moves left-to-right across editable cells, then to the next row
      • Tabbing past the last row creates a new blank row automatically
      • F9 on any cell triggers the LOV callback
      • FocusOut triggers auto-lookup / auto-calculate callbacks
      • Totals update on every KeyRelease

    columns  – list of dicts:
        id        : unique key
        header    : column header text
        width     : Entry width in characters
        editable  : bool (default True); False = auto-filled, shown read-only
        align     : "left" | "right"  (default "left")
        bold      : bool (default False) — make auto-filled column bold/coloured

    Callbacks (set after construction):
        on_focus_out(row_idx, col_id, value) – called when an editable cell loses focus
        on_f9(row_idx, col_id, value)        – called when F9 is pressed
        on_change(all_rows)                  – called on any keystroke (for live totals)
        on_delete_row(row_idx)               – called when a row is deleted
    """

    ROW_H = 22

    def __init__(self, parent, columns, start_rows=15, **kw):
        super().__init__(parent, bg=FORM_BG, **kw)
        self._cols       = columns
        self._start_rows = start_rows
        self._widgets    = []   # list of  {col_id: Entry}
        self._frames     = []   # list of  row Frame

        # Public callbacks
        self.on_focus_out  = None
        self.on_f9         = None
        self.on_change     = None
        self.on_delete_row = None

        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Header bar
        hdr = tk.Frame(self, bg=GRID_HDR_BG, height=self.ROW_H + 2)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for col in self._cols:
            anchor = "e" if col.get("align") == "right" else "w"
            tk.Label(hdr, text=col["header"], bg=GRID_HDR_BG, fg=GRID_HDR_FG,
                     font=FONT_GRID_H, width=col["width"],
                     anchor=anchor, padx=2).pack(side="left", padx=1)
        # Reserve space for scrollbar
        tk.Label(hdr, text="", bg=GRID_HDR_BG, width=2).pack(side="right")

        # Scrollable body
        body = tk.Frame(self, bg=FORM_BG)
        body.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(body, bg=GRID_ROW1, highlightthickness=0)
        vsb = tk.Scrollbar(body, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=GRID_ROW1)
        self._cwin  = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._cwin, width=e.width))
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._inner.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Draw initial blank rows
        for _ in range(self._start_rows):
            self._add_row()

    def _row_bg(self, idx):
        return GRID_ROW1 if idx % 2 == 0 else GRID_ROW2

    def _add_row(self, values=None):
        idx = len(self._widgets)
        bg  = self._row_bg(idx)

        rf = tk.Frame(self._inner, bg=bg, height=self.ROW_H)
        rf.pack(fill="x")
        rf.pack_propagate(False)

        row = {}
        for col in self._cols:
            cid      = col["id"]
            editable = col.get("editable", True)
            align    = col.get("align", "left")
            bold_col = col.get("bold", False)
            w        = col["width"]

            entry_bg = ENTRY_BG if editable else "#E4E8F0"
            entry_fg = "#000080" if bold_col else "black"
            fnt      = FONT_GRID_H if bold_col else FONT_GRID

            e = tk.Entry(rf, width=w, bg=entry_bg, fg=entry_fg, font=fnt,
                         relief="flat", bd=0,
                         state="normal" if editable else "readonly",
                         justify="right" if align == "right" else "left",
                         highlightthickness=1,
                         highlightbackground="#B0B8C8",
                         highlightcolor=GRID_HDR_BG)
            e.pack(side="left", padx=1, pady=1, ipady=1)

            if values and cid in values:
                v = values[cid]
                if not editable:
                    e.configure(state="normal")
                e.delete(0, "end")
                e.insert(0, str(v) if v is not None else "")
                if not editable:
                    e.configure(state="readonly")

            if editable:
                e.bind("<Tab>",        lambda ev, r=idx, c=cid: self._tab(ev, r, c))
                e.bind("<F9>",         lambda ev, r=idx, c=cid: self._f9(r, c))
                e.bind("<FocusOut>",   lambda ev, r=idx, c=cid: self._fo(r, c))
                e.bind("<KeyRelease>", lambda ev: self._change())
                e.bind("<BackSpace>",  lambda ev: self._change())

            row[cid] = e

        self._widgets.append(row)
        self._frames.append(rf)

        # Scroll to show the new row
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)
        return row

    # ── Tab navigation ─────────────────────────────────────────────────────────

    def _editable_ids(self):
        return [c["id"] for c in self._cols if c.get("editable", True)]

    def _tab(self, event, row_idx, col_id):
        eids = self._editable_ids()
        try:
            ci = eids.index(col_id)
        except ValueError:
            return
        if ci < len(eids) - 1:
            # next editable col in same row
            self._widgets[row_idx][eids[ci + 1]].focus_set()
        else:
            # last col → next row (create if needed)
            next_r = row_idx + 1
            if next_r >= len(self._widgets):
                self._add_row()
            self._widgets[next_r][eids[0]].focus_set()
            # Scroll to show it
            self._canvas.update_idletasks()
            self._canvas.yview_moveto(
                next_r / max(1, len(self._widgets)))
        return "break"

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _f9(self, row_idx, col_id):
        val = self._widgets[row_idx][col_id].get()
        if self.on_f9:
            self.on_f9(row_idx, col_id, val)

    def _fo(self, row_idx, col_id):
        val = self._widgets[row_idx][col_id].get().strip()
        if self.on_focus_out:
            self.on_focus_out(row_idx, col_id, val)

    def _change(self):
        if self.on_change:
            self.on_change(self.get_all_rows())

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_value(self, row_idx, col_id):
        if row_idx < len(self._widgets):
            e = self._widgets[row_idx].get(col_id)
            return e.get().strip() if e else ""
        return ""

    def set_value(self, row_idx, col_id, value):
        """Set a cell value (works on both editable and readonly cells)."""
        if row_idx >= len(self._widgets):
            return
        e = self._widgets[row_idx].get(col_id)
        if not e:
            return
        s = e.cget("state")
        e.configure(state="normal")
        e.delete(0, "end")
        e.insert(0, str(value) if value is not None else "")
        e.configure(state=s)

    def get_all_rows(self):
        """Return non-empty rows as list of dicts."""
        eids = self._editable_ids()
        result = []
        for row in self._widgets:
            data = {c["id"]: row[c["id"]].get().strip() for c in self._cols}
            if any(data.get(eid) for eid in eids):
                result.append(data)
        return result

    def load_rows(self, data_list):
        """Clear and load data. data_list = list of dicts."""
        self.reset()
        for i, row_data in enumerate(data_list):
            if i < len(self._widgets):
                for col in self._cols:
                    cid = col["id"]
                    if cid in row_data:
                        self.set_value(i, cid, row_data[cid])
            else:
                self._add_row(row_data)
        self._change()

    def reset(self):
        """Clear all rows and redraw blank rows."""
        for rf in self._frames:
            rf.destroy()
        self._widgets = []
        self._frames  = []
        for _ in range(self._start_rows):
            self._add_row()

    def delete_focused_row(self):
        """Delete whichever row currently has keyboard focus."""
        focused = self.focus_get()
        for i, row in enumerate(self._widgets):
            if focused in row.values():
                self._delete_row(i)
                return

    def _delete_row(self, idx):
        if idx >= len(self._frames):
            return
        self._frames[idx].destroy()
        self._widgets.pop(idx)
        self._frames.pop(idx)
        # Re-stripe
        for i, rf in enumerate(self._frames):
            rf.configure(bg=self._row_bg(i))
        # Ensure at least start_rows blank rows remain
        while len(self._widgets) < self._start_rows:
            self._add_row()
        if self.on_delete_row:
            self.on_delete_row(idx)
        self._change()

    def focus_first(self):
        eids = self._editable_ids()
        if eids and self._widgets:
            self._widgets[0][eids[0]].focus_set()

    def set_editable(self, editable):
        """Enable or lock all editable cells (readonly keeps text visible)."""
        for row in self._widgets:
            for col in self._cols:
                if col.get("editable", True):
                    e = row.get(col["id"])
                    if e:
                        e.configure(state="normal" if editable else "readonly")
