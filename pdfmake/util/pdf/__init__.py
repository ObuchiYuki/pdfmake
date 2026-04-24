#
# __init__.py
# pdfmake.util.pdf
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

from pdfmake.util.pdf.compress_level import PDFCompressLevel
from pdfmake.util.pdf.compressor import PDFCompressor, is_ghostscript_available
from pdfmake.util.pdf.document import PDFDocument

__all__ = [
    "PDFCompressLevel",
    "PDFCompressor", "is_ghostscript_available",
    "PDFDocument",
]
