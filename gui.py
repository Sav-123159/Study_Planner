import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import datetime
import Main as planner


class StudyPlannerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Study Planner')
        self.geometry('1100x700')
        self.minsize(900, 600)

        self.modules = []
        self.current_module = None
        self.last_plan = None
        self._data_cache = planner.load_tests()

        self._setup_style()
        self._build_ui()
        self.reload_modules()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _get_data(self) -> dict:
        return self._data_cache

    def _invalidate_cache(self):
        self._data_cache = planner.load_tests()

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TFrame', background='#f7f7f7')
        style.configure('TLabel', background='#f7f7f7', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('TButton', padding=6)
        self.default_font = ('Segoe UI', 10)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        container = ttk.Frame(self, padding=10)
        container.pack(fill='both', expand=True)

        # ---- Left: Modules ----
        left = ttk.Frame(container)
        left.grid(row=0, column=0, sticky='ns', padx=(0, 10))

        ttk.Label(left, text='Modules', style='Header.TLabel').pack(anchor='w')
        ml_frame = ttk.Frame(left)
        ml_frame.pack(fill='y', expand=True)
        self.module_list = tk.Listbox(ml_frame, width=28, height=22, font=self.default_font)
        self.module_list.pack(side='left', fill='y')
        mscroll = ttk.Scrollbar(ml_frame, orient='vertical', command=self.module_list.yview)
        mscroll.pack(side='left', fill='y')
        self.module_list.config(yscrollcommand=mscroll.set)
        self.module_list.bind('<<ListboxSelect>>', self.on_module_select)

        bframe = ttk.Frame(left)
        bframe.pack(pady=8)
        ttk.Button(bframe, text='Add', width=10, command=self.add_module).grid(row=0, column=0, padx=4)
        ttk.Button(bframe, text='Remove', width=10, command=self.remove_module).grid(row=0, column=1, padx=4)

        # ---- Mid: Tests (Treeview) ----
        mid = ttk.Frame(container)
        mid.grid(row=0, column=1, sticky='nsew', padx=(0, 10))
        container.columnconfigure(1, weight=1)

        ttk.Label(mid, text='Tests', style='Header.TLabel').pack(anchor='w')

        cols = ('ID', 'Date', 'Subject', 'Weight', 'Priority')
        self.test_tree = ttk.Treeview(mid, columns=cols, show='headings', height=20)
        col_widths = {'ID': 80, 'Date': 90, 'Subject': 120, 'Weight': 60, 'Priority': 70}
        for c in cols:
            self.test_tree.heading(c, text=c)
            self.test_tree.column(c, width=col_widths[c], anchor='center')
        tscroll = ttk.Scrollbar(mid, orient='vertical', command=self.test_tree.yview)
        self.test_tree.config(yscrollcommand=tscroll.set)
        self.test_tree.pack(side='left', fill='both', expand=True)
        tscroll.pack(side='left', fill='y')

        tframe = ttk.Frame(container)
        tframe.grid(row=1, column=1, pady=8)
        ttk.Button(tframe, text='Add Test', command=self.add_test).grid(row=0, column=0, padx=4)
        ttk.Button(tframe, text='Remove Test', command=self.remove_test).grid(row=0, column=1, padx=4)
        ttk.Button(tframe, text='Show Plan', command=self.generate_plan).grid(row=0, column=2, padx=4)

        # ---- Right: Plan ----
        right = ttk.Frame(container)
        right.grid(row=0, column=2, sticky='nsew')
        container.columnconfigure(2, weight=2)

        ttk.Label(right, text='Plan (next 30 days)', style='Header.TLabel').pack(anchor='w')
        self.plan_text = tk.Text(right, wrap='none', font=('Consolas', 10))
        self.plan_text.tag_configure('date_header', font=('Consolas', 10, 'bold'), foreground='#1a4a8a')
        self.plan_text.pack(fill='both', expand=True)

        hscroll = ttk.Scrollbar(right, orient='horizontal', command=self.plan_text.xview)
        hscroll.pack(fill='x')
        self.plan_text.config(xscrollcommand=hscroll.set)

        rframe = ttk.Frame(right)
        rframe.pack(pady=8)
        ttk.Button(rframe, text='Export JSON', command=lambda: self.export_plan('json')).grid(row=0, column=0, padx=4)
        ttk.Button(rframe, text='Export CSV', command=lambda: self.export_plan('csv')).grid(row=0, column=1, padx=4)

        # ---- Status bar ----
        self.status_var = tk.StringVar(value='Ready')
        status_bar = ttk.Label(self, textvariable=self.status_var, relief='sunken', anchor='w', padding=(6, 2))
        status_bar.pack(side='bottom', fill='x')

    # ------------------------------------------------------------------
    # Module operations
    # ------------------------------------------------------------------

    def reload_modules(self):
        data = self._get_data()
        self.modules = planner.list_modules(data)
        self.module_list.delete(0, 'end')
        for m in self.modules:
            self.module_list.insert('end', m)

    def on_module_select(self, event=None):
        sel = self.module_list.curselection()
        if not sel:
            return
        self.current_module = self.modules[sel[0]]
        self.reload_tests()

    def add_module(self):
        name = simpledialog.askstring('Add Module', 'Module name:', parent=self)
        if not name:
            return
        data = self._get_data()
        if planner.add_module(data, name):
            planner.save_tests(data)
            self.reload_modules()
            self._set_status(f"Module '{name}' added.")
        else:
            messagebox.showinfo('Info', 'Module already exists', parent=self)

    def remove_module(self):
        sel = self.module_list.curselection()
        if not sel:
            return
        module = self.modules[sel[0]]
        if not messagebox.askyesno('Confirm', f"Remove module '{module}' and all its tests?", parent=self):
            return
        data = self._get_data()
        planner.remove_module(data, module)
        planner.save_tests(data)
        self.current_module = None
        self.reload_modules()
        self._clear_tests()
        self._set_status(f"Module '{module}' removed.")

    # ------------------------------------------------------------------
    # Test operations
    # ------------------------------------------------------------------

    def reload_tests(self):
        self._clear_tests()
        if not self.current_module:
            return
        tests = planner.list_tests(self._get_data(), self.current_module)
        for tid, info in tests.items():
            self.test_tree.insert('', 'end', iid=tid, values=(
                tid,
                info.get('date', ''),
                info.get('subject', ''),
                info.get('weight', ''),
                info.get('priority', '')
            ))

    def _clear_tests(self):
        for row in self.test_tree.get_children():
            self.test_tree.delete(row)

    def add_test(self):
        if not self.current_module:
            messagebox.showinfo('Info', 'Select a module first', parent=self)
            return

        tid = simpledialog.askstring('Test ID', 'Test ID (e.g., test1):', parent=self)
        if not tid:
            return

        date = simpledialog.askstring('Date', 'Date (YYYY-MM-DD):', parent=self)
        if date:
            try:
                datetime.date.fromisoformat(date)
            except ValueError:
                messagebox.showerror('Error', 'Invalid date format. Use YYYY-MM-DD.', parent=self)
                return

        weight = simpledialog.askfloat('Weight', 'Weight (0.0 – 1.0):', parent=self)
        if weight is not None and not (0.0 <= weight <= 1.0):
            messagebox.showerror('Error', 'Weight must be between 0.0 and 1.0.', parent=self)
            return

        subject = simpledialog.askstring('Subject', 'Subject name:', parent=self)
        score = simpledialog.askinteger('Score', 'Score (optional, leave blank to skip):', parent=self)
        priority = simpledialog.askstring('Priority', 'Priority (Low / Medium / High):', parent=self)
        if priority and priority not in planner.VALID_PRIORITIES:
            messagebox.showerror('Error', f"Priority must be one of: {', '.join(planner.VALID_PRIORITIES)}", parent=self)
            return

        data = self._get_data()
        try:
            planner.add_test(
                data, self.current_module, tid,
                date or '', weight or 0.0,
                subject or self.current_module,
                score, priority or 'Medium'
            )
        except ValueError as e:
            messagebox.showerror('Error', str(e), parent=self)
            return

        planner.save_tests(data)
        self.reload_tests()
        self._set_status(f"Test '{tid}' added to '{self.current_module}'.")

    def remove_test(self):
        sel = self.test_tree.selection()
        if not sel or not self.current_module:
            return
        test_id = sel[0]
        if not messagebox.askyesno('Confirm', f"Remove test '{test_id}'?", parent=self):
            return
        data = self._get_data()
        planner.remove_test(data, self.current_module, test_id)
        planner.save_tests(data)
        self.reload_tests()
        self._set_status(f"Test '{test_id}' removed.")

    # ------------------------------------------------------------------
    # Plan
    # ------------------------------------------------------------------

    def generate_plan(self):
        data = self._get_data()
        plan = planner.generate_study_plan(data)
        self.last_plan = plan
        self.plan_text.delete('1.0', 'end')
        for date in sorted(plan.keys()):
            self.plan_text.insert('end', f"{date}:\n", 'date_header')
            for s in plan[date]:
                self.plan_text.insert('end',
                    f"  - {s['activity']}: {s['subject']} ({s['module']}/{s['test_id']}) on {s['test_date']}\n")
        now = datetime.datetime.now().strftime('%H:%M:%S')
        self._set_status(f"Plan generated at {now}.")

    def export_plan(self, fmt: str):
        if not self.last_plan:
            self.generate_plan()
        filetypes = [('JSON file', '*.json')] if fmt == 'json' else [('CSV file', '*.csv')]
        f = filedialog.asksaveasfilename(
            parent=self,
            defaultextension='.' + fmt,
            filetypes=filetypes
        )
        if not f:
            return
        if fmt == 'json':
            planner.export_plan_json(self.last_plan, f)
        else:
            planner.export_plan_csv(self.last_plan, f)
        self._set_status(f"Plan exported to {f}")
        messagebox.showinfo('Export', f'Plan exported to:\n{f}', parent=self)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self.status_var.set(msg)


if __name__ == '__main__':
    app = StudyPlannerGUI()
    app.mainloop()