"""使用临时账本驱动真实 Tk 窗口，验证按钮与界面的结果。"""

from datetime import date, timedelta
from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch

from app import App
from ledger import Ledger


def main():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "gui.sqlite3"
        root = tk.Tk()
        app = App(root, Ledger(path))
        root.update()
        with patch("app.messagebox.showerror") as error, patch("app.messagebox.showinfo") as info, patch("app.messagebox.askyesno", return_value=False) as confirm:
            today = date.today()
            for day, amount, category in [
                (today.isoformat(), "12.50", "餐饮"),
                (today.isoformat(), "3.00", "交通"),
                ((today.replace(day=1) - timedelta(days=1)).isoformat(), "20.00", "学习"),
            ]:
                app.day.set(day)
                app.amount.set(amount)
                app.category.set(category)
                app.add_button.invoke()
            root.update()
            assert len(app.table.get_children()) == 3
            assert "15.50" in app.summary_text.get()
            app.budget_input.set("15.50")
            app.budget_button.invoke()
            assert "已达到预算" in app.reminder.get()
            app.amount.set("-1")
            app.add_button.invoke()
            assert error.call_count == 1
            assert len(app.table.get_children()) == 3
            assert app.amount.get() == "-1"
            app.day.set("2026-2-9")
            app.amount.set("12.50")
            app.note.set("保留输入")
            app.add_button.invoke()
            assert error.call_count == 2
            assert len(app.table.get_children()) == 3
            assert app.day.get() == "2026-2-9"
            assert app.amount.get() == "12.50"
            assert app.note.get() == "保留输入"
            app.delete_button.invoke()
            assert info.call_count == 1
            app.table.selection_set(app.table.get_children()[0])
            summary_before = app.summary_text.get()
            app.delete_button.invoke()
            assert len(app.table.get_children()) == 3
            assert app.summary_text.get() == summary_before
            dialog_text = confirm.call_args.args[1]
            assert today.isoformat() in dialog_text
            assert "3.00" in dialog_text and "交通" in dialog_text
            confirm.return_value = True
            app.delete_button.invoke()
            assert len(app.table.get_children()) == 2
        app.close()
        root = tk.Tk()
        app = App(root, Ledger(path))
        root.update()
        assert len(app.table.get_children()) == 2
        assert app.budget_input.get() == "15.50"
        app.close()
    print("GUI check passed: add, monthly total, budget, invalid date, cancel/confirm delete, reload.")


if __name__ == "__main__":
    main()
