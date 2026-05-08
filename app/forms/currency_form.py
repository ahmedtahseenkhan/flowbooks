"""Currency Transaction Form / CTF  and  Value Adjustment Form / VAF."""

import tkinter as tk
from tkinter import messagebox
from config import *
from forms.base_form import BaseForm, make_grid, InventoryLOVDialog, AccountLOVDialog
import database as db
from datetime import date


class CurrencyTransactionForm(BaseForm):

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "CURRENCY TRANSACTION FORM / CTF",
                         "CURRENCY TRANSACTION FORM", username,
                         "Alt+A : Add    Alt+S : Save    Alt+D : Delete    "
                         "Alt+X : Exit    F9 : LOV")
        self.geometry("860x580")
        self._lines = []
        self._current = None
        self._build_form()
        self._bind_keys()

    def _build_form(self):
        c = self.content

        hp = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hp.pack(fill="x", padx=8, pady=6)
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)
        tkw = dict(bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)

        tk.Label(hp, text="Invoice #", **lkw).grid(row=0,column=0,sticky="e",padx=(8,2),pady=4)
        self._inv_e = tk.Entry(hp, width=12, **tkw)
        self._inv_e.grid(row=0,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hp, text="Dated", **lkw).grid(row=0,column=2,sticky="e",padx=(6,2),pady=4)
        self._dated_e = tk.Entry(hp, width=12, bg="#D0DCF0",
                                 font=FONT_NORMAL, relief="sunken", bd=2)
        self._dated_e.grid(row=0,column=3,sticky="w",padx=2,pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hp, text="A/C", **lkw).grid(row=0,column=4,sticky="e",padx=(6,2),pady=4)
        self._ac_e = tk.Entry(hp, width=9, **tkw)
        self._ac_e.grid(row=0,column=5,sticky="w",padx=2,pady=4)
        self._ac_name_var = tk.StringVar()
        tk.Entry(hp, textvariable=self._ac_name_var, width=22,
                 bg="#E8E8E8", font=FONT_NORMAL, state="readonly",
                 relief="sunken", bd=2).grid(row=0,column=6,sticky="ew",padx=(2,8),pady=4)

        tk.Label(hp, text="Type", **lkw).grid(row=1,column=0,sticky="e",padx=(8,2),pady=4)
        self._type_var = tk.StringVar(value="BUY")
        tk.OptionMenu(hp, self._type_var, "BUY","SELL").grid(
            row=1,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hp, text="Party", **lkw).grid(row=1,column=2,sticky="e",padx=(6,2),pady=4)
        self._party_e = tk.Entry(hp, width=30, **tkw)
        self._party_e.grid(row=1,column=3,columnspan=3,sticky="ew",padx=2,pady=4)

        tk.Label(hp, text="Description", **lkw).grid(row=2,column=0,sticky="e",padx=(8,2),pady=4)
        self._desc_e = tk.Entry(hp, width=60, **tkw)
        self._desc_e.grid(row=2,column=1,columnspan=6,sticky="ew",padx=(2,8),pady=4)

        # Grid
        cols = [("serial","Serial",50),("code","Inv Code",80),
                ("name","Currency Name",180),("qty","Quantity",90),
                ("rate","Rate",90),("value","Value",100)]
        gf, self._ltree = make_grid(c, cols, height=10)
        gf.pack(fill="both", expand=True, padx=8, pady=4)
        self._ltree.bind("<<TreeviewSelect>>", self._on_sel)

        # Line entry
        ler = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        ler.pack(fill="x", padx=8, pady=2)
        for attr, lbl, w in [("_le_code","Inv Code",9),("_le_name","Name",22),
                              ("_le_qty","Quantity",9),("_le_rate","Rate",9),
                              ("_le_val","Value",10)]:
            tk.Label(ler,text=lbl,bg=FORM_BG,fg=LABEL_FG,font=FONT_SMALL).pack(side="left",padx=(6,2))
            e = tk.Entry(ler,width=w,bg=ENTRY_BG,font=FONT_NORMAL,relief="sunken",bd=2)
            e.pack(side="left",padx=2)
            setattr(self, attr, e)
        self._le_code.bind("<F9>", self._f9_inv)
        self._le_qty.bind("<FocusOut>", self._calc)
        self._le_rate.bind("<FocusOut>", self._calc)
        tk.Button(ler,text="Add Line",bg=BTN_BG,font=FONT_SMALL,
                  relief="raised",bd=2,command=self._add_line).pack(side="left",padx=6,pady=3)
        tk.Button(ler,text="Remove",bg=BTN_BG,font=FONT_SMALL,
                  relief="raised",bd=2,command=self._del_line).pack(side="left",padx=2,pady=3)

        # Total
        tf = tk.Frame(c, bg=FORM_BG)
        tf.pack(fill="x", padx=8, pady=2)
        self._total_var = tk.StringVar(value="0.00")
        tk.Label(tf,text="Total Value",bg=FORM_BG,fg=LABEL_FG,font=FONT_BOLD).pack(side="right",padx=4)
        tk.Entry(tf,textvariable=self._total_var,width=16,bg="#E8E8E8",
                 font=FONT_NORMAL,state="readonly",relief="sunken",bd=2).pack(side="right",padx=4)

        self._ac_e.bind("<F9>", self._f9_ac)
        self._ac_e.bind("<FocusOut>", self._lookup_ac)
        self._set_hdr("disabled")

    def _f9_ac(self, _):
        dlg = AccountLOVDialog(self, self._ac_e.get())
        if dlg.result:
            self._ac_e.delete(0,"end"); self._ac_e.insert(0, dlg.result[0])
            self._ac_name_var.set(dlg.result[1])

    def _f9_inv(self, _):
        dlg = InventoryLOVDialog(self, self._le_code.get())
        if dlg.result:
            self._le_code.delete(0,"end"); self._le_code.insert(0, dlg.result[0])
            self._le_name.delete(0,"end"); self._le_name.insert(0, dlg.result[1])
            self._le_rate.delete(0,"end"); self._le_rate.insert(0, f"{dlg.result[3]:.4f}")
            self._le_qty.focus_set()

    def _lookup_ac(self, _):
        row = db.get_account(self._ac_e.get().strip())
        if row:
            self._ac_name_var.set(row["ac_name"])

    def _calc(self, _):
        try:
            v = float(self._le_qty.get() or 0) * float(self._le_rate.get() or 0)
            self._le_val.delete(0,"end"); self._le_val.insert(0, f"{v:.2f}")
        except ValueError:
            pass

    def _add_line(self):
        code = self._le_code.get().strip()
        if not code:
            messagebox.showwarning("Input","Inv Code required.",parent=self); return
        try:
            qty  = float(self._le_qty.get()  or 0)
            rate = float(self._le_rate.get() or 0)
            val  = float(self._le_val.get()  or 0) or qty*rate
        except ValueError:
            messagebox.showwarning("Input","Numeric values required.",parent=self); return
        sn = len(self._lines)+1
        self._lines.append([sn, code, self._le_name.get().strip(), qty, rate, val])
        self._render()
        for e in [self._le_code,self._le_name,self._le_qty,self._le_rate,self._le_val]:
            e.delete(0,"end")
        self._le_code.focus_set()

    def _del_line(self):
        sel = self._ltree.selection()
        if not sel: return
        del self._lines[self._ltree.index(sel[0])]
        for i,r in enumerate(self._lines): r[0]=i+1
        self._render()

    def _on_sel(self, _):
        sel = self._ltree.selection()
        if not sel: return
        r = self._lines[self._ltree.index(sel[0])]
        for e,v in [(self._le_code,r[1]),(self._le_name,r[2]),
                    (self._le_qty,f"{r[3]:.2f}"),(self._le_rate,f"{r[4]:.4f}"),
                    (self._le_val,f"{r[5]:.2f}")]:
            e.delete(0,"end"); e.insert(0,v)

    def _render(self):
        self._ltree.delete(*self._ltree.get_children())
        total=0.0
        for i,r in enumerate(self._lines):
            tag="odd" if i%2 else "even"
            self._ltree.insert("","end",values=(r[0],r[1],r[2],
                f"{r[3]:,.2f}",f"{r[4]:,.4f}",f"{r[5]:,.2f}"),tags=(tag,))
            total+=r[5]
        self._total_var.set(f"{total:,.2f}")

    def _set_hdr(self, state):
        for e in [self._dated_e,self._ac_e,self._party_e,self._desc_e]:
            e.configure(state=state)

    def on_add(self):
        self._current=None; self._lines=[]
        self._ltree.delete(*self._ltree.get_children())
        self._total_var.set("0.00")
        self._set_hdr("normal")
        next_no = db.next_invoice_no("purchase_transactions")
        self._inv_e.configure(state="normal")
        self._inv_e.delete(0,"end"); self._inv_e.insert(0, f"CTF-{next_no}")
        self._inv_e.configure(state="readonly")
        for e in [self._ac_e,self._party_e,self._desc_e]: e.delete(0,"end")
        self._dated_e.delete(0,"end")
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._ac_name_var.set("")
        self._dated_e.focus_set()
        self._mode="add"

    def on_save(self):
        if not self._lines:
            messagebox.showwarning("Validation","Add at least one line.",parent=self); return
        messagebox.showinfo("Saved","Currency transaction saved.",parent=self)
        self._set_hdr("disabled"); self._mode="view"

    def on_ignore(self):
        self._set_hdr("disabled"); self._mode="view"

    def _bind_keys(self):
        self.bind("<Alt-a>",lambda e:self.on_add())
        self.bind("<Alt-s>",lambda e:self.on_save())
        self.bind("<Alt-x>",lambda e:self.on_exit())


class ValueAdjustmentForm(BaseForm):
    """Value Adjustment Form / VAF – adjust inventory value."""

    def __init__(self, master, username="ADMIN"):
        super().__init__(master, "VALUE ADJUSTMENT FORM / VAF",
                         "VALUE ADJUSTMENT FORM", username,
                         "Alt+A : Add    Alt+S : Save    Alt+X : Exit    F9 : LOV")
        self.geometry("760x480")
        self._lines = []
        self._build_form()
        self._bind_keys()

    def _build_form(self):
        c = self.content
        hp = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        hp.pack(fill="x", padx=8, pady=6)
        lkw = dict(bg=FORM_BG, fg=LABEL_FG, font=FONT_BOLD)
        tkw = dict(bg=ENTRY_BG, font=FONT_NORMAL, relief="sunken", bd=2)

        tk.Label(hp, text="Ref #",  **lkw).grid(row=0,column=0,sticky="e",padx=(8,2),pady=4)
        self._ref_e = tk.Entry(hp, width=12, **tkw)
        self._ref_e.grid(row=0,column=1,sticky="w",padx=2,pady=4)

        tk.Label(hp, text="Dated", **lkw).grid(row=0,column=2,sticky="e",padx=(6,2),pady=4)
        self._dated_e = tk.Entry(hp, width=12, bg="#D0DCF0",
                                 font=FONT_NORMAL, relief="sunken", bd=2)
        self._dated_e.grid(row=0,column=3,sticky="w",padx=2,pady=4)
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))

        tk.Label(hp, text="Description", **lkw).grid(row=1,column=0,sticky="e",padx=(8,2),pady=4)
        self._desc_e = tk.Entry(hp, width=50, **tkw)
        self._desc_e.grid(row=1,column=1,columnspan=4,sticky="ew",padx=(2,8),pady=4)

        cols = [("code","Inv Code",80),("name","Inventory Name",200),
                ("old_val","Old Value",100),("new_val","New Value",100),
                ("diff","Difference",100)]
        gf, self._ltree = make_grid(c, cols, height=10)
        gf.pack(fill="both", expand=True, padx=8, pady=4)

        ler = tk.Frame(c, bg=FORM_BG, bd=1, relief="groove")
        ler.pack(fill="x", padx=8, pady=2)
        for attr, lbl, w in [("_le_code","Inv Code",9),("_le_name","Name",24),
                              ("_le_old","Old Value",10),("_le_new","New Value",10)]:
            tk.Label(ler,text=lbl,bg=FORM_BG,fg=LABEL_FG,font=FONT_SMALL).pack(side="left",padx=(6,2))
            e = tk.Entry(ler,width=w,bg=ENTRY_BG,font=FONT_NORMAL,relief="sunken",bd=2)
            e.pack(side="left",padx=2)
            setattr(self, attr, e)
        self._le_code.bind("<F9>", self._f9_inv)
        self._le_code.bind("<FocusOut>", self._lookup_inv)
        tk.Button(ler,text="Add",bg=BTN_BG,font=FONT_SMALL,
                  relief="raised",bd=2,command=self._add_line).pack(side="left",padx=6,pady=3)

        self._set_hdr("disabled")

    def _f9_inv(self, _):
        dlg = InventoryLOVDialog(self, self._le_code.get())
        if dlg.result:
            self._le_code.delete(0,"end"); self._le_code.insert(0, dlg.result[0])
            self._le_name.delete(0,"end"); self._le_name.insert(0, dlg.result[1])
            item = db.get_inventory_item(dlg.result[0])
            if item:
                self._le_old.delete(0,"end")
                self._le_old.insert(0, f"{item['value']:,.2f}")
            self._le_new.focus_set()

    def _lookup_inv(self, _):
        item = db.get_inventory_item(self._le_code.get().strip())
        if item:
            self._le_name.delete(0,"end"); self._le_name.insert(0, item["name"])
            self._le_old.delete(0,"end");  self._le_old.insert(0, f"{item['value']:,.2f}")

    def _add_line(self):
        code = self._le_code.get().strip()
        if not code:
            messagebox.showwarning("Input","Inv Code required.",parent=self); return
        try:
            old = float(self._le_old.get() or 0)
            new = float(self._le_new.get() or 0)
        except ValueError:
            messagebox.showwarning("Input","Numeric values required.",parent=self); return
        diff = new - old
        tag = "odd" if len(self._lines)%2 else "even"
        self._lines.append((code, self._le_name.get(), old, new, diff))
        self._ltree.insert("","end",values=(code, self._le_name.get(),
            f"{old:,.2f}", f"{new:,.2f}", f"{diff:,.2f}"),tags=(tag,))
        for e in [self._le_code,self._le_name,self._le_old,self._le_new]: e.delete(0,"end")
        self._le_code.focus_set()

    def _set_hdr(self, state):
        for e in [self._dated_e, self._desc_e]: e.configure(state=state)

    def on_add(self):
        self._lines=[]
        self._ltree.delete(*self._ltree.get_children())
        self._set_hdr("normal")
        self._ref_e.configure(state="normal"); self._ref_e.delete(0,"end")
        self._ref_e.insert(0, f"VAF-{date.today().strftime('%Y%m%d')}")
        self._ref_e.configure(state="readonly")
        self._dated_e.delete(0,"end")
        self._dated_e.insert(0, date.today().strftime("%d/%m/%Y"))
        self._desc_e.delete(0,"end")
        self._dated_e.focus_set()
        self._mode="add"

    def on_save(self):
        if not self._lines:
            messagebox.showwarning("Validation","Add at least one line.",parent=self); return
        messagebox.showinfo("Saved","Value adjustment saved.",parent=self)
        self._set_hdr("disabled"); self._mode="view"

    def on_ignore(self):
        self._set_hdr("disabled"); self._mode="view"

    def _bind_keys(self):
        self.bind("<Alt-a>",lambda e:self.on_add())
        self.bind("<Alt-s>",lambda e:self.on_save())
        self.bind("<Alt-x>",lambda e:self.on_exit())
