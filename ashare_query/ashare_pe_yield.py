# -*- coding: utf-8 -*-
"""
A-share PE / dividend-yield desktop query tool for Windows.

Data source: East Money public quote API (沪深京 A 股实时行情).
"""
from __future__ import print_function

import csv
import json
import os
import sys
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    sys.stderr.write("This program needs tkinter (usually bundled with Windows Python).\n")
    sys.exit(1)

try:
    import requests
except ImportError:
    sys.stderr.write("Missing dependency: requests\n  pip install requests\n")
    sys.exit(1)


APP_TITLE = "A股估值查询  |  PE / 股息率"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(SCRIPT_DIR, "cache", "last_quote.json")
PAGE_SIZE = 100
FETCH_WORKERS = 4
REQUEST_TIMEOUT = 20
AUTO_INTERVALS_SEC = (30, 60, 120, 300)

EASTMONEY_URLS = (
    "https://push2.eastmoney.com/api/qt/clist/get",
    "https://82.push2.eastmoney.com/api/qt/clist/get",
    "https://push2delay.eastmoney.com/api/qt/clist/get",
)
# 沪市主板+科创、深市主板+创业、北交所
A_SHARE_FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
FIELDS = "f12,f13,f14,f2,f3,f9,f114,f115,f133,f23,f20,f8,f100"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/center/gridlist.html",
}

COLUMNS = (
    ("code", "代码", 80, "center"),
    ("name", "名称", 110, "w"),
    ("board", "板块", 80, "center"),
    ("industry", "行业", 110, "w"),
    ("price", "最新价", 80, "e"),
    ("chg_pct", "涨跌幅%", 80, "e"),
    ("pe_dyn", "PE(动态)", 90, "e"),
    ("pe_ttm", "PE(TTM)", 90, "e"),
    ("pe_lyr", "PE(静)", 80, "e"),
    ("div_yield", "股息率%", 80, "e"),
    ("pb", "市净率", 80, "e"),
    ("mcap", "总市值(亿)", 100, "e"),
)

BOARD_CHOICES = (
    "全部",
    "上证主板",
    "科创板",
    "深证主板",
    "创业板",
    "北交所",
)

NAVY = "#1b365d"
NAVY_2 = "#234e80"
BG = "#eef2f6"
CARD = "#ffffff"
TEXT = "#1a202c"
MUTED = "#4a5568"
RED_UP = "#c53030"
GREEN_DOWN = "#2f855a"
ACCENT = "#dd6b20"


def _enable_windows_dpi():
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            from ctypes import windll

            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def to_float(value):
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_num(value, digits=2):
    if value is None:
        return "-"
    try:
        return "{:.{digits}f}".format(value, digits=digits)
    except (TypeError, ValueError):
        return "-"


def board_of(code):
    code = (code or "").strip()
    if code.startswith("688") or code.startswith("689"):
        return "科创板"
    if code.startswith("6"):
        return "上证主板"
    if code.startswith("30"):
        return "创业板"
    if code.startswith("00"):
        return "深证主板"
    if code.startswith("8") or code.startswith("4") or code.startswith("9"):
        return "北交所"
    return "其他"


def quote_url(code):
    code = (code or "").strip()
    if code.startswith("6"):
        market = "sh"
    elif code.startswith(("8", "4", "9")):
        market = "bj"
    else:
        market = "sz"
    return "https://quote.eastmoney.com/{}{}.html".format(market, code)


def classify_row(raw):
    code = str(raw.get("f12") or "").zfill(6)
    price = to_float(raw.get("f2"))
    mcap = to_float(raw.get("f20"))
    industry = raw.get("f100")
    if industry in (None, "", "-"):
        industry = "-"
    return {
        "code": code,
        "name": str(raw.get("f14") or ""),
        "board": board_of(code),
        "industry": industry,
        "price": price,
        "chg_pct": to_float(raw.get("f3")),
        "pe_dyn": to_float(raw.get("f9")),
        "pe_ttm": to_float(raw.get("f115")),
        "pe_lyr": to_float(raw.get("f114")),
        "div_yield": to_float(raw.get("f133")),
        "pb": to_float(raw.get("f23")),
        "mcap": None if mcap is None else mcap / 1e8,
        "turnover": to_float(raw.get("f8")),
    }


def _fetch_page(session, url, page, page_size):
    params = {
        "pn": page,
        "pz": page_size,
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2,
        "invt": 2,
        "wbp2u": "|0|0|0|web",
        "fid": "f12",
        "fs": A_SHARE_FS,
        "fields": FIELDS,
    }
    resp = session.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data") or {}
    diff = data.get("diff") or []
    if isinstance(diff, dict):
        diff = list(diff.values())
    return int(data.get("total") or 0), diff


def fetch_ashare_quotes(progress_cb=None):
    """Download all A-share quotes. Returns (rows, source_url, fetched_at)."""
    last_error = None
    for url in EASTMONEY_URLS:
        try:
            session = requests.Session()
            total, first = _fetch_page(session, url, 1, PAGE_SIZE)
            if total <= 0 and not first:
                raise RuntimeError("行情接口返回空数据")
            page_size = max(len(first), 1)
            pages = max(1, (total + page_size - 1) // page_size)
            chunks = {1: first}
            if progress_cb:
                progress_cb(len(first), total)

            def load_page(page):
                local = requests.Session()
                _total, chunk = _fetch_page(local, url, page, page_size)
                return page, chunk

            if pages > 1:
                done = [len(first)]
                lock = threading.Lock()
                with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
                    futures = [pool.submit(load_page, page) for page in range(2, pages + 1)]
                    for fut in as_completed(futures):
                        page, chunk = fut.result()
                        chunks[page] = chunk
                        if progress_cb:
                            with lock:
                                done[0] += len(chunk)
                                progress_cb(min(done[0], total), total)

            raw_rows = []
            for page in range(1, pages + 1):
                raw_rows.extend(chunks.get(page) or [])
            rows = [classify_row(item) for item in raw_rows]
            uniq = {}
            for row in rows:
                uniq.setdefault(row["code"], row)
            ordered = list(uniq.values())
            ordered.sort(key=lambda r: r["code"])
            return ordered, url, datetime.now()
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("无法获取 A 股行情: {}".format(last_error))


def save_cache(rows, fetched_at):
    folder = os.path.dirname(CACHE_PATH)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    payload = {
        "fetched_at": fetched_at.strftime("%Y-%m-%d %H:%M:%S"),
        "rows": rows,
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def load_cache():
    if not os.path.isfile(CACHE_PATH):
        return None, None
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload.get("rows") or [], payload.get("fetched_at")
    except Exception:
        return None, None


def row_values(row):
    return (
        row["code"],
        row["name"],
        row["board"],
        row["industry"],
        fmt_num(row["price"]),
        fmt_num(row["chg_pct"]),
        fmt_num(row["pe_dyn"]),
        fmt_num(row["pe_ttm"]),
        fmt_num(row["pe_lyr"]),
        fmt_num(row["div_yield"]),
        fmt_num(row["pb"]),
        fmt_num(row["mcap"], 2),
    )


def parse_optional_float(text):
    text = (text or "").strip()
    if not text:
        return None
    return to_float(text.replace("%", ""))


class AShareApp(object):
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x760")
        self.root.minsize(980, 560)
        self.root.configure(bg=BG)

        self.all_rows = []
        self.view_rows = []
        self.fetched_at = None
        self.from_cache = False
        self.sort_key = "code"
        self.sort_reverse = False
        self.fetching = False
        self.auto_job = None
        self._search_job = None

        self.search_var = tk.StringVar()
        self.board_var = tk.StringVar(value="全部")
        self.pe_min_var = tk.StringVar()
        self.pe_max_var = tk.StringVar()
        self.yield_min_var = tk.StringVar()
        self.exclude_loss_var = tk.BooleanVar(value=False)
        self.only_div_var = tk.BooleanVar(value=False)
        self.auto_var = tk.BooleanVar(value=False)
        self.interval_var = tk.IntVar(value=60)
        self.status_var = tk.StringVar(value="准备就绪")
        self.meta_var = tk.StringVar(value="尚未加载数据")

        self._build_style()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(200, self.refresh_async)

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        font_ui = ("Microsoft YaHei UI", 10)
        font_head = ("Microsoft YaHei UI", 10, "bold")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=TEXT, font=font_ui)
        style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=font_ui)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("TButton", font=font_ui, padding=(10, 4))
        style.configure("TCheckbutton", background=BG, font=font_ui)
        style.configure("TMenubutton", font=font_ui)
        style.configure(
            "Treeview",
            font=font_ui,
            rowheight=26,
            background=CARD,
            fieldbackground=CARD,
            bordercolor="#cbd5e0",
            relief="flat",
        )
        style.configure(
            "Treeview.Heading",
            font=font_head,
            background=NAVY_2,
            foreground="white",
            relief="flat",
            padding=4,
        )
        style.map("Treeview", background=[("selected", "#2b6cb0")], foreground=[("selected", "white")])
        style.map("Treeview.Heading", background=[("active", NAVY)], foreground=[("active", "white")])

    def _build_ui(self):
        header = tk.Frame(self.root, bg=NAVY, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="A 股全市场估值",
            bg=NAVY,
            fg="white",
            font=("Microsoft YaHei UI", 16, "bold"),
        ).pack(side="left", padx=18, pady=12)
        tk.Label(
            header,
            text="市盈率 PE  ·  股息率  ·  东方财富行情",
            bg=NAVY,
            fg="#bee3f8",
            font=("Microsoft YaHei UI", 10),
        ).pack(side="left", padx=(0, 12))

        btn_bar = tk.Frame(header, bg=NAVY)
        btn_bar.pack(side="right", padx=14)
        self.refresh_btn = tk.Button(
            btn_bar,
            text="刷新最新",
            command=self.refresh_async,
            bg="#c53030",
            fg="white",
            activebackground="#9b2c2c",
            activeforeground="white",
            relief="flat",
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=4,
            cursor="hand2",
        )
        self.refresh_btn.pack(side="left", padx=4)
        tk.Button(
            btn_bar,
            text="导出 Excel",
            command=lambda: self.export_table("xlsx"),
            bg="#2b6cb0",
            fg="white",
            activebackground="#2c5282",
            activeforeground="white",
            relief="flat",
            font=("Microsoft YaHei UI", 10),
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=4)
        tk.Button(
            btn_bar,
            text="导出 CSV",
            command=lambda: self.export_table("csv"),
            bg="#2c5282",
            fg="white",
            activebackground="#1a365d",
            activeforeground="white",
            relief="flat",
            font=("Microsoft YaHei UI", 10),
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=4)

        filter_bar = ttk.Frame(self.root, style="TFrame")
        filter_bar.pack(fill="x", padx=12, pady=(10, 4))

        ttk.Label(filter_bar, text="搜索").grid(row=0, column=0, sticky="w", padx=(0, 4))
        search_entry = ttk.Entry(filter_bar, textvariable=self.search_var, width=22)
        search_entry.grid(row=0, column=1, padx=(0, 12))
        search_entry.bind("<KeyRelease>", self._on_search_typed)

        ttk.Label(filter_bar, text="板块").grid(row=0, column=2, sticky="w", padx=(0, 4))
        board_box = ttk.Combobox(
            filter_bar,
            textvariable=self.board_var,
            values=BOARD_CHOICES,
            width=10,
            state="readonly",
        )
        board_box.grid(row=0, column=3, padx=(0, 12))
        board_box.bind("<<ComboboxSelected>>", lambda _e: self.apply_filter())

        ttk.Label(filter_bar, text="PE(TTM)").grid(row=0, column=4, sticky="w", padx=(0, 4))
        ttk.Entry(filter_bar, textvariable=self.pe_min_var, width=7).grid(row=0, column=5)
        ttk.Label(filter_bar, text="~").grid(row=0, column=6, padx=3)
        ttk.Entry(filter_bar, textvariable=self.pe_max_var, width=7).grid(row=0, column=7, padx=(0, 12))

        ttk.Label(filter_bar, text="股息率 ≥").grid(row=0, column=8, sticky="w", padx=(0, 4))
        ttk.Entry(filter_bar, textvariable=self.yield_min_var, width=7).grid(row=0, column=9, padx=(0, 12))

        ttk.Checkbutton(
            filter_bar, text="排除亏损", variable=self.exclude_loss_var, command=self.apply_filter
        ).grid(row=0, column=10, padx=(0, 8))
        ttk.Checkbutton(
            filter_bar, text="仅有分红", variable=self.only_div_var, command=self.apply_filter
        ).grid(row=0, column=11, padx=(0, 8))
        ttk.Button(filter_bar, text="筛选", command=self.apply_filter).grid(row=0, column=12, padx=4)
        ttk.Button(filter_bar, text="清空", command=self.clear_filters).grid(row=0, column=13, padx=4)

        auto_bar = ttk.Frame(self.root, style="TFrame")
        auto_bar.pack(fill="x", padx=12, pady=(0, 6))
        ttk.Checkbutton(
            auto_bar,
            text="自动刷新",
            variable=self.auto_var,
            command=self._toggle_auto,
        ).pack(side="left")
        ttk.Label(auto_bar, text="间隔(秒)", style="Muted.TLabel").pack(side="left", padx=(10, 4))
        interval_box = ttk.Combobox(
            auto_bar,
            values=AUTO_INTERVALS_SEC,
            textvariable=self.interval_var,
            width=6,
            state="readonly",
        )
        interval_box.pack(side="left")
        interval_box.bind("<<ComboboxSelected>>", lambda _e: self._toggle_auto())
        ttk.Label(
            auto_bar,
            text="双击行打开东方财富行情页  ·  点击表头排序  ·  Ctrl+C 复制选中行",
            style="Muted.TLabel",
        ).pack(side="left", padx=16)

        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        cols = [item[0] for item in COLUMNS]
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, minwidth=60, anchor=anchor, stretch=True)

        self.tree.tag_configure("odd", background="#f7fafc")
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("up", foreground=RED_UP)
        self.tree.tag_configure("down", foreground=GREEN_DOWN)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.root.bind("<Control-c>", self._copy_selection)
        self.root.bind("<F5>", lambda _e: self.refresh_async())

        status = tk.Frame(self.root, bg="#d9e2ec", height=28)
        status.pack(fill="x", side="bottom")
        tk.Label(
            status,
            textvariable=self.status_var,
            bg="#d9e2ec",
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).pack(side="left", padx=12)
        tk.Label(
            status,
            textvariable=self.meta_var,
            bg="#d9e2ec",
            fg=NAVY,
            font=("Microsoft YaHei UI", 9),
            anchor="e",
        ).pack(side="right", padx=12)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="打开行情页", command=self._open_selected)
        self.menu.add_command(label="复制选中行", command=lambda: self._copy_selection(None))

    def _on_search_typed(self, _event):
        if self._search_job is not None:
            self.root.after_cancel(self._search_job)
        self._search_job = self.root.after(280, self.apply_filter)

    def clear_filters(self):
        self.search_var.set("")
        self.board_var.set("全部")
        self.pe_min_var.set("")
        self.pe_max_var.set("")
        self.yield_min_var.set("")
        self.exclude_loss_var.set(False)
        self.only_div_var.set(False)
        self.apply_filter()

    def apply_filter(self):
        keyword = (self.search_var.get() or "").strip().lower()
        board = self.board_var.get()
        pe_min = parse_optional_float(self.pe_min_var.get())
        pe_max = parse_optional_float(self.pe_max_var.get())
        y_min = parse_optional_float(self.yield_min_var.get())
        exclude_loss = bool(self.exclude_loss_var.get())
        only_div = bool(self.only_div_var.get())

        filtered = []
        for row in self.all_rows:
            if board != "全部" and row["board"] != board:
                continue
            if keyword:
                blob = "{} {}".format(row["code"], row["name"]).lower()
                if keyword not in blob and keyword not in (row.get("industry") or "").lower():
                    continue
            pe = row["pe_ttm"]
            if pe is None:
                pe = row["pe_dyn"]
            if exclude_loss and (pe is None or pe <= 0):
                continue
            if pe_min is not None and (pe is None or pe < pe_min):
                continue
            if pe_max is not None and (pe is None or pe > pe_max):
                continue
            dy = row["div_yield"]
            if only_div and (dy is None or dy <= 0):
                continue
            if y_min is not None and (dy is None or dy < y_min):
                continue
            filtered.append(row)

        self.view_rows = filtered
        self._sort_view()
        self._reload_tree()
        self._update_meta()

    def sort_by(self, key):
        if self.sort_key == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_key = key
            self.sort_reverse = key not in ("code", "name", "board", "industry")
        self._sort_view()
        self._reload_tree()

    def _sort_view(self):
        key = self.sort_key
        reverse = self.sort_reverse
        text_keys = {"code", "name", "board", "industry"}

        def sort_item(row):
            value = row.get(key)
            if key in text_keys:
                return value or ""
            if value is None:
                return float("-inf") if reverse else float("inf")
            return value

        self.view_rows.sort(key=sort_item, reverse=reverse)

    def _reload_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self.view_rows):
            tags = ["odd" if idx % 2 else "even"]
            chg = row.get("chg_pct")
            if chg is not None:
                tags.append("up" if chg > 0 else "down" if chg < 0 else "even")
            self.tree.insert("", "end", iid=row["code"] + "-{}".format(idx), values=row_values(row), tags=tuple(tags))

    def _update_meta(self):
        n_all = len(self.all_rows)
        n_view = len(self.view_rows)
        pes = [r["pe_ttm"] for r in self.view_rows if r["pe_ttm"] is not None and r["pe_ttm"] > 0]
        dys = [r["div_yield"] for r in self.view_rows if r["div_yield"] is not None]
        pe_med = "-"
        dy_med = "-"
        if pes:
            pes_sorted = sorted(pes)
            pe_med = fmt_num(pes_sorted[len(pes_sorted) // 2])
        if dys:
            dys_sorted = sorted(dys)
            dy_med = fmt_num(dys_sorted[len(dys_sorted) // 2])
        stamp = self.fetched_at.strftime("%Y-%m-%d %H:%M:%S") if self.fetched_at else "--"
        cache_note = "（缓存）" if self.from_cache else ""
        self.meta_var.set(
            "显示 {} / {} 家  |  PE(TTM)中位数 {}  |  股息率中位数 {}%  |  更新 {}{}".format(
                n_view, n_all, pe_med, dy_med, stamp, cache_note
            )
        )

    def refresh_async(self, silent=False):
        if self.fetching:
            return
        self.fetching = True
        if not silent:
            self.status_var.set("正在从东方财富拉取全部 A 股行情...")
        self.refresh_btn.configure(state="disabled", text="刷新中...")

        def worker():
            try:
                def progress(done, total):
                    self.root.after(0, lambda: self.status_var.set("正在拉取 {} / {} ...".format(done, total)))

                rows, _url, fetched_at = fetch_ashare_quotes(progress_cb=progress)
                try:
                    save_cache(rows, fetched_at)
                except Exception:
                    pass
                self.root.after(0, lambda: self._on_fetch_ok(rows, fetched_at, False))
            except Exception as exc:
                self.root.after(0, lambda: self._on_fetch_fail(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_fetch_ok(self, rows, fetched_at, from_cache):
        self.fetching = False
        self.refresh_btn.configure(state="normal", text="刷新最新")
        self.all_rows = rows
        self.fetched_at = fetched_at
        self.from_cache = from_cache
        self.status_var.set("已加载 {} 家上市公司".format(len(rows)))
        self.apply_filter()

    def _on_fetch_fail(self, exc):
        self.fetching = False
        self.refresh_btn.configure(state="normal", text="刷新最新")
        cached_rows, cached_at = load_cache()
        if cached_rows:
            self.all_rows = cached_rows
            try:
                self.fetched_at = datetime.strptime(cached_at, "%Y-%m-%d %H:%M:%S") if cached_at else None
            except Exception:
                self.fetched_at = None
            self.from_cache = True
            self.status_var.set("在线刷新失败，已显示本地缓存。原因: {}".format(exc))
            self.apply_filter()
            return
        self.status_var.set("刷新失败: {}".format(exc))
        messagebox.showerror("刷新失败", "无法获取最新 A 股数据。\n\n{}".format(exc))

    def _toggle_auto(self):
        if self.auto_job is not None:
            self.root.after_cancel(self.auto_job)
            self.auto_job = None
        if self.auto_var.get():
            self._schedule_auto()

    def _schedule_auto(self):
        try:
            interval_ms = int(self.interval_var.get()) * 1000
        except Exception:
            interval_ms = 60000
        interval_ms = max(15000, interval_ms)

        def tick():
            if self.auto_var.get():
                self.refresh_async(silent=True)
                self.auto_job = self.root.after(interval_ms, tick)

        self.auto_job = self.root.after(interval_ms, tick)
        self.status_var.set("已开启自动刷新，每 {} 秒更新一次".format(interval_ms // 1000))

    def export_table(self, kind):
        if not self.view_rows:
            messagebox.showinfo("导出", "当前没有可导出的数据。")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if kind == "csv":
            path = filedialog.asksaveasfilename(
                title="导出 CSV",
                defaultextension=".csv",
                initialfile="ashare_pe_yield_{}.csv".format(stamp),
                filetypes=[("CSV", "*.csv")],
            )
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                    writer = csv.writer(fh)
                    writer.writerow([title for _k, title, _w, _a in COLUMNS])
                    for row in self.view_rows:
                        writer.writerow(row_values(row))
            except Exception as exc:
                messagebox.showerror("导出失败", str(exc))
                return
        else:
            try:
                from openpyxl import Workbook
            except ImportError:
                messagebox.showerror("缺少依赖", "导出 Excel 需要 openpyxl:\n  pip install openpyxl")
                return
            path = filedialog.asksaveasfilename(
                title="导出 Excel",
                defaultextension=".xlsx",
                initialfile="ashare_pe_yield_{}.xlsx".format(stamp),
                filetypes=[("Excel", "*.xlsx")],
            )
            if not path:
                return
            try:
                wb = Workbook()
                ws = wb.active
                ws.title = "A股PE股息率"
                headers = [title for _k, title, _w, _a in COLUMNS]
                ws.append(headers)
                for row in self.view_rows:
                    ws.append(list(row_values(row)))
                for col in ws.columns:
                    ws.column_dimensions[col[0].column_letter].width = 14
                wb.save(path)
            except Exception as exc:
                messagebox.showerror("导出失败", str(exc))
                return
        self.status_var.set("已导出: {}".format(path))

    def _selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        if not values:
            return None
        return values

    def _open_selected(self):
        values = self._selected_row()
        if not values:
            return
        webbrowser.open(quote_url(values[0]))

    def _on_double_click(self, _event):
        self._open_selected()

    def _on_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.menu.tk_popup(event.x_root, event.y_root)

    def _copy_selection(self, _event):
        items = self.tree.selection()
        if not items:
            return "break"
        lines = ["\t".join([title for _k, title, _w, _a in COLUMNS])]
        for item in items:
            values = self.tree.item(item, "values")
            lines.append("\t".join([str(v) for v in values]))
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.status_var.set("已复制 {} 行".format(len(items)))
        return "break"

    def _on_close(self):
        if self.auto_job is not None:
            self.root.after_cancel(self.auto_job)
        self.root.destroy()


def main():
    _enable_windows_dpi()
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    AShareApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
