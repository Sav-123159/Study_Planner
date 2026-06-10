# Study_Planner
Semester Study Planner, based on a 7 day study planner

## Usage

List modules:

```bash
python Main.py list
```

Show modules and tests:

```bash
python Main.py show-tests
```

Show study plan for next 30 days:

```bash
python Main.py plan
```

Export study plan to JSON:

```bash
python Main.py plan --export json --out plan.json
```

Export study plan to CSV:

```bash
python Main.py plan --export csv --out plan.csv
```

Add a module:

```bash
python Main.py add-module Biology
```

Remove a module:

```bash
python Main.py remove-module Biology
```

Add a test:

```bash
python Main.py add-test Math test5 2026-07-10 0.2 Math --score 0 --priority High
```

Remove a test:

```bash
python Main.py remove-test Math test5
```

## GUI

A simple styled Tkinter GUI is provided in `gui.py` to view and edit modules/tests and to generate/export the study plan.

Run the GUI with:

```bash
python gui.py
```

GUI notes:
- Uses ttk styling and Segoe UI fonts on Windows for a cleaner look.
- Lists have scrollbars; the plan view uses a monospaced font for readability.
- Date input is validated as `YYYY-MM-DD` when adding tests.

