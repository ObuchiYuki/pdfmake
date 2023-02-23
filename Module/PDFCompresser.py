from pathlib import Path
import subprocess
import distutils.spawn
from enum import Enum

from Core.FileManager import FileManager
from Core.Logger import Logger

class PDFCompressLevel(Enum):
    none = -1

    very_high = 0
    high = 1
    default = 2
    # low = 3
    # very_low = 4

    @staticmethod
    def from_str(string: str) -> "PDFCompressLevel":
        if string == "default":
            return PDFCompressLevel.default
        if string == "high":
            return PDFCompressLevel.high
        if string == "very_high":
            return PDFCompressLevel.very_high
        return PDFCompressLevel.default

    def gs_name(self) -> str:
        if self == PDFCompressLevel.very_high:
            return "screen"
        if self == PDFCompressLevel.high:
            return "ebook"
        if self == PDFCompressLevel.default:
            return "default"
            
        return "default"


class PDFCompresser:
    enabled: bool

    logger: Logger
    filemanager: FileManager

    def __init__(self, filemanager: FileManager, logger: Logger):
        self.logger = logger
        self.filemanager = filemanager
        self.enabled = distutils.spawn.find_executable("gs") is not None
        
    def compress(self, level: PDFCompressLevel, pdf_path: Path, output_path: Path):
        if not self.enabled:
            self.logger.error("Command 'gs' not found. Please install ghostscript.")
            return pdf_path
        if level == PDFCompressLevel.none:
            return pdf_path
            
        self.logger.log(f"Compressing PDF... (compress_level: {level.gs_name()})")

        subprocess.call([
            "gs", 
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{level.gs_name()}",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={str(output_path)}",
            str(pdf_path)
        ])
        