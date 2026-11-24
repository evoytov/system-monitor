"""
SYSTEM MONITOR — прозрачный оверлей-виджет для Windows.
Зависимости: PyQt6 / psutil / nvidia-ml-py.

Запуск:    python monitor.py   (или SystemMonitor.exe в портативной сборке)
Настройки: шестерёнка в правом верхнем углу виджета
Хоткей:    Ctrl+Alt+H — скрыть/показать
Мышь:      перетаскивание за любую точку, правый клик — то же меню
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import json
import os
import sys
import threading
import time
from datetime import datetime

import psutil
from PyQt6.QtCore import QPoint, QRect, QRectF, QSize, QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

try:
    import winreg
except ImportError:  # не Windows
    winreg = None

HERE = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
SETTINGS_PATH = os.path.join(HERE, "settings.json")
LOG_PATH = os.path.join(HERE, "events.log")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "HermesSystemMonitor"

APP_NAME = "System Monitor"
APP_VERSION = "1.03"
APP_IDEA = "Evgeniy_RED"
APP_IMPL = "DeepSeek V4.1-Flash 1017"

# --------------------------------------------------------------- переводы ---
TEXTS = {
    "ru": {
        "sec_gpu": "Видеокарта", "sec_cpu": "Процессор", "sec_mem": "Память",
        "sec_disk": "Диск", "sec_net": "Интернет", "sec_misc": "Прочее",

        "f_gpu_load": "Загрузка GPU", "f_vram": "Видеопамять",
        "f_gpu_temp": "Температура GPU", "f_gpu_power": "Питание GPU",
        "f_gpu_clock": "Частота ядра", "f_gpu_fan": "Кулер GPU",
        "f_cpu_load": "Загрузка CPU", "f_cpu_temp": "Температура CPU",
        "f_cpu_freq": "Частота CPU",
        "f_ram": "Оперативная память", "f_ram_free": "Свободно ОЗУ",
        "f_disk": "Диск C:", "f_disk_io": "Скорость диска",
        "f_net_speed": "Скорость сети", "f_net_total": "Трафик за сессию",
        "f_clock": "Часы",

        "t_gpu_load": "ЗАГРУЗКА GPU", "t_vram": "ВИДЕОПАМЯТЬ",
        "t_gpu_temp": "ТЕМПЕРАТУРА GPU", "t_gpu_power": "ПИТАНИЕ GPU",
        "t_gpu_clock": "ЧАСТОТА ЯДРА", "t_gpu_fan": "КУЛЕР GPU",
        "t_cpu_load": "ПРОЦЕССОР", "t_cpu_temp": "ТЕМПЕРАТУРА CPU",
        "t_cpu_freq": "ЧАСТОТА CPU",
        "t_ram": "ОПЕРАТИВНАЯ ПАМЯТЬ", "t_ram_free": "СВОБОДНО ОЗУ",
        "t_disk": "ДИСК C:", "t_disk_io": "ДИСК: ЧТЕНИЕ / ЗАПИСЬ",
        "t_net_speed": "СЕТЬ: ↓ / ↑", "t_net_total": "ТРАФИК ЗА СЕССИЮ",
        "t_clock": "ВРЕМЯ",

        "m_all_on": "Выбрать всё", "m_all_off": "Снять все галочки",
        "m_reset": "Сбросить настройки",
        "m_autostart": "Запускать при входе в Windows",
        "m_hide": "Скрыть (Ctrl+Alt+H)", "m_quit": "Выход",
        "m_show": "Показать / скрыть", "m_settings": "Настройки",
        "m_notify": "Всплывающие уведомления",
        "m_openlog": "Открыть журнал событий",

        "tip_gear": "Что показывать", "tip_about": "О виджете",
        "tip_lang": "Язык / Language",
        "tip_freeram": "Освободить память (сжать рабочие наборы процессов)",
        "msg_freed": "Освобождено", "msg_nothing": "Освобождать нечего",

        "about_idea": "Concept by", "about_dev": "Developed by",

        "a_gpu_temp": "Температура GPU", "a_cpu_temp": "Температура CPU",
        "lvl_warn": "высокая", "lvl_crit": "критическая",
        "tip_cputemp": "температура — из HWiNFO (должен быть запущен)",

        "u_gb": "ГБ", "u_watt": "Вт", "u_mhz": "МГц",
        "u_mbits": "Мбит/с", "u_mbs": "МБ/с",
        "v_nodata": "нет данных",
    },
    "en": {
        "sec_gpu": "Graphics card", "sec_cpu": "Processor", "sec_mem": "Memory",
        "sec_disk": "Disk", "sec_net": "Network", "sec_misc": "Other",

        "f_gpu_load": "GPU load", "f_vram": "Video memory",
        "f_gpu_temp": "GPU temperature", "f_gpu_power": "GPU power",
        "f_gpu_clock": "Core clock", "f_gpu_fan": "GPU fan",
        "f_cpu_load": "CPU load", "f_cpu_temp": "CPU temperature",
        "f_cpu_freq": "CPU clock",
        "f_ram": "RAM", "f_ram_free": "Free RAM",
        "f_disk": "Disk C:", "f_disk_io": "Disk activity",
        "f_net_speed": "Network speed", "f_net_total": "Session traffic",
        "f_clock": "Clock",

        "t_gpu_load": "GPU LOAD", "t_vram": "VRAM",
        "t_gpu_temp": "GPU TEMP", "t_gpu_power": "GPU POWER",
        "t_gpu_clock": "CORE CLOCK", "t_gpu_fan": "GPU FAN",
        "t_cpu_load": "CPU", "t_cpu_temp": "CPU TEMP",
        "t_cpu_freq": "CPU CLOCK",
        "t_ram": "MEMORY", "t_ram_free": "FREE RAM",
        "t_disk": "DISK C:", "t_disk_io": "DISK READ / WRITE",
        "t_net_speed": "NET ↓ / ↑", "t_net_total": "SESSION TRAFFIC",
        "t_clock": "TIME",

        "m_all_on": "Select all", "m_all_off": "Clear all",
        "m_reset": "Reset to defaults",
        "m_autostart": "Run at Windows startup",
        "m_hide": "Hide (Ctrl+Alt+H)", "m_quit": "Quit",
        "m_show": "Show / hide", "m_settings": "Settings",
        "m_notify": "Tray notifications",
        "m_openlog": "Open event log",

        "tip_gear": "What to show", "tip_about": "About",
        "tip_lang": "Language / Язык",
        "tip_freeram": "Free memory (trim process working sets)",
        "msg_freed": "Freed", "msg_nothing": "Nothing to free",

        "about_idea": "Concept by", "about_dev": "Developed by",

        "a_gpu_temp": "GPU temperature", "a_cpu_temp": "CPU temperature",
        "lvl_warn": "high", "lvl_crit": "critical",
        "tip_cputemp": "CPU temperature comes from HWiNFO (must be running)",

        "u_gb": "GB", "u_watt": "W", "u_mhz": "MHz",
        "u_mbits": "Mbit/s", "u_mbs": "MB/s",
        "v_nodata": "no data",
    },
}
LANGS = ("ru", "en")


def tr(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["ru"]).get(key, key)


# ширина виджета: тянется мышью за боковые края
MIN_W, MAX_W, DEFAULT_W = 260, 440, 300
EDGE = 6  # зона захвата у края, px

# В журнал и уведомления пишем ТОЛЬКО температуры. Нагрузка 100 % — это
# нормальная работа рендера на часы, лог от неё превращается в мусор.
# Перегрев — событие редкое и важное. Два уровня: высокая и критическая.
HYST_TEMP = 3.0  # возврат в норму только ниже порога на столько градусов

# ---------------------------------------------------------------- палитра ---
BG      = QColor(18, 18, 22, 208)
BORDER  = QColor(255, 255, 255, 26)
TEXT    = QColor(242, 242, 247)
MUTED   = QColor(142, 142, 152)
TRACK   = QColor(255, 255, 255, 20)

GRAD_GPU  = (QColor("#ff6b5b"), QColor("#ffab3d"))
GRAD_CPU  = (QColor("#4ecdc4"), QColor("#3d9bff"))
GRAD_RAM  = (QColor("#a78bfa"), QColor("#6d7cf7"))
GRAD_VRAM = (QColor("#ff8fab"), QColor("#c56cf0"))
GRAD_DISK = (QColor("#7ed957"), QColor("#3fb6a8"))
GRAD_NET  = (QColor("#5ad1ff"), QColor("#7b8cff"))
GRAD_PWR  = (QColor("#ffd166"), QColor("#ef476f"))
GRAD_FAN  = (QColor("#9be7ff"), QColor("#5a9bff"))
GRAD_TEMP = (QColor("#ffb37b"), QColor("#ff5e5b"))

# ------------------------------------------------------------- настройки ----
DEFAULTS = {
    "gpu_load":  True,
    "vram":      True,
    "gpu_temp":  True,
    "gpu_power": True,
    "gpu_clock": False,
    "gpu_fan":   False,
    "cpu_load":  True,
    "cpu_temp":  True,
    "cpu_freq":  False,
    "ram":       True,
    "ram_free":  False,
    "disk":      False,
    "disk_io":   False,
    "net_speed": False,
    "net_total": False,
    "clock":     False,
}

SECTIONS = [
    ("gpu",  ["gpu_load", "vram", "gpu_temp", "gpu_power", "gpu_clock", "gpu_fan"]),
    ("cpu",  ["cpu_load", "cpu_temp", "cpu_freq"]),
    ("mem",  ["ram", "ram_free"]),
    ("disk", ["disk", "disk_io"]),
    ("net",  ["net_speed", "net_total"]),
    ("misc", ["clock"]),
]


def load_settings() -> tuple[dict, dict]:
    data = dict(DEFAULTS)
    ui = {"lang": "ru", "width": DEFAULT_W, "pos": None, "notify": True}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            stored = json.load(f)
        for k in DEFAULTS:
            if k in stored:
                data[k] = bool(stored[k])
        if stored.get("lang") in LANGS:
            ui["lang"] = stored["lang"]
        w = stored.get("width")
        if isinstance(w, int) and MIN_W <= w <= MAX_W:
            ui["width"] = w
        x, y = stored.get("x"), stored.get("y")
        if isinstance(x, int) and isinstance(y, int):
            ui["pos"] = (x, y)
        if isinstance(stored.get("notify"), bool):
            ui["notify"] = stored["notify"]
    except (FileNotFoundError, ValueError, OSError):
        pass
    return data, ui


def save_settings(data: dict, ui: dict) -> None:
    payload = {k: bool(data.get(k, DEFAULTS[k])) for k in DEFAULTS}
    payload["lang"] = ui.get("lang") if ui.get("lang") in LANGS else "ru"
    payload["width"] = int(max(MIN_W, min(MAX_W, ui.get("width", DEFAULT_W))))
    pos = ui.get("pos")
    if pos:
        payload["x"], payload["y"] = int(pos[0]), int(pos[1])
    payload["notify"] = bool(ui.get("notify", True))
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print("[settings] не сохранилось:", exc)


def log_event(label: str, value: str, limit: str) -> None:
    """Строка в журнал событий рядом с программой."""
    line = (f"{datetime.now():%Y-%m-%d %H:%M:%S} | {label} | "
            f"{value} | above {limit}\n")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as exc:
        print("[log] не записалось:", exc)


# ------------------------------------------------------------- автозагрузка --
def autostart_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_NAME)
            return True
    except OSError:
        return False


def set_autostart(enable: bool) -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enable:
                if getattr(sys, "frozen", False):
                    command = f'"{sys.executable}"'
                else:
                    exe = sys.executable
                    if os.path.basename(exe).lower() != "pythonw.exe":
                        cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
                        if os.path.exists(cand):
                            exe = cand
                    command = f'"{exe}" "{os.path.abspath(__file__)}"'
                winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, RUN_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        print("[autostart] ошибка:", exc)
        return False


# ------------------------------------------------------------- сбор данных --
# ----------------------------------------------- датчики HWiNFO (SM) -------
_SM_SIG = 0x53695748  # 'HWiS'


class HWiNFO:
    """Температура процессора из общей памяти HWiNFO.

    HWiNFO умеет отдавать датчики без драйверов и без прав администратора,
    но только пока он сам запущен (настройка SensorsSM=1 в его INI).
    """

    FILE_MAP_READ = 0x0004

    def __init__(self) -> None:
        self._h = None
        self._addr = None
        self._k32 = None
        self._ctypes = None
        try:
            import ctypes
            import ctypes.wintypes as wt

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenFileMappingW.restype = wt.HANDLE
            k32.OpenFileMappingW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
            k32.MapViewOfFile.restype = ctypes.c_void_p
            k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD,
                                          wt.DWORD, ctypes.c_size_t]
            k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
            k32.CloseHandle.argtypes = [wt.HANDLE]
            self._k32, self._ctypes = k32, ctypes
        except Exception as exc:  # noqa: BLE001
            print("[HWiNFO] вызовы WinAPI недоступны:", exc)

    def _open(self) -> bool:
        if self._addr is not None:
            return True
        if self._k32 is None:
            return False
        h = self._k32.OpenFileMappingW(self.FILE_MAP_READ, False,
                                       "Global\\HWiNFO_SENS_SM2")
        if not h:
            return False
        addr = self._k32.MapViewOfFile(h, self.FILE_MAP_READ, 0, 0, 0)
        if not addr:
            self._k32.CloseHandle(h)
            return False
        self._h, self._addr = h, addr
        return True

    def close(self) -> None:
        if self._k32 is not None:
            if self._addr is not None:
                self._k32.UnmapViewOfFile(self._addr)
            if self._h is not None:
                self._k32.CloseHandle(self._h)
        self._addr = self._h = None

    def cpu_temp(self) -> float | None:
        if not self._open():
            return None
        try:
            import struct

            ctypes = self._ctypes
            head = ctypes.string_at(self._addr, 44)
            (sig, _ver, _rev, _poll, _o_s, _z_s, _n_s,
             o_r, z_r, n_r) = struct.unpack_from("<IIIqIIIIII", head)
            if sig != _SM_SIG or not n_r or not z_r:
                return None
            raw = ctypes.string_at(self._addr, o_r + z_r * n_r)
            best: tuple[int, float] | None = None
            for i in range(n_r):
                base = o_r + i * z_r
                _rid, _sid, rtype = struct.unpack_from("<III", raw, base)
                if rtype >> 24 != 1:  # старший байт — тип датчика, 1 = температура
                    continue
                lab = raw[base + 12:base + 140].split(b"\0")[0]
                text = lab.decode("utf-8", "replace").lower()
                val = struct.unpack_from("<d", raw, base + 284)[0]
                if not (-50.0 < val < 200.0):   # мусор в датчике — пропускаем
                    continue
                if "tctl" in text or "tdie" in text:
                    weight = 3          # у AMD это и есть температура ядра
                elif "package" in text:
                    weight = 2
                elif "core max" in text:
                    weight = 1
                else:
                    weight = 0
                if best is None or weight > best[0]:
                    best = (weight, val)
            return round(best[1], 1) if best else None
        except Exception as exc:  # noqa: BLE001
            print("[HWiNFO] чтение не удалось:", exc)
            self.close()
            return None


def cpu_name() -> str:
    """Имя процессора из реестра: «AMD Ryzen 5 3600 6-Core Processor»."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as key:
            return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    except Exception:  # noqa: BLE001
        return ""


class Collector:
    def __init__(self) -> None:
        self.nv = None
        self.handle = None
        self.gpu_name = "GPU"
        self.has_gpu = False

        try:
            import pynvml

            pynvml.nvmlInit()
            self.nv = pynvml
            if pynvml.nvmlDeviceGetCount() > 0:
                self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                raw = pynvml.nvmlDeviceGetName(self.handle)
                self.gpu_name = raw.decode() if isinstance(raw, bytes) else str(raw)
                self.has_gpu = True
        except Exception as exc:  # noqa: BLE001
            print(f"[GPU] недоступен: {exc}")

        self._net_prev = None
        self._disk_prev = None
        self.net_total = [0.0, 0.0]
        self.hwinfo = HWiNFO()
        self.cpu_name = cpu_name()
        psutil.cpu_percent(interval=None)

    def read(self) -> dict:
        now = time.monotonic()
        d: dict = {"cpu": psutil.cpu_percent(interval=None)}

        vm = psutil.virtual_memory()
        d["ram_used"] = vm.used / 1024**3
        d["ram_total"] = vm.total / 1024**3
        d["ram_pct"] = vm.percent
        d["ram_free"] = vm.available / 1024**3

        freq = psutil.cpu_freq()
        if freq:
            d["cpu_freq"] = freq.current

        temp = self.hwinfo.cpu_temp() if self.hwinfo is not None else None
        if temp is not None:
            d["cpu_temp"] = temp

        du = psutil.disk_usage("C:\\")
        d["disk_used"] = du.used / 1024**3
        d["disk_total"] = du.total / 1024**3
        d["disk_pct"] = du.percent

        net = psutil.net_io_counters()
        if self._net_prev is not None:
            dt = max(now - self._net_prev[0], 1e-6)
            down = (net.bytes_recv - self._net_prev[1]) * 8 / 1e6 / dt
            up = (net.bytes_sent - self._net_prev[2]) * 8 / 1e6 / dt
            self.net_total[0] += (net.bytes_recv - self._net_prev[1]) / 1024**3
            self.net_total[1] += (net.bytes_sent - self._net_prev[2]) / 1024**3
        else:
            down = up = 0.0
        d["net_down"], d["net_up"] = down, up
        self._net_prev = (now, net.bytes_recv, net.bytes_sent)
        d["net_total"] = tuple(self.net_total)

        try:
            io = psutil.disk_io_counters()
            if io is not None:
                if self._disk_prev is not None:
                    dt = max(now - self._disk_prev[0], 1e-6)
                    d["disk_read"] = (io.read_bytes - self._disk_prev[1]) / 1024**2 / dt
                    d["disk_write"] = (io.write_bytes - self._disk_prev[2]) / 1024**2 / dt
                else:
                    d["disk_read"] = d["disk_write"] = 0.0
                self._disk_prev = (now, io.read_bytes, io.write_bytes)
        except Exception:  # noqa: BLE001
            pass

        d["clock"] = datetime.now().strftime("%H:%M:%S")

        if not self.has_gpu:
            return d

        nv, h = self.nv, self.handle
        try:
            d["gpu_load"] = nv.nvmlDeviceGetUtilizationRates(h).gpu
            mi = nv.nvmlDeviceGetMemoryInfo(h)
            d["vram_used"] = mi.used / 1024**3
            d["vram_total"] = mi.total / 1024**3
            d["vram_pct"] = mi.used / mi.total * 100 if mi.total else 0
            d["gpu_temp"] = nv.nvmlDeviceGetTemperature(h, 0)
            d["gpu_power"] = nv.nvmlDeviceGetPowerUsage(h) / 1000.0
            try:
                d["gpu_power_limit"] = nv.nvmlDeviceGetEnforcedPowerLimit(h) / 1000.0
            except Exception:  # noqa: BLE001
                d["gpu_power_limit"] = None
            try:
                d["gpu_clock"] = nv.nvmlDeviceGetClockInfo(h, 0)
            except Exception:  # noqa: BLE001
                pass
            try:
                d["gpu_fan"] = nv.nvmlDeviceGetFanSpeed(h)
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            print(f"[GPU] ошибка чтения: {exc}")
        return d

    def close(self) -> None:
        if self.hwinfo is not None:
            self.hwinfo.close()
        if self.nv is not None:
            try:
                self.nv.nvmlShutdown()
            except Exception:  # noqa: BLE001
                pass


# ----------------------------------------------------- полоска с градиентом --
class Bar(QWidget):
    WARN, CRIT = 60.0, 85.0
    C_OK = (QColor("#5ee07a"), QColor("#28b485"))
    C_WARN = (QColor("#ffc94d"), QColor("#ff8a00"))
    C_CRIT = (QColor("#ff6b6b"), QColor("#ff2d55"))

    def __init__(self, colors: tuple[QColor, QColor], height: int = 6,
                 warn: float | None = None, crit: float | None = None) -> None:
        super().__init__()
        self._pct = 0.0
        self._colors = colors
        self._warn = self.WARN if warn is None else warn
        self._crit = self.CRIT if crit is None else crit
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, pct: float) -> None:
        pct = max(0.0, min(100.0, float(pct)))
        if abs(pct - self._pct) > 0.05:
            self._pct = pct
            self.update()

    def colors_now(self) -> tuple[QColor, QColor]:
        """Цвет по нагрузке: норма → предупреждение → критично."""
        if self._pct >= self._crit:
            return self.C_CRIT
        if self._pct >= self._warn:
            return self.C_WARN
        return self.C_OK

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        radius = r.height() / 2

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(TRACK)
        p.drawRoundedRect(QRectF(r), radius, radius)

        w = r.width() * self._pct / 100.0
        if self._pct > 0 and w < r.height():
            w = float(r.height())
        if w <= 0:
            return

        grad = QLinearGradient(0, 0, max(w, 1.0), 0)
        c0, c1 = self.colors_now()
        grad.setColorAt(0.0, c0)
        grad.setColorAt(1.0, c1)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(0, 0, w, r.height()), radius, radius)


# -------------------------------------------------------------- строка метрики
def _label(text: str, color: QColor, px: int, bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    font = QFont("Segoe UI", px)
    font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color: {color.name(QColor.NameFormat.HexArgb)};")
    return lbl


class Metric(QWidget):
    def __init__(self, title: str,
                 colors: tuple[QColor, QColor] | None = None,
                 bar: bool = True,
                 warn: float | None = None,
                 crit: float | None = None,
                 action=None, action_tip: str = "") -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.title = _label(title, MUTED, 8)
        self.value = _label("--", TEXT, 9, bold=True)
        self.value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        row.addWidget(self.title)
        row.addStretch(1)
        row.addWidget(self.value)
        lay.addLayout(row)

        self.bar = None
        if bar and colors:
            self.bar = Bar(colors, warn=warn, crit=crit)
            if action is not None:
                row2 = QHBoxLayout()
                row2.setContentsMargins(0, 0, 0, 0)
                row2.setSpacing(6)
                row2.addWidget(self.bar, 1)
                btn = QToolButton(self)
                btn.setIcon(self.style().standardIcon(
                    QStyle.StandardPixmap.SP_BrowserReload))
                btn.setIconSize(QSize(12, 12))
                btn.setToolTip(action_tip)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedSize(16, 16)
                btn.setStyleSheet(
                    "QToolButton { border: none; background: transparent;"
                    " padding: 0; }"
                    " QToolButton:hover { background: rgba(255,255,255,26);"
                    " border-radius: 8px; }"
                )
                btn.clicked.connect(action)
                row2.addWidget(btn)
                lay.addLayout(row2)
            else:
                lay.addWidget(self.bar)
        self._alert = None

    def set(self, text: str, pct: float | None = None,
            alert: str | None = None) -> None:
        self.value.setText(text)
        if alert != self._alert:
            self._alert = alert
            color = {"crit": "#ff6b6b", "warn": "#ffc94d"}.get(alert, TEXT.name())
            self.value.setStyleSheet(f"color: {color};")
        if self.bar is not None and pct is not None:
            self.bar.set_value(pct)


# ------------------------------------------------------------ меню и «About» --
class StickyMenu(QMenu):
    """Меню, которое не закрывается, пока щёлкаешь галочки."""

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        act = self.actionAt(e.position().toPoint())
        if act is not None and act.isEnabled() and not act.isSeparator():
            if isinstance(act, QWidgetAction):      # заголовки групп
                e.accept()
                return
            if act.isCheckable() or act.property("sticky"):
                act.trigger()                       # меню остаётся открытым
                e.accept()
                return
            self.close()                            # обычный пункт: закрыть
            act.trigger()
            e.accept()
            return
        super().mouseReleaseEvent(e)


class LangSwitch(QWidget):
    """Переключатель языка: RU | EN."""

    changed = pyqtSignal(str)

    def __init__(self, lang: str, parent=None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        self._labels = {}
        for code in LANGS:
            lbl = QLabel(code.upper())
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl.mousePressEvent = lambda _e, c=code: self._pick(c)
            lay.addWidget(lbl)
            self._labels[code] = lbl
        self._style(lang)

    def _style(self, lang: str) -> None:
        for code, lbl in self._labels.items():
            active = code == lang
            lbl.setStyleSheet(
                f"color: {'#f2f2f7' if active else '#6f6f7a'};"
                f" font-size: 9px; font-weight: {'700' if active else '500'};"
            )

    def _pick(self, code: str) -> None:
        self._style(code)
        self.changed.emit(code)

    def refresh(self, lang: str) -> None:
        """Обновить подсветку без отправки сигнала."""
        self._style(lang)


class AboutDialog(QWidget):
    """Окно «о программе» в стиле виджета: три строки, закрывается кликом."""

    def __init__(self, lang: str = "ru", parent=None) -> None:
        super().__init__(parent,
                         Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 15, 18, 16)
        lay.setSpacing(7)
        rows = (
            (f"{APP_NAME} {APP_VERSION}", TEXT, 10, True),
            (f"{tr(lang, 'about_idea')}: {APP_IDEA}", MUTED, 9, False),
            (f"{tr(lang, 'about_dev')}: {APP_IMPL}", MUTED, 9, False),
        )
        for text, color, size, bold in rows:
            lay.addWidget(_label(text, color, size, bold))
        self.adjustSize()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        p.fillPath(path, QColor(24, 24, 29, 242))
        p.setPen(QPen(BORDER, 1))
        p.drawPath(path)

    def mousePressEvent(self, _e) -> None:  # noqa: N802
        self.close()

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() == Qt.Key.Key_Escape:
            self.close()


# ------------------------------------------------------------ глобальный хоткей
class Hotkey(QThread):
    triggered = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._thread_id: int | None = None
        self._ready = threading.Event()

    def run(self) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        MOD_ALT, MOD_CONTROL, VK_H = 0x0001, 0x0002, 0x48
        ok = user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT, VK_H)
        self._ready.set()
        if not ok:
            print("[HOTKEY] Ctrl+Alt+H занят другой программой")
            return

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:
                self.triggered.emit()
        user32.UnregisterHotKey(None, 1)

    def stop(self) -> None:
        self._ready.wait(1.0)
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        self.wait(2000)


# ------------------------------------------------------------------ виджет --
class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)  # иначе курсор на краях не обновляется
        self.setMinimumWidth(MIN_W)
        self.setMaximumWidth(MAX_W)

        self.settings, ui = load_settings()
        self.lang = ui["lang"]
        self._width = ui["width"]
        self._pos = ui["pos"]
        self.notify = ui["notify"]
        self._alerted: dict[str, int] = {}
        self._save()
        self.collector = Collector()
        self._drag: QPoint | None = None
        self._resize: tuple | None = None
        self._field_actions: dict = {}
        self._about: QWidget | None = None
        self._tray: QSystemTrayIcon | None = None
        self.fields: dict[str, Metric] = {}
        self.sections: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 13, 16, 15)
        outer.setSpacing(11)
        self._outer = outer

        # --- шапка с шестерёнкой -------------------------------------
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet("color: #ff6b5b; font-size: 9px;")
        name = _label(self.collector.gpu_name.replace("NVIDIA GeForce ", ""), TEXT, 9, True)
        head.addWidget(dot)
        head.addWidget(name)
        head.addStretch(1)

        btn_style = (
            "QToolButton { border: none; background: transparent; color: #8e8e98;"
            " font-size: 13px; padding: 0; }"
            " QToolButton:hover { color: #f2f2f7; }"
        )

        self.langs = LangSwitch(self.lang, self)
        self.langs.setToolTip(self._t("tip_lang"))
        self.langs.changed.connect(self.set_language)
        head.addWidget(self.langs)

        self.about = QToolButton(self)
        self.about.setText("ⓘ")
        self.about.setToolTip(self._t("tip_about"))
        self.about.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about.setFixedSize(18, 18)
        self.about.setStyleSheet(btn_style)
        self.about.clicked.connect(self.show_about)
        head.addWidget(self.about)

        self.gear = QToolButton(self)
        self.gear.setText("⚙")
        self.gear.setToolTip(self._t("tip_gear"))
        self.gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gear.setFixedSize(18, 18)
        self.gear.setStyleSheet(btn_style)
        self.gear.clicked.connect(self.show_menu_at_gear)
        head.addWidget(self.gear)
        outer.addLayout(head)

        self._build_sections()
        self._apply_visibility()

        if not self.collector.has_gpu:
            self.fields["gpu_load"].set(self._t("v_nodata"))
            self.fields["vram"].set(self._t("v_nodata"))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

        self.hotkey = Hotkey()
        self.hotkey.triggered.connect(self.toggle)
        self.hotkey.start()

        self._make_tray()
        self.refresh()
        self._place_top_right()

    # ------------------------------------------------------------------
    def _build_sections(self) -> None:
        bars = {
            "gpu_load": (GRAD_GPU, True), "vram": (GRAD_VRAM, True),
            "gpu_temp": (GRAD_TEMP, True), "gpu_power": (GRAD_PWR, True),
            "gpu_clock": (None, False), "gpu_fan": (GRAD_FAN, True),
            "cpu_load": (GRAD_CPU, True), "cpu_temp": (GRAD_TEMP, True),
            "cpu_freq": (None, False),
            "ram": (GRAD_RAM, True), "ram_free": (None, False),
            "disk": (GRAD_DISK, True), "disk_io": (None, False),
            "net_speed": (GRAD_NET, False), "net_total": (None, False),
            "clock": (None, False),
        }

        for sec_key, keys in SECTIONS:
            divider = None
            if self.sections:
                divider = QWidget()
                divider.setFixedHeight(1)
                divider.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                divider.setStyleSheet("background: rgba(255,255,255,18);")
                self._outer.addWidget(divider)

            box = QWidget()
            lay = QVBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(11)
            for k in keys:
                grad, with_bar = bars[k]
                extra: dict = {}
                if k == "gpu_temp":
                    w, c = self._temp_limits()
                    extra = {"warn": w, "crit": c}
                elif k == "cpu_temp":
                    w, c = self._cpu_temp_limits()
                    extra = {"warn": w, "crit": c}
                elif k == "ram":
                    extra = {"action": self.free_ram,
                             "action_tip": self._t("tip_freeram")}
                m = Metric(self._t(f"t_{k}"), grad, bar=with_bar, **extra)
                self.fields[k] = m
                lay.addWidget(m)
            self._outer.addWidget(box)
            self.sections.append(
                {"key": sec_key, "keys": keys, "widget": box, "divider": divider}
            )

    def _apply_visibility(self) -> None:
        first_visible = True
        for sec in self.sections:
            any_on = False
            for k in sec["keys"]:
                on = bool(self.settings.get(k, False))
                self.fields[k].setVisible(on)
                any_on = any_on or on
            sec["widget"].setVisible(any_on)
            if sec["divider"] is not None:
                sec["divider"].setVisible(any_on and not first_visible)
            if any_on:
                first_visible = False
        self._apply_size()
        # Qt пересчитывает вложенные лэйауты отложенно — добираем высоту
        # на следующем тике, иначе после скрытия строки остаётся старая
        QTimer.singleShot(0, self._apply_size)

    def _content_height(self) -> int:
        """Высота по содержимому. Лэйаут надо заставить пересчитаться,
        иначе после скрытия строк остаётся старая высота."""
        lay = self.layout()
        if lay is not None:
            lay.invalidate()
            lay.activate()
            return lay.totalMinimumSize().height()
        return self.minimumSizeHint().height()

    def _apply_size(self) -> None:
        self.resize(self._width, self._content_height())

    # --- язык -----------------------------------------------------------
    def _t(self, key: str) -> str:
        return tr(self.lang, key)

    def set_language(self, lang: str) -> None:
        if lang not in LANGS or lang == self.lang:
            return
        self.lang = lang
        self._save()
        self.apply_language()

    def apply_language(self) -> None:
        for key, metric in self.fields.items():
            metric.title.setText(self._t(f"t_{key}"))
        self.langs.refresh(self.lang)
        self.gear.setToolTip(self._t("tip_gear"))
        self.about.setToolTip(self._t("tip_about"))
        self.langs.setToolTip(self._t("tip_lang"))
        self.refresh()
        self._apply_size()

    # --- меню -----------------------------------------------------------
    def _menu_style(self) -> str:
        return (
            "QMenu { background:#1c1c20; color:#f2f2f7; border:1px solid #34343c;"
            " padding:5px; }"
            " QMenu::item { padding:6px 20px 6px 8px; border-radius:4px; }"
            " QMenu::item:selected { background:#2c2c34; }"
            " QMenu::separator { height:1px; background:#34343c; margin:5px 8px; }"
            " QMenu::indicator { width:14px; height:14px; }"
        )

    def _header_action(self, text: str, menu: QMenu) -> QWidgetAction:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            "color:#8e8e98; font-size:10px; font-weight:600;"
            " padding:7px 10px 2px 10px; background:transparent;"
        )
        act = QWidgetAction(menu)
        act.setDefaultWidget(lbl)
        return act

    def build_menu(self) -> QMenu:
        menu = StickyMenu(self)
        menu.setStyleSheet(self._menu_style())
        self._field_actions = {}

        all_on = menu.addAction(self._t("m_all_on"))
        all_on.setProperty("sticky", True)
        all_on.triggered.connect(lambda: self._set_all(True))
        all_off = menu.addAction(self._t("m_all_off"))
        all_off.setProperty("sticky", True)
        all_off.triggered.connect(lambda: self._set_all(False))
        reset = menu.addAction(self._t("m_reset"))
        reset.setProperty("sticky", True)
        reset.triggered.connect(self._reset_defaults)
        menu.addSeparator()

        for i, (sec_key, keys) in enumerate(SECTIONS):
            if i:
                menu.addSeparator()
            menu.addAction(self._header_action(self._t(f"sec_{sec_key}"), menu))
            for k in keys:
                act = menu.addAction(self._t(f"f_{k}"))
                act.setCheckable(True)
                act.setChecked(bool(self.settings.get(k, False)))
                # сигнал подключаем ПОСЛЕ setChecked, иначе он срабатывает
                # при построении меню и меняет настройки на лету
                act.toggled.connect(lambda checked, key=k: self.toggle_field(key, checked))
                self._field_actions[k] = act

        menu.addSeparator()
        notify_act = menu.addAction(self._t("m_notify"))
        notify_act.setCheckable(True)
        notify_act.setChecked(self.notify)
        notify_act.toggled.connect(self.toggle_notify)
        menu.addAction(self._t("m_openlog"), self.open_log)

        menu.addSeparator()
        auto = menu.addAction(self._t("m_autostart"))
        auto.setCheckable(True)
        auto.setChecked(autostart_enabled())
        auto.toggled.connect(self.toggle_autostart)

        menu.addSeparator()
        menu.addAction(self._t("m_hide"), self.toggle)
        menu.addAction(self._t("m_quit"), self.quit)
        return menu

    def show_menu_at_gear(self) -> None:
        menu = self.build_menu()
        pos = self.gear.mapToGlobal(QPoint(0, self.gear.height() + 4))
        menu.exec(pos)

    def show_about(self) -> None:
        dlg = AboutDialog(self.lang, self)
        dlg.adjustSize()
        pos = self.about.mapToGlobal(QPoint(0, self.about.height() + 6))
        dlg.move(max(0, pos.x() + self.about.width() - dlg.width()), pos.y())
        dlg.show()
        self._about = dlg  # держим ссылку, иначе окно соберёт сборщик мусора

    def _set_all(self, value: bool) -> None:
        for k in DEFAULTS:
            self.settings[k] = value
        self._save()
        for k, act in getattr(self, "_field_actions", {}).items():
            act.blockSignals(True)
            act.setChecked(value)
            act.blockSignals(False)
        self._apply_visibility()
        self.refresh()

    def _reset_defaults(self) -> None:
        """Вернуть набор строк и ширину, с которыми виджет начинал."""
        self.settings = dict(DEFAULTS)
        self._width = DEFAULT_W
        self._save()
        for k, act in getattr(self, "_field_actions", {}).items():
            act.blockSignals(True)
            act.setChecked(bool(DEFAULTS[k]))
            act.blockSignals(False)
        self._apply_visibility()
        self.refresh()

    def toggle_field(self, key: str, checked: bool) -> None:
        self.settings[key] = checked
        self._save()
        self._apply_visibility()
        self.refresh()

    def toggle_autostart(self, checked: bool) -> None:
        if not set_autostart(checked):
            print("[autostart] не удалось изменить")

    def toggle_notify(self, checked: bool) -> None:
        self.notify = checked
        self._save()

    def open_log(self) -> None:
        try:
            if not os.path.exists(LOG_PATH):
                open(LOG_PATH, "a", encoding="utf-8").close()
            os.startfile(LOG_PATH)  # noqa: S606  (только Windows)
        except Exception as exc:  # noqa: BLE001
            print("[log] не открылся:", exc)

    # --- события по порогам ---------------------------------------------
    def _check_alerts(self, d: dict) -> None:
        """Журнал и трей: только температуры, только пересечение порога."""
        pairs = (
            ("gpu_temp", d.get("gpu_temp"), *self._temp_limits(), "a_gpu_temp"),
            ("cpu_temp", d.get("cpu_temp"), *self._cpu_temp_limits(), "a_cpu_temp"),
        )
        for key, value, warn, crit, label_key in pairs:
            if value is None:
                self._alerted[key] = 0
                continue
            stage = 2 if value >= crit else (1 if value >= warn else 0)
            old = self._alerted.get(key, 0)
            if stage > old:
                self._alerted[key] = stage
                limit = crit if stage == 2 else warn
                level = self._t("lvl_crit" if stage == 2 else "lvl_warn")
                shown = f"{value:.0f} °C"
                log_event(f"{self._t(label_key)} — {level}", shown,
                          f"{limit:.0f} °C")
                if self.notify and self._tray is not None:
                    self._tray.showMessage(
                        f"{APP_NAME}: {self._t(label_key)}",
                        f"{shown} — {level} ({limit:.0f} °C)",
                        QSystemTrayIcon.MessageIcon.Critical if stage == 2
                        else QSystemTrayIcon.MessageIcon.Warning,
                        5000,
                    )
            elif stage < old:
                back = (crit if old == 2 else warn) - HYST_TEMP
                if value < back:
                    self._alerted[key] = stage

    def _temp_limits(self) -> tuple[float, float]:
        """Пороги температуры GPU: для RTX 3060 свои, для прочих общие."""
        if "3060" in self.collector.gpu_name.lower():
            return 54.0, 58.0
        return 72.0, 82.0

    def _cpu_temp_limits(self) -> tuple[float, float]:
        """Пороги температуры CPU.

        У Ryzen 5 3600 (Zen 2) предел по паспорту AMD — 95 °C, поэтому
        «высокая» ставится на 80, а «критическая» на 90: остаётся запас
        до троттлинга. У Intel пределы выше, там 85/95.
        """
        name = self.collector.cpu_name.lower()
        if "amd" in name or "ryzen" in name:
            return 80.0, 90.0
        return 85.0, 95.0

    # --- освобождение памяти -------------------------------------------
    def free_ram(self) -> None:
        self._ram_before = psutil.virtual_memory().available
        try:
            trimmed = self._trim_working_sets()
        except Exception as exc:  # noqa: BLE001
            print("[ram] ошибка:", exc)
            trimmed = 0
        QTimer.singleShot(1500, lambda: self._ram_report(trimmed))

    @staticmethod
    def _trim_working_sets() -> int:
        """Сжимает рабочие наборы процессов текущей сессии.

        Это ровно то, что делают «чистилки» памяти: страницы уходят
        в резерв, счётчик свободной памяти растёт. Полезного эффекта
        немного — Windows сам управляет кэшем, — но вреда тоже нет.
        """
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
        psapi.EmptyWorkingSet.restype = wintypes.BOOL

        access = 0x0400 | 0x0100  # QUERY_INFORMATION | SET_QUOTA
        skip = {"system", "registry", "memory compression", "csrss.exe",
                "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
                "smss.exe", "dwm.exe", "fontdrvhost.exe"}
        me = os.getpid()
        done = 0
        for proc in psutil.process_iter(["pid", "name"]):
            pid = proc.info.get("pid")
            if pid == me or (proc.info.get("name") or "").lower() in skip:
                continue
            handle = k32.OpenProcess(access, False, pid)
            if not handle:
                continue
            try:
                if psapi.EmptyWorkingSet(handle):
                    done += 1
            finally:
                k32.CloseHandle(handle)
        return done

    def _ram_report(self, trimmed: int) -> None:
        freed = max(0, psutil.virtual_memory().available - self._ram_before) / 1024**2
        self.refresh()
        if self._tray is None:
            return
        unit = "МБ" if self.lang == "ru" else "MB"
        text = (f"{self._t('msg_freed')} ~{freed:.0f} {unit}" if freed >= 1
                else self._t("msg_nothing"))
        self._tray.showMessage(APP_NAME, text,
                               QSystemTrayIcon.MessageIcon.Information, 3000)

    # ------------------------------------------------------------------
    def _pos_visible(self, x: int, y: int) -> bool:
        rect = QRect(x, y, self._width, max(60, self.height()))
        return any(s.availableGeometry().intersects(rect)
                   for s in QApplication.screens())

    def _place_top_right(self) -> None:
        self._apply_size()
        if self._pos and self._pos_visible(*self._pos):
            self.move(*self._pos)
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - 24, geo.top() + 24)

    def _save_pos(self) -> None:
        self._pos = (self.x(), self.y())
        self._save()

    def _ui_state(self) -> dict:
        return {"lang": self.lang, "width": self._width,
                "pos": self._pos, "notify": self.notify}

    def _save(self) -> None:
        save_settings(self.settings, self._ui_state())

    # --- трей -----------------------------------------------------------
    def _make_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(QIcon(self._tray_pixmap()), self)
        tray.setToolTip(f"{APP_NAME} {APP_VERSION}")
        menu = QMenu()
        menu.setStyleSheet(self._menu_style())
        menu.addAction(self._t("m_show"), self.toggle)
        menu.addAction(self._t("m_settings"), self.show_menu_at_gear)
        menu.addSeparator()
        menu.addAction(self._t("m_quit"), self.quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self._tray_click)
        tray.show()
        self._tray = tray
        self._tray_menu = menu

    def _tray_click(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle()

    @staticmethod
    def _tray_pixmap() -> QPixmap:
        pm = QPixmap(32, 32)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ff6b5b"))
        p.drawEllipse(1, 1, 30, 30)
        p.setBrush(QColor("#12121a"))
        p.drawEllipse(11, 11, 10, 10)
        p.end()
        return pm

    def refresh(self) -> None:
        d = self.collector.read()
        self._check_alerts(d)
        f = self.fields
        s = self.settings
        gb, watt = self._t("u_gb"), self._t("u_watt")
        mhz, mbits, mbs = self._t("u_mhz"), self._t("u_mbits"), self._t("u_mbs")

        if "gpu_load" in d:
            if s["gpu_load"]:
                f["gpu_load"].set(f"{d['gpu_load']} %", d["gpu_load"])
            if s["vram"]:
                f["vram"].set(
                    f"{d['vram_used']:.1f} / {d['vram_total']:.0f} {gb}", d["vram_pct"]
                )
            if s["gpu_temp"]:
                t = d.get("gpu_temp")
                warn, crit = self._temp_limits()
                num = isinstance(t, (int, float))
                alert = ("crit" if num and t >= crit else
                         "warn" if num and t >= warn else None)
                f["gpu_temp"].set(f"{t if t is not None else '--'} °C",
                                  pct=float(t) if num else None, alert=alert)
            if s["gpu_power"]:
                pw, lim = d.get("gpu_power"), d.get("gpu_power_limit")
                if pw is not None and lim:
                    f["gpu_power"].set(f"{pw:.0f} / {lim:.0f} {watt}", pw / lim * 100)
                elif pw is not None:
                    f["gpu_power"].set(f"{pw:.0f} {watt}")
            if s["gpu_clock"] and "gpu_clock" in d:
                f["gpu_clock"].set(f"{d['gpu_clock']} {mhz}")
            if s["gpu_fan"] and "gpu_fan" in d:
                f["gpu_fan"].set(f"{d['gpu_fan']} %", d["gpu_fan"])

        if s["cpu_load"]:
            f["cpu_load"].set(f"{d['cpu']:.0f} %", d["cpu"])
        if s["cpu_temp"]:
            t = d.get("cpu_temp")
            warn, crit = self._cpu_temp_limits()
            num = isinstance(t, (int, float))
            alert = ("crit" if num and t >= crit else
                     "warn" if num and t >= warn else None)
            f["cpu_temp"].set(
                f"{t:.1f} °C" if num else self._t("v_nodata"),
                pct=float(t) if num else None, alert=alert,
            )
            f["cpu_temp"].value.setToolTip("" if num else self._t("tip_cputemp"))
        if s["cpu_freq"] and "cpu_freq" in d:
            f["cpu_freq"].set(f"{d['cpu_freq']:.0f} {mhz}")

        if s["ram"]:
            f["ram"].set(f"{d['ram_used']:.1f} / {d['ram_total']:.0f} {gb}", d["ram_pct"])
        if s["ram_free"]:
            f["ram_free"].set(f"{d['ram_free']:.1f} {gb}")

        if s["disk"]:
            f["disk"].set(
                f"{d['disk_used']:.0f} / {d['disk_total']:.0f} {gb}", d["disk_pct"]
            )
        if s["disk_io"] and "disk_read" in d:
            f["disk_io"].set(f"{d['disk_read']:.1f} / {d['disk_write']:.1f} {mbs}")

        if s["net_speed"]:
            f["net_speed"].set(f"{d['net_down']:.1f} / {d['net_up']:.1f} {mbits}")
        if s["net_total"]:
            tot = d["net_total"]
            f["net_total"].set(f"↓ {tot[0]:.2f} / ↑ {tot[1]:.2f} {gb}")

        if s["clock"]:
            f["clock"].set(d["clock"])

    # ------------------------------------------------------------------
    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    def _edge_at(self, pos: QPoint) -> str | None:
        if pos.x() <= EDGE:
            return "left"
        if pos.x() >= self.width() - EDGE:
            return "right"
        return None

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() != Qt.MouseButton.LeftButton:
            return
        edge = self._edge_at(e.position().toPoint())
        if edge:
            self._resize = (edge, e.globalPosition().toPoint().x(),
                            self._width, self.x())
            e.accept()
            return
        self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        e.accept()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        pt = e.position().toPoint()
        if self._resize is not None and e.buttons() & Qt.MouseButton.LeftButton:
            edge, start_x, start_w, win_x = self._resize
            dx = e.globalPosition().toPoint().x() - start_x
            w = start_w + dx if edge == "right" else start_w - dx
            w = max(MIN_W, min(MAX_W, w))
            if edge == "left":  # правый край стоит на месте
                self.move(win_x + (start_w - w), self.y())
            self._width = w
            self.resize(w, self._content_height())
            e.accept()
            return
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)
            e.accept()
            return
        self.setCursor(
            Qt.CursorShape.SizeHorCursor if self._edge_at(pt)
            else Qt.CursorShape.ArrowCursor
        )

    def mouseReleaseEvent(self, _e) -> None:  # noqa: N802
        was_resize = self._resize is not None
        was_drag = self._drag is not None
        self._resize = None
        self._drag = None
        if was_resize or was_drag:
            self._save_pos()

    def contextMenuEvent(self, e) -> None:  # noqa: N802
        self.build_menu().exec(e.globalPos())

    def quit(self) -> None:
        self.timer.stop()
        self.hotkey.stop()
        self._save_pos()
        if self._tray is not None:
            self._tray.hide()
        self.collector.close()
        QApplication.quit()

    def closeEvent(self, e) -> None:  # noqa: N802
        self.quit()
        e.accept()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)
        p.fillPath(path, BG)
        p.setPen(QPen(BORDER, 1))
        p.drawPath(path)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("System Monitor")
    app.setFont(QFont("Segoe UI", 9))
    widget = Overlay()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
