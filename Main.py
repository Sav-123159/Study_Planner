import datetime
import json
import re
import os
import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent
TESTS_FILE = BASE_DIR / "Tests.txt"

# Activity thresholds (days before test)
ORGANIZE_THRESHOLD = 7
REVIEW_CONTENT_MIN = 4
STUDY_MATERIAL_MIN = 2

VALID_PRIORITIES = {"Low", "Medium", "High"}


def _clean_json_like(text: str) -> str:
    text = text.strip()
    text = re.sub(r',\s*([}\]])', r"\1", text)
    return text


def load_tests() -> dict:
    if not TESTS_FILE.exists():
        return {}
    raw = TESTS_FILE.read_text(encoding='utf-8')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = _clean_json_like(raw)
        return json.loads(cleaned)


def save_tests(data: dict):
    TESTS_FILE.write_text(json.dumps(data, indent=4, sort_keys=True), encoding='utf-8')


def list_modules(data: dict):
    return list(data.keys())


def list_tests(data: dict, module: str):
    return data.get(module, {})


def add_module(data: dict, module: str):
    if module in data:
        return False
    data[module] = {}
    return True


def remove_module(data: dict, module: str):
    if module in data:
        del data[module]
        return True
    return False


def add_test(data: dict, module: str, test_id: str, date: str, weight: float,
             subject: str, score: int = None, priority: str = 'Medium'):
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Priority must be one of {VALID_PRIORITIES}")
    if not (0.0 <= weight <= 1.0):
        raise ValueError("Weight must be between 0.0 and 1.0")
    if module not in data:
        data[module] = {}
    if test_id in data[module]:
        raise ValueError(f"Test ID '{test_id}' already exists in module '{module}'")
    data[module][test_id] = {
        'date': date,
        'weight': weight,
        'subject': subject,
        'score': score,
        'priority': priority
    }


def remove_test(data: dict, module: str, test_id: str):
    if module in data and test_id in data[module]:
        del data[module][test_id]
        return True
    return False


def _flatten_tests(data: dict) -> list:
    flattened = []
    for module, tests in data.items():
        for test_id, info in tests.items():
            if not info.get('date'):
                continue  # skip tests with no date
            flattened.append({
                'module': module,
                'id': test_id,
                'date': info['date'],
                'weight': info.get('weight', 0),
                'subject': info.get('subject', module),
                'score': info.get('score'),
                'priority': info.get('priority', 'Medium')
            })
    return flattened


def _activity_for_days_before(days_before: int) -> str:
    if days_before >= ORGANIZE_THRESHOLD:
        return 'Organize'
    if days_before >= REVIEW_CONTENT_MIN:
        return 'Review Content & Self Test'
    if days_before >= STUDY_MATERIAL_MIN:
        return 'Study Material'
    return 'Review'


def generate_study_plan(data: dict, today: datetime.date = None, days_ahead: int = 30) -> dict:
    if today is None:
        today = datetime.date.today()
    end_date = today + datetime.timedelta(days=days_ahead)

    sessions: dict[str, list] = {}
    for i in range((end_date - today).days + 1):
        sessions[(today + datetime.timedelta(days=i)).isoformat()] = []

    tests = sorted(_flatten_tests(data), key=lambda t: t['date'])
    placed_sessions: set[tuple] = set()  # (test_id, module, date) to avoid duplicates

    for test in tests:
        try:
            test_date = datetime.date.fromisoformat(test['date'])
        except ValueError:
            continue

        window_start = max(today, test_date - datetime.timedelta(days=14))
        window_end = min(test_date - datetime.timedelta(days=1), end_date)
        if window_end < window_start:
            continue

        aim_sessions = 4
        days_range = (window_end - window_start).days + 1
        step = max(1, days_range // aim_sessions)

        chosen_dates = []
        for i in range(0, days_range, step):
            d = window_start + datetime.timedelta(days=i)
            if d > window_end:
                break
            chosen_dates.append(d)
            if len(chosen_dates) >= aim_sessions:
                break

        for sd in chosen_dates:
            day_key = sd.isoformat()
            session_key = (test['id'], test['module'], day_key)
            if day_key not in sessions:
                continue
            if len(sessions[day_key]) >= 2:
                continue
            if session_key in placed_sessions:
                continue
            days_before = (test_date - sd).days
            sessions[day_key].append({
                'subject': test['subject'],
                'module': test['module'],
                'test_id': test['id'],
                'test_date': test['date'],
                'activity': _activity_for_days_before(days_before)
            })
            placed_sessions.add(session_key)

    # remove empty days
    return {d: v for d, v in sessions.items() if v}


def print_plan(sessions: dict):
    for date in sorted(sessions.keys()):
        print(f"{date}:")
        for s in sessions[date]:
            print(f"  - {s['activity']}: {s['subject']} ({s['module']}/{s['test_id']}) on {s['test_date']}")


def _cli_list(args):
    data = load_tests()
    modules = list_modules(data)
    if not modules:
        print('No modules found.')
        return
    for m in modules:
        print(m)


def _cli_show_tests(args):
    data = load_tests()
    for m in list_modules(data):
        print(m)
        for tid, info in list_tests(data, m).items():
            print(f"  - {tid}: {info}")


def _cli_plan(args):
    data = load_tests()
    sessions = generate_study_plan(data, today=datetime.date.today(), days_ahead=30)
    print_plan(sessions)
    if hasattr(args, 'export') and args.export:
        out = getattr(args, 'out', None) or f"plan.{args.export}"
        if args.export == 'json':
            export_plan_json(sessions, out)
            print(f"Exported plan to {out}")
        elif args.export == 'csv':
            export_plan_csv(sessions, out)
            print(f"Exported plan to {out}")


def export_plan_json(sessions: dict, out_file: str):
    Path(out_file).write_text(json.dumps(sessions, indent=2), encoding='utf-8')


def export_plan_csv(sessions: dict, out_file: str):
    import csv
    rows = [
        {
            'date': date,
            'activity': it.get('activity'),
            'subject': it.get('subject'),
            'module': it.get('module'),
            'test_id': it.get('test_id'),
            'test_date': it.get('test_date')
        }
        for date, items in sessions.items()
        for it in items
    ]
    with open(out_file, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['date', 'activity', 'subject', 'module', 'test_id', 'test_date'])
        writer.writeheader()
        writer.writerows(rows)


def _cli_add_module(args):
    data = load_tests()
    if add_module(data, args.module):
        save_tests(data)
        print('Module added.')
    else:
        print('Module already exists.')


def _cli_remove_module(args):
    data = load_tests()
    if remove_module(data, args.module):
        save_tests(data)
        print('Module removed.')
    else:
        print('Module not found.')


def _cli_add_test(args):
    data = load_tests()
    try:
        add_test(data, args.module, args.test_id, args.date, args.weight,
                 args.subject, args.score, args.priority)
        save_tests(data)
        print('Test added.')
    except ValueError as e:
        print(f'Error: {e}')


def _cli_remove_test(args):
    data = load_tests()
    if remove_test(data, args.module, args.test_id):
        save_tests(data)
        print('Test removed.')
    else:
        print('Test not found.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Study planner tool')
    sub = parser.add_subparsers(dest='cmd')

    sub.add_parser('list', help='List modules')
    sub.add_parser('show-tests', help='Show modules and tests')
    p_plan = sub.add_parser('plan', help='Show study plan for next 30 days')
    p_plan.add_argument('--export', choices=['json', 'csv'])
    p_plan.add_argument('--out', help='Output filename')

    p_addm = sub.add_parser('add-module')
    p_addm.add_argument('module')

    p_remm = sub.add_parser('remove-module')
    p_remm.add_argument('module')

    p_addt = sub.add_parser('add-test')
    p_addt.add_argument('module')
    p_addt.add_argument('test_id')
    p_addt.add_argument('date')
    p_addt.add_argument('weight', type=float)
    p_addt.add_argument('subject')
    p_addt.add_argument('--score', type=int, default=None)
    p_addt.add_argument('--priority', default='Medium')

    p_remt = sub.add_parser('remove-test')
    p_remt.add_argument('module')
    p_remt.add_argument('test_id')

    args = parser.parse_args(argv)
    dispatch = {
        'list': _cli_list,
        'show-tests': _cli_show_tests,
        'plan': _cli_plan,
        'add-module': _cli_add_module,
        'remove-module': _cli_remove_module,
        'add-test': _cli_add_test,
        'remove-test': _cli_remove_test,
    }
    fn = dispatch.get(args.cmd)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()