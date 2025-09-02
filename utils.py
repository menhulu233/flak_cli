```python
import tkinter as tk  # 导入 tkinter 模块，用于创建 GUI 界面
from tkinter import ttk, messagebox, filedialog  # 从 tkinter 导入 ttk（主题工具集）、messagebox（消息框）和 filedialog（文件对话框）
from datetime import datetime  # 导入 datetime 模块，用于处理日期和时间
import csv, requests  # 导入 csv 模块处理 CSV 文件，requests 模块用于 HTTP 请求
from collections import defaultdict  # 从 collections 导入 defaultdict，用于创建默认字典
import matplotlib  # 导入 matplotlib 库，用于绘图

matplotlib.use("TkAgg")  # 设置 matplotlib 使用 TkAgg 后端，与 tkinter 集成
from matplotlib.figure import Figure  # 从 matplotlib 导入 Figure 类，用于创建图表
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # 导入用于将 matplotlib 图表嵌入 tkinter 的类
import customtkinter as ctk  # 导入 customtkinter 库，用于创建现代化的 tkinter 界面

# 设置 customtkinter 的外观为 Material Design 风格（浅模式，使用蓝色主题以增加可爱感）
ctk.set_appearance_mode("Light")  # 设置浅模式，更可爱
ctk.set_default_color_theme("blue")  # 设置默认颜色主题为蓝色，更柔和可爱

# 用户可以选择的类别列表
CATEGORIES = ["Food", "Transport", "Groceries", "Rent", "Utilities",
              "Entertainment", "Shopping", "Health", "Education", "Other"]

# 支持的货币列表
CURRENCIES = ["USD", "CNY", "SGD", "EUR", "GBP", "JPY", "AUD", "CAD", "HKD", "KRW", 'INR', 'MYR', 'IDR']


def get_historical_exchange_rate(base_currency, target_currency, date_str):
    '''
    此函数用于通过 frankfurter API 获取历史汇率

    参数
    ----------
    base_currency : str
        用户实际支付的货币
    target_currency : str
        用户想要记录的货币
    date_str : str, 格式:
        '2025-08-31'

    返回
    -------
    float
        历史汇率，如果失败返回 None
    '''
    if base_currency == target_currency:  # 如果相同，返回1
        return 1.0

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%Y-%m-%d")
        url = f"https://api.frankfurter.app/{formatted_date}?from={base_currency}&to={target_currency}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 抛出HTTP错误
        data = response.json()
        return data['rates'].get(target_currency)
    except (ValueError, requests.exceptions.RequestException):
        return None


def get_exchange_rate(base_currency, target_currency):
    '''
    此函数用于获取当前汇率

    参数
    ----------
    base_currency : str
        用户实际支付的货币
    target_currency : str
        用户想要记录的货币

    返回
    -------
    float
        最新汇率，如果失败返回 None
    '''
    if base_currency == target_currency:
        return 1.0

    try:
        url = f"https://api.frankfurter.app/latest?from={base_currency}&to={target_currency}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['rates'].get(target_currency)
    except requests.exceptions.RequestException:
        return None


class Ledger:
    '''
    账本的核心功能类，管理记录、预算和汇率转换
    '''
    def __init__(self):
        '''
        初始化账本
        self.rows: 列表，每项是字典（date, base_amount, base_currency, amount, target_currency, category, note, exchange_rate）
        self.month_budget: 月预算，默认 0.0
        self.base_currency: 默认基础货币 "SGD"
        self.target_currency: 默认目标货币 "CNY"
        self.exchange_rate: 默认汇率
        self.target_currency_locked: 是否锁定目标货币，默认 False
        '''
        self.rows = []  # 存储所有记录的列表
        self.month_budget = 0.0  # 月预算

        # 默认货币
        self.base_currency = "SGD"  # 默认基础货币
        self.target_currency = "CNY"  # 默认目标货币
        self.exchange_rate = get_exchange_rate("SGD", "CNY") or 1.0  # 获取默认汇率或1.0

        # 信号是否锁定目标货币
        self.target_currency_locked = False  # 目标货币是否已锁定

    def add(self, amount, category, note, date=None, base_currency=None):
        '''
        添加记录，并计算汇率转换

        参数
        ----------
        amount : float
            使用货币的金额
        category : str
            支付类别
        note : str
            每笔支付的备注，可以为空
        date : str, 可选
            支付日期，默认 None，格式:'2025-08-31'
        base_currency : str, 可选
            支付使用的货币

        返回
        -------
        None
        '''
        # 使用输入的基础货币或默认基础货币
        base_curr = base_currency if base_currency else self.base_currency

        # 获取支付日期和历史汇率
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        exchange_rate = get_historical_exchange_rate(base_curr, self.target_currency, date_str)

        # 如果获取历史汇率失败，使用当前汇率
        if exchange_rate is None:
            exchange_rate = get_exchange_rate(base_curr, self.target_currency) or 1.0

        # 转换为目标货币的金额，四舍五入到两位小数
        converted = round(float(amount) * exchange_rate, 2)

        # 添加记录到 rows 列表
        self.rows.append({
            "date": date_str,
            "base_amount": round(float(amount), 2),
            "base_currency": base_curr,
            "amount": converted,
            "target_currency": self.target_currency,
            "category": category,
            "note": note.strip(),
            "exchange_rate": exchange_rate
        })

    def set_target_currency(self, currency):
        '''
        设置目标货币，只能设置一次

        参数
        ----------
        currency : str
            目标货币

        返回
        -------
        bool
            是否设置成功
        '''
        if not self.target_currency_locked:  # 如果目标货币未锁定
            # 设置目标货币并锁定
            self.target_currency = currency
            self.target_currency_locked = True
            # 更新现有记录的汇率和金额
            for row in self.rows:
                exchange_rate = get_historical_exchange_rate(
                    row["base_currency"], currency, row["date"]
                ) or get_exchange_rate(row["base_currency"], currency) or 1.0
                row["exchange_rate"] = exchange_rate
                row["amount"] = round(row["base_amount"] * exchange_rate, 2)
                row["target_currency"] = currency
            return True
        return False

    def remove_by_indices(self, indices):
        '''
        删除选定的行

        参数
        ----------
        indices : list
            要删除的行的索引列表
        '''
        for i in sorted(indices, reverse=True):  # 从后往前删除以避免索引变化
            del self.rows[i]

    def total_this_month(self):
        '''
        计算本月基于目标货币的总支出
        '''
        now = datetime.now().strftime("%Y-%m")  # 当前年月
        return round(sum(r["amount"] for r in self.rows if r["date"].startswith(now)), 2)  # 求和并四舍五入

    def summary_by_category(self):
        '''
        按类别汇总本月基于目标货币的支出
        '''
        now = datetime.now().strftime("%Y-%m")  # 当前年月
        sums = defaultdict(float)  # 默认字典，用于汇总
        for r in self.rows:
            if r["date"].startswith(now):
                sums[r["category"]] += r["amount"]
        return dict(sorted(sums.items(), key=lambda x: -x[1]))  # 按金额降序排序

    def daily_totals_this_month(self):
        '''
        计算本月基于目标货币的每日总支出
        '''
        now = datetime.now().strftime("%Y-%m")  # 当前年月
        sums = defaultdict(float)  # 默认字典，用于汇总
        for r in self.rows:
            if r["date"].startswith(now):
                sums[r["date"]] += r["amount"]
        return sorted(sums.items())  # 按日期排序返回

    def save_csv(self, path):
        '''
        将账本记录保存为 CSV 格式
        保存字段: "date", "base_amount", "base_currency", "amount", "target_currency", "category", "exchange_rate", "note"
        '''
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "date", "base_amount", "base_currency", "amount",
                "target_currency", "category", "exchange_rate", "note"
            ])
            writer.writeheader()  # 写入表头
            writer.writerows(self.rows)  # 写入所有行

    def load_csv(self, path):
        '''
        从 CSV 文件加载记录，必须与导出格式相同
        '''
        self.rows.clear()  # 清空现有记录
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):  # 读取每一行
                row["base_amount"] = float(row["base_amount"])  # 转换为浮点数
                row["amount"] = float(row["amount"])
                row["exchange_rate"] = float(row.get("exchange_rate", 1.0))
                self.rows.append(row)  # 添加到 rows

        # 如果导入记录包含目标货币信息，使用第一条记录的目标货币
        if self.rows:
            first_row = self.rows[0]
            if "target_currency" in first_row and first_row["target_currency"]:
                self.target_currency = first_row["target_currency"]
                self.target_currency_locked = True
            else:
                # 如果没有，使用默认目标货币并锁定
                self.target_currency = "CNY"
                self.target_currency_locked = True


class App(ctk.CTk):
    '''
    应用程序主类，继承 ctk.CTk，负责 UI 视图和控制器
    UI 布局概述：
    - 主窗口大小 1400x1000
    - 网格布局：列 0 权重 3（左侧表格），列 1 权重 1（右侧类别汇总）
    - 行 0 权重 1（主内容区域）
    - 左侧：记录表格（_build_table），包括标题、按钮栏、Treeview 和滚动条
    - 右侧：类别汇总（_build_category_summary），包括标题和标签
    - 底部：页脚（_build_footer），显示本月总计、预算和剩余
    '''
    def __init__(self):
        super().__init__()  # 调用父类初始化
        self.title("Multi-Currency Ledger 💰✨")  # 设置窗口标题，添加可爱表情
        self.geometry("1400x1000")  # 设置窗口大小
        self.ledger = Ledger()  # 创建 Ledger 实例，管理核心数据
        self.chart_win = None  # 图表窗口，初始 None
        self.target_disabled = False  # 目标货币设置是否禁用
        self.budget_disabled = False  # 预算设置是否禁用

        # 配置网格布局：左侧列权重更大，用于表格；行 0 扩展填充
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 构建 UI 组件
        self._build_table()  # 构建左侧记录表格
        self._build_category_summary()  # 构建右侧类别汇总
        self._build_footer()  # 构建底部页脚

        # 刷新总计和类别汇总
        self._refresh_totals()
        self._refresh_category_summary()

        # 设置 Treeview 样式，与浅模式兼容，使用蓝色主题，更可爱
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background="#f0f0f0",  # 浅背景
                        foreground="black",  # 黑前景
                        fieldbackground="#f0f0f0",  # 字段背景
                        rowheight=30,  # 行高
                        font=("Helvetica", 12, "italic"))  # 斜体字体，更可爱
        style.map("Treeview",
                  background=[('selected', '#81d4fa')],  # 浅蓝选中背景
                  foreground=[('selected', 'black')])  # 选中前景
        style.configure("Treeview.Heading",
                        background="#29b6f6",  # 蓝表头背景
                        foreground="white",  # 白表头前景
                        relief="flat",  # 无边框
                        font=("Helvetica", 13, "bold italic"))  # 斜体表头字体
        style.map("Treeview.Heading",
                  background=[('active', '#03a9f4')])  # 激活蓝

    def _show_currency_dialog(self):
        '''
        显示货币设置对话框（弹窗）
        '''
        dialog = ctk.CTkToplevel(self)  # 创建置顶窗口
        dialog.title("Currency Settings 💱")  # 添加可爱表情
        dialog.geometry("650x400")
        dialog.grab_set()  # 置顶并阻塞主窗口

        # 配置窗口网格
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        # 标题
        lbl_title = ctk.CTkLabel(dialog, text="Currency Settings ✨", font=ctk.CTkFont(size=20, weight="bold", slant="italic"))
        lbl_title.pack(pady=20)

        # 输入框架
        input_frm = ctk.CTkFrame(dialog, fg_color="transparent")
        input_frm.pack(fill="x", padx=30, pady=20)

        input_frm.grid_columnconfigure((0, 2), weight=1)
        input_frm.grid_columnconfigure((1, 3), weight=2)
        input_frm.grid_rowconfigure(0, weight=1)

        # 目标货币
        ctk.CTkLabel(input_frm, text="Target Currency (set once) 🌟", font=ctk.CTkFont(size=14, slant="italic")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        cmb_target = ctk.CTkComboBox(input_frm, values=CURRENCIES, width=180, font=ctk.CTkFont(size=13, slant="italic"))
        cmb_target.set(self.ledger.target_currency)
        cmb_target.grid(row=0, column=1, padx=15, pady=15, sticky="ew")

        # 汇率显示
        lbl_rate = ctk.CTkLabel(input_frm, text="Current Default Rate: ", font=ctk.CTkFont(size=14, slant="italic"))
        lbl_rate.grid(row=0, column=2, padx=15, pady=15, sticky="w")
        rate = get_exchange_rate(self.ledger.base_currency, self.ledger.target_currency)
        if rate:
            self.ledger.exchange_rate = rate
            lbl_rate.configure(text=f"1 {self.ledger.base_currency} = {rate:.4f} {self.ledger.target_currency} 💹")
        else:
            lbl_rate.configure(text="Could not fetch exchange rate 😔")

        # 按钮框架
        btn_frm = ctk.CTkFrame(input_frm, fg_color="transparent")
        btn_frm.grid(row=1, column=0, columnspan=4, pady=20, sticky="e")

        btn_target = ctk.CTkButton(btn_frm, text="Set Target Currency 🌈", command=lambda: self._set_target_currency_dialog(cmb_target, dialog), width=180, font=ctk.CTkFont(size=14, slant="italic"))
        btn_target.pack(side="left", padx=10)
        if self.target_disabled or self.ledger.target_currency_locked:
            btn_target.configure(state="disabled")

        btn_cancel = ctk.CTkButton(btn_frm, text="Cancel 😊", command=dialog.destroy, width=180, font=ctk.CTkFont(size=14, slant="italic"))
        btn_cancel.pack(side="left", padx=10)

    def _set_target_currency_dialog(self, cmb_target, dialog):
        currency = cmb_target.get()
        if self.ledger.set_target_currency(currency):
            messagebox.showinfo("Success 🎉", f"Target currency set to {currency} 🌟")
            self.target_disabled = True
            dialog.destroy()
            self._refresh_table()
            self._refresh_totals()
        else:
            messagebox.showerror("Error 😢", "Target currency can only be set once")

    def _show_add_expense_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Expense 💸")
        dialog.geometry("1000x450")
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        lbl_title = ctk.CTkLabel(dialog, text="Add Expense 🌈", font=ctk.CTkFont(size=20, weight="bold", slant="italic"))
        lbl_title.pack(pady=20)

        input_frm = ctk.CTkFrame(dialog, fg_color="transparent")
        input_frm.pack(fill="x", padx=30, pady=20)

        input_frm.grid_columnconfigure((0, 2, 4, 6), weight=1)
        input_frm.grid_columnconfigure((1, 3, 5, 7), weight=2)
        input_frm.grid_columnconfigure(8, weight=3)

        # 第一行
        ctk.CTkLabel(input_frm, text="Date (YYYY-MM-DD) 📅", font=ctk.CTkFont(size=14, slant="italic")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        ent_date = ctk.CTkEntry(input_frm, width=180, font=ctk.CTkFont(size=13, slant="italic"))
        ent_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ent_date.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(input_frm, text="Amount 💰", font=ctk.CTkFont(size=14, slant="italic")).grid(row=0, column=2, padx=15, pady=10, sticky="w")
        ent_amount = ctk.CTkEntry(input_frm, width=160, font=ctk.CTkFont(size=13, slant="italic"))
        ent_amount.grid(row=0, column=3, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(input_frm, text="Currency 🌍", font=ctk.CTkFont(size=14, slant="italic")).grid(row=0, column=4, padx=15, pady=10, sticky="w")
        cmb_currency = ctk.CTkComboBox(input_frm, values=CURRENCIES, width=140, font=ctk.CTkFont(size=13, slant="italic"))
        cmb_currency.set(self.ledger.base_currency)
        cmb_currency.grid(row=0, column=5, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(input_frm, text="Category 🛒", font=ctk.CTkFont(size=14, slant="italic")).grid(row=0, column=6, padx=15, pady=10, sticky="w")
        cmb_cat = ctk.CTkComboBox(input_frm, values=CATEGORIES, width=180, font=ctk.CTkFont(size=13, slant="italic"))
        cmb_cat.set(CATEGORIES[0])
        cmb_cat.grid(row=0, column=7, padx=15, pady=10, sticky="ew")

        # 第二行
        ctk.CTkLabel(input_frm, text="Note 📝", font=ctk.CTkFont(size=14, slant="italic")).grid(row=1, column=0, padx=15, pady=10, sticky="w")
        ent_note = ctk.CTkEntry(input_frm, width=800, font=ctk.CTkFont(size=13, slant="italic"))
        ent_note.grid(row=1, column=1, columnspan=7, padx=15, pady=10, sticky="ew")

        # 第三行
        ctk.CTkLabel(input_frm, text="Monthly Budget 🎯", font=ctk.CTkFont(size=14, slant="italic")).grid(row=2, column=0, padx=15, pady=15, sticky="w")
        ent_budget = ctk.CTkEntry(input_frm, width=160, font=ctk.CTkFont(size=13, slant="italic"))
        ent_budget.insert(0, str(self.ledger.month_budget))
        ent_budget.grid(row=2, column=1, padx=15, pady=15, sticky="ew")
        btn_budget = ctk.CTkButton(input_frm, text="Set Budget 🌟", command=lambda: self._set_budget_dialog(ent_budget.get()), width=160, font=ctk.CTkFont(size=14, slant="italic"))
        btn_budget.grid(row=2, column=2, padx=15, pady=15, sticky="ew")
        if self.budget_disabled:
            btn_budget.configure(state="disabled")

        btn_frm = ctk.CTkFrame(input_frm, fg_color="transparent")
        btn_frm.grid(row=2, column=6, columnspan=2, padx=15, pady=15, sticky="e")

        btn_add = ctk.CTkButton(btn_frm, text="Add 🎉", command=lambda: self._on_add_dialog(ent_date.get(), ent_amount.get(), cmb_currency.get(), cmb_cat.get(), ent_note.get(), ent_amount, ent_note, dialog), width=160, font=ctk.CTkFont(size=14, slant="italic"))
        btn_add.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(btn_frm, text="Cancel 😊", command=dialog.destroy, width=160, font=ctk.CTkFont(size=14, slant="italic"))
        btn_cancel.pack(side="left", padx=10)

    def _on_add_dialog(self, date, amt, currency, cat, note, ent_amount, ent_note, dialog):
        try:
            amount = float(amt)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid amount 😢", "Please enter a positive number.")
            return

        try:
            input_date = datetime.strptime(date.strip(), "%Y-%m-%d")
            if input_date.date() > datetime.now().date():
                messagebox.showerror("Invalid Date 📅", "Date cannot be in the future. Please enter a date today or earlier.")
                return
        except ValueError:
            messagebox.showerror("Invalid Date 📅", "Please use the format: YYYY-MM-DD")
            return

        self.ledger.add(amount, cat, note, date=date, base_currency=currency)
        self.target_disabled = True
        self.budget_disabled = True
        ent_amount.delete(0, tk.END)
        ent_note.delete(0, tk.END)
        self._refresh_table()
        self._refresh_totals()
        self._maybe_budget_alert()
        self._refresh_category_summary()
        dialog.destroy()

    def _set_budget_dialog(self, budget_str):
        try:
            b = float(budget_str)
            if b < 0:
                raise ValueError
            self.ledger.month_budget = b
            self.budget_disabled = True
            self._refresh_totals()
            self._maybe_budget_alert()
            self._refresh_category_summary()
        except ValueError:
            messagebox.showerror("Invalid budget 😢", "Enter a non-negative number.")

    def _build_table(self):
        frm = ctk.CTkFrame(self, corner_radius=20, border_width=1)  # 更大圆角，更可爱
        frm.grid(row=0, column=0, sticky="nsew")
        frm.grid_rowconfigure(2, weight=1)
        frm.grid_columnconfigure(0, weight=1)

        lbl_title = ctk.CTkLabel(frm, text="Records 📋✨", font=ctk.CTkFont(size=20, weight="bold", slant="italic"))
        lbl_title.grid(row=0, column=0, columnspan=2, pady=12, sticky="ew")

        btns = ctk.CTkFrame(frm, fg_color="transparent")
        btns.grid(row=1, column=0, columnspan=2, pady=16, sticky="ew")

        ctk.CTkButton(btns, text="Delete Selected 🗑️", command=self._delete_selected, width=160, font=ctk.CTkFont(size=14, slant="italic")).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Import CSV 📥", command=self._import_csv, width=160, font=ctk.CTkFont(size=14, slant="italic")).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Export CSV 📤", command=self._export_csv, width=160, font=ctk.CTkFont(size=14, slant="italic")).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Monthly Summary 📊", command=self._show_summary, width=160, font=ctk.CTkFont(size=14, slant="italic")).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Charts 📈🌈", command=self._open_charts, width=160, font=ctk.CTkFont(size=14, slant="italic")).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Currency Settings 💱", command=self._show_currency_dialog, width=160, font=ctk.CTkFont(size=14, slant="italic")).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Add Expense 💸", command=self._show_add_expense_dialog, width=160, font=ctk.CTkFont(size=14, slant="italic")).pack(side="left", padx=12)

        cols = ("date", "base_amount", "base_currency", "exchange_rate", "target_amount", "target_currency", "category",
                "budget_left", "spent_so_far", "note")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=22)

        self.tree.heading("date", text="Date 📅")
        self.tree.column("date", width=140, anchor="w")

        self.tree.heading("base_amount", text="Amount 💰")
        self.tree.column("base_amount", width=120, anchor="e")

        self.tree.heading("base_currency", text="Currency 🌍")
        self.tree.column("base_currency", width=100, anchor="center")

        self.tree.heading("exchange_rate", text="Exchange Rate 💹")
        self.tree.column("exchange_rate", width=140, anchor="e")

        self.tree.heading("target_amount", text="Converted Amount 🔄")
        self.tree.column("target_amount", width=160, anchor="e")

        self.tree.heading("target_currency", text="Target Currency 🎯")
        self.tree.column("target_currency", width=150, anchor="center")

        self.tree.heading("category", text="Category 🛒")
        self.tree.column("category", width=140, anchor="w")

        self.tree.heading("budget_left", text="Budget Left 🌟")
        self.tree.column("budget_left", width=120, anchor="w")

        self.tree.heading("spent_so_far", text="Spent So Far 📈")
        self.tree.column("spent_so_far", width=140, anchor="w")

        self.tree.heading("note", text="Note 📝")
        self.tree.column("note", width=400, anchor="w")

        self.tree.grid(row=2, column=0, sticky="nsew")

        scroll = ctk.CTkScrollbar(frm, orientation="vertical", command=self.tree.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

    def _build_category_summary(self):
        frm = ctk.CTkFrame(self, corner_radius=20, border_width=1)
        frm.grid(row=0, column=1, sticky="nsew")
        frm.grid_rowconfigure(1, weight=1)

        lbl_title = ctk.CTkLabel(frm, text="Category Summary (This Month) 📊✨", font=ctk.CTkFont(size=20, weight="bold", slant="italic"))
        lbl_title.pack(pady=12)

        self.lbl_summary = ctk.CTkLabel(frm, text="No records yet. 😊", justify="left", anchor="w", font=ctk.CTkFont(size=14, slant="italic"))
        self.lbl_summary.pack(fill="both", expand=True, padx=24, pady=12)

    def _build_footer(self):
        bar = ctk.CTkFrame(self, corner_radius=20, border_width=1)
        bar.grid(row=1, column=0, columnspan=2, padx=24, pady=16, sticky="ew")

        self.lbl_total = ctk.CTkLabel(bar, text="This month: 0.00 💸", font=ctk.CTkFont(size=16, slant="italic"))
        self.lbl_total.pack(side="left", padx=24)

        self.lbl_budget = ctk.CTkLabel(bar, text="Budget: 0.00  |  Remaining: 0.00 🌟", font=ctk.CTkFont(size=16, slant="italic"))
        self.lbl_budget.pack(side="right", padx=24)

    def _refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        sorted_rows = sorted(self.ledger.rows, key=lambda x: x["date"])

        running_total = 0.0
        current_month = datetime.now().strftime("%Y-%m")

        for r in sorted_rows:
            if r["date"].startswith(current_month):
                running_total += r["amount"]
            remaining = self.ledger.month_budget - running_total

            self.tree.insert("", "end", values=(
                r["date"],
                f"{r['base_amount']:.2f}",
                r["base_currency"],
                f"{r['exchange_rate']:.4f}",
                f"{r['amount']:.2f}",
                r["target_currency"],
                r["category"],
                f"{remaining:.2f}",
                f"{running_total:.2f}",
                r["note"]
            ))

    def _delete_selected(self):
        items = self.tree.selection()
        if not items:
            return
        idx = [self.tree.index(i) for i in items]
        self.ledger.remove_by_indices(idx)
        for i in items:
            self.tree.delete(i)
        self._refresh_totals()
        self._refresh_category_summary()

    def _refresh_totals(self):
        total = self.ledger.total_this_month()
        self.lbl_total.configure(text=f"This month: {self.ledger.target_currency} {total:.2f} 💸")
        b = self.ledger.month_budget
        rem = b - total
        self.lbl_budget.configure(text=f"Budget: {self.ledger.target_currency} {b:.2f}  |  Remaining: {rem:.2f} 🌟")
        color = "green" if rem >= b * 0.3 else ("orange" if rem >= 0 else "red")
        self.lbl_budget.configure(text_color=color)

    def _refresh_category_summary(self):
        sums = self.ledger.summary_by_category()
        if not sums:
            self.lbl_summary.configure(text="No records this month. 😊")
            return
        text = "\n".join(f"{k:15s} : {self.ledger.target_currency} {v:.2f} 💰" for k, v in sums.items())
        self.lbl_summary.configure(text=text)

    def _maybe_budget_alert(self):
        b = self.ledger.month_budget
        if b <= 0:
            return
        total = self.ledger.total_this_month()
        if total > b:
            messagebox.showwarning("Budget exceeded 😱", f"You exceeded the monthly budget by {total - b:.2f} {self.ledger.target_currency}.")
        elif total >= 0.9 * b:
            messagebox.showinfo("Near budget ⚠️", "You've reached 90% of your monthly budget. 😊")

    def _show_summary(self):
        sums = self.ledger.summary_by_category()
        if not sums:
            messagebox.showinfo("Summary 📊", "No records this month yet. 😊")
            return
        text = "\n".join(f"{k:15s} : {self.ledger.target_currency} {v:.2f} 💰" for k, v in sums.items())
        total = self.ledger.total_this_month()
        messagebox.showinfo("Monthly Summary 🎉", f"{text}\n\nTotal this month: {self.ledger.target_currency} {total:.2f} 🌟")

    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Export to CSV 📤")
        if not path:
            return
        try:
            self.ledger.save_csv(path)
            messagebox.showinfo("Saved 🎉", f"Exported to\n{path} 😊")
        except Exception as e:
            messagebox.showerror("Save failed 😢", str(e))

    def _import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")], title="Import CSV 📥")
        if not path:
            return
        try:
            self.ledger.load_csv(path)
            self._refresh_table()
            self._refresh_totals()
            if self.ledger.target_currency_locked:
                self.target_disabled = True
            self.budget_disabled = True
            self._refresh_category_summary()
            messagebox.showinfo("Import Successful 🎉", f"Loaded {len(self.ledger.rows)} records 😊")
        except Exception as e:
            messagebox.showerror("Load failed 😢", str(e))

    def _open_charts(self):
        if self.chart_win and self.chart_win.winfo_exists():
            self.chart_win.focus()
            return

        self.chart_win = ctk.CTkToplevel(self)
        win = self.chart_win
        win.title("Charts - This Month 📈✨")
        win.geometry("900x650")
        win.grab_set()
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        def _on_close():
            try:
                win.destroy()
            finally:
                self.chart_win = None

        win.protocol("WM_DELETE_WINDOW", _on_close)

        lbl_title = ctk.CTkLabel(win, text="Monthly Spending Charts 🌈", font=ctk.CTkFont(size=20, weight="bold", slant="italic"))
        lbl_title.pack(pady=15)

        sums = self.ledger.summary_by_category()
        if not sums:
            messagebox.showinfo("Charts 📊", "No records this month yet. 😊")
            _on_close()
            return
        labels = list(sums.keys())
        values = list(sums.values())

        tabview = ctk.CTkTabview(win, fg_color="transparent", segmented_button_selected_color="#03a9f4", width=800)
        tabview.pack(pady=15, padx=50, fill="x")

        # 饼图
        tabview.add("Pie by Category 🥧")
        frm_pie = ctk.CTkFrame(tabview.tab("Pie by Category"), fg_color="transparent")
        frm_pie.grid(row=0, column=0, sticky="nsew")
        frm_pie.grid_columnconfigure(0, weight=1)
        frm_pie.grid_rowconfigure(0, weight=1)
        fig1 = Figure(figsize=(6.5, 4.5), dpi=100, facecolor="#f0f0f0")
        ax1 = fig1.add_subplot(111, facecolor="#f0f0f0")
        ax1.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, counterclock=False, textprops={'color': 'black', 'fontsize': 12})
        ax1.axis("equal")
        fig1.tight_layout()
        c1 = FigureCanvasTkAgg(fig1, master=frm_pie)
        c1.draw()
        c1.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)

        # 条形图
        tabview.add("Bar by Category 📊")
        frm_bar = ctk.CTkFrame(tabview.tab("Bar by Category"), fg_color="transparent")
        frm_bar.grid(row=0, column=0, sticky="nsew")
        frm_bar.grid_columnconfigure(0, weight=1)
        frm_bar.grid_rowconfigure(0, weight=1)
        fig2 = Figure(figsize=(6.5, 4.5), dpi=100, facecolor="#f0f0f0")
        ax2 = fig2.add_subplot(111, facecolor="#f0f0f0")
        ax2.bar(labels, values, color="#29b6f6")
        ax2.set_ylabel("Amount", color="black", fontsize=12)
        ax2.set_xlabel("Category", color="black", fontsize=12)
        ax2.set_title("Spending by Category (This Month)", color="black", fontsize=14)
        ax2.tick_params(axis='x', rotation=25, colors="black")
        ax2.tick_params(axis='y', colors="black")
        fig2.tight_layout()
        c2 = FigureCanvasTkAgg(fig2, master=frm_bar)
        c2.draw()
        c2.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)

        # 日趋势线
        tabview.add("Daily Trend 📈")
        frm_line = ctk.CTkFrame(tabview.tab("Daily Trend"), fg_color="transparent")
        frm_line.grid(row=0, column=0, sticky="nsew")
        frm_line.grid_columnconfigure(0, weight=1)
        frm_line.grid_rowconfigure(0, weight=1)
        fig3 = Figure(figsize=(6.5, 4.5), dpi=100, facecolor="#f0f0f0")
        ax3 = fig3.add_subplot(111, facecolor="#f0f0f0")
        daily = self.ledger.daily_totals_this_month()
        if daily:
            x = [d for d, _ in daily]
            y = [v for _, v in daily]
            ax3.plot(x, y, marker="o", color="#29b6f6", linewidth=2)
            ax3.set_xlabel("Date", color="black", fontsize=12)
            ax3.set_ylabel("Amount", color="black", fontsize=12)
            ax3.set_title("Daily Total (This Month)", color="black", fontsize=14)
            for lab in ax3.get_xticklabels():
                lab.set_rotation(35)
                lab.set_ha("right")
                lab.set_color("black")
            ax3.tick_params(axis='y', colors="black")
        else:
            ax3.text(0.5, 0.5, "No data 😔", ha="center", va="center", color="black", fontsize=14)
        fig3.tight_layout()
        c3 = FigureCanvasTkAgg(fig3, master=frm_line)
        c3.draw()
        c3.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)

        tabview.set("Pie by Category")


if __name__ == "__main__":
    App().mainloop()
```
