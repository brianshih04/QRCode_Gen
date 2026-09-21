from __future__ import annotations

import re
import secrets
import string
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import qrcode
from PIL import Image, ImageTk
from qrcode.constants import ERROR_CORRECT_Q


APP_TITLE = "Wi-Fi QR Code 產生器"
DEFAULT_MODEL_NAME = "AMR-200"
DEFAULT_SERIAL_NUMBER = "A1B2C"
PASSWORD_LENGTH = 10
PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
SERIAL_PATTERN = re.compile(r"^[A-Z0-9]{5}$")
WIFI_ESCAPE_PATTERN = re.compile(r"([\\;,:\"])")
DEFAULT_WINDOW_WIDTH = 1180
DEFAULT_WINDOW_HEIGHT = 960
MIN_WINDOW_WIDTH = 980
MIN_WINDOW_HEIGHT = 820


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """Generate an easy-to-read WPA/WPA2 password."""

    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def escape_wifi_value(value: str) -> str:
    """Escape values according to the Wi-Fi QR payload convention."""

    return WIFI_ESCAPE_PATTERN.sub(r"\\\1", value)


def build_wifi_payload(ssid: str, password: str) -> str:
    """Build the standard payload understood by iOS and Android scanners."""

    return (
        f"WIFI:T:WPA;S:{escape_wifi_value(ssid)};"
        f"P:{escape_wifi_value(password)};;"
    )


def utf8_length(value: str) -> int:
    return len(value.encode("utf-8"))


class WifiQrGenerator(tk.Tk):
    """Desktop application for generating machine Wi-Fi QR codes."""

    COLORS = {
        "background": "#07121F",
        "surface": "#0E2031",
        "surface_alt": "#122A3F",
        "border": "#244158",
        "text": "#F2F7FA",
        "muted": "#9EB5C7",
        "subtle": "#71899D",
        "accent": "#43E3C1",
        "accent_dark": "#1CA88A",
        "blue": "#65A9FF",
        "danger": "#FF8491",
        "success": "#6BE3A6",
        "qr_dark": "#081827",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=self.COLORS["background"])
        self._set_initial_window_geometry()

        self.model_name_var = tk.StringVar(value=DEFAULT_MODEL_NAME)
        self.serial_number_var = tk.StringVar(value=DEFAULT_SERIAL_NUMBER)
        self.password_var = tk.StringVar(value=generate_password())
        self.ssid_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.result_var = tk.StringVar(value="")
        self.password_visible_var = tk.BooleanVar(value=False)

        self.current_payload = ""
        self.current_image: Image.Image | None = None
        self.qr_photo: ImageTk.PhotoImage | None = None
        self._normalizing_serial = False

        self._configure_styles()
        self._build_ui()
        self._bind_events()
        self._refresh_qr()

    def _set_initial_window_geometry(self) -> None:
        """Open at a comfortable size without exceeding the current screen."""

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        available_width = max(800, screen_width - 80)
        available_height = max(600, screen_height - 100)
        width = min(DEFAULT_WINDOW_WIDTH, available_width)
        height = min(DEFAULT_WINDOW_HEIGHT, available_height)
        self.minsize(
            min(MIN_WINDOW_WIDTH, width),
            min(MIN_WINDOW_HEIGHT, height),
        )
        left = max((screen_width - width) // 2, 0)
        top = max((screen_height - height) // 2, 0)
        self.geometry(f"{width}x{height}+{left}+{top}")

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "App.TFrame",
            background=self.COLORS["background"],
        )
        style.configure(
            "Card.TFrame",
            background=self.COLORS["surface"],
            relief="flat",
        )
        style.configure(
            "TEntry",
            fieldbackground=self.COLORS["surface_alt"],
            background=self.COLORS["surface_alt"],
            foreground=self.COLORS["text"],
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["border"],
            darkcolor=self.COLORS["border"],
            padding=(12, 9),
            insertcolor=self.COLORS["accent"],
        )
        style.map(
            "TEntry",
            fieldbackground=[("focus", "#17344B")],
            bordercolor=[("focus", self.COLORS["accent"])],
            lightcolor=[("focus", self.COLORS["accent"])],
            darkcolor=[("focus", self.COLORS["accent"])],
        )
        style.configure(
            "Primary.TButton",
            background=self.COLORS["accent"],
            foreground="#062016",
            borderwidth=0,
            padding=(16, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#75F2D6"), ("disabled", "#315A5B")],
            foreground=[("disabled", "#8BA3A2")],
        )
        style.configure(
            "Secondary.TButton",
            background=self.COLORS["surface_alt"],
            foreground=self.COLORS["text"],
            borderwidth=1,
            bordercolor=self.COLORS["border"],
            padding=(13, 9),
            font=("Segoe UI", 10),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#1A3A53"), ("disabled", "#132635")],
            foreground=[("disabled", "#5D7485")],
        )
        style.configure(
            "TCheckbutton",
            background=self.COLORS["surface"],
            foreground=self.COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.map(
            "TCheckbutton",
            background=[("active", self.COLORS["surface"])],
            foreground=[("active", self.COLORS["text"])],
        )

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=(34, 27, 34, 24))
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        header.columnconfigure(1, weight=1)

        mark = tk.Canvas(
            header,
            width=47,
            height=47,
            bg=self.COLORS["background"],
            highlightthickness=0,
        )
        mark.grid(row=0, column=0, rowspan=2, padx=(0, 14))
        mark.create_rounded_rectangle = self._rounded_rectangle  # type: ignore[attr-defined]
        self._draw_mark(mark)

        tk.Label(
            header,
            text="MACHINE NETWORK TOOL",
            bg=self.COLORS["background"],
            fg=self.COLORS["accent"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=1, sticky="w")
        tk.Label(
            header,
            text="Wi-Fi QR Code 產生器",
            bg=self.COLORS["background"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 24, "bold"),
        ).grid(row=1, column=1, sticky="w", pady=(2, 0))
        tk.Label(
            header,
            text="輸入機台資訊，立即建立手機可掃描的 Wi-Fi 設定碼",
            bg=self.COLORS["background"],
            fg=self.COLORS["muted"],
            font=("Microsoft JhengHei UI", 10),
        ).grid(row=0, column=2, rowspan=2, sticky="e", padx=(15, 0))

        content = ttk.Frame(root, style="App.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=5, minsize=430)
        content.columnconfigure(1, weight=4, minsize=380)
        content.rowconfigure(0, weight=1)

        self._build_form_card(content)
        self._build_preview_card(content)

        footer = ttk.Frame(root, style="App.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        footer.columnconfigure(0, weight=1)

        tk.Label(
            footer,
            text="標準格式：WIFI:T:WPA · 密碼只在此電腦產生，不會上傳",
            bg=self.COLORS["background"],
            fg=self.COLORS["subtle"],
            font=("Microsoft JhengHei UI", 9),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            footer,
            text="複製 Wi-Fi 設定字串",
            style="Secondary.TButton",
            command=self._copy_payload,
        ).grid(row=0, column=1, sticky="e")

    def _build_form_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(26, 25, 26, 24))
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        card.columnconfigure(0, weight=1)

        self._card_heading(
            card,
            eyebrow="1 / MACHINE IDENTITY",
            title="設定機台資訊",
            subtitle="SSID 會由 Model Name 與 SN 直接串接。",
        )

        self._field_label(card, "機台型號（Model Name）", 3)
        self.model_entry = ttk.Entry(card, textvariable=self.model_name_var, font=("Segoe UI", 11))
        self.model_entry.grid(row=4, column=0, sticky="ew", pady=(7, 3))
        self._hint(card, "例如：AMR-200、ROBOT-A", 5)

        self._field_label(card, "機台 SN（固定 5 碼）", 6)
        self.serial_entry = ttk.Entry(
            card,
            textvariable=self.serial_number_var,
            font=("Consolas", 11),
            width=12,
        )
        self.serial_entry.grid(row=7, column=0, sticky="ew", pady=(7, 3))
        self._hint(card, "限英文字母與數字，會自動轉成大寫", 8)

        ssid_box = tk.Frame(card, bg=self.COLORS["surface_alt"], padx=14, pady=12)
        ssid_box.grid(row=9, column=0, sticky="ew", pady=(17, 0))
        ssid_box.columnconfigure(0, weight=1)
        tk.Label(
            ssid_box,
            text="SSID 預覽",
            bg=self.COLORS["surface_alt"],
            fg=self.COLORS["muted"],
            font=("Microsoft JhengHei UI", 9),
        ).grid(row=0, column=0, sticky="w")
        self.ssid_label = tk.Label(
            ssid_box,
            textvariable=self.ssid_var,
            bg=self.COLORS["surface_alt"],
            fg=self.COLORS["accent"],
            font=("Consolas", 15, "bold"),
            anchor="w",
        )
        self.ssid_label.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(
            ssid_box,
            text="複製",
            style="Secondary.TButton",
            command=self._copy_ssid,
        ).grid(row=0, column=1, rowspan=2, padx=(12, 0))

        self._card_heading(
            card,
            eyebrow="2 / ACCESS",
            title="設定 Wi-Fi 密碼",
            subtitle="預設使用隨機產生的 WPA/WPA2 密碼。",
            row=10,
            padding_top=28,
        )

        password_row = ttk.Frame(card, style="Card.TFrame")
        password_row.grid(row=13, column=0, sticky="ew", pady=(8, 0))
        password_row.columnconfigure(0, weight=1)
        self.password_entry = ttk.Entry(
            password_row,
            textvariable=self.password_var,
            show="•",
            font=("Consolas", 11),
            validate="key",
            validatecommand=(self.register(self._validate_password_edit), "%P"),
        )
        self.password_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(
            password_row,
            text="重新產生",
            style="Secondary.TButton",
            command=self._regenerate_password,
        ).grid(row=0, column=1, padx=(9, 0))

        options_row = ttk.Frame(card, style="Card.TFrame")
        options_row.grid(row=14, column=0, sticky="ew", pady=(7, 0))
        ttk.Checkbutton(
            options_row,
            text="顯示密碼",
            variable=self.password_visible_var,
            command=self._toggle_password,
        ).pack(side="left")
        self._hint(options_row, "固定 10 碼，可手動修改", side="right")

        self.status_label = tk.Label(
            card,
            textvariable=self.status_var,
            bg=self.COLORS["surface"],
            fg=self.COLORS["success"],
            font=("Microsoft JhengHei UI", 10),
            anchor="w",
            justify="left",
            wraplength=440,
        )
        self.status_label.grid(row=15, column=0, sticky="ew", pady=(22, 0))

        self.model_entry.focus_set()

    def _build_preview_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(26, 25, 26, 24))
        card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        self._card_heading(
            card,
            eyebrow="3 / READY TO SCAN",
            title="Wi-Fi QR Code",
            subtitle="用手機相機或系統掃描器掃描即可加入網路。",
        )

        qr_shell = tk.Frame(
            card,
            bg="#FFFFFF",
            highlightbackground="#D4E2E9",
            highlightthickness=1,
        )
        qr_shell.grid(row=3, column=0, sticky="nsew", pady=(22, 16))
        qr_shell.columnconfigure(0, weight=1)
        qr_shell.rowconfigure(0, weight=1)

        self.qr_label = tk.Label(qr_shell, bg="#FFFFFF", bd=0)
        self.qr_label.grid(row=0, column=0, padx=19, pady=19)

        self.result_label = tk.Label(
            card,
            textvariable=self.result_var,
            bg=self.COLORS["surface"],
            fg=self.COLORS["muted"],
            font=("Microsoft JhengHei UI", 9),
            justify="center",
        )
        self.result_label.grid(row=4, column=0, sticky="ew", pady=(0, 15))

        action_row = ttk.Frame(card, style="Card.TFrame")
        action_row.grid(row=5, column=0, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        ttk.Button(
            action_row,
            text="下載 PNG",
            style="Primary.TButton",
            command=self._download_png,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(
            action_row,
            text="複製密碼",
            style="Secondary.TButton",
            command=self._copy_password,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def _card_heading(
        self,
        parent: ttk.Frame,
        eyebrow: str,
        title: str,
        subtitle: str,
        row: int = 0,
        padding_top: int = 0,
    ) -> None:
        heading = ttk.Frame(parent, style="Card.TFrame")
        heading.grid(row=row, column=0, sticky="ew", pady=(padding_top, 0))
        tk.Label(
            heading,
            text=eyebrow,
            bg=self.COLORS["surface"],
            fg=self.COLORS["accent"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        tk.Label(
            heading,
            text=title,
            bg=self.COLORS["surface"],
            fg=self.COLORS["text"],
            font=("Microsoft JhengHei UI", 15, "bold"),
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            heading,
            text=subtitle,
            bg=self.COLORS["surface"],
            fg=self.COLORS["muted"],
            font=("Microsoft JhengHei UI", 9),
        ).pack(anchor="w", pady=(4, 0))

    def _field_label(self, parent: ttk.Frame, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text,
            bg=self.COLORS["surface"],
            fg=self.COLORS["text"],
            font=("Microsoft JhengHei UI", 10, "bold"),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(18, 0))

    def _hint(
        self,
        parent: tk.Misc,
        text: str,
        row: int | None = None,
        side: str | None = None,
    ) -> None:
        label = tk.Label(
            parent,
            text=text,
            bg=self.COLORS["surface"] if isinstance(parent, ttk.Frame) else self.COLORS["surface_alt"],
            fg=self.COLORS["subtle"],
            font=("Microsoft JhengHei UI", 8),
            anchor="w",
        )
        if side:
            label.pack(side=side)
        else:
            label.grid(row=row, column=0, sticky="w")

    def _bind_events(self) -> None:
        self.model_name_var.trace_add("write", self._on_input_changed)
        self.serial_number_var.trace_add("write", self._on_serial_changed)
        self.password_var.trace_add("write", self._on_input_changed)

    def _on_serial_changed(self, *_args: object) -> None:
        if self._normalizing_serial:
            return
        raw = self.serial_number_var.get().upper()
        normalized = re.sub(r"[^A-Z0-9]", "", raw)[:5]
        if raw != normalized:
            self._normalizing_serial = True
            self.serial_number_var.set(normalized)
            self._normalizing_serial = False
        self._refresh_qr()

    def _on_input_changed(self, *_args: object) -> None:
        self._refresh_qr()

    @staticmethod
    def _validate_password_edit(proposed: str) -> bool:
        return len(proposed) <= PASSWORD_LENGTH

    def _validate(self) -> tuple[bool, str, str]:
        model_name = self.model_name_var.get().strip()
        serial_number = self.serial_number_var.get().strip().upper()
        password = self.password_var.get()
        ssid = f"{model_name}{serial_number}"

        if not model_name:
            return False, "請先輸入機台型號。", ssid
        if not SERIAL_PATTERN.fullmatch(serial_number):
            return False, "SN 必須是 5 碼英數字，例如 A1B2C。", ssid
        if utf8_length(ssid) > 32:
            return False, "SSID 最多 32 bytes，請縮短機台型號。", ssid
        if len(password) != PASSWORD_LENGTH:
            return False, f"Wi-Fi 密碼必須固定為 {PASSWORD_LENGTH} 碼。", ssid
        return True, "設定完成，可用手機掃描右側 QR Code。", ssid

    def _refresh_qr(self) -> None:
        is_valid, message, ssid = self._validate()
        self.ssid_var.set(ssid or "等待輸入機台資訊")
        self.status_var.set(message)
        self.status_label.configure(
            fg=self.COLORS["success"] if is_valid else self.COLORS["danger"]
        )

        if not is_valid:
            self.current_payload = ""
            self.current_image = None
            self.qr_photo = None
            self.qr_label.configure(image="", text="")
            self.result_var.set("請完成左側欄位後產生 QR Code")
            return

        password = self.password_var.get()
        payload = build_wifi_payload(ssid, password)
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_Q,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        image = qr.make_image(
            fill_color=self.COLORS["qr_dark"],
            back_color="#FFFFFF",
        ).convert("RGB")

        self.current_payload = payload
        self.current_image = image
        self.qr_photo = ImageTk.PhotoImage(image)
        self.qr_label.configure(image=self.qr_photo)
        self.result_var.set(f"SSID  {ssid}\nWPA/WPA2  ·  密碼 {len(password)} 碼")

    def _regenerate_password(self) -> None:
        self.password_var.set(generate_password())
        self._announce("已產生新的隨機密碼。")

    def _toggle_password(self) -> None:
        self.password_entry.configure(
            show="" if self.password_visible_var.get() else "•"
        )

    def _announce(self, message: str) -> None:
        self.status_var.set(message)
        self.status_label.configure(fg=self.COLORS["success"])
        self.after(2400, self._refresh_qr)

    def _copy_text(self, value: str, message: str) -> None:
        if not value:
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        self._announce(message)

    def _copy_ssid(self) -> None:
        valid, _, ssid = self._validate()
        if valid:
            self._copy_text(ssid, "SSID 已複製到剪貼簿。")

    def _copy_password(self) -> None:
        valid, _, _ = self._validate()
        if valid:
            self._copy_text(self.password_var.get(), "密碼已複製到剪貼簿。")

    def _copy_payload(self) -> None:
        if self.current_payload:
            self._copy_text(self.current_payload, "Wi-Fi 設定字串已複製。")

    def _download_png(self) -> None:
        if self.current_image is None:
            return
        _, _, ssid = self._validate()
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", ssid) or "wifi"
        file_path = filedialog.asksaveasfilename(
            title="儲存 Wi-Fi QR Code",
            defaultextension=".png",
            initialfile=f"{safe_name}-wifi-qr.png",
            filetypes=[("PNG 圖片", "*.png"), ("所有檔案", "*.*")],
        )
        if not file_path:
            return
        try:
            self.current_image.save(file_path, format="PNG")
        except OSError as exc:
            messagebox.showerror("儲存失敗", f"無法儲存檔案：\n{exc}")
            return
        self._announce(f"QR Code 已儲存：{Path(file_path).name}")

    @staticmethod
    def _rounded_rectangle(
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        **kwargs: object,
    ) -> None:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_mark(self, canvas: tk.Canvas) -> None:
        self._rounded_rectangle(
            canvas,
            2,
            2,
            45,
            45,
            10,
            fill=self.COLORS["accent"],
            outline="",
        )
        canvas.create_rectangle(14, 14, 20, 20, fill=self.COLORS["background"], outline="")
        canvas.create_rectangle(27, 14, 33, 20, fill=self.COLORS["background"], outline="")
        canvas.create_rectangle(14, 27, 20, 33, fill=self.COLORS["background"], outline="")
        canvas.create_line(27, 30, 34, 30, fill=self.COLORS["background"], width=3)
        canvas.create_line(31, 26, 31, 34, fill=self.COLORS["background"], width=3)


def main() -> None:
    app = WifiQrGenerator()
    app.mainloop()


if __name__ == "__main__":
    main()
