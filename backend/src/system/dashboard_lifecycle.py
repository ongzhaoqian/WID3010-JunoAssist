from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CleanupResult:
    matched: list[int]
    terminated: list[int]
    skipped: list[int]
    errors: list[str]


class DashboardLifecycleManager:
    """Best-effort desktop/dashboard lifecycle helper.

    The robot backend must remain alive so JUNO can be woken again in the same
    run. This helper therefore closes/focuses the browser/dashboard and cleans up
    auxiliary runtime processes without touching roscore or the current backend
    process.
    """

    def __init__(
        self,
        *,
        dashboard_title: str = "JUNO Assist Dashboard",
        reuse_existing: bool = True,
        close_browser_on_sleep: bool = True,
        cleanup_enabled: bool = True,
        cleanup_patterns: Iterable[str] = (),
        cleanup_exclude_patterns: Iterable[str] = (),
        cleanup_grace_seconds: float = 1.0,
    ) -> None:
        self.dashboard_title = dashboard_title
        self.reuse_existing = bool(reuse_existing)
        self.close_browser_on_sleep = bool(close_browser_on_sleep)
        self.cleanup_enabled = bool(cleanup_enabled)
        self.cleanup_patterns = tuple(pattern for pattern in cleanup_patterns if pattern)
        self.cleanup_exclude_patterns = tuple(pattern for pattern in cleanup_exclude_patterns if pattern)
        self.cleanup_grace_seconds = max(0.1, float(cleanup_grace_seconds or 1.0))
        self._last_open_url: str | None = None
        self._opened_once = False

    def open_or_focus(self, url: str) -> dict:
        """Open the dashboard once, or focus an existing dashboard window.

        `xdg-open` often creates duplicate tabs. We first try to focus an
        existing browser window by title/URL using wmctrl. If that fails, we open
        the URL normally. This keeps repeated power-on events from spawning many
        dashboard pages.
        """
        url = str(url).strip()
        if not url:
            return {"opened": False, "focused": False, "reason": "empty_url"}

        focused = False
        if self.reuse_existing:
            focused = self._focus_existing_dashboard_window(url)
            if focused:
                self._last_open_url = url
                self._opened_once = True
                return {"opened": False, "focused": True, "url": url}

        try:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._last_open_url = url
            self._opened_once = True
            return {"opened": True, "focused": False, "url": url}
        except Exception as exc:
            try:
                import webbrowser
                webbrowser.open(url)
                self._last_open_url = url
                self._opened_once = True
                return {"opened": True, "focused": False, "url": url, "fallback": "webbrowser"}
            except Exception as fallback_exc:
                return {
                    "opened": False,
                    "focused": False,
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}; fallback={type(fallback_exc).__name__}: {fallback_exc}",
                }

    def close_dashboard(self) -> dict:
        """Request the dashboard browser window to close.

        The frontend also receives a `dashboard_should_close` state flag and will
        call `window.close()` itself. This method is an OS-level fallback for
        robot/demo desktops that have wmctrl installed.
        """
        if not self.close_browser_on_sleep:
            return {"closed": False, "reason": "disabled"}

        closed = False
        candidates = [
            self.dashboard_title,
            "JUNO Assist",
            "localhost:5173",
            "127.0.0.1:5173",
            self._last_open_url or "",
        ]
        for candidate in [item for item in candidates if item]:
            if self._wmctrl_close(candidate):
                closed = True
                break
        self._opened_once = False
        return {"closed": closed}

    def cleanup_powerdown_processes_async(self) -> None:
        if not self.cleanup_enabled:
            return
        thread = threading.Thread(target=self.cleanup_powerdown_processes, name="juno-powerdown-cleanup", daemon=True)
        thread.start()

    def cleanup_powerdown_processes(self) -> CleanupResult:
        """Terminate configured auxiliary JUNO runtime processes.

        The method intentionally skips roscore/rosmaster/rosout and the current
        Python process. It works with process command lines rather than literal
        terminal emulator windows so it is safer across GNOME Terminal, VS Code,
        Terminator, and xterm.
        """
        if not self.cleanup_enabled or not self.cleanup_patterns:
            return CleanupResult([], [], [], [])

        current_pid = os.getpid()
        rows = self._process_rows()
        matched: list[int] = []
        skipped: list[int] = []
        terminated: list[int] = []
        errors: list[str] = []

        for pid, command in rows:
            if pid == current_pid or pid <= 1:
                skipped.append(pid)
                continue
            if self._is_excluded(command):
                skipped.append(pid)
                continue
            if not self._matches_any(command, self.cleanup_patterns):
                continue
            matched.append(pid)

        for pid in matched:
            try:
                os.kill(pid, signal.SIGTERM)
                terminated.append(pid)
            except ProcessLookupError:
                pass
            except Exception as exc:
                errors.append(f"SIGTERM {pid}: {type(exc).__name__}: {exc}")

        if terminated:
            time.sleep(self.cleanup_grace_seconds)

        for pid in list(terminated):
            if not self._pid_alive(pid):
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as exc:
                errors.append(f"SIGKILL {pid}: {type(exc).__name__}: {exc}")

        return CleanupResult(matched, terminated, skipped, errors)

    def _focus_existing_dashboard_window(self, url: str) -> bool:
        for target in (self.dashboard_title, "JUNO Assist", "localhost:5173", "127.0.0.1:5173", url):
            if target and self._wmctrl_activate(target):
                return True
        return False

    @staticmethod
    def _wmctrl_activate(target: str) -> bool:
        try:
            result = subprocess.run(["wmctrl", "-a", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.8)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _wmctrl_close(target: str) -> bool:
        try:
            result = subprocess.run(["wmctrl", "-c", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.8)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _process_rows() -> list[tuple[int, str]]:
        try:
            result = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, timeout=1.5)
            if result.returncode != 0:
                return []
            rows: list[tuple[int, str]] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    continue
                try:
                    rows.append((int(parts[0]), parts[1]))
                except ValueError:
                    continue
            return rows
        except Exception:
            return []

    def _is_excluded(self, command: str) -> bool:
        default_exclusions = (
            r"\broscore\b",
            r"\brosmaster\b",
            r"\brosout\b",
            r"\bbackend/main\.py\b",
            r"\buvicorn\b.*\bbackend\b",
            r"\bpytest\b",
        )
        return self._matches_any(command, default_exclusions) or self._matches_any(command, self.cleanup_exclude_patterns)

    @staticmethod
    def _matches_any(command: str, patterns: Iterable[str]) -> bool:
        return any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in patterns if pattern)

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
