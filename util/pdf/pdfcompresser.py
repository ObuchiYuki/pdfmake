from pathlib import Path
import subprocess
import distutils.spawn
from enum import Enum
from typing import Union

import util

class PDFCompressLevel(Enum):
    none = -1

    very_high = 0
    high = 1
    default = 2
    low = 3
    very_low = 4

    def display_string(self) -> str:
        if self == PDFCompressLevel.very_high:
            return "Very High"
        if self == PDFCompressLevel.high:
            return "High"
        if self == PDFCompressLevel.default:
            return "Default"
        if self == PDFCompressLevel.low:
            return "Low"
        if self == PDFCompressLevel.very_low:
            return "Very Low"
        if self == PDFCompressLevel.none:
            return "None"
        return "Unknown"

    @staticmethod
    def from_str(string: str) -> Union["PDFCompressLevel", None]:
        if string == "default":
            return PDFCompressLevel.default
        if string == "high":
            return PDFCompressLevel.high
        if string == "very_high":
            return PDFCompressLevel.very_high
        if string == "low":
            return PDFCompressLevel.low
        if string == "very_low":
            return PDFCompressLevel.very_low
        if string == "none":
            return PDFCompressLevel.none
        return None

    def gs_name(self) -> str:
        if self == PDFCompressLevel.very_high:
            return "screen"
        if self == PDFCompressLevel.high:
            return "ebook"
        if self == PDFCompressLevel.default:
            return "default"
        if self == PDFCompressLevel.low:
            return "printer"
        if self == PDFCompressLevel.very_low:
            return "prepress"
        if self == PDFCompressLevel.none:
            assert False, "PDFCompressLevel.none has no gs_name."
            
        return "default"


class PDFCompresser:
    enabled: bool

    logger: util.Logger
    filemanager: util.FileManager

    def __init__(self, filemanager: util.FileManager, logger: util.Logger):
        self.logger = logger
        self.filemanager = filemanager
        self.enabled = distutils.spawn.find_executable("gs") is not None
        
    def compress(self, level: PDFCompressLevel, pdf_path: Path, output_path: Path):
        if not self.enabled:
            return pdf_path
        if level == PDFCompressLevel.none:
            return pdf_path
            
        subprocess.call([
            "gs", 
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{level.gs_name()}",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={str(output_path)}",
            str(pdf_path)
        ])
        