"""Background bridge maintenance; Qt receives results on its own event loop."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal

from .bridge_install import BridgeInstaller, BridgeUse, InstallPlan, InstallReport, desktop_profile
from .settings import load_bridge, save_bridge
from .task_bridge import TaskMonitor, TaskSummary


class BridgeController(QObject):
    prepared = Signal(object)
    notice = Signal(str, str)

    def __init__(self, settings_path: Path, installer: BridgeInstaller, parent: QObject) -> None:
        super().__init__(parent)
        self.settings_path = settings_path
        self.installer = installer
        self.busy = False
        saved = load_bridge(settings_path)
        self.enabled = saved.enabled
        self.profiles = saved.profiles or (desktop_profile(),)
        self._monitor: TaskMonitor | None = None
        self._lease: BridgeUse | None = None
        self._closed = False
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sukuna-bridge")
        self._preflight: Future[InstallPlan] | None = None
        self._operation: Future[InstallReport] | None = None
        self._action = ""
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    @property
    def summary(self) -> TaskSummary:
        return self._monitor.summary if self._monitor is not None else TaskSummary()

    def start(self) -> None:
        if self.enabled and not self.busy:
            self._submit("refresh", self._refresh)

    def _refresh(self) -> InstallReport:
        self._lease = self.installer.acquire_use(self.profiles)
        return self.installer.refresh(self.profiles)

    def prepare(self) -> None:
        if not self.busy:
            self.busy = True
            self._preflight = self._executor.submit(self.installer.preflight)

    def confirm(self, plan: InstallPlan) -> None:
        if not self.busy:
            self.profiles = plan.profiles
            self._submit("install", lambda: self._install(plan))

    def _install(self, plan: InstallPlan) -> InstallReport:
        self._lease = self.installer.acquire_use(plan.profiles)
        return self.installer.install(plan)

    def disable(self) -> None:
        if self.busy:
            return
        try:
            save_bridge(self.settings_path, False, self.profiles)
        except OSError as error:
            self.notice.emit("无法保存接入设置", str(error))
            return
        self.enabled = False
        if self._monitor is not None:
            self._monitor.close()
            self._monitor = None
        self._submit("remove", self._remove)

    def _release_use(self) -> None:
        if self._lease is not None:
            self._lease.close()
            self._lease = None

    def _remove(self) -> InstallReport:
        self._release_use()
        return self.installer.remove(self.profiles)

    def _submit(self, action: str, operation: Callable[[], InstallReport]) -> None:
        self.busy = True
        self._action = action
        self._operation = self._executor.submit(self._run, action, operation)

    def _run(self, action: str, operation: Callable[[], InstallReport]) -> InstallReport:
        try:
            report = operation()
            self._record(action, report.message)
            return report
        except Exception as error:
            self._record(action, str(error))
            raise

    def _record(self, action: str, detail: str) -> None:
        self.installer.data_dir.mkdir(parents=True, exist_ok=True)
        with (self.installer.data_dir / "maintenance.log").open("a", encoding="utf-8") as stream:
            stream.write(f"[{datetime.now().isoformat(timespec='seconds')}] {action}\n{detail}\n")

    def _poll(self) -> None:
        if self._preflight is not None and self._preflight.done():
            future, self._preflight = self._preflight, None
            self.busy = False
            try:
                plan = future.result()
            except Exception as error:
                self.notice.emit("DeepSeek 接入预检失败", str(error))
            else:
                self.prepared.emit(plan)
        if self._operation is not None and self._operation.done():
            operation_future, self._operation = self._operation, None
            self.busy = False
            try:
                report = operation_future.result()
                if self._action == "install":
                    if report.ok:
                        save_bridge(self.settings_path, True, self.profiles)
                        self.enabled = True
                    else:
                        self._release_use()
                if self.enabled and self._monitor is None:
                    self._monitor = TaskMonitor()
                if report.results:
                    title = "DeepSeek 接入已更新" if report.ok else "DeepSeek 接入维护失败"
                    self.notice.emit(title, report.message)
            except Exception as error:
                if not self.enabled:
                    self._release_use()
                self.notice.emit("DeepSeek 接入维护失败", str(error)
                                 + f"\n诊断：{self.installer.data_dir / 'maintenance.log'}")

    def close(self) -> None:
        self._closed = True
        self._timer.stop()
        if self._monitor is not None:
            self._monitor.close()
            self._monitor = None
        if self._operation is not None and not self._operation.done():
            self._operation.add_done_callback(lambda future: self._release_use())
        else:
            self._release_use()
        self._executor.shutdown(wait=False, cancel_futures=True)
