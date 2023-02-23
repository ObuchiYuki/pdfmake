from pathlib import Path
from dataclasses import dataclass
from typing import Any

from Core.Error import CommandError
from Core.Logger import Logger

from Module.PDFCompresser import PDFCompressLevel

@dataclass
class ResizeMode:
    no_limit: bool
    size: tuple[int, int]

@dataclass
class CompressMode:
    no_compress: bool
    level: PDFCompressLevel 

class OptionParser:
    logger: Logger

    def __init__(self, logger: Logger) -> None:
        self.logger = logger
    
    def parse_compress(self, compress_str: Any | None) -> CompressMode:
        if compress_str == "none":
            return CompressMode(no_compress=True, level=PDFCompressLevel.default)
        if compress_str == "default":
            return CompressMode(no_compress=False, level=PDFCompressLevel.default)
        if compress_str == "high":
            return CompressMode(no_compress=False, level=PDFCompressLevel.high)
        if compress_str == "very_high":
            return CompressMode(no_compress=False, level=PDFCompressLevel.very_high)
        
        self.logger.error(f"Unkown compress mode '{compress_str}'. Using default mode. (default)")
        return CompressMode(no_compress=False, level=PDFCompressLevel.default)

    def parse_output(self, output_str: Any | None) -> Path | None:
        output: Path | None = None
        if isinstance(output_str, str):
            output_path = Path(output_str)
            if not output_path.exists():
                raise CommandError(f"Output path '{output_str}' dose not exist.")
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
