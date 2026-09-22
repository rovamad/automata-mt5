import os
import json
import subprocess
import time
import shutil
import threading
from datetime import datetime
from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkcalendar import DateEntry
import requests

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ─────────────────────────────────────────────────────────────────
#  AUTO-DETECTION
# ─────────────────────────────────────────────────────────────────

def find_mt5_executables():
    """Escanea ubicaciones comunes buscando terminal64.exe"""
    found = []
    pf_dirs = []
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432"):
        d = os.environ.get(env, "")
        if d and d not in pf_dirs:
            pf_dirs.append(d)
    for default in (r"C:\Program Files", r"C:\Program Files (x86)"):
        if default not in pf_dirs:
            pf_dirs.append(default)

    for pf in pf_dirs:
        if not os.path.isdir(pf):
            continue
        try:
            for folder in os.listdir(pf):
                exe = os.path.join(pf, folder, "terminal64.exe")
                if os.path.isfile(exe) and exe not in found:
                    found.append(exe)
        except Exception:
            pass
    return found


def find_mt5_data_paths():
    """Busca carpetas de datos de MT5 en %APPDATA%\\MetaQuotes\\Terminal\\"""
    found = []
    appdata = os.environ.get("APPDATA", "")
    terminal_base = os.path.join(appdata, "MetaQuotes", "Terminal")
    if not os.path.isdir(terminal_base):
        return found
    try:
        for guid in os.listdir(terminal_base):
            path = os.path.join(terminal_base, guid)
            if os.path.isdir(os.path.join(path, "MQL5", "Experts")):
                found.append(path)
    except Exception:
        pass
    return found


# ─────────────────────────────────────────────────────────────────
#  SETTINGS WINDOW
# ─────────────────────────────────────────────────────────────────

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configuración — MT5 Backtest Pro")
        self.geometry("640x460")
        self.minsize(640, 540)
        self.resizable(True, True)
        self.configure(fg_color="#0d0d0d")
        self.grab_set()
        self.lift()
        self.focus_force()

        # ── Header ──────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr, text="Configuración",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=20)

        # ── Footer (pack antes que tabs para que side=bottom funcione) ──
        ftr = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=62)
        ftr.pack(fill="x", side="bottom")
        ftr.pack_propagate(False)

        ctk.CTkButton(
            ftr, text="Guardar configuración",
            height=44, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00d9ff", hover_color="#00b8d4",
            text_color="#000000",
            command=self._save
        ).pack(side="right", padx=10, pady=(0,10))

        ctk.CTkButton(
            ftr, text="Cancelar",
            height=44, corner_radius=10,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", hover_color="#1e1e1e",
            border_width=1, border_color="#2a2a2a",
            text_color="#555555",
            command=self.destroy
        ).pack(side="right", padx=10, pady=(0,10))

        # ── Tabs ────────────────────────────────────────────────────────
        self.tabs = ctk.CTkTabview(
            self,
            fg_color="#141414",
            segmented_button_fg_color="#141414",
            segmented_button_selected_color="#00d9ff",
            segmented_button_selected_hover_color="#00b8d4",
            segmented_button_unselected_color="#1e1e1e",
            segmented_button_unselected_hover_color="#242424",
            text_color="#ffffff",
            corner_radius=0,
        )
        self.tabs.pack(fill="both", expand=True)
        self.tabs.add("MT5")
        self.tabs.add("Telegram")

        self._build_mt5_tab()
        self._build_telegram_tab()

    # ── Shared helpers ───────────────────────────────────────────────────

    def _sec_title(self, parent, title, subtitle=""):
        """Título de sección con subtítulo opcional."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(
            frame, text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#aaaaaa"
        ).pack(side="left")
        if subtitle:
            ctk.CTkLabel(
                frame, text=f"  ·  {subtitle}",
                font=ctk.CTkFont(size=11),
                text_color="#3a3a3a"
            ).pack(side="left", pady=(0,10))

    def _card(self, parent):
        """Card contenedor estilo glassmorphism oscuro."""
        c = ctk.CTkFrame(
            parent, fg_color="#181818",
            corner_radius=12,
            border_width=1, border_color="#272727"
        )
        c.pack(fill="x", pady=(0,10))
        return c

    def _field_lbl(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#555555"
        ).pack(anchor="w", padx=10, pady=(0,10))

    def _small_btn(self, parent, text, cmd):
        return ctk.CTkButton(
            parent, text=text, width=82, height=44, corner_radius=8,
            fg_color="#202020", hover_color="#2a2a2a",
            border_width=1, border_color="#2e2e2e",
            text_color="#00d9ff", font=ctk.CTkFont(size=12),
            command=cmd
        )

    def _styled_entry(self, parent, value, placeholder=""):
        e = ctk.CTkEntry(
            parent, height=44, corner_radius=8,
            fg_color="#202020", border_color="#2a2a2a",
            text_color="#ffffff", font=ctk.CTkFont(size=11),
            placeholder_text=placeholder
        )
        e.insert(0, value)
        return e

    def _styled_combo(self, parent, values):
        return ctk.CTkComboBox(
            parent, values=values, height=44, corner_radius=8,
            fg_color="#202020", border_color="#2a2a2a",
            button_color="#00d9ff", button_hover_color="#00b8d4",
            dropdown_fg_color="#1a1a1a", dropdown_hover_color="#252525",
            text_color="#ffffff", font=ctk.CTkFont(size=11)
        )

    # ── MT5 Tab ──────────────────────────────────────────────────────────

    _PLACEHOLDER = "Seleccione…"

    def _build_mt5_tab(self):
        tab = self.tabs.tab("MT5")
        conf = self.parent.conf

        content = ctk.CTkFrame(tab, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=4)

        # ── Ejecutable ───────────────────────────────────────────────────
        self._sec_title(content, "Ejecutable de MT5", "terminal64.exe")
        card1 = self._card(content)

        row_exe = ctk.CTkFrame(card1, fg_color="transparent")
        row_exe.pack(fill="x", padx=10, pady=8)
        row_exe.columnconfigure(0, weight=1)

        exes = find_mt5_executables()
        cur_exe = conf.get("mt5_path", "")
        self.combo_exes = self._styled_combo(row_exe, exes if exes else [self._PLACEHOLDER])
        self.combo_exes.set(cur_exe if cur_exe in exes else (exes[0] if exes else self._PLACEHOLDER))
        self.combo_exes.configure(command=self._check_exe)
        self.combo_exes.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.combo_exes.bind("<KeyRelease>", self._check_exe)
        self._small_btn(row_exe, "Buscar", self._browse_exe).grid(row=0, column=1, padx=(0, 8))
        self.lbl_exe_ok = ctk.CTkLabel(row_exe, text="", font=ctk.CTkFont(size=15), width=26)
        self.lbl_exe_ok.grid(row=0, column=2)
        self._check_exe()

        # ── Carpeta de datos ─────────────────────────────────────────────
        self._sec_title(content, "Carpeta de datos de MT5", "AppData / MetaQuotes / Terminal / GUID")
        card2 = self._card(content)

        row_data = ctk.CTkFrame(card2, fg_color="transparent")
        row_data.pack(fill="x", padx=10, pady=8)
        row_data.columnconfigure(0, weight=1)

        data_paths = find_mt5_data_paths()
        cur_data = conf.get("mt5_data_path", "")
        self.combo_data = self._styled_combo(row_data, data_paths if data_paths else [self._PLACEHOLDER])
        self.combo_data.set(cur_data if cur_data in data_paths else (data_paths[0] if data_paths else self._PLACEHOLDER))
        self.combo_data.configure(command=self._check_data)
        self.combo_data.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.combo_data.bind("<KeyRelease>", self._check_data)
        self._small_btn(row_data, "Buscar", self._browse_data).grid(row=0, column=1, padx=(0, 8))
        self.lbl_data_ok = ctk.CTkLabel(row_data, text="", font=ctk.CTkFont(size=15), width=26)
        self.lbl_data_ok.grid(row=0, column=2)
        self._check_data()

        # ── Carpeta de Reportes ────────────────────────────────────────────
        self._sec_title(content, "Carpeta de Reportes", "vacío = carpeta reports/")
        card3 = self._card(content)

        row_rep = ctk.CTkFrame(card3, fg_color="transparent")
        row_rep.pack(fill="x", padx=10, pady=8)
        row_rep.columnconfigure(0, weight=1)

        self.entry_reports = self._styled_entry(
            row_rep, self.parent.conf.get("reports_path", ""),
            "Ej: C:\\Reportes\\MT5  (vacío = carpeta reports/)"
        )
        self.entry_reports.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._small_btn(row_rep, "Buscar", self._browse_reports_path).grid(row=0, column=1)

    def _browse_exe(self):
        path = filedialog.askopenfilename(
            title="Seleccionar terminal64.exe",
            filetypes=[("MT5 executable", "terminal64.exe"), ("Ejecutables", "*.exe")]
        )
        if path:
            path = path.replace("/", "\\")
            values = [v for v in self.combo_exes.cget("values") if v != self._PLACEHOLDER]
            if path not in values:
                values.append(path)
            self.combo_exes.configure(values=values)
            self.combo_exes.set(path)
            self._check_exe()

    def _browse_data(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de datos de MT5")
        if path:
            path = path.replace("/", "\\")
            values = [v for v in self.combo_data.cget("values") if v != self._PLACEHOLDER]
            if path not in values:
                values.append(path)
            self.combo_data.configure(values=values)
            self.combo_data.set(path)
            self._check_data()

    def _browse_reports_path(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta donde guardar los informes")
        if path:
            self.entry_reports.delete(0, "end")
            self.entry_reports.insert(0, path.replace("/", "\\"))

    def _check_exe(self, *_):
        ok = os.path.isfile(self.combo_exes.get())
        self.lbl_exe_ok.configure(
            text="✓" if ok else "✗",
            text_color="#34d399" if ok else "#fb5a6f"
        )

    def _check_data(self, *_):
        ok = os.path.isdir(os.path.join(self.combo_data.get(), "MQL5", "Experts"))
        self.lbl_data_ok.configure(
            text="✓" if ok else "✗",
            text_color="#34d399" if ok else "#fb5a6f"
        )

    # ── Telegram Tab ──────────────────────────────────────────────────────

    def _build_telegram_tab(self):
        tab = self.tabs.tab("Telegram")
        tg = self.parent.conf.get("telegram", {})

        content = ctk.CTkFrame(tab, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=4)

        # Toggle card
        self._sec_title(content, "Estado")
        card_sw = self._card(content)
        sw_row = ctk.CTkFrame(card_sw, fg_color="transparent")
        sw_row.pack(fill="x", padx=10, pady=12)

        info = ctk.CTkFrame(sw_row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(info, text="Notificaciones de Telegram",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#ffffff").pack(anchor="w")
        ctk.CTkLabel(info, text="Recibe un aviso cuando el backtest termina",
                     font=ctk.CTkFont(size=11), text_color="#444444").pack(anchor="w", pady=(3, 0))

        self.tg_enabled = ctk.BooleanVar(value=tg.get("enabled", False))
        ctk.CTkSwitch(sw_row, text="", variable=self.tg_enabled,
                      progress_color="#00d9ff", width=52, height=26).pack(side="right")

        # Credentials card
        self._sec_title(content, "Credenciales del bot")
        card_creds = self._card(content)

        self._field_lbl(card_creds, "BOT TOKEN")
        self.entry_token = ctk.CTkEntry(
            card_creds, height=44, corner_radius=8, show="•",
            fg_color="#202020", border_color="#2a2a2a",
            text_color="#ffffff", font=ctk.CTkFont(size=12),
            placeholder_text="1234567890:AABBCCddeeff…"
        )
        self.entry_token.pack(fill="x", padx=10, pady=(0, 0))
        self.entry_token.insert(0, tg.get("bot_token", ""))

        self._field_lbl(card_creds, "CHAT ID")
        self.entry_chat = ctk.CTkEntry(
            card_creds, height=44, corner_radius=8,
            fg_color="#202020", border_color="#2a2a2a",
            text_color="#ffffff", font=ctk.CTkFont(size=12),
            placeholder_text="Tu chat ID numérico…"
        )
        self.entry_chat.pack(fill="x", padx=10)
        self.entry_chat.insert(0, tg.get("chat_id", ""))

        test_row = ctk.CTkFrame(card_creds, fg_color="transparent")
        test_row.pack(fill="x", padx=10, pady=(10, 12))

        self.btn_test = ctk.CTkButton(
            test_row, text="Enviar mensaje de prueba",
            height=40, corner_radius=8,
            fg_color="transparent", hover_color="#1e1e1e",
            border_width=1, border_color="#2a2a2a",
            text_color="#00d9ff", font=ctk.CTkFont(size=12),
            command=self._test_telegram
        )
        self.btn_test.pack(side="left")

        self.lbl_tg_result = ctk.CTkLabel(test_row, text="", font=ctk.CTkFont(size=12))
        self.lbl_tg_result.pack(side="left", padx=(14, 0))

    def _test_telegram(self):
        token = self.entry_token.get().strip()
        chat_id = self.entry_chat.get().strip()
        if not token or not chat_id:
            self.lbl_tg_result.configure(
                text="⚠  Completa el token y el Chat ID primero",
                text_color="#fbbf24"
            )
            return
        self.btn_test.configure(state="disabled", text="Enviando…")

        def _send():
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": chat_id, "text": "✅ MT5 Backtest Pro — conexión verificada correctamente."},
                    timeout=10
                )
                ok = r.status_code == 200
                self.lbl_tg_result.configure(
                    text="✓  Mensaje enviado correctamente" if ok else f"✗  Error {r.status_code}",
                    text_color="#34d399" if ok else "#fb5a6f"
                )
            except Exception as e:
                self.lbl_tg_result.configure(text=f"✗  {e}", text_color="#fb5a6f")
            finally:
                self.btn_test.configure(state="normal", text="Enviar mensaje de prueba")

        threading.Thread(target=_send, daemon=True).start()

    # ── Save ────────────────────────────────────────────────────────────

    def _save(self):
        conf = self.parent.conf
        exe_val = self.combo_exes.get().strip()
        conf["mt5_path"] = "" if exe_val == self._PLACEHOLDER else exe_val
        data_val = self.combo_data.get().strip()
        conf["mt5_data_path"] = "" if data_val == self._PLACEHOLDER else data_val
        conf["reports_path"]  = self.entry_reports.get().strip()
        conf["telegram"]["enabled"]   = self.tg_enabled.get()
        conf["telegram"]["bot_token"] = self.entry_token.get().strip()
        conf["telegram"]["chat_id"]   = self.entry_chat.get().strip()
        self.parent.save_config()
        self.parent.on_settings_saved()
        self.destroy()


# ─────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────

class BacktestGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MT5 Backtest Pro")
        self.geometry("760x780")
        self.minsize(780, 620)
        self.configure(fg_color=("#0f0f0f", "#0a0a0a"))

        self.load_config()
        self.stop_event = threading.Event()
        self.current_proc = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()  # row 0 (fijo)

        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(3, weight=1)

        self._build_setup_banner()    # content row 0 (oculto si está configurado)
        self._build_config_panel()    # content row 1
        self._build_advanced_panel()  # content row 2 (colapsado por defecto)
        self._build_log()             # content row 3
        self._build_run_button()      # content row 4

        self._update_banner()

    # ── HEADER ───────────────────────────────────────────────────

    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, padx=28, pady=(22, 12), sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left, text="MT5 Backtest Pro",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=("#ffffff", "#ffffff")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left, text="Automated backtesting system",
            font=ctk.CTkFont(size=13),
            text_color=("#555555", "#555555")
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        right = ctk.CTkFrame(frame, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")

        self.lbl_config_status = ctk.CTkLabel(
            right, text="",
            font=ctk.CTkFont(size=12),
            text_color=("#666666", "#666666")
        )
        self.lbl_config_status.grid(row=0, column=0, padx=(0, 16))

        ctk.CTkButton(
            right, text="⚙  Configuración",
            height=40, corner_radius=10,
            fg_color=("#1a1a1a", "#141414"),
            hover_color=("#252525", "#1f1f1f"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            text_color=("#00d9ff", "#00d9ff"),
            font=ctk.CTkFont(size=13),
            command=self._open_settings
        ).grid(row=0, column=1)

    # ── SETUP BANNER ─────────────────────────────────────────────

    def _build_setup_banner(self):
        self.frame_banner = ctk.CTkFrame(
            self.content,
            fg_color=("#1a0e0e", "#140a0a"),
            corner_radius=12,
            border_width=1,
            border_color=("#fb5a6f", "#e02d4a")
        )
        self.frame_banner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.frame_banner,
            text="⚠  Configuración incompleta — MT5 no está configurado correctamente.",
            font=ctk.CTkFont(size=13),
            text_color=("#fb5a6f", "#fb5a6f")
        ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        ctk.CTkButton(
            self.frame_banner, text="Configurar ahora →",
            height=34, corner_radius=8,
            fg_color="transparent", hover_color=("#2a1414", "#201010"),
            border_width=1, border_color=("#fb5a6f", "#e02d4a"),
            text_color=("#fb5a6f", "#fb5a6f"), font=ctk.CTkFont(size=12),
            command=self._open_settings
        ).grid(row=0, column=1, padx=(0, 16), pady=10)

    def _update_banner(self):
        if self._is_configured():
            self.frame_banner.grid_remove()
            self.lbl_config_status.configure(
                text="●  MT5 configurado",
                text_color=("#34d399", "#34d399")
            )
        else:
            self.frame_banner.grid(row=0, column=0, padx=28, pady=(12, 12), sticky="ew")
            self.lbl_config_status.configure(
                text="●  Sin configurar",
                text_color=("#fb5a6f", "#fb5a6f")
            )
        # Refresh folder list
        self.carpetas_disponibles = self.detectar_carpetas()
        if self.carpetas_disponibles:
            self.combo_folder.configure(values=self.carpetas_disponibles)
            cur = self.conf.get("ea_folder", "")
            self.combo_folder.set(cur if cur in self.carpetas_disponibles else self.carpetas_disponibles[0])
        else:
            self.combo_folder.configure(values=["— no se encontraron carpetas —"])
            self.combo_folder.set("— no se encontraron carpetas —")

    def _is_configured(self):
        exe  = self.conf.get("mt5_path", "")
        data = self.conf.get("mt5_data_path", "")
        return (
            os.path.isfile(exe) and
            os.path.isdir(os.path.join(data, "MQL5", "Experts"))
        )

    # ── CONFIG PANEL ─────────────────────────────────────────────

    def _build_config_panel(self):
        frame = ctk.CTkFrame(self.content, fg_color=("#1a1a1a", "#141414"), corner_radius=16)
        frame.grid(row=1, column=0, padx=28, pady=(12, 12), sticky="ew")
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        # EA Folder
        self._slbl(frame, "Expert Advisor Folder", 0, 0)
        row_folder = ctk.CTkFrame(frame, fg_color="transparent")
        row_folder.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        row_folder.grid_columnconfigure(0, weight=1)

        self.carpetas_disponibles = self.detectar_carpetas()
        self.combo_folder = ctk.CTkComboBox(
            row_folder,
            values=self.carpetas_disponibles if self.carpetas_disponibles else ["— no se encontraron carpetas —"],
            height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        ea = self.conf.get("ea_folder", "")
        self.combo_folder.set(ea if ea in self.carpetas_disponibles else (self.carpetas_disponibles[0] if self.carpetas_disponibles else "— no se encontraron carpetas —"))
        self.combo_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row_folder, text="↻", width=40, height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), hover_color=("#2a2a2a", "#252525"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            font=ctk.CTkFont(size=18), text_color=("#666666", "#666666"),
            command=self.refrescar_carpetas
        ).grid(row=0, column=1)

        # Symbol
        self._slbl(frame, "Symbol", 0, 1)
        self.combo_symbol = ctk.CTkComboBox(
            frame,
            values=["EURUSD", "GBPUSD", "GDAXI", "NDX", "USDCHF", "USDJPY", "WS30", "XAUUSD", "XTIUSD"],
            height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        self.combo_symbol.set(self.conf["common_settings"].get("symbol", "XAUUSD"))
        self.combo_symbol.grid(row=1, column=1, padx=10, pady=(0,10), sticky="ew")

        # Timeframe
        self._slbl(frame, "Timeframe", 0, 2)
        self.combo_period = ctk.CTkComboBox(
            frame,
            values=["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"],
            height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        self.combo_period.set(self.conf["common_settings"].get("period", "H1"))
        self.combo_period.grid(row=1, column=2, padx=10, pady=(0,10), sticky="ew")

        # Dates
        self._slbl(frame, "Start Date", 3, 0)
        fr_from = ctk.CTkFrame(frame, fg_color=("#252525", "#1f1f1f"), corner_radius=10, border_width=1, border_color=("#2a2a2a", "#252525"))
        fr_from.grid(row=4, column=0, padx=10, pady=(0,10), sticky="ew")
        self.date_from = DateEntry(fr_from, width=30, background="#1f1f1f", foreground="white", borderwidth=0, font=("Arial", 11), date_pattern="yyyy.mm.dd", year=2020, month=1, day=1)
        self.date_from.pack(padx=10, pady=8, fill="x")

        self._slbl(frame, "End Date", 3, 1)
        fr_to = ctk.CTkFrame(frame, fg_color=("#252525", "#1f1f1f"), corner_radius=10, border_width=1, border_color=("#2a2a2a", "#252525"))
        fr_to.grid(row=4, column=1, padx=10, pady=(0,10), sticky="ew")
        self.date_to = DateEntry(fr_to, width=30, background="#1f1f1f", foreground="white", borderwidth=0, font=("Arial", 11), date_pattern="yyyy.mm.dd", year=2025, month=12, day=28)
        self.date_to.pack(padx=10, pady=8, fill="x")

        ctk.CTkButton(
            frame, text="Use Default Range",
            height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), hover_color=("#2a2a2a", "#252525"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            text_color=("#666666", "#666666"), font=ctk.CTkFont(size=12),
            command=self.set_default_dates
        ).grid(row=4, column=2, padx=10, pady=(0,10), sticky="ew")

    def _slbl(self, parent, text, row, col):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#666666", "#666666")
        ).grid(row=row, column=col, padx=10, pady=(18, 6), sticky="w")

    # ── ADVANCED SETTINGS PANEL ─────────────────────────────────────

    MODEL_OPTIONS = [
        ("Cada tick (Every tick)", 0),
        ("OHLC 1 minuto (1 minute OHLC)", 1),
        ("Solo precio de apertura (Open prices only)", 2),
        ("Cálculos matemáticos (Math calculations)", 3),
        ("Cada tick — ticks reales (Every tick based on real ticks)", 4),
    ]

    def _build_advanced_panel(self):
        adv = self.conf.get("advanced", {})
        cs = self.conf.get("common_settings", {})

        wrapper = ctk.CTkFrame(self.content, fg_color="transparent")
        wrapper.grid(row=2, column=0, padx=28, pady=(0, 12), sticky="ew")
        wrapper.grid_columnconfigure(0, weight=1)

        self.btn_toggle_advanced = ctk.CTkButton(
            wrapper, text="▸  Ajustes Avanzados",
            height=32, corner_radius=10, anchor="w",
            fg_color=("#161616", "#121212"), hover_color=("#1e1e1e", "#191919"),
            border_width=1, border_color=("#2a2a2a", "#252525"),
            text_color=("#888888", "#888888"), font=ctk.CTkFont(size=12, weight="bold"),
            command=self._toggle_advanced_panel
        )
        self.btn_toggle_advanced.grid(row=0, column=0, sticky="ew")

        self.frame_advanced = ctk.CTkFrame(
            wrapper, fg_color=("#1a1a1a", "#141414"), corner_radius=16
        )
        self.frame_advanced.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self._advanced_visible = False

        pad = dict(padx=(18, 10), pady=(0, 16))

        # Deposit
        self._slbl(self.frame_advanced, "Depósito (USD)", 0, 0)
        self.entry_deposit = ctk.CTkEntry(
            self.frame_advanced, height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        self.entry_deposit.insert(0, str(cs.get("deposit", 100000)))
        self.entry_deposit.grid(row=1, column=0, sticky="ew", **pad)

        # Leverage
        self._slbl(self.frame_advanced, "Apalancamiento", 0, 1)
        self.entry_leverage = ctk.CTkEntry(
            self.frame_advanced, height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13),
            placeholder_text="Ej: 1:100"
        )
        self.entry_leverage.insert(0, str(cs.get("leverage", "1:1")))
        self.entry_leverage.grid(row=1, column=1, sticky="ew", **pad)

        # Modelling
        self._slbl(self.frame_advanced, "Modelado", 0, 2)
        self.combo_model = ctk.CTkComboBox(
            self.frame_advanced,
            values=[label for label, _ in self.MODEL_OPTIONS],
            height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            button_color=("#00d9ff", "#00d9ff"), button_hover_color=("#00b8d4", "#00b8d4"),
            dropdown_fg_color=("#252525", "#1f1f1f"), dropdown_hover_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13)
        )
        model_code = adv.get("model", 1)
        model_label = next((l for l, c in self.MODEL_OPTIONS if c == model_code), self.MODEL_OPTIONS[1][0])
        self.combo_model.set(model_label)
        self.combo_model.grid(row=1, column=2, sticky="ew", **pad)

        # Delay
        self._slbl(self.frame_advanced, "Delay (ms)", 0, 3)
        self.entry_delay = ctk.CTkEntry(
            self.frame_advanced, height=40, corner_radius=10,
            fg_color=("#252525", "#1f1f1f"), border_color=("#2a2a2a", "#252525"),
            text_color=("#ffffff", "#ffffff"), font=ctk.CTkFont(size=13),
            placeholder_text="0, -1, >0"
        )
        self.entry_delay.insert(0, str(adv.get("delay_ms", 0)))
        self.entry_delay.grid(row=1, column=3, sticky="ew", **pad)

        # Visual mode
        self._slbl(self.frame_advanced, "Modo visual", 0, 4)
        self.var_visual_mode = ctk.BooleanVar(value=adv.get("visual_mode", False))
        ctk.CTkSwitch(
            self.frame_advanced, text="", variable=self.var_visual_mode,
            progress_color="#00d9ff", width=52, height=26
        ).grid(row=1, column=4, sticky="w", padx=(18, 10), pady=(0, 16))

    def _toggle_advanced_panel(self):
        self._advanced_visible = not self._advanced_visible
        if self._advanced_visible:
            self.frame_advanced.grid(row=1, column=0, sticky="ew", pady=(8, 0))
            self.btn_toggle_advanced.configure(text="▾  Ajustes Avanzados")
        else:
            self.frame_advanced.grid_remove()
            self.btn_toggle_advanced.configure(text="▸  Ajustes Avanzados")

    def _collect_run_settings(self):
        label = self.combo_model.get()
        model_code = next((c for l, c in self.MODEL_OPTIONS if l == label), 1)
        try:
            delay_ms = int(self.entry_delay.get().strip() or "0")
        except ValueError:
            delay_ms = 0
        try:
            deposit = int(self.entry_deposit.get().strip())
        except ValueError:
            deposit = self.conf.get("common_settings", {}).get("deposit", 100000)
        leverage = self.entry_leverage.get().strip() or "1:100"
        return {
            "model": model_code,
            "no_leverage": self.var_no_leverage.get(),
            "delay_ms": delay_ms,
            "visual_mode": self.var_visual_mode.get(),
            "deposit": deposit,
            "leverage": leverage,
            "reports_path": self.conf.get("reports_path", ""),
        }

    # ── LOG ──────────────────────────────────────────────────────

    def _build_log(self):
        frame = ctk.CTkFrame(self.content, fg_color=("#1a1a1a", "#141414"), corner_radius=16, height=180)
        frame.grid(row=3, column=0, padx=28, pady=(0, 12), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_propagate(False)

        ctk.CTkLabel(
            frame, text="Activity Log",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#ffffff", "#ffffff")
        ).grid(row=0, column=0, padx=10, pady=(16, 8), sticky="w")

        self.logbox = ctk.CTkTextbox(
            frame, font=("Courier", 11),
            fg_color=("#0f0f0f", "#0a0a0a"),
            text_color=("#00d9ff", "#00d9ff"),
            corner_radius=10, border_width=0
        )
        self.logbox.grid(row=1, column=0, padx=10, pady=(0, 16), sticky="nsew")
        self.logbox.configure(state="disabled")

    # ── RUN BUTTON ───────────────────────────────────────────────

    def _build_run_button(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.grid(row=4, column=0, padx=28, pady=(0, 16), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        self.btn = ctk.CTkButton(
            frame, text="Start Backtest",
            height=48, corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=("#00d9ff", "#00d9ff"),
            hover_color=("#00b8d4", "#00b8d4"),
            text_color=("#000000", "#000000"),
            command=self.start_thread
        )
        self.btn.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            frame, text="Detener",
            height=48, width=130, corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=("#2a1414", "#201010"),
            hover_color=("#3a1a1a", "#2a1515"),
            border_width=1, border_color=("#fb5a6f", "#e02d4a"),
            text_color=("#fb5a6f", "#fb5a6f"),
            state="disabled",
            command=self.stop_backtests
        )
        self.btn_stop.grid(row=0, column=1, sticky="ew")

    # ── HELPERS ──────────────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(self)

    def on_settings_saved(self):
        self._update_banner()
        self.log("✓ Configuración guardada correctamente")

    def set_default_dates(self):
        self.date_from.set_date(datetime(2020, 1, 1))
        self.date_to.set_date(datetime(2025, 12, 28))
        self.log("Default date range applied: 2020.01.01 - 2025.12.28")

    def detectar_carpetas(self):
        try:
            ruta_experts = os.path.join(self.conf.get("mt5_data_path", ""), "MQL5", "Experts")
            if not os.path.isdir(ruta_experts):
                return []
            carpetas = []
            for root, dirs, files in os.walk(ruta_experts):
                if any(f.endswith(".ex5") for f in files):
                    rel = os.path.relpath(root, ruta_experts)
                    if rel != ".":
                        carpetas.append(rel)
            return sorted(carpetas)
        except Exception:
            return []

    def refrescar_carpetas(self):
        self.carpetas_disponibles = self.detectar_carpetas()
        if self.carpetas_disponibles:
            self.combo_folder.configure(values=self.carpetas_disponibles)
            self.combo_folder.set(self.carpetas_disponibles[0])
            self.log("Folders refreshed")
        else:
            self.combo_folder.configure(values=["— no se encontraron carpetas —"])
            self.combo_folder.set("— no se encontraron carpetas —")
            self.log("No .ex5 folders found")

    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                self.conf = json.load(f)
            self.conf.setdefault("mt5_data_path", "")
            self.conf.setdefault("reports_path", "")
            self.conf.setdefault("telegram", {"enabled": False, "bot_token": "", "chat_id": ""})
        except Exception:
            self.conf = {
                "mt5_path": "", "mt5_data_path": "", "ea_folder": "",
                "common_settings": {
                    "deposit": 100000, "currency": "USD",
                    "leverage": "1:100", "symbol": "XAUUSD", "period": "H1"
                },
                "telegram": {"enabled": False, "bot_token": "", "chat_id": ""}
            }
        self.conf.setdefault("advanced", {
            "model": 1,
            "no_leverage": False,
            "delay_ms": 0,
            "visual_mode": False,
        })

    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.conf, f, indent=2, ensure_ascii=False)

    def log(self, text):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", f"{time.strftime('%H:%M:%S')} → {text}\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def send_telegram_message(self, message):
        try:
            tg = self.conf.get("telegram", {})
            if not tg.get("enabled") or not tg.get("bot_token") or not tg.get("chat_id"):
                return False
            r = requests.post(
                f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage",
                data={"chat_id": tg["chat_id"], "text": message, "parse_mode": "HTML"},
                timeout=10
            )
            return r.status_code == 200
        except Exception:
            return False

    # ── RUN BACKTESTS ────────────────────────────────────────────

    def start_thread(self):
        if not self._is_configured():
            messagebox.showwarning(
                "Sin configurar",
                "Configura la ruta de MT5 antes de correr backtests.\nUsa el botón ⚙ Configuración."
            )
            return
        self.stop_event.clear()
        threading.Thread(target=self.run_backtests, daemon=True).start()

    def stop_backtests(self):
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        self.btn_stop.configure(state="disabled", text="Deteniendo…")
        self.log("⏹ Deteniendo backtest tras el EA actual…")
        proc = self.current_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def run_backtests(self):
        self.btn.configure(
            state="disabled", text="Processing…",
            fg_color=("#2a2a2a", "#252525"), text_color=("#666666", "#666666")
        )
        self.btn_stop.configure(state="normal", text="Detener")
        settings = self._collect_run_settings()
        self.conf["advanced"] = {
            "model": settings["model"],
            "no_leverage": settings["no_leverage"],
            "delay_ms": settings["delay_ms"],
            "visual_mode": settings["visual_mode"],
        }
        self.conf["common_settings"]["deposit"] = settings["deposit"]
        self.conf["common_settings"]["leverage"] = settings["leverage"]
        self.conf["reports_path"] = settings["reports_path"]
        self.save_config()
        start_time = time.time()
        exitosos = fallidos = 0
        detenido = False

        try:
            ruta_rep = settings["reports_path"]
            carpeta_final = ruta_rep if ruta_rep else os.path.abspath("reports")
            os.makedirs(carpeta_final, exist_ok=True)
            self.log(f"Guardando informes en: {carpeta_final}")

            ruta_mt5    = self.conf.get("mt5_data_path", "")
            ruta_experts = os.path.join(ruta_mt5, "MQL5", "Experts", self.combo_folder.get())
            ruta_files   = os.path.join(ruta_mt5, "MQL5", "Files")

            if not os.path.exists(ruta_experts):
                self.log(f"Error: carpeta no encontrada → {ruta_experts}")
                return

            expertos = [f for f in os.listdir(ruta_experts) if f.endswith(".ex5")]
            total = len(expertos)
            self.log(f"Found {total} Expert Advisors")
            self.log("─" * 50)

            self.send_telegram_message(
                f"🚀 <b>MT5 Backtest Started</b>\n\n"
                f"📊 Total EAs: {total}\n"
                f"💱 Symbol: {self.combo_symbol.get()}\n"
                f"⏰ Timeframe: {self.combo_period.get()}\n"
                f"📅 Period: {self.date_from.get_date().strftime('%Y.%m.%d')} - {self.date_to.get_date().strftime('%Y.%m.%d')}"
            )

            leverage = "1:1" if settings["no_leverage"] else settings["leverage"]
            visual_flag = 1 if settings["visual_mode"] else 0

            for idx, ea in enumerate(expertos, 1):
                if self.stop_event.is_set():
                    detenido = True
                    self.log("⏹ Backtest detenido por el usuario")
                    break

                self.log(f"[{idx}/{total}] Testing → {ea}")
                nombre_temp = "reporte.html"
                for r in [os.path.join(ruta_files, nombre_temp), os.path.join(ruta_mt5, nombre_temp)]:
                    if os.path.exists(r):
                        os.remove(r)

                ini_content = (
                    "[Tester]\n"
                    f'Expert="{self.combo_folder.get()}\\{ea}"\n'
                    f"Symbol={self.combo_symbol.get()}\n"
                    f"Period={self.combo_period.get()}\n"
                    f"Deposit={settings['deposit']}\n"
                    f"Leverage={leverage}\n"
                    f"Model={settings['model']}\n"
                    f"ExecutionMode={settings['delay_ms']}\n"
                    f"FromDate={self.date_from.get_date().strftime('%Y.%m.%d')}\n"
                    f"ToDate={self.date_to.get_date().strftime('%Y.%m.%d')}\n"
                    f"Report={nombre_temp}\nReplaceReport=1\nShutdownTerminal=1\nVisual={visual_flag}\n"
                )

                ini_path = os.path.abspath("config_batch.ini")
                with open(ini_path, "w", encoding="utf-16") as f:
                    f.write(ini_content)

                self.current_proc = subprocess.Popen(
                    [self.conf["mt5_path"], f"/config:{ini_path}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                while self.current_proc.poll() is None:
                    if self.stop_event.is_set():
                        try:
                            self.current_proc.terminate()
                        except Exception:
                            pass
                        break
                    time.sleep(0.3)
                self.current_proc = None

                if self.stop_event.is_set():
                    detenido = True
                    self.log("⏹ Backtest detenido por el usuario")
                    break

                encontrado = False
                for _ in range(15):
                    time.sleep(1)
                    for origen in [os.path.join(ruta_files, nombre_temp), os.path.join(ruta_mt5, nombre_temp)]:
                        if os.path.exists(origen):
                            destino = os.path.join(carpeta_final, ea.replace(".ex5", ".html"))
                            shutil.move(origen, destino)
                            self.log(f"  ✓ {ea.replace('.ex5', '.html')}")
                            exitosos += 1
                            encontrado = True
                            break
                    if encontrado:
                        break

                if not encontrado:
                    self.log("  ✗ Report not generated")
                    fallidos += 1

            tiempo_total = int(time.time() - start_time)
            mins, secs = tiempo_total // 60, tiempo_total % 60
            self.log("─" * 50)
            estado = "Detenido" if detenido else "Completed"
            self.log(f"{estado} → {exitosos} OK, {fallidos} failed — {mins}m {secs}s")

            self.send_telegram_message(
                f"{'⏹' if detenido else ('✅' if fallidos == 0 else '⚠️')} "
                f"<b>Backtest {'Detenido' if detenido else 'Completed'}!</b>\n\n"
                f"✅ Successful: {exitosos}\n❌ Failed: {fallidos}\n"
                f"⏱ Time: {mins}m {secs}s\n"
                f"💱 {self.combo_symbol.get()} {self.combo_period.get()}"
            )
            if detenido:
                messagebox.showinfo("Detenido", f"Backtest detenido · {exitosos} EAs procesados · {fallidos} fallidos")
            else:
                messagebox.showinfo("Completado", f"{exitosos} EAs procesados · {fallidos} fallidos")

        except Exception as e:
            self.log(f"Error crítico → {e}")
            self.send_telegram_message(f"❌ <b>Error en backtest</b>\n{e}\n✅ {exitosos}  ❌ {fallidos}")
            messagebox.showerror("Error", str(e))
        finally:
            self.current_proc = None
            self.stop_event.clear()
            self.btn.configure(
                state="normal", text="Start Backtest",
                fg_color=("#00d9ff", "#00d9ff"), text_color=("#000000", "#000000")
            )
            self.btn_stop.configure(state="disabled", text="Detener")


if __name__ == "__main__":
    app = BacktestGUI()
    app.mainloop()
