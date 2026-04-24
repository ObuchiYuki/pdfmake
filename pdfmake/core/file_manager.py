#
# file_manager.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

import shutil
import atexit
import os
from pathlib import Path
from uuid import uuid4 as uuid

from pdfmake.core.errors import InternalError


class FileManager:
    command_name: str
    root: Path

    def __init__(self, command_name: str, root: Path) -> None:
        self.command_name = command_name
        self.root = root
        self._cleanup_tmp_dir()
        atexit.register(self._cleanup_tmp_dir)

    def noduplicate_path(self, directory: Path, basename: str, ext: str | None) -> Path:
        return directory / self._noduplicate_filename(directory, basename, ext)

    def _noduplicate_filename(self, directory: Path, basename: str, ext: str | None) -> str:
        filename = f"{basename}.{ext}" if ext else basename
        counter = 2
        while (directory / filename).exists():
            filename = f"{basename} ({counter}).{ext}" if ext else f"{basename} ({counter})"
            counter += 1
        return filename

    def command_directory(self) -> Path:
        """Persistent data directory for options/settings."""
        self._create_command_dir()
        return self._command_path

    def temporary_directory(self) -> Path:
        self._create_tmp_dir()
        return self._tmp_path

    def unique_temporary_directory(self) -> Path:
        dirpath = self.temporary_directory() / uuid().hex
        dirpath.mkdir(parents=True, exist_ok=True)
        return dirpath

    @property
    def _command_path(self) -> Path:
        return self.root / f".{self.command_name}({os.getpid()})"

    @property
    def _tmp_path(self) -> Path:
        return self.root / f".tmp_{self.command_name}({os.getpid()})"

    def _cleanup_tmp_dir(self):
        try:
            if self._tmp_path.exists():
                shutil.rmtree(self._tmp_path)
        except Exception:
            raise InternalError("Cleanup temporary directory failed.")

    def _create_tmp_dir(self):
        try:
            self._tmp_path.mkdir(exist_ok=True)
        except Exception:
            raise InternalError("Create temporary directory failed.")

    def _create_command_dir(self):
        try:
            self._command_path.mkdir(exist_ok=True)
        except Exception:
            raise InternalError("Create command directory failed.")
