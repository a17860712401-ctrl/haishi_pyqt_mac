import json
import os
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from PyQt6.QtCore import (
    QObject,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)


class OriginMonitorStateError(RuntimeError):
    """目录监控状态无法读取或保存。"""


class OriginMonitor(QObject):
    """
    监控指定目录的直接子项，并保存永久净计数。

    监控规则：
    1. D:\\origin 下新增或删除的直接子文件夹；
    2. D:\\origin\\Origin 2022(64bit) 下新增或删除的直接文件；
    3. 不递归扫描；
    4. 首次扫描只建立基准，不计数；
    5. 删除首次基准对象不减数；
    6. 删除后来计数过的对象时减数；
    7. 删除后重新创建同名对象时再次加数。
    """

    counts_changed = pyqtSignal(int, int)
    log_message = pyqtSignal(str, str)

    ROOT_DIRECTORY = Path(r"D:\origin")
    FILE_DIRECTORY = Path(
        r"D:\origin\Origin 2022(64bit)"
    )

    SCAN_INTERVAL_MS = 1000
    STATE_VERSION = 2
    APPLICATION_NAME = "SerialUdpBridge"

    def __init__(
        self,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        local_app_data = os.environ.get(
            "LOCALAPPDATA",
            str(Path.home()),
        )

        self._state_path = (
            Path(local_app_data)
            / self.APPLICATION_NAME
            / "origin_monitor_state.json"
        )

        self._folders_initialized = False
        self._files_initialized = False

        self._known_folders: Set[str] = set()
        self._counted_folders: Set[str] = set()

        self._known_files: Set[str] = set()
        self._counted_files: Set[str] = set()

        self._unavailable_paths: Set[str] = set()

        self._timer = QTimer(self)
        self._timer.setInterval(
            self.SCAN_INTERVAL_MS
        )
        self._timer.timeout.connect(
            self.scan_now
        )
    @property
    def folder_count(self) -> int:
        return len(self._counted_folders)

    @property
    def file_count(self) -> int:
        return len(self._counted_files)  

    @property
    def state_path(self) -> Path:
        return self._state_path
    
    
    def start(self) -> None:
        if self._timer.isActive():
            return

        try:
            self._load_state()
        except OriginMonitorStateError as error:
            self.log_message.emit(
                str(error),
                "ERROR",
            )
            return

        self.scan_now()
        self.counts_changed.emit(
            self.folder_count,
            self.file_count, 
        )

        self._timer.start()

        self.log_message.emit(
            "Origin 目录监控已启动，"
            f"文件夹计数：{self.folder_count}, "
            f"文件计数：{self.file_count}",
            "INFO",
        )

    def stop(self) -> None:
        self._timer.stop()

    @pyqtSlot()
    def scan_now(self) -> None:
        current_folders = self._read_direct_items(
            self.ROOT_DIRECTORY,
            expect_directories=True,
        )

        current_files = self._read_file_items()

        folders_initialized = (
            self._folders_initialized
        )
        files_initialized = (
            self._files_initialized
        )

        known_folders = set(
            self._known_folders
        )
        counted_folders = set(
            self._counted_folders
        )

        known_files = set(
            self._known_files
        )
        counted_files = set(
            self._counted_files
        )

        messages = []
        state_changed = False

        if current_folders is not None:
            folder_names = set(
                current_folders.keys()
            )

            if not folders_initialized:
                known_folders = folder_names
                folders_initialized = True
                state_changed = True

                messages.append(
                    (
                        f"已建立 {self.ROOT_DIRECTORY} "
                        "直接子文件夹基准",
                        "INFO",
                    )
                )
            else:
                added_folders = (
                    folder_names - known_folders
                )
                removed_folders = (
                    known_folders - folder_names
                )

                for name in sorted(
                    added_folders
                ):
                    counted_folders.add(name)

                    messages.append(
                        (
                            "检测到新文件夹："
                            f"{self.ROOT_DIRECTORY / current_folders[name]}",
                            "INFO",
                        )
                    )

                for name in sorted(
                    removed_folders
                ):
                    if name in counted_folders:
                        counted_folders.remove(name)

                        messages.append(
                            (
                                "检测到已计数文件夹被删除："
                                f"{self.ROOT_DIRECTORY / name}",
                                "INFO",
                            )
                        )
                    else:
                        messages.append(
                            (
                                "首次基准文件夹被删除，"
                                "累计数不变："
                                f"{self.ROOT_DIRECTORY / name}",
                                "INFO",
                            )
                        )

                if (
                    added_folders
                    or removed_folders
                ):
                    known_folders = folder_names
                    state_changed = True

        if current_files is not None:
            file_names = set(
                current_files.keys()
            )

            if not files_initialized:
                known_files = file_names
                files_initialized = True
                state_changed = True

                messages.append(
                    (
                        f"已建立 {self.FILE_DIRECTORY} "
                        "直接文件基准",
                        "INFO",
                    )
                )
                
            else:
                added_files = (
                    file_names - known_files
                )
                removed_files = (
                    known_files - file_names
                )

                for name in sorted(added_files):
                    counted_files.add(name)

                    messages.append(
                        (
                            "检测到新文件："
                            f"{self.FILE_DIRECTORY / current_files[name]}",
                            "INFO",
                        )
                    )

                for name in sorted(
                    removed_files
                ):
                    if name in counted_files:
                        counted_files.remove(name)

                        messages.append(
                            (
                                "检测到已计数文件被删除："
                                f"{self.FILE_DIRECTORY / name}",
                                "INFO",
                            )
                        )
                    else:
                        messages.append(
                            (
                                "首次基准文件被删除，"
                                "累计数不变："
                                f"{self.FILE_DIRECTORY / name}",
                                "INFO",
                            )
                        )

                if added_files or removed_files:
                    known_files = file_names
                    state_changed = True

        if not state_changed:
            return

        try:
            self._save_state(
                folders_initialized,
                files_initialized,
                known_folders,
                counted_folders,
                known_files,
                counted_files,
            )
        except OriginMonitorStateError as error:
            self.log_message.emit(
                str(error),
                "ERROR",
            )
            return

        old_folder_count = self.folder_count
        old_file_count = self.file_count

        self._folders_initialized = (
            folders_initialized
        )
        self._files_initialized = (
            files_initialized
        )

        self._known_folders = known_folders
        self._counted_folders = (
            counted_folders
        )

        self._known_files = known_files
        self._counted_files = counted_files

        for message, level in messages:
            self.log_message.emit(
                message,
                level,
            )
            
        counts_changed = (self.folder_count != old_folder_count
                          or self.file_count != old_file_count)

        if counts_changed:
            self.counts_changed.emit(
                self.folder_count,
                self.file_count,
            )

            self.log_message.emit(
                "Origin 当前计数："
                f"文件夹 {self.folder_count},"
                f"文件 {self.file_count}",
                "INFO",
            )

    def _read_file_items(
        self,
    ) -> Optional[Dict[str, str]]:
        """
        目标文件夹被删除时，将其视为空目录。

        前提是 D:\\origin 本身仍然可以访问。
        这样删除整个 Origin 2022 文件夹时，
        其中已计数的直接文件也会正确减数。
        """

        if (
            not self.FILE_DIRECTORY.exists()
            and self.ROOT_DIRECTORY.is_dir()
        ):
            self._report_unavailable(
                self.FILE_DIRECTORY,
                "目标文件夹不存在",
            )
            return {}

        return self._read_direct_items(
            self.FILE_DIRECTORY,
            expect_directories=False,
        )

    def _read_direct_items(
        self,
        directory: Path,
        expect_directories: bool,
    ) -> Optional[Dict[str, str]]:
        try:
            items: Dict[str, str] = {}

            for entry in directory.iterdir():
                matches = (
                    entry.is_dir()
                    if expect_directories
                    else entry.is_file()
                )

                if not matches:
                    continue

                normalized_name = os.path.normcase(
                    entry.name
                )

                items[normalized_name] = (
                    entry.name
                )

        except OSError as error:
            self._report_unavailable(
                directory,
                str(error),
            )
            return None

        path_key = str(directory)

        if path_key in self._unavailable_paths:
            self._unavailable_paths.remove(
                path_key
            )

            self.log_message.emit(
                f"目录恢复可访问：{directory}",
                "INFO",
            )

        return items

    def _report_unavailable(
        self,
        directory: Path,
        reason: str,
    ) -> None:
        path_key = str(directory)

        if path_key in self._unavailable_paths:
            return

        self._unavailable_paths.add(path_key)

        self.log_message.emit(
            f"暂时无法监控目录 {directory}："
            f"{reason}",
            "WARNING",
        )

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return

        try:
            data = json.loads(
                self._state_path.read_text(
                    encoding="utf-8"
                )
            )

            if (
                data.get("version")
                != self.STATE_VERSION
            ):
                raise ValueError(
                    "状态文件版本不受支持"
                )

            known_folders = self._read_name_set(
                data,
                "known_folders",
            )
            counted_folders = (
                self._read_name_set(
                    data,
                    "counted_folders",
                )
            )
            known_files = self._read_name_set(
                data,
                "known_files",
            )
            counted_files = self._read_name_set(
                data,
                "counted_files",
            )

            if not counted_folders.issubset(
                known_folders
            ):
                raise ValueError(
                    "文件夹计数状态不一致"
                )

            if not counted_files.issubset(
                known_files
            ):
                raise ValueError(
                    "文件计数状态不一致"
                )

            expected_folder_count = len(
                counted_folders
            )
            expected_file_count = len(
                counted_files
            )

            if (
                data.get("folder_count")
                != expected_folder_count
            ):
                raise ValueError(
                    "文件夹计数与状态明细不一致"
                )

            if (
                data.get("file_count")
                != expected_file_count
            ):
                raise ValueError(
                    "文件计数与状态明细不一致"
                )

            self._folders_initialized = bool(
                data.get(
                    "folders_initialized",
                    False,
                )
            )
            self._files_initialized = bool(
                data.get(
                    "files_initialized",
                    False,
                )
            )

            self._known_folders = known_folders
            self._counted_folders = (
                counted_folders
            )

            self._known_files = known_files
            self._counted_files = (
                counted_files
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            raise OriginMonitorStateError(
                "无法读取 Origin 永久计数状态："
                f"{error}。为避免累计数丢失，"
                "目录监控没有启动。"
            ) from error

    @staticmethod
    def _read_name_set(
        data: dict,
        key: str,
    ) -> Set[str]:
        values = data.get(key, [])

        if not isinstance(values, list):
            raise ValueError(
                f"{key} 必须是列表"
            )

        if not all(
            isinstance(value, str)
            for value in values
        ):
            raise ValueError(
                f"{key} 中存在非字符串"
            )

        return set(values)

    def _save_state(
        self,
        folders_initialized: bool,
        files_initialized: bool,
        known_folders: Set[str],
        counted_folders: Set[str],
        known_files: Set[str],
        counted_files: Set[str],
    ) -> None:
        data = {
            "version": self.STATE_VERSION,
            "folder_count": len(counted_folders),
            "file_count": len(counted_files),            
            "folders_initialized": (
                folders_initialized
            ),
            "files_initialized": (
                files_initialized
            ),
            "known_folders": sorted(
                known_folders
            ),
            "counted_folders": sorted(
                counted_folders
            ),
            "known_files": sorted(
                known_files
            ),
            "counted_files": sorted(
                counted_files
            ),
        }

        temporary_path = (
            self._state_path.with_suffix(
                ".tmp"
            )
        )

        try:
            self._state_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary_path.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                self._state_path
            )

        except OSError as error:
            raise OriginMonitorStateError(
                "无法保存 Origin 永久计数状态："
                f"{error}"
            ) from error