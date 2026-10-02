"""校园消费记账：金额以分保存，SQLite 负责本地持久化。"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3
import re

CATEGORIES = ("餐饮", "交通", "学习", "购物", "娱乐", "其他")
DEFAULT_DB = Path(__file__).resolve().parent / "data" / "ledger.sqlite3"


def parse_money(text):
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        raise ValueError("请输入金额，例如 12.50。") from None
    if not value.is_finite() or value <= 0 or value > Decimal("99999999.99"):
        raise ValueError("金额须大于 0，且不超过 99999999.99 元。")
    cents = value * 100
    if cents != cents.to_integral_value():
        raise ValueError("金额最多保留两位小数。")
    return int(cents)


def validate_date(text):
    text = text.strip()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValueError("日期格式须为 YYYY-MM-DD，月份和日期须写满两位。")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValueError("请输入有效日期，格式为 YYYY-MM-DD。") from None


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def validate_month(text):
    text = text.strip()
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", text) or text.startswith("0000-"):
        raise ValueError("查看月份须为 YYYY-MM，例如 2026-10，月份为 01 到 12。")
    return text


class Ledger:
    def __init__(self, path=DEFAULT_DB):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                cents INTEGER NOT NULL CHECK (cents > 0),
                category TEXT NOT NULL,
                note TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                cents INTEGER NOT NULL CHECK (cents > 0)
            );
        """)

    def add(self, day, amount, category, note=""):
        day = validate_date(day)
        cents = parse_money(amount)
        if category not in CATEGORIES:
            raise ValueError("请选择列表中的消费类别。")
        with self.db:
            row = self.db.execute(
                "INSERT INTO expenses (day, cents, category, note) VALUES (?, ?, ?, ?)",
                (day, cents, category, note.strip()),
            )
        return row.lastrowid

    def delete(self, record_id):
        with self.db:
            self.db.execute("DELETE FROM expenses WHERE id = ?", (record_id,))

    def records(self, month=None):
        if month is not None:
            month = validate_month(month)
            return self.db.execute(
                "SELECT id, day, cents, category, note FROM expenses WHERE substr(day, 1, 7) = ? ORDER BY day DESC, id DESC",
                (month,),
            ).fetchall()
        return self.db.execute(
            "SELECT id, day, cents, category, note FROM expenses ORDER BY day DESC, id DESC"
        ).fetchall()

    def summary(self, month):
        month = validate_month(month)
        rows = self.db.execute(
            "SELECT category, SUM(cents) FROM expenses WHERE substr(day, 1, 7) = ? GROUP BY category",
            (month,),
        ).fetchall()
        by_category = {category: 0 for category in CATEGORIES}
        by_category.update(rows)
        return sum(by_category.values()), by_category

    def set_budget(self, amount):
        cents = parse_money(amount)
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('budget', ?)", (cents,))

    def budget(self):
        row = self.db.execute("SELECT cents FROM settings WHERE key = 'budget'").fetchone()
        return row[0] if row else None

    def close(self):
        self.db.close()


if __name__ == "__main__":
    from app import main
    main()
