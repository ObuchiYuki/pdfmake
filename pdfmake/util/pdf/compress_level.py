#
# compress_level.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

from enum import Enum


class PDFCompressLevel(Enum):
    none = -1
    very_high = 0
    high = 1
    default = 2
    low = 3
    very_low = 4

    def display_string(self) -> str:
        return {
            PDFCompressLevel.very_high: "Very High",
            PDFCompressLevel.high: "High",
            PDFCompressLevel.default: "Default",
            PDFCompressLevel.low: "Low",
            PDFCompressLevel.very_low: "Very Low",
            PDFCompressLevel.none: "None",
        }.get(self, "Unknown")

    @staticmethod
    def from_str(string: str) -> "PDFCompressLevel | None":
        mapping = {
            "default": PDFCompressLevel.default,
            "high": PDFCompressLevel.high,
            "very_high": PDFCompressLevel.very_high,
            "low": PDFCompressLevel.low,
            "very_low": PDFCompressLevel.very_low,
            "none": PDFCompressLevel.none,
        }
        return mapping.get(string)

    def gs_name(self) -> str:
        """Ghostscript -dPDFSETTINGS name."""
        mapping = {
            PDFCompressLevel.very_high: "screen",
            PDFCompressLevel.high: "ebook",
            PDFCompressLevel.default: "default",
            PDFCompressLevel.low: "printer",
            PDFCompressLevel.very_low: "prepress",
        }
        name = mapping.get(self)
        if name is None:
            raise ValueError(f"PDFCompressLevel.{self.name} has no gs_name")
        return name
