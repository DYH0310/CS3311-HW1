import tempfile
import unittest
from pathlib import Path

from ledger import Ledger, parse_money, validate_date, validate_month


class LedgerTests(unittest.TestCase):
    def test_add_statistics_delete_and_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ledger.sqlite3"
            ledger = Ledger(path)
            first = ledger.add("2026-10-02", "12.50", "餐饮", "午饭")
            ledger.add("2026-10-03", "3.00", "交通")
            ledger.add("2026-09-30", "20.00", "学习")
            ledger.set_budget("15.50")
            total, categories = ledger.summary("2026-10")
            self.assertEqual(total, 1550)
            self.assertEqual(categories["餐饮"], 1250)
            self.assertEqual(categories["交通"], 300)
            self.assertEqual(categories["学习"], 0)
            self.assertGreaterEqual(total, ledger.budget())
            ledger.close()
            ledger = Ledger(path)
            self.assertEqual(len(ledger.records()), 3)
            self.assertEqual(ledger.budget(), 1550)
            ledger.delete(first)
            self.assertEqual(ledger.summary("2026-10")[0], 300)
            ledger.close()

    def test_invalid_values_and_valid_leap_day(self):
        for amount in ("", "-1", "0", "abc", "NaN", "Infinity", "1.234"):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                parse_money(amount)
        for day in ("", "2026-2-9", "2026-02-29", "2026-13-01", "2026-04-31"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                validate_date(day)
        self.assertEqual(validate_date("2024-02-29"), "2024-02-29")
        self.assertEqual(parse_money("0.01"), 1)
        self.assertEqual(parse_money("99999999.99"), 9999999999)
        with self.assertRaises(ValueError):
            parse_money("100000000.00")

    def test_invalid_date_does_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Ledger(Path(folder) / "ledger.sqlite3")
            for day in ("2026-2-9", "2026-02-29"):
                with self.assertRaises(ValueError):
                    ledger.add(day, "12.50", "餐饮", "保留输入")
                self.assertEqual(ledger.records(), [])
            ledger.add(" 2026-02-09 ", "12.50", "餐饮")
            self.assertEqual(ledger.records()[0][1], "2026-02-09")
            ledger.close()

    def test_month_filter_and_empty_month(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Ledger(Path(folder) / "ledger.sqlite3")
            ledger.add("2026-09-30", "20", "学习")
            lunch = ledger.add("2026-10-02", "12.50", "餐饮")
            ledger.add("2026-10-03", "3", "交通")
            self.assertEqual(len(ledger.records("2026-09")), 1)
            self.assertEqual(ledger.summary("2026-09")[0], 2000)
            self.assertEqual(len(ledger.records("2026-10")), 2)
            self.assertEqual(ledger.summary("2026-10")[0], 1550)
            self.assertEqual(ledger.records("2026-11"), [])
            total, categories = ledger.summary("2026-11")
            self.assertEqual(total, 0)
            self.assertTrue(all(amount == 0 for amount in categories.values()))
            ledger.delete(lunch)
            self.assertEqual(len(ledger.records("2026-10")), 1)
            self.assertEqual(ledger.summary("2026-10")[0], 300)
            for month in ("2026-9", "2026-00", "2026-13", "0000-01", ""):
                with self.subTest(month=month), self.assertRaises(ValueError):
                    validate_month(month)
            ledger.close()

    def test_invalid_budget_preserves_saved_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ledger.sqlite3"
            ledger = Ledger(path)
            ledger.set_budget("1000")
            for amount in ("", "-1", "abc", "1.234", "NaN"):
                with self.assertRaises(ValueError):
                    ledger.set_budget(amount)
                self.assertEqual(ledger.budget(), 100000)
            ledger.set_budget("2000")
            ledger.close()
            ledger = Ledger(path)
            self.assertEqual(ledger.budget(), 200000)
            ledger.close()


if __name__ == "__main__":
    unittest.main()
