import os, sys, shutil
from pathlib import Path
from argparse import ArgumentParser

import send2trash

from Core.Util.RegexChoice import RegexChoice
from Core.Error import CommandError
from Core.Logger import Logger
from Core.FileManager import FileManager

from Module.OptionParser import OptionParser

from PDFMake import PDFMake
from PDFUnpack import PDFUnpack

class PDFCompress:
    command_name: str
    logger: Logger
    filemanager: FileManager
    pdfmake: PDFMake
    pdfunpack: PDFUnpack
    option_parser: OptionParser

    def __init__(self, command_name: str, filemanager: FileManager, logger: Logger) -> None:    
        self.command_name = command_name
        self.logger = logger
        self.filemanager = filemanager
        self.pdfmake = PDFMake(command_name, filemanager, logger)
        self.pdfunpack = PDFUnpack(command_name, filemanager, logger)
        self.option_parser = OptionParser(logger)

    def run(self, arguments: list[str]):
        parser = ArgumentParser(prog=self.command_name, description="Convert images to PDF.")
        parser.add_argument("inputs", nargs="+", help="input images or directory.")
        parser.add_argument("-s", "--size", type=str, default="nolimit", choices=RegexChoice(r"nolimit|small|medium|large|\d+x\d+"), 
                            help="Image max size in PDF. small: 1200x1200, medium: 1500x1500, large: 2000x2000 (default: nolimit)")
        parser.add_argument("-o", "--output", default=None, help="Output directory. (default: input file directory)")
        parser.add_argument("-d", "--delete", default=False, action="store_true", help="delete images/directories after convert.")
        parser.add_argument("-c", "--compress", type=str, default="default", choices=["none", "default", "high", "very_high"], help="PDF Compression Level.")
        parser.add_argument("-f", "--force_override", default=False, action="store_true", help="override an original pdf.")

        res = parser.parse_args(arguments)

        delete = res.delete or False
        override = res.force_override or False
        output = self.option_parser.parse_output(res.output)
        resizemode = self.option_parser.parse_size(res.size)
        compressmode = self.option_parser.parse_compress(res.compress)

        options = PDFMake.Options(delete=delete, resizemode=resizemode, compressmode=compressmode)
        
        input_pathes = [Path(i) for i in res.inputs]

        for path in input_pathes:
            try:
                self.unpack_and_make_pdf(override, options, path, output or Path())
            except Exception as e:
                self.logger.exeception(e)
            print()

    def unpack_and_make_pdf(self, override: bool, options: PDFMake.Options, pdf_path: Path, ouput_path: Path):
        tmp_unpack_path = self.filemanager.unique_temporary_directory() / pdf_path.stem
        tmp_unpack_path.mkdir(parents=True, exist_ok=True)

        self.pdfunpack.unpack_pdf(pdf_path, tmp_unpack_path)

        tmp_output_path = self.filemanager.unique_temporary_directory() 
        result_path = self.pdfmake.make_pdf_from_directory(options, tmp_output_path, tmp_unpack_path)

        if result_path is None:
            raise CommandError("PDF compress failed. Nothing changed.")

        original_filesize = os.stat(pdf_path).st_size / (1024 * 1024)
        compressed_filesize = os.stat(result_path).st_size / (1024 * 1024)

        if original_filesize <= compressed_filesize:
            raise CommandError(f"PDF compress failed. ({original_filesize:.2f} MB -> {compressed_filesize:.2f} MB)")
        else:
            ratio = (compressed_filesize / original_filesize) * 100
            self.logger.log(f"PDF compress success ({ratio:.2f}%). ({original_filesize:.2f} MB -> {compressed_filesize:.2f} MB)")

        if override:
            self.logger.log(f"Moving original file to trash... ({pdf_path} -> Trash)")
            send2trash.send2trash(pdf_path)
            self.logger.important(f"PDF compressed at '{pdf_path.name}'")
            shutil.move(result_path, pdf_path)
        else:
            output_path = self.filemanager.noduplicate_path(ouput_path, pdf_path.stem, ext="pdf")
            shutil.move(result_path, output_path)

if __name__ == "__main__":
    command_name = "pdfcompress"
    logger = Logger(command_name=command_name, is_debug=False)
    filemanager = FileManager(command_name=command_name, root=Path(), logger=logger)
    pdfcomress = PDFCompress(command_name=command_name, filemanager=filemanager, logger=logger)
    pdfcomress.run(sys.argv[1:])