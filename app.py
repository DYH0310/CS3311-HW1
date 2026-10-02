"""中文桌面界面，运行 python app.py 启动。"""

import argparse
from datetime import date
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from ledger import CATEGORIES, DEFAULT_DB, Ledger, money


class App:
    def __init__(self, root, ledger):
        self.root, self.ledger = root, ledger
        root.title("校园消费记账")
        root.geometry("1000x650")
        root.minsize(800, 580)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TLabel", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=5)
        style.configure("Treeview", font=("Microsoft YaHei UI", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"))
        panel = ttk.Frame(root, padding=20)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="校园消费记账", font=("Microsoft YaHei UI", 22, "bold")).pack(anchor="w")
        ttk.Label(panel, text="记下日常开销，看看生活费花在哪里。", foreground="#52606d").pack(anchor="w", pady=(5, 15))

        form = ttk.LabelFrame(panel, text="记一笔", padding=12)
        form.pack(fill="x")
        self.day = tk.StringVar(value=date.today().isoformat())
        self.amount = tk.StringVar()
        self.category = tk.StringVar(value=CATEGORIES[0])
        self.note = tk.StringVar()
        for column, (label, variable, width) in enumerate([
            ("日期 YYYY-MM-DD", self.day, 15), ("金额（元）", self.amount, 12),
            ("类别", self.category, 9), ("备注", self.note, 25),
        ]):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w")
            if variable is self.category:
                field = ttk.Combobox(form, textvariable=variable, values=CATEGORIES, state="readonly", width=width)
            else:
                field = ttk.Entry(form, textvariable=variable, width=width)
            field.grid(row=1, column=column, padx=(0, 12), pady=6, sticky="ew")
        form.columnconfigure(3, weight=1)
        self.add_button = ttk.Button(form, text="添加记录", command=self.add)
        self.add_button.grid(row=1, column=4)

        budget_bar = ttk.Frame(panel)
        budget_bar.pack(fill="x", pady=12)
        ttk.Label(budget_bar, text="每月预算（元）").pack(side="left")
        self.budget_input = tk.StringVar()
        ttk.Entry(budget_bar, textvariable=self.budget_input, width=12).pack(side="left", padx=8)
        self.budget_button = ttk.Button(budget_bar, text="保存预算", command=self.save_budget)
        self.budget_button.pack(side="left")
        self.delete_button = ttk.Button(budget_bar, text="删除选中记录", command=self.delete)
        self.delete_button.pack(side="right")

        table_frame = ttk.Frame(panel)
        table_frame.pack(fill="both", expand=True)
        self.table = ttk.Treeview(table_frame, columns=("day", "amount", "category", "note"), show="headings", selectmode="browse")
        for key, label, width in [("day", "日期", 140), ("amount", "金额（元）", 120), ("category", "类别", 100), ("note", "备注", 400)]:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, anchor="e" if key == "amount" else "w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.summary_text = tk.StringVar()
        ttk.Label(panel, textvariable=self.summary_text, wraplength=920).pack(anchor="w", pady=(12, 5))
        self.reminder = tk.StringVar()
        self.reminder_label = ttk.Label(panel, textvariable=self.reminder)
        self.reminder_label.pack(anchor="w")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()

    def run_action(self, action):
        try:
            action()
            self.refresh()
        except (ValueError, sqlite3.Error, OSError) as error:
            messagebox.showerror("未能保存", str(error), parent=self.root)

    def add(self):
        def action():
            self.ledger.add(self.day.get(), self.amount.get(), self.category.get(), self.note.get())
            self.amount.set("")
            self.note.set("")
        self.run_action(action)

    def delete(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("请选择记录", "请先在列表中选中要删除的记录。", parent=self.root)
            return
        day, amount, category, _ = self.table.item(selected[0], "values")
        if not messagebox.askyesno(
            "确认删除", f"删除这笔消费吗？\n日期：{day}\n金额：{amount} 元\n类别：{category}", parent=self.root
        ):
            return
        self.run_action(lambda: self.ledger.delete(int(selected[0])))

    def save_budget(self):
        self.run_action(lambda: self.ledger.set_budget(self.budget_input.get()))

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for record_id, day, cents, category, note in self.ledger.records():
            self.table.insert("", "end", iid=str(record_id), values=(day, money(cents), category, note))
        month = date.today().strftime("%Y-%m")
        total, categories = self.ledger.summary(month)
        self.summary_text.set(f"{month} 本月支出：{money(total)} 元\n" + "　".join(f"{name} {money(value)}" for name, value in categories.items()))
        budget = self.ledger.budget()
        self.budget_input.set(money(budget) if budget is not None else "")
        if budget is None:
            self.reminder.set("尚未设置预算。")
        elif total >= budget:
            self.reminder.set(f"预算提醒：本月支出已达到预算 {money(budget)} 元。")
        else:
            self.reminder.set(f"本月预算还剩 {money(budget - total)} 元。")
        self.reminder_label.configure(foreground="#b42318" if budget is not None and total >= budget else "#205d46")

    def close(self):
        self.ledger.close()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="校园消费记账桌面程序")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="数据库文件路径")
    args = parser.parse_args()
    root = tk.Tk()
    try:
        ledger = Ledger(args.db)
        App(root, ledger)
    except (sqlite3.Error, OSError) as error:
        messagebox.showerror("无法打开记账数据", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
