"""
app/core/trackpad_controller.py
Điều khiển bật/tắt trackpad — hỗ trợ Windows, Linux (xinput), macOS.
Global hotkey KHÔNG cần thư viện ngoài:
  - Windows : WinAPI RegisterHotKey (chạy message-loop trong thread riêng)
  - Linux   : python-xlib (nếu có) hoặc bỏ qua
  - macOS   : Quartz CGEventTap (nếu có) hoặc bỏ qua
"""
from __future__ import annotations

import platform
import subprocess
import threading
import time
import logging
import ctypes
import os
import sys

log = logging.getLogger("TrackpadController")
OS = platform.system()   # "Windows" | "Linux" | "Darwin"


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_ps(script: str, timeout: int = 20):
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout
        )
    except Exception as e:
        log.error("PowerShell error: %s", e)
        return None


def _run_ps_elevated(script: str) -> bool:
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ps1", delete=False, encoding="utf-8"
        ) as f:
            f.write(script)
            tmp = f.name
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "powershell",
            f'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{tmp}"',
            None, 0
        )
        ok = int(result) > 32
        threading.Timer(5.0, lambda: os.unlink(tmp) if os.path.exists(tmp) else None).start()
        return ok
    except Exception as e:
        log.error("Elevated run error: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  Backend classes
# ══════════════════════════════════════════════════════════════════════════════

class _BaseBackend:
    def find(self) -> list[dict]: return []
    def disable(self, dev_id) -> bool: return False
    def enable(self, dev_id) -> bool: return False
    def is_disabled(self, dev_id) -> bool: return False


class _WindowsBackend(_BaseBackend):

    def find(self) -> list[dict]:
        import json
        script = (
            "Get-PnpDevice | Where-Object { "
            "  ($_.FriendlyName -match 'touch|trackpad|synaptics|elan|alps') -or "
            "  ($_.InstanceId  -match 'ELAN|SYN|ALPS|ITE8350|CRS') "
            "} | Select-Object InstanceId,FriendlyName,Status | ConvertTo-Json -Compress"
        )
        r = _run_ps(script)
        candidates = []
        if r and r.returncode == 0 and r.stdout.strip():
            try:
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                candidates = [
                    {"id": d["InstanceId"], "name": d["FriendlyName"], "status": d.get("Status", "")}
                    for d in data if d.get("InstanceId") and d.get("FriendlyName")
                ]
            except Exception as e:
                log.error("JSON parse: %s", e)

        if not candidates:
            return [{"id": "auto", "name": "Touchpad (auto-detect)", "status": "Unknown"}]

        import re
        def score(d: dict) -> int:
            name = d["name"].lower()
            iid  = d["id"].upper()
            s = 0
            if re.search(r"touch\s+pad", name): s += 100
            if re.search(r"touchpad",    name): s += 90
            if re.search(r"trackpad",    name): s += 80
            if "ELAN" in iid or "SYN" in iid:  s += 50
            if "ALPS" in iid or "ITE"  in iid: s += 40
            if re.search(r"keyboard|sensor|vendor.defined|controller|config", name): s -= 200
            return s

        candidates.sort(key=score, reverse=True)
        best = candidates[0]
        log.info("Chọn thiết bị: %s [%s]", best["name"], best["id"])
        return [best]

    def _ps_cmd(self, action: str, dev_id: str) -> str:
        verb = "Enable-PnpDevice" if action == "enable" else "Disable-PnpDevice"
        if dev_id and dev_id != "auto":
            return f'{verb} -InstanceId "{dev_id}" -Confirm:$false -ErrorAction SilentlyContinue'
        return (
            f"Get-PnpDevice | Where-Object {{ $_.FriendlyName -match "
            f"'touch\\s*pad|trackpad|synaptics|elan' }} | "
            f"{verb} -Confirm:$false -ErrorAction SilentlyContinue"
        )

    def disable(self, dev_id) -> bool: return self._exec("disable", dev_id)
    def enable(self,  dev_id) -> bool: return self._exec("enable",  dev_id)

    def _exec(self, action: str, dev_id: str) -> bool:
        cmd = self._ps_cmd(action, dev_id)
        if _is_admin():
            r = _run_ps(cmd)
            ok = r is not None and r.returncode == 0
            if not ok:
                log.error("%s failed: %s", action, r.stderr if r else "timeout")
            return ok
        else:
            return _run_ps_elevated(cmd)

    def is_disabled(self, dev_id) -> bool:
        if dev_id and dev_id != "auto":
            s = (f'$d = Get-PnpDevice -InstanceId "{dev_id}" -ErrorAction SilentlyContinue; '
                 f'if ($d) {{ $d.Status }} else {{ "Unknown" }}')
        else:
            s = ("(Get-PnpDevice | Where-Object { $_.FriendlyName -match "
                 "'touch\\s*pad|trackpad|synaptics|elan' } "
                 "| Select-Object -First 1).Status")
        r = _run_ps(s)
        if r and r.stdout.strip():
            return r.stdout.strip().lower() == "error"
        return False


class _LinuxBackend(_BaseBackend):
    KEYWORDS = ["touchpad", "trackpad", "synaptics", "elan", "alps", "finger"]

    def _has_xinput(self):
        return subprocess.run(["which", "xinput"], capture_output=True).returncode == 0

    def find(self):
        if not self._has_xinput(): return []
        try:
            r = subprocess.run(["xinput", "list", "--short"], capture_output=True, text=True, timeout=5)
            devs = []
            for line in r.stdout.splitlines():
                if any(k in line.lower() for k in self.KEYWORDS):
                    for part in line.split():
                        if part.startswith("id="):
                            devs.append({"id": part.split("=")[1],
                                         "name": line.split("\t")[0].strip().lstrip("⎜↳⎡⎣ ")})
                            break
            return devs
        except Exception as e:
            log.error("Linux find: %s", e); return []

    def disable(self, dev_id) -> bool:
        return subprocess.run(["xinput", "disable", str(dev_id)], capture_output=True, timeout=5).returncode == 0

    def enable(self, dev_id) -> bool:
        return subprocess.run(["xinput", "enable", str(dev_id)], capture_output=True, timeout=5).returncode == 0

    def is_disabled(self, dev_id) -> bool:
        try:
            r = subprocess.run(["xinput", "list-props", str(dev_id)], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                if "Device Enabled" in line:
                    return line.strip().split(":")[-1].strip() == "0"
        except Exception: pass
        return False


class _MacBackend(_BaseBackend):
    def find(self): return [{"id": "builtin", "name": "Built-in Trackpad"}]

    def _defaults(self, value: int):
        r = subprocess.run(["defaults", "write",
            "com.apple.driver.AppleBluetoothMultitouch.trackpad",
            "TrackpadEnabled", "-int", str(value)], capture_output=True, timeout=5)
        subprocess.run(["killall", "-HUP", "cfprefsd"], capture_output=True)
        return r.returncode == 0

    def disable(self, dev_id=None) -> bool: return self._defaults(0)
    def enable(self,  dev_id=None) -> bool: return self._defaults(1)
    def is_disabled(self, dev_id=None) -> bool:
        try:
            r = subprocess.run(["defaults", "read",
                "com.apple.driver.AppleBluetoothMultitouch.trackpad", "TrackpadEnabled"],
                capture_output=True, text=True, timeout=5)
            return r.stdout.strip() == "0"
        except Exception: return False


class _FallbackBackend(_BaseBackend):
    def __init__(self): self._state = False
    def find(self): return [{"id": "sim", "name": "Trackpad (Simulation)"}]
    def disable(self, dev_id=None): self._state = True;  return True
    def enable(self,  dev_id=None): self._state = False; return True
    def is_disabled(self, dev_id=None): return self._state


def _make_backend() -> _BaseBackend:
    if OS == "Windows": return _WindowsBackend()
    if OS == "Linux":
        b = _LinuxBackend()
        if subprocess.run(["which", "xinput"], capture_output=True).returncode == 0:
            return b
    if OS == "Darwin": return _MacBackend()
    log.warning("Không tìm thấy backend – dùng FallbackBackend")
    return _FallbackBackend()


# ══════════════════════════════════════════════════════════════════════════════
#  Global Hotkey Engine
# ══════════════════════════════════════════════════════════════════════════════
#
#  Không dùng thư viện ngoài.  Mỗi OS có engine riêng:
#    Windows : RegisterHotKey  (WinAPI, message loop trong thread daemon)
#    Linux   : python-xlib XGrabKey (nếu có, fallback im lặng)
#    macOS   : Quartz CGEventTap (nếu có, fallback im lặng)
#
#  HotkeySpec = (modifiers: int, vk: int)  — đã parse từ chuỗi config.
#
#  Chuỗi config ví dụ: "ctrl+alt+t"  "ctrl+shift+F9"  "alt+F12"
# ──────────────────────────────────────────────────────────────────────────────

# ── Modifier + VK maps ────────────────────────────────────────────────────────

# Windows modifier flags (cho RegisterHotKey)
_WIN_MOD = {
    "alt":    0x0001,
    "ctrl":   0x0002,
    "shift":  0x0004,
    "win":    0x0008,
    "norepeat": 0x4000,   # ghép thêm để tránh lặp khi giữ phím
}

# Virtual-key codes Windows (chỉ những key hay dùng làm hotkey)
_WIN_VK = {
    **{f"f{i}": 0x6F + i for i in range(1, 13)},   # F1–F12
    **{chr(c): ord(chr(c).upper()) for c in range(ord('a'), ord('z')+1)},  # a-z → 0x41-0x5A
    **{str(i): 0x30 + i for i in range(10)},        # 0-9
    "space":  0x20, "tab": 0x09, "enter": 0x0D,
    "insert": 0x2D, "delete": 0x2E,
    "home":   0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
    "up":     0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "backspace": 0x08, "escape": 0x1B,
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63,
    "numpad4": 0x64, "numpad5": 0x65, "numpad6": 0x66, "numpad7": 0x67,
    "numpad8": 0x68, "numpad9": 0x69,
}

# Linux keysyms (python-xlib)
_LINUX_MOD = {
    "alt":   1 << 3,   # Mod1Mask
    "ctrl":  1 << 2,   # ControlMask
    "shift": 1 << 0,   # ShiftMask
    "win":   1 << 6,   # Mod4Mask (Super)
}


def parse_hotkey(spec: str) -> tuple[list[str], str]:
    """
    Tách "ctrl+alt+t" → (["ctrl","alt"], "t")
    Trả về (modifiers, key) đều lowercase.
    Raise ValueError nếu format sai.
    """
    parts = [p.strip().lower() for p in spec.strip().split("+")]
    if len(parts) < 2:
        raise ValueError(f"Hotkey cần ít nhất modifier+key, nhận: '{spec}'")
    known_mods = {"ctrl", "alt", "shift", "win"}
    mods = [p for p in parts if p in known_mods]
    keys = [p for p in parts if p not in known_mods]
    if not keys:
        raise ValueError(f"Không tìm thấy key trong hotkey: '{spec}'")
    return mods, keys[-1]


def hotkey_display(spec: str) -> str:
    """Trả về chuỗi hiển thị đẹp, vd "Ctrl+Alt+T"."""
    try:
        mods, key = parse_hotkey(spec)
        parts = [m.capitalize() for m in mods] + [key.upper() if len(key) == 1 else key.capitalize()]
        return "+".join(parts)
    except Exception:
        return spec


# ──────────────────────────────────────────────────────────────────────────────
# Windows engine
# ──────────────────────────────────────────────────────────────────────────────

class _WinHotkeyEngine:
    """
    Đăng ký hotkey toàn cục qua WinAPI RegisterHotKey.
    Mỗi hotkey nhận một id riêng. Message loop chạy trong thread daemon.
    """

    WM_HOTKEY = 0x0312

    def __init__(self):
        self._lock    = threading.Lock()
        self._next_id = 1000            # ID bắt đầu từ 1000 tránh xung đột
        self._reg: dict[int, callable] = {}   # id → callback
        self._thread: threading.Thread | None = None
        self._hwnd: int = 0
        self._started = threading.Event()
        self._stop    = threading.Event()
        
        self._pending_regs = []
        self._pending_unregs = []

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="HotkeyMsgLoop")
        self._thread.start()
        self._started.wait(timeout=2.0)

    def stop(self):
        self._stop.set()
        # Gửi WM_QUIT vào thread để thoát GetMessage
        if self._hwnd:
            try:
                ctypes.windll.user32.PostMessageW(self._hwnd, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass

    def register(self, spec: str, callback: callable) -> int | None:
        """
        Đăng ký hotkey. Trả về hotkey-id nếu thành công, None nếu thất bại.
        Thread-safe; có thể gọi trước start().
        """
        try:
            mods_str, key = parse_hotkey(spec)
        except ValueError as e:
            log.error("Hotkey parse error: %s", e)
            return None

        mod_flags = _WIN_MOD["norepeat"]
        for m in mods_str:
            mod_flags |= _WIN_MOD.get(m, 0)

        vk = _WIN_VK.get(key.lower())
        if vk is None:
            log.error("Không tìm thấy VK cho key='%s' trong hotkey '%s'", key, spec)
            return None

        self.start()   # đảm bảo thread đang chạy

        with self._lock:
            hk_id = self._next_id
            self._next_id += 1
            self._pending_regs.append((hk_id, mod_flags, vk, callback, spec))

        return hk_id

    def unregister(self, hk_id: int):
        with self._lock:
            self._pending_unregs.append(hk_id)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _loop(self):
        """Message loop chạy trong thread daemon riêng."""
        user32 = ctypes.windll.user32

        self._hwnd = 0   # dùng thread queue
        self._started.set()

        MSG = ctypes.wintypes.MSG
        msg = MSG()

        while not self._stop.is_set():
            # Đăng ký pending hotkeys
            with self._lock:
                while self._pending_regs:
                    hk_id, mod_flags, vk, callback, spec = self._pending_regs.pop(0)
                    ok = user32.RegisterHotKey(None, hk_id, mod_flags, vk)
                    if ok:
                        self._reg[hk_id] = callback
                        log.info("Đã đăng ký global hotkey: %s (id=%d)", hotkey_display(spec), hk_id)
                    else:
                        err = ctypes.get_last_error()
                        log.error("RegisterHotKey thất bại cho '%s': error=%d "
                                  "(hotkey này có thể đã bị app khác chiếm)", spec, err)

                # Hủy đăng ký pending hotkeys
                while self._pending_unregs:
                    hk_id = self._pending_unregs.pop(0)
                    user32.UnregisterHotKey(None, hk_id)
                    self._reg.pop(hk_id, None)

            # PeekMessage non-blocking, timeout 50ms
            r = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)  # PM_REMOVE=1
            if r:
                if msg.message == self.WM_HOTKEY:
                    hk_id = msg.wParam
                    cb = self._reg.get(hk_id)
                    if cb:
                        threading.Thread(target=cb, daemon=True).start()
                elif msg.message == 0x0012:  # WM_QUIT
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.05)

        # Hủy đăng ký tất cả
        with self._lock:
            for hk_id in list(self._reg.keys()):
                user32.UnregisterHotKey(None, hk_id)
            self._reg.clear()
            self._pending_regs.clear()
            self._pending_unregs.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Linux engine (python-xlib, optional)
# ──────────────────────────────────────────────────────────────────────────────

class _LinuxHotkeyEngine:
    def __init__(self): self._thread = None; self._handlers: list[tuple] = []
    def start(self): pass

    def register(self, spec: str, callback: callable) -> bool:
        try:
            from Xlib import X, display as xdisplay
            from Xlib.ext import record
        except ImportError:
            log.warning("python-xlib không có – global hotkey bị bỏ qua trên Linux")
            return False

        try:
            mods_str, key = parse_hotkey(spec)
        except ValueError as e:
            log.error("Hotkey parse: %s", e); return False

        mod_mask = 0
        for m in mods_str:
            mod_mask |= _LINUX_MOD.get(m, 0)

        d = xdisplay.Display()
        root = d.screen().root
        keycode = d.keysym_to_keycode(
            __import__("Xlib.XK", fromlist=["string_to_keysym"]).string_to_keysym(key)
        )
        root.grab_key(keycode, mod_mask, True, X.GrabModeAsync, X.GrabModeAsync)
        d.flush()

        def _loop():
            while True:
                event = d.next_event()
                if event.type == X.KeyPress and event.detail == keycode:
                    threading.Thread(target=callback, daemon=True).start()

        t = threading.Thread(target=_loop, daemon=True, name="LinuxHotkeyLoop")
        t.start()
        self._thread = t
        log.info("Linux global hotkey đăng ký: %s", hotkey_display(spec))
        return True

    def stop(self): pass
    def unregister(self, *a): pass


# ──────────────────────────────────────────────────────────────────────────────
# macOS engine (Quartz, optional)
# ──────────────────────────────────────────────────────────────────────────────

class _MacHotkeyEngine:
    def __init__(self): pass
    def start(self): pass

    def register(self, spec: str, callback: callable) -> bool:
        try:
            import Quartz
        except ImportError:
            log.warning("Quartz không có – global hotkey bị bỏ qua trên macOS")
            return False

        try:
            mods_str, key = parse_hotkey(spec)
        except ValueError as e:
            log.error("Hotkey parse: %s", e); return False

        _MAC_MOD = {"ctrl": Quartz.kCGEventFlagMaskControl,
                    "alt":  Quartz.kCGEventFlagMaskAlternate,
                    "shift":Quartz.kCGEventFlagMaskShift,
                    "win":  Quartz.kCGEventFlagMaskCommand}
        mod_mask = 0
        for m in mods_str:
            mod_mask |= _MAC_MOD.get(m, 0)

        # CGEventTap (simplified)
        keycode = ord(key[0]) if len(key) == 1 else 0

        def handler(proxy, etype, event, refcon):
            flags = Quartz.CGEventGetFlags(event)
            kc    = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if kc == keycode and (flags & mod_mask) == mod_mask:
                threading.Thread(target=callback, daemon=True).start()
            return event

        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
            handler, None
        )
        if tap:
            src = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
            Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetMain(), src, Quartz.kCFRunLoopCommonModes)
            Quartz.CGEventTapEnable(tap, True)
            log.info("macOS global hotkey đăng ký: %s", hotkey_display(spec))
            return True
        else:
            log.error("CGEventTapCreate thất bại (cần quyền Accessibility)")
            return False

    def stop(self): pass
    def unregister(self, *a): pass


def _make_hotkey_engine():
    if OS == "Windows": return _WinHotkeyEngine()
    if OS == "Linux":   return _LinuxHotkeyEngine()
    if OS == "Darwin":  return _MacHotkeyEngine()
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  Public controller
# ══════════════════════════════════════════════════════════════════════════════

# Hotkey mặc định
DEFAULT_HOTKEY_TOGGLE  = "ctrl+alt+t"   # Toggle bật/tắt


class TrackpadController:
    """
    Giao diện duy nhất để MainWindow sử dụng.

        ctrl = TrackpadController()
        ctrl.toggle()
        ctrl.disable()
        ctrl.enable()
        state = ctrl.state   # "on" | "off" | "sim"

    Global hotkey (hoạt động kể cả khi app không focus):
        ctrl.register_hotkeys()               # dùng hotkey mặc định
        ctrl.register_hotkeys(                # tuỳ chỉnh
            toggle  = "ctrl+alt+t",
            disable = "ctrl+alt+d",
            enable  = "ctrl+alt+e",
        )
        ctrl.unregister_hotkeys()
        ctrl.hotkey_specs                     # dict hiện tại
    """

    def __init__(self):
        self._backend  = _make_backend()
        self._lock     = threading.Lock()
        self._disabled = False
        self._on_change: list[callable] = []

        # Hotkey engine & state
        self._hk_engine = _make_hotkey_engine()
        self._hk_ids: dict[str, int | None] = {}   # "toggle" → id
        self._hk_specs: dict[str, str] = {
            "toggle":  DEFAULT_HOTKEY_TOGGLE,
        }
        self._hk_active = False

        devs = self._backend.find()
        if devs:
            self._device = devs[0]
            try:
                self._disabled = self._backend.is_disabled(self._device["id"])
            except Exception:
                self._disabled = False
        else:
            self._device = {"id": None, "name": "Không tìm thấy"}

        log.info("TrackpadController init: device=%s state=%s admin=%s",
                 self.device_name, self.state, _is_admin())

    # ── properties ─────────────────────────────────────────────────────────

    @property
    def device_name(self) -> str:
        return self._device.get("name", "Unknown")

    @property
    def is_simulation(self) -> bool:
        return isinstance(self._backend, _FallbackBackend)

    @property
    def state(self) -> str:
        if self.is_simulation:
            return "sim"
        return "off" if self._disabled else "on"

    @property
    def hotkey_specs(self) -> dict[str, str]:
        """Trả về bản sao dict {action: spec} của các hotkey đang dùng."""
        return dict(self._hk_specs)

    @property
    def hotkeys_active(self) -> bool:
        return self._hk_active

    # ── callbacks ──────────────────────────────────────────────────────────

    def on_change(self, cb: callable):
        """Đăng ký callback(state: str) khi trạng thái thay đổi."""
        self._on_change.append(cb)

    def _emit_change(self):
        for cb in self._on_change:
            try:
                cb(self.state)
            except Exception as e:
                log.error("on_change callback: %s", e)

    # ── public actions ─────────────────────────────────────────────────────

    def toggle(self):
        with self._lock:
            if self._disabled:
                self._do_enable()
            else:
                self._do_disable()

    def disable(self) -> bool:
        with self._lock:
            return self._do_disable()

    def enable(self) -> bool:
        with self._lock:
            return self._do_enable()

    def refresh_device(self):
        devs = self._backend.find()
        if devs:
            self._device = devs[0]
            try:
                self._disabled = self._backend.is_disabled(self._device["id"])
            except Exception:
                pass
        self._emit_change()

    # ── Global hotkey API ──────────────────────────────────────────────────

    def register_hotkeys(
        self,
        toggle:  str | None = None,
    ) -> dict[str, bool]:
        """
        Đăng ký global hotkey. Truyền None để dùng giá trị mặc định / giá trị hiện tại.
        Trả về dict {action: ok} để caller biết cái nào thành công.

        Ví dụ::

            ctrl.register_hotkeys(toggle="ctrl+alt+t")
            ctrl.register_hotkeys(toggle="ctrl+alt+t", disable="ctrl+alt+d", enable="ctrl+alt+e")
        """
        if self._hk_active:
            self.unregister_hotkeys()

        if toggle  is not None: self._hk_specs["toggle"]  = toggle

        if self._hk_engine is None:
            log.warning("Không có hotkey engine cho OS=%s", OS)
            return {"toggle": False}

        results = {}
        action_map = {
            "toggle":  self.toggle,
        }

        for action, spec in self._hk_specs.items():
            cb = action_map[action]
            if OS == "Windows":
                hk_id = self._hk_engine.register(spec, cb)
                ok = hk_id is not None
                self._hk_ids[action] = hk_id
            else:
                ok = self._hk_engine.register(spec, cb)
                self._hk_ids[action] = ok
            results[action] = ok

        self._hk_active = any(results.values())
        if self._hk_active:
            log.info(
                "Global hotkeys: toggle=%s",
                hotkey_display(self._hk_specs["toggle"]),
            )
        return results

    def unregister_hotkeys(self):
        """Hủy đăng ký tất cả global hotkey."""
        if self._hk_engine is None:
            return
        if OS == "Windows":
            for action, hk_id in self._hk_ids.items():
                if hk_id is not None:
                    self._hk_engine.unregister(hk_id)
        else:
            # Linux/macOS engine không hỗ trợ unregister từng cái → stop engine
            try:
                self._hk_engine.stop()
            except Exception:
                pass
        self._hk_ids.clear()
        self._hk_active = False
        log.info("Đã hủy đăng ký tất cả global hotkey")

    def update_hotkey(self, action: str, new_spec: str) -> bool:
        """
        Cập nhật hotkey cho action 'toggle'.
        Trả về True nếu thành công.
        """
        if action != "toggle":
            raise ValueError(f"action phải là 'toggle', nhận '{action}'")

        # Xác thực spec trước
        try:
            parse_hotkey(new_spec)
        except ValueError as e:
            log.error("Hotkey không hợp lệ: %s", e)
            return False

        was_active = self._hk_active
        if was_active:
            self.unregister_hotkeys()

        self._hk_specs[action] = new_spec

        if was_active:
            results = self.register_hotkeys()
            return results.get(action, False)
        return True

    # ── internal ───────────────────────────────────────────────────────────

    def _do_disable(self) -> bool:
        ok = self._backend.disable(self._device.get("id"))
        if ok:
            self._disabled = True
            log.info("Trackpad TẮT: %s", self.device_name)
        else:
            log.error("Không thể tắt trackpad – kiểm tra quyền Admin")
        self._emit_change()
        return ok

    def _do_enable(self) -> bool:
        ok = self._backend.enable(self._device.get("id"))
        if ok:
            self._disabled = False
            log.info("Trackpad BẬT: %s", self.device_name)
        else:
            log.error("Không thể bật trackpad")
        self._emit_change()
        return ok

    def __del__(self):
        try:
            self.unregister_hotkeys()
        except Exception:
            pass
