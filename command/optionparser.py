from pathlib import Path
from dataclasses import dataclass
from typing import Any

import util
import util.pdf as pdf

@dataclass
class ResizeMode:
    no_limit: bool
    size: tuple[int, int]

@dataclass
class CompressMode:
    no_compress: bool
    level: pdf.PDFCompressLevel 

class OptionParser:
    logger: util.Logger

    def __init__(self, logger: util.Logger) -> None:
        self.logger = logger

    def parse_preprocess(self, compress: Any | None, size: Any | None, type: Any | None) -> tuple[ResizeMode, CompressMode]:
        resize_mode = self.parse_size(size)
        compress_mode = self.parse_compress(compress)
        
        if type == "comic":
            resize_mode = ResizeMode(no_limit=False, size=(2000, 2000))
            compress_mode = CompressMode(no_compress=False, level=pdf.PDFCompressLevel.default)
        elif type == "illust":
            resize_mode = ResizeMode(no_limit=False, size=(2000, 2000))
            compress_mode = CompressMode(no_compress=False, level=pdf.PDFCompressLevel.very_low)
        elif type == "photo":
            resize_mode = ResizeMode(no_limit=True, size=(0, 0))
            compress_mode = CompressMode(no_compress=False, level=pdf.PDFCompressLevel.very_low)
        elif type == "novel":
            resize_mode = ResizeMode(no_limit=True, size=(0, 0))
            compress_mode = CompressMode(no_compress=True, level=pdf.PDFCompressLevel.default)
        
        return resize_mode, compress_mode

    
    def parse_compress(self, compress_str: Any | None) -> CompressMode:
        if compress_str is None:
            return CompressMode(no_compress=True, level=pdf.PDFCompressLevel.default)
        
        level = pdf.PDFCompressLevel.from_str(compress_str)
        if level is None:
            self.logger.error(f"Unkown compress mode '{compress_str}'.")
            exit(1)

        if level == pdf.PDFCompressLevel.none:
            return CompressMode(no_compress=True, level=pdf.PDFCompressLevel.default)

        return CompressMode(no_compress=False, level=level)

    def parse_output(self, output_str: Any | None) -> Path | None:
        output: Path | None = None
        if isinstance(output_str, str):
            output_path = Path(output_str)
            if not output_path.exists():
                raise util.CommandError(f"Output path '{output_str}' dose not exist.")
            output = output_path

        return output
    
    def parse_size(self, size_str: Any | None) -> ResizeMode:
        size: tuple[int, int] = (2000, 2000)
        no_limit = False
        if isinstance(size_str, str):
            try:
                if size_str == "nolimit":
                    no_limit = True
                elif size_str == "small":
                    size = (1200, 1200)
                elif size_str == "medium":
                    size = (1500, 1500)
                elif size_str == "large":
                    size = (2000, 2000)
                else:
                    esize = [int(s) for s in size_str.split("x")]
                    size = (esize[0], esize[1])
            except:
                no_limit = True
                self.logger.error(f"Size specification '{size_str}' parse failed. Using default mode. (nolimit)")

        return ResizeMode(no_limit=no_limit, size=size)
