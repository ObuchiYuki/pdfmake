#
# compressor.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

from pathlib import Path
import shutil
import subprocess

from pdfmake.core.logger import Logger
from pdfmake.core.file_manager import FileManager
from pdfmake.util.pdf.compress_level import PDFCompressLevel


_gs_available: bool | None = None


def is_ghostscript_available() -> bool:
    global _gs_available
    if _gs_available is None:
        _gs_available = shutil.which("gs") is not None
    return _gs_available


class PDFCompressor:
    enabled: bool
    logger: Logger
    filemanager: FileManager

    def __init__(self, filemanager: FileManager, logger: Logger):
        self.logger = logger
        self.filemanager = filemanager
        self.enabled = is_ghostscript_available()

    def compress(self, level: PDFCompressLevel, pdf_path: Path, output_path: Path):
        if not self.enabled:
            self.logger.error("Ghostscript not found. Skipping compression.")
            return pdf_path
        if level == PDFCompressLevel.none:
            return pdf_path

        subprocess.run([
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{level.gs_name()}",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_path}",
            str(pdf_path)
        ], capture_output=True)
