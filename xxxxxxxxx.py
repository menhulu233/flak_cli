import tkinter as tk  # 导入 tkinter 模块，用于创建 GUI 界面
from tkinter import ttk, messagebox, filedialog  # 从 tkinter 导入 ttk（主题工具集）、messagebox（消息框）和 filedialog（文件对话框）
from datetime import datetime  # 导入 datetime 模块，用于处理日期和时间
import csv, requests  # 导入 csv 模块处理 CSV 文件，requests 模块用于 HTTP 请求
from collections import defaultdict  # 从 collections 导入 defaultdict，用于创建默认字典
import matplotlib  # 导入 matplotlib 库，用于绘图

matplotlib.use("TkAgg")  # 设置 matplotlib 使用 TkAgg 后端，与 tkinter 集成
from matplotlib.figure import Figure  # 从 matplotlib 导入 Figure 类，用于创建图表
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk  # 导入用于将 matplotlib 图表嵌入 tkinter 的类
import customtkinter as ctk  # 导入 customtkinter 库，用于创建现代化的 tkinter 界面

# 设置 customtkinter 的外观为 Material Design 风格（暗模式，使用绿色主题以增加活力）
ctk.set_appearance_mode("Dark")  # 设置暗模式
ctk.set_default_color_theme("green")  # 设置默认颜色主题为绿色

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
    if base_currency != target_currency:  # 如果目标货币不等于基础货币
        date_formats = ["%Y-%m-%d", "%Y-%m", "%Y"]  # 支持的日期格式
        date_obj = None

        for fmt in date_formats:  # 尝试解析日期
            try:
                date_obj = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

        if not date_obj:  # 如果日期解析失败，返回 None
            return None

        # 将日期格式化为 API 所需的格式
        formatted_date = date_obj.strftime("%Y-%m-%d")

        try:
            # 构造 API URL 并发送 GET 请求
            url = f"https://api.frankfurter.app/{formatted_date}?from={base_currency}&to={target_currency}"
            response = requests.get(url, timeout=10)
            data = response.json()

            if target_currency in data['rates']:  # 如果响应中包含目标货币的汇率，返回它
                return data['rates'][target_currency]
            else:
                return None
        except requests.exceptions.RequestException as e:  # 处理请求异常
            print(f"Error fetching historical rates: {e}")
            return None
    else:  # 如果目标货币等于基础货币，汇率为 1
        return 1


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
    try:
        # 构造 API URL 并发送 GET 请求
        url = f"https://api.frankfurter.app/latest?from={base_currency}&to={target_currency}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if target_currency in data['rates']:  # 如果响应中包含目标货币的汇率，返回它
            return data['rates'][target_currency]
        else:
            return None
    except requests.exceptions.RequestException as e:  # 处理请求异常
        print(f"Error fetching current rates: {e}")
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
        self.exchange_rate = get_exchange_rate("SGD", "CNY")  # 获取默认汇率

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
            exchange_rate = get_exchange_rate(base_curr, self.target_currency)
            if exchange_rate is None:
                # 最终失败，使用默认汇率 1.0
                exchange_rate = self.exchange_rate if base_curr == self.base_currency else 1.0

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
                )
                if exchange_rate:
                    row["exchange_rate"] = exchange_rate
                    row["amount"] = round(row["base_amount"] * exchange_rate, 2)
                    row["target_currency"] = currency
            return True
        else:
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
        self.title("Multi-Currency Ledger with Historical Exchange Rates")  # 设置窗口标题
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

        # 设置 Treeview 样式，与暗模式兼容，使用绿色主题
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background="#2a2d2e",  # 背景色
                        foreground="white",  # 前景色
                        fieldbackground="#2a2d2e",  # 字段背景
                        rowheight=30,  # 行高
                        font=("Helvetica", 12))  # 字体
        style.map("Treeview",
                  background=[('selected', '#1b5e20')],  # 选中背景色
                  foreground=[('selected', 'white')])  # 选中前景色
        style.configure("Treeview.Heading",
                        background="#388e3c",  # 表头背景
                        foreground="white",  # 表头前景
                        relief="flat",  # 无边框
                        font=("Helvetica", 13, "bold"))  # 表头字体
        style.map("Treeview.Heading",
                  background=[('active', '#2e7d32')])  # 激活状态背景

    def _show_currency_dialog(self):
        '''
        显示货币设置对话框（弹窗）
        - 窗口大小 700x400（略增宽度和高度，容纳控件并提升美观）
        - grab_set() 置顶阻塞主窗口
        - 布局：标题、输入框架（两行网格：第一行目标货币选择+汇率显示，第二行按钮）
        - 优化：调整网格列权重，增加间距，确保“设置目标货币”和“取消”按钮并排，整体布局更清晰
        '''
        dialog = ctk.CTkToplevel(self)  # 创建置顶窗口
        dialog.title("Currency Settings")  # 设置标题
        dialog.geometry("650x400")  # 调整窗口大小，增加宽度和高度以容纳控件
        dialog.grab_set()  # 置顶并阻塞主窗口

        # 配置窗口网格，行和列可扩展
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        # 标题
        lbl_title = ctk.CTkLabel(dialog, text="Currency Settings", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_title.pack(pady=20)  # 增加垂直间距，改善视觉层次

        # 输入框架
        input_frm = ctk.CTkFrame(dialog, fg_color="transparent")  # 透明背景
        input_frm.pack(fill="x", padx=30, pady=20)  # 增加水平间距（30），填充 x 方向

        # 配置输入框架网格，分配列权重以平衡布局
        input_frm.grid_columnconfigure((0, 2), weight=1)  # 标签列
        input_frm.grid_columnconfigure((1, 3), weight=2)  # 输入框/显示列
        input_frm.grid_rowconfigure(0, weight=1)  # 第一行扩展

        # 第一行：目标货币选择和汇率显示
        # 目标货币标签和组合框
        ctk.CTkLabel(input_frm, text="Target Currency (set once)", font=ctk.CTkFont(size=14)).grid(row=0, column=0,
                                                                                                   padx=15, pady=15,
                                                                                                   sticky="w")
        cmb_target = ctk.CTkComboBox(input_frm, values=CURRENCIES, width=180, font=ctk.CTkFont(size=13))  # 增加宽度，改善体验
        cmb_target.set(self.ledger.target_currency)  # 设置默认值
        cmb_target.grid(row=0, column=1, padx=15, pady=15, sticky="ew")

        # 汇率显示标签
        lbl_rate = ctk.CTkLabel(input_frm, text="Current Default Rate: ", font=ctk.CTkFont(size=14))
        lbl_rate.grid(row=0, column=2, padx=15, pady=15, sticky="w")
        rate = get_exchange_rate(self.ledger.base_currency, self.ledger.target_currency)
        if rate:
            self.ledger.exchange_rate = rate
            lbl_rate.configure(text=f"1 {self.ledger.base_currency} = {rate:.4f} {self.ledger.target_currency}")
        else:
            lbl_rate.configure(text="Could not fetch exchange rate")

        # 第二行：按钮框架
        btn_frm = ctk.CTkFrame(input_frm, fg_color="transparent")  # 按钮专用框架
        btn_frm.grid(row=1, column=0, columnspan=4, pady=20, sticky="e")  # 放置在右下，跨 4 列

        # 设置目标货币按钮
        btn_target = ctk.CTkButton(btn_frm, text="Set Target Currency",
                                   command=lambda: self._set_target_currency_dialog(cmb_target, dialog), width=180,
                                   font=ctk.CTkFont(size=14))  # 减小宽度
        btn_target.pack(side="left", padx=10)  # 左右间距 10，与取消按钮并排
        if self.target_disabled or self.ledger.target_currency_locked:
            btn_target.configure(state="disabled")

        # 取消按钮
        btn_cancel = ctk.CTkButton(btn_frm, text="Cancel", command=dialog.destroy, width=180,
                                   font=ctk.CTkFont(size=14))  # 统一宽度
        btn_cancel.pack(side="left", padx=10)  # 并排显示
    def _set_target_currency_dialog(self, cmb_target, dialog):
        '''
        在对话框中设置目标货币，并处理成功/失败
        - 如果成功，显示消息，锁定，关闭对话框，刷新表格和总计
        '''
        currency = cmb_target.get()  # 获取选中的货币
        if self.ledger.set_target_currency(currency):  # 调用设置方法
            messagebox.showinfo("Success", f"Target currency set to {currency}")  # 成功消息
            self.target_disabled = True  # 禁用设置
            dialog.destroy()  # 关闭对话框
            self._refresh_table()  # 刷新表格
            self._refresh_totals()  # 刷新总计
        else:
            messagebox.showerror("Error", "Target currency can only be set once")  # 错误消息

    def _show_add_expense_dialog(self):
        '''
        显示添加支出对话框（弹窗）
        - 窗口大小 1000x450（缩小宽度，增加高度以容纳控件）
        - grab_set() 置顶阻塞主窗口
        - 布局：标题、输入框架（三行网格：第一行日期/金额/货币/类别，第二行备注，第三行预算/按钮）
        - 优化：调整网格列权重，增加间距，确保“取消”按钮可见，备注字段跨列合理
        '''
        dialog = ctk.CTkToplevel(self)  # 创建置顶窗口
        dialog.title("Add Expense")  # 设置标题
        dialog.geometry("1500x450")  # 调整窗口大小，宽度减小避免拥挤，高度增加容纳控件
        dialog.grab_set()  # 置顶并阻塞主窗口

        # 配置窗口网格，确保扩展合理
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        lbl_title = ctk.CTkLabel(dialog, text="Add Expense", font=ctk.CTkFont(size=20, weight="bold"))  # 标题
        lbl_title.pack(pady=20)  # 增加垂直间距，改善视觉层次

        input_frm = ctk.CTkFrame(dialog, fg_color="transparent")  # 输入框架，透明背景
        input_frm.pack(fill="x", padx=30, pady=20)  # 增加水平间距（30）并填充 x 方向

        # 配置输入框架网格，分配列权重以平衡布局
        input_frm.grid_columnconfigure((0, 2, 4, 6), weight=1)  # 标签列
        input_frm.grid_columnconfigure((1, 3, 5, 7), weight=2)  # 输入框列
        input_frm.grid_columnconfigure(8, weight=3)  # 按钮列，留更多空间

        # 第一行：日期、金额、货币、类别输入
        # 日期输入
        ctk.CTkLabel(input_frm, text="Date (YYYY-MM-DD)", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=15,
                                                                                          pady=10, sticky="w")
        ent_date = ctk.CTkEntry(input_frm, width=180, font=ctk.CTkFont(size=13))  # 增加宽度，改善输入体验
        ent_date.insert(0, datetime.now().strftime("%Y-%m-%d"))  # 默认当前日期
        ent_date.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        # 金额输入
        ctk.CTkLabel(input_frm, text="Amount", font=ctk.CTkFont(size=14)).grid(row=0, column=2, padx=15, pady=10,
                                                                               sticky="w")
        ent_amount = ctk.CTkEntry(input_frm, width=160, font=ctk.CTkFont(size=13))
        ent_amount.grid(row=0, column=3, padx=15, pady=10, sticky="ew")

        # 货币选择
        ctk.CTkLabel(input_frm, text="Currency", font=ctk.CTkFont(size=14)).grid(row=0, column=4, padx=15, pady=10,
                                                                                 sticky="w")
        cmb_currency = ctk.CTkComboBox(input_frm, values=CURRENCIES, width=140, font=ctk.CTkFont(size=13))
        cmb_currency.set(self.ledger.base_currency)  # 默认基础货币
        cmb_currency.grid(row=0, column=5, padx=15, pady=10, sticky="ew")

        # 类别选择
        ctk.CTkLabel(input_frm, text="Category", font=ctk.CTkFont(size=14)).grid(row=0, column=6, padx=15, pady=10,
                                                                                 sticky="w")
        cmb_cat = ctk.CTkComboBox(input_frm, values=CATEGORIES, width=180, font=ctk.CTkFont(size=13))
        cmb_cat.set(CATEGORIES[0])  # 默认第一个类别
        cmb_cat.grid(row=0, column=7, padx=15, pady=10, sticky="ew")

        # 第二行：备注输入
        ctk.CTkLabel(input_frm, text="Note", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=15, pady=10,
                                                                             sticky="w")
        ent_note = ctk.CTkEntry(input_frm, width=800, font=ctk.CTkFont(size=13))  # 减少宽度（900→800），避免挤压按钮
        ent_note.grid(row=1, column=1, columnspan=7, padx=15, pady=10, sticky="ew")  # 跨 7 列，留空间给按钮

        # 第三行：月预算和按钮
        ctk.CTkLabel(input_frm, text="Monthly Budget", font=ctk.CTkFont(size=14)).grid(row=2, column=0, padx=15,
                                                                                       pady=15, sticky="w")
        ent_budget = ctk.CTkEntry(input_frm, width=160, font=ctk.CTkFont(size=13))
        ent_budget.insert(0, str(self.ledger.month_budget))  # 默认当前预算
        ent_budget.grid(row=2, column=1, padx=15, pady=15, sticky="ew")
        btn_budget = ctk.CTkButton(input_frm, text="Set Budget",
                                   command=lambda: self._set_budget_dialog(ent_budget.get()), width=160,
                                   font=ctk.CTkFont(size=14))
        btn_budget.grid(row=2, column=2, padx=15, pady=15, sticky="ew")
        if self.budget_disabled:  # 如果已禁用，禁用按钮
            btn_budget.configure(state="disabled")

        # 按钮框架，确保“添加”和“取消”按钮在同一行且对齐
        btn_frm = ctk.CTkFrame(input_frm, fg_color="transparent")
        btn_frm.grid(row=2, column=6, columnspan=2, padx=15, pady=15, sticky="e")

        btn_add = ctk.CTkButton(btn_frm, text="Add",
                                command=lambda: self._on_add_dialog(ent_date.get(), ent_amount.get(),
                                                                    cmb_currency.get(), cmb_cat.get(), ent_note.get(),
                                                                    ent_amount, ent_note, dialog), width=160,
                                font=ctk.CTkFont(size=14))
        btn_add.pack(side="left", padx=10)  # 左右间距 10

        btn_cancel = ctk.CTkButton(btn_frm, text="Cancel", command=dialog.destroy, width=160, font=ctk.CTkFont(size=14))
        btn_cancel.pack(side="left", padx=10)  # 确保“取消”按钮与“添加”并排显示
    def _on_add_dialog(self, date, amt, currency, cat, note, ent_amount, ent_note, dialog):
        '''
        在对话框中处理添加支出
        - 验证金额和日期
        - 添加记录
        - 清空输入，刷新 UI，检查预算警报，关闭对话框
        '''
        try:
            amount = float(amt)  # 转换为浮点数
            if amount <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid amount", "Please enter a positive number.")  # 无效金额错误
            return

        try:
            input_date = datetime.strptime(date.strip(), "%Y-%m-%d")  # 解析日期
            if input_date.date() > datetime.now().date():
                messagebox.showerror("Invalid Date", "Date cannot be in the future. Please enter a date today or earlier.")  # 未来日期错误
                return
        except ValueError:
            messagebox.showerror("Invalid Date", "Please use the format: YYYY-MM-DD")  # 格式错误
            return

        self.ledger.add(amount, cat, note, date=date, base_currency=currency)  # 添加记录
        self.target_disabled = True  # 禁用目标货币设置
        self.budget_disabled = True  # 禁用预算设置
        ent_amount.delete(0, tk.END)  # 清空金额输入
        ent_note.delete(0, tk.END)  # 清空备注输入
        self._refresh_table()  # 刷新表格
        self._refresh_totals()  # 刷新总计
        self._maybe_budget_alert()  # 检查预算警报
        self._refresh_category_summary()  # 刷新类别汇总
        dialog.destroy()  # 关闭对话框

    def _set_budget_dialog(self, budget_str):
        '''
        在对话框中设置月预算
        - 验证并设置预算，禁用按钮，刷新 UI
        '''
        try:
            b = float(budget_str)  # 转换为浮点数
            if b < 0: raise ValueError
            self.ledger.month_budget = b  # 设置预算
            self.budget_disabled = True  # 禁用设置
            self._refresh_totals()  # 刷新总计
            self._maybe_budget_alert()  # 检查警报
            self._refresh_category_summary()  # 刷新汇总
        except Exception:
            messagebox.showerror("Invalid budget", "Enter a non-negative number.")  # 无效预算错误

    def _build_table(self):
        '''
        构建左侧记录表格 UI
        - 框架：角圆 16，边框 1
        - 网格：行 2 扩展，列 0 扩展
        - 组件：标题标签、按钮栏（删除、导入、导出、汇总、图表、货币设置、添加支出）、Treeview 表格、垂直滚动条
        '''
        frm = ctk.CTkFrame(self, corner_radius=16, border_width=1)  # 创建框架
        frm.grid(row=0, column=0, sticky="nsew")  # 放置在网格 (0,0)，填充所有方向
        frm.grid_rowconfigure(2, weight=1)  # 行 2 扩展（用于表格）
        frm.grid_columnconfigure(0, weight=1)  # 列 0 扩展

        lbl_title = ctk.CTkLabel(frm, text="Records", font=ctk.CTkFont(size=20, weight="bold"))  # 标题
        lbl_title.grid(row=0, column=0, columnspan=2, pady=12, sticky="ew")  # 跨列，水平填充

        btns = ctk.CTkFrame(frm, fg_color="transparent")  # 按钮栏框架
        btns.grid(row=1, column=0, columnspan=2, pady=16, sticky="ew")  # 放置在行 1，水平填充

        # 按钮：删除选中、导入 CSV、导出 CSV、月汇总、图表、货币设置、添加支出
        ctk.CTkButton(btns, text="Delete Selected", command=self._delete_selected, width=160, font=ctk.CTkFont(size=14)).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Import CSV", command=self._import_csv, width=160, font=ctk.CTkFont(size=14)).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Export CSV", command=self._export_csv, width=160, font=ctk.CTkFont(size=14)).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Monthly Summary", command=self._show_summary, width=160, font=ctk.CTkFont(size=14)).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Charts", command=self._open_charts, width=160, font=ctk.CTkFont(size=14)).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Currency Settings", command=self._show_currency_dialog, width=160, font=ctk.CTkFont(size=14)).pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Add Expense", command=self._show_add_expense_dialog, width=160, font=ctk.CTkFont(size=14)).pack(side="left", padx=12)

        # 定义表格列
        cols = ("date", "base_amount", "base_currency", "exchange_rate", "target_amount", "target_currency", "category",
                "budget Left", "spent so far", "note")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=22)  # 创建 Treeview，显示表头，高度 22 行

        # 设置列标题和宽度、对齐
        self.tree.heading("date", text="Date")
        self.tree.column("date", width=140, anchor="w")

        self.tree.heading("base_amount", text="Amount")
        self.tree.column("base_amount", width=120, anchor="e")

        self.tree.heading("base_currency", text="Currency")
        self.tree.column("base_currency", width=100, anchor="center")

        self.tree.heading("exchange_rate", text="Exchange Rate")
        self.tree.column("exchange_rate", width=140, anchor="e")

        self.tree.heading("target_amount", text="Converted Amount")
        self.tree.column("target_amount", width=160, anchor="e")

        self.tree.heading("target_currency", text="Target Currency")
        self.tree.column("target_currency", width=150, anchor="center")

        self.tree.heading("category", text="Category")
        self.tree.column("category", width=140, anchor="w")

        self.tree.heading("budget Left", text="Budget Left")
        self.tree.column("budget Left", width=120, anchor="w")

        self.tree.heading("spent so far", text="Spent So Far")
        self.tree.column("spent so far", width=140, anchor="w")

        self.tree.heading("note", text="Note")
        self.tree.column("note", width=400, anchor="w")

        self.tree.grid(row=2, column=0, sticky="nsew")  # 放置表格，填充所有方向

        # 垂直滚动条
        scroll = ctk.CTkScrollbar(frm, orientation="vertical", command=self.tree.yview)
        scroll.grid(row=2, column=1, sticky="ns")  # 放置在右侧，垂直填充
        self.tree.configure(yscrollcommand=scroll.set)  # 配置表格滚动

    def _build_category_summary(self):
        '''
        构建右侧类别汇总 UI
        - 框架：角圆 16，边框 1
        - 行 1 扩展
        - 组件：标题标签、汇总标签（显示文本）
        '''
        frm = ctk.CTkFrame(self, corner_radius=16, border_width=1)  # 创建框架
        frm.grid(row=0, column=1, sticky="nsew")  # 放置在网格 (0,1)，填充
        frm.grid_rowconfigure(1, weight=1)  # 行 1 扩展

        lbl_title = ctk.CTkLabel(frm, text="Category Summary (This Month)", font=ctk.CTkFont(size=20, weight="bold"))  # 标题
        lbl_title.pack(pady=12)  # 打包，垂直间距 12

        self.lbl_summary = ctk.CTkLabel(frm, text="No records yet.", justify="left", anchor="w", font=ctk.CTkFont(size=14))  # 汇总标签
        self.lbl_summary.pack(fill="both", expand=True, padx=24, pady=12)  # 填充扩展，间距

    def _build_footer(self):
        '''
        构建底部页脚 UI
        - 框架：角圆 16，边框 1
        - 放置在行 1，跨两列
        - 组件：本月总计标签、预算和剩余标签
        '''
        bar = ctk.CTkFrame(self, corner_radius=16, border_width=1)  # 创建框架
        bar.grid(row=1, column=0, columnspan=2, padx=24, pady=16, sticky="ew")  # 放置跨列，水平填充

        self.lbl_total = ctk.CTkLabel(bar, text="This month: 0.00", font=ctk.CTkFont(size=16))  # 本月总计
        self.lbl_total.pack(side="left", padx=24)  # 左侧打包

        self.lbl_budget = ctk.CTkLabel(bar, text="Budget: 0.00  |  Remaining: 0.00", font=ctk.CTkFont(size=16))  # 预算剩余
        self.lbl_budget.pack(side="right", padx=24)  # 右侧打包

    def _refresh_table(self):
        '''
        刷新表格
        - 清空现有项
        - 按日期排序记录
        - 计算运行总计和剩余预算
        - 插入新项
        '''
        for item in self.tree.get_children():  # 清空表格
            self.tree.delete(item)

        sorted_rows = sorted(self.ledger.rows, key=lambda x: x["date"])  # 按日期排序

        running_total = 0.0  # 运行总计
        current_month = datetime.now().strftime("%Y-%m")  # 当前月

        for r in sorted_rows:  # 遍历排序记录
            if r["date"].startswith(current_month):  # 如果是本月，累加
                running_total += r["amount"]
            remaining = self.ledger.month_budget - running_total  # 计算剩余

            # 插入行
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
        '''
        删除选中行
        - 获取选中项索引
        - 删除记录
        - 刷新总计和汇总
        '''
        items = self.tree.selection()  # 获取选中项
        if not items:
            return
        idx = [self.tree.index(i) for i in items]  # 获取索引
        self.ledger.remove_by_indices(idx)  # 删除记录
        for i in items:
            self.tree.delete(i)  # 从表格删除
        self._refresh_totals()  # 刷新总计
        self._refresh_category_summary()  # 刷新汇总

    def _refresh_totals(self):
        '''
        刷新页脚总计
        - 计算本月总支出
        - 更新标签文本和颜色（剩余 >=30% 绿，>=0 橙，<0 红）
        '''
        total = self.ledger.total_this_month()  # 本月总计
        self.lbl_total.configure(text=f"This month: {self.ledger.target_currency} {total:.2f}")  # 更新总计标签
        b = self.ledger.month_budget  # 预算
        rem = b - total  # 剩余
        self.lbl_budget.configure(text=f"Budget: {self.ledger.target_currency} {b:.2f}  |  Remaining: {rem:.2f}")  # 更新预算标签
        color = "green" if rem >= b * 0.3 else ("orange" if rem >= 0 else "red")  # 根据剩余确定颜色
        self.lbl_budget.configure(text_color=color)  # 设置颜色

    def _refresh_category_summary(self):
        '''
        刷新类别汇总
        - 获取按类别汇总
        - 更新标签文本
        '''
        sums = self.ledger.summary_by_category()  # 获取汇总
        if not sums:
            self.lbl_summary.configure(text="No records this month.")  # 无记录
            return
        text = "\n".join(f"{k:15s} : {self.ledger.target_currency} {v:.2f}" for k, v in sums.items())  # 格式化文本
        self.lbl_summary.configure(text=text)  # 更新标签

    def _maybe_budget_alert(self):
        '''
        检查并显示预算警报
        - 如果预算 >0 且支出 >预算，显示超出警报
        - 如果支出 >=90% 预算，显示接近警报
        '''
        b = self.ledger.month_budget  # 预算
        if b <= 0: return  # 预算 <=0 无警报
        total = self.ledger.total_this_month()  # 总支出
        if total > b:
            messagebox.showwarning("Budget exceeded",
                                   f"You exceeded the monthly budget by {total - b:.2f} {self.ledger.target_currency}.")  # 超出警报
        elif total >= 0.9 * b:
            messagebox.showinfo("Near budget", "You've reached 90% of your monthly budget.")  # 接近警报

    def _show_summary(self):
        '''
        显示月汇总消息框
        - 获取类别汇总和总计
        - 显示信息
        '''
        sums = self.ledger.summary_by_category()  # 获取汇总
        if not sums:
            messagebox.showinfo("Summary", "No records this month yet.")  # 无记录
            return
        text = "\n".join(f"{k:15s} : {self.ledger.target_currency} {v:.2f}" for k, v in sums.items())  # 格式化
        total = self.ledger.total_this_month()  # 总计
        messagebox.showinfo("Monthly Summary",
                            f"{text}\n\nTotal this month: {self.ledger.target_currency} {total:.2f}")  # 显示

    def _export_csv(self):
        '''
        导出 CSV
        - 打开保存对话框
        - 保存记录
        '''
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")],
                                            title="Export to CSV")  # 保存对话框
        if not path: return  # 取消返回
        try:
            self.ledger.save_csv(path)  # 保存
            messagebox.showinfo("Saved", f"Exported to\n{path}")  # 成功消息
        except Exception as e:
            messagebox.showerror("Save failed", str(e))  # 失败错误

    def _import_csv(self):
        '''
        导入 CSV
        - 打开打开对话框
        - 加载记录，刷新 UI
        '''
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")], title="Import CSV")  # 打开对话框
        if not path: return  # 取消返回
        try:
            self.ledger.load_csv(path)  # 加载
            self._refresh_table()  # 刷新表格
            self._refresh_totals()  # 刷新总计
            if self.ledger.target_currency_locked:
                self.target_disabled = True  # 如果锁定，禁用目标设置
            self.budget_disabled = True  # 禁用预算设置
            self._refresh_category_summary()  # 刷新汇总
            messagebox.showinfo("Import Successful", f"Loaded {len(self.ledger.rows)} records")  # 成功消息
        except Exception as e:
            messagebox.showerror("Load failed", str(e))  # 失败错误

    def _open_charts(self):
        '''
        打开图表窗口
        - 如果窗口已存在，焦点置顶
        - 创建新窗口，使用 CTkTabview 展示饼图、条形图、日趋势线
        - 如果无数据，显示消息并关闭
        - 优化：调整 CTkTabview 标签导航居中对齐图表，优化窗口大小（900x650），统一 customtkinter 风格（暗模式，绿色主题）
        '''
        if self.chart_win and self.chart_win.winfo_exists():  # 如果窗口存在，焦点置顶
            self.chart_win.focus()
            return

        self.chart_win = ctk.CTkToplevel(self)  # 创建新 CTk 窗口
        win = self.chart_win
        win.title("Charts - This Month")  # 设置标题
        win.geometry("500x450")  # 调整窗口大小，宽度略减，高度优化以适配布局
        win.grab_set()  # 置顶并阻塞主窗口
        win.grid_columnconfigure(0, weight=1)  # 列扩展
        win.grid_rowconfigure(1, weight=1)  # 内容行扩展
        def _on_close():  # 关闭处理
            try:
                win.destroy()
            finally:
                self.chart_win = None

        win.protocol("WM_DELETE_WINDOW", _on_close)  # 设置关闭协议

        # 标题
        lbl_title = ctk.CTkLabel(win, text="Monthly Spending Charts", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_title.pack(pady=15)  # 减少垂直间距，适配更紧凑的窗口

        # 检查数据
        sums = self.ledger.summary_by_category()  # 获取类别汇总
        if not sums:
            messagebox.showinfo("Charts", "No records this month yet.")  # 无数据提示
            _on_close()
            return
        labels = list(sums.keys())  # 类别标签
        values = list(sums.values())  # 类别金额

        # 创建 CTkTabview，设置绿色主题，居中对齐
        tabview = ctk.CTkTabview(win, fg_color="transparent", segmented_button_selected_color="#2e7d32",
                                 width=800)  # 固定宽度，居中
        tabview.pack(pady=15, padx=50, fill="x")  # 居中，水平填充，增加间距

        # 饼图页
        tabview.add("Pie by Category")  # 添加标签页
        frm_pie = ctk.CTkFrame(tabview.tab("Pie by Category"), fg_color="transparent")
        frm_pie.grid(row=0, column=0, sticky="nsew")
        frm_pie.grid_columnconfigure(0, weight=1)
        frm_pie.grid_rowconfigure(0, weight=1)
        fig1 = Figure(figsize=(6.5, 4.5), dpi=100, facecolor="#2a2d2e")  # 略减图表尺寸，适配窗口
        ax1 = fig1.add_subplot(111, facecolor="#2a2d2e")
        ax1.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, counterclock=False,
                textprops={'color': 'white', 'fontsize': 12})  # 白色文字
        ax1.axis("equal")  # 等轴
        fig1.tight_layout()
        c1 = FigureCanvasTkAgg(fig1, master=frm_pie)
        c1.draw()
        c1.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)  # 增加间距

        # 条形图页
        tabview.add("Bar by Category")
        frm_bar = ctk.CTkFrame(tabview.tab("Bar by Category"), fg_color="transparent")
        frm_bar.grid(row=0, column=0, sticky="nsew")
        frm_bar.grid_columnconfigure(0, weight=1)
        frm_bar.grid_rowconfigure(0, weight=1)
        fig2 = Figure(figsize=(6.5, 4.5), dpi=100, facecolor="#2a2d2e")
        ax2 = fig2.add_subplot(111, facecolor="#2a2d2e")
        ax2.bar(labels, values, color="#388e3c")  # 绿色条形
        ax2.set_ylabel("Amount", color="white", fontsize=12)
        ax2.set_xlabel("Category", color="white", fontsize=12)
        ax2.set_title("Spending by Category (This Month)", color="white", fontsize=14)
        ax2.tick_params(axis='x', rotation=25, colors="white")  # 白色刻度
        ax2.tick_params(axis='y', colors="white")
        fig2.tight_layout()
        c2 = FigureCanvasTkAgg(fig2, master=frm_bar)
        c2.draw()
        c2.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)

        # 日趋势线页
        tabview.add("Daily Trend")
        frm_line = ctk.CTkFrame(tabview.tab("Daily Trend"), fg_color="transparent")
        frm_line.grid(row=0, column=0, sticky="nsew")
        frm_line.grid_columnconfigure(0, weight=1)
        frm_line.grid_rowconfigure(0, weight=1)
        fig3 = Figure(figsize=(6.5, 4.5), dpi=100, facecolor="#2a2d2e")
        ax3 = fig3.add_subplot(111, facecolor="#2a2d2e")
        daily = self.ledger.daily_totals_this_month()  # 获取每日总计
        if daily:
            x = [d for d, _ in daily]  # 日期
            y = [v for _, v in daily]  # 金额
            ax3.plot(x, y, marker="o", color="#388e3c", linewidth=2)  # 绿色线条
            ax3.set_xlabel("Date", color="white", fontsize=12)
            ax3.set_ylabel("Amount", color="white", fontsize=12)
            ax3.set_title("Daily Total (This Month)", color="white", fontsize=14)
            for lab in ax3.get_xticklabels():
                lab.set_rotation(35)
                lab.set_ha("right")
                lab.set_color("white")  # 白色刻度
            ax3.tick_params(axis='y', colors="white")
        else:
            ax3.text(0.5, 0.5, "No data", ha="center", va="center", color="white", fontsize=14)
        fig3.tight_layout()
        c3 = FigureCanvasTkAgg(fig3, master=frm_line)
        c3.draw()
        c3.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)

        tabview.set("Pie by Category")  # 默认选中饼图页


if __name__ == "__main__":
    App().mainloop()  # 如果直接运行脚本，启动应用主循环
