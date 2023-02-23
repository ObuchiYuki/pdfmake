import os
import shutil
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass

import tqdm
from PIL import Image

from Core.lib.regex_check import regex_check
from Core.Error import CommandError
from Core.Logger import Logger
from Core.FileManager import FileManager
from Core.PDFDocument import PDFDocument

from Module.PDFCompresser import PDFCompresser
from Module.OptionParser import OptionParser, ResizeMode, CompressMode

image_exts =  {"png", "jpeg", "jpg", "webp", "heic"}


class PDFMake:
    command_name: str
    logger: Logger
    filemanager: FileManager
    compressor: PDFCompresser
    option_parser: OptionParser

    @dataclass
    class Options:
        delete: bool
        resizemode: ResizeMode
        compressmode: CompressMode

    def __init__(self, command_name: str, filemanager: FileManager, logger: Logger) -> None:    
        self.command_name = command_name
        self.logger = logger
        self.filemanager = filemanager
        self.compressor = PDFCompresser(filemanager=self.filemanager, logger=self.logger)
        self.option_parser = OptionParser(logger)

    def run(self, arguments: list[str]):
        parser = ArgumentParser(prog=self.command_name, description="Convert images to PDF.")
        parser.add_argument("inputs", nargs="+", help="Input images or directory.")
        parser.add_argument("-s", "--size", type=str, default="nolimit", choices=regex_check(r"nolimit|small|medium|large|\d+x\d+"), 
                            help="Image max size in PDF. small: 1200x1200, medium: 1500x1500, large: 2000x2000 (default: nolimit)")
        parser.add_argument("-o", "--output", default=None, help="Output directory. (default: input file directory)")
        parser.add_argument("-d", "--delete", default=False, action="store_true", help="Delete images/directories after convert.")
        parser.add_argument("-c", "--compress", type=str, default="default", choices=["none", "default", "high", "very_high"], help="PDF Compression Level.")

        res = parser.parse_args(arguments)
        
        delete = res.delete or False
        output = self.option_parser.parse_output(res.output)
        resizemode = self.option_parser.parse_size(res.size)
        compressmode = self.option_parser.parse_compress(res.compress)

        options = PDFMake.Options(delete=delete, resizemode=resizemode, compressmode=compressmode)

        # ================================================== #
        # input #
        input_path = [Path(i) for i in res.inputs]

        directory_pathes: list[Path] = []
        images_pathes: list[Path] = []

        for path in input_path:
            if not path.exists():
                self.logger.error(f"File not found '{path}'.")
                continue

            if path.is_dir():
                directory_pathes.append(path)
            elif path.suffix.lstrip('.') in image_exts:
                images_pathes.append(path)
            else:
                self.logger.error(f"Files with the extension '{path.suffix}' are not supported.")


        # ================================================== #
        # convert #
        if len(images_pathes):
            self.make_pdf_from_images(name=images_pathes[0].name, options=options, output=output or Path(), images=images_pathes)
        if len(directory_pathes):
            self.make_pdf_from_directories(options=options, output=output, directories=directory_pathes)

    def make_pdf_from_directories(self, options: Options, output: Path | None, directories: list[Path]):
        if output is not None:
            output.mkdir(parents=True, exist_ok=True)
        for directory in directories:
            self.make_pdf_from_directory(options, output, directory)
                
    def make_pdf_from_directory(self, options: Options, output: Path | None, directory: Path) -> Path | None:
        try:
            if not directory.is_dir():
                raise CommandError(f"{directory.name} is not directory.")
            images = [p for p in directory.iterdir() if p.suffix.lstrip('.') in image_exts and not p.name.startswith(".")]
            images.sort()
            if len(images):
                self.logger.log(f"{len(images)} images found in '{directory.name}'.")
                output_result = self.make_pdf_from_images(name=directory.name, options=options, output=output or directory.parent, images=images)
                if options.delete:
                    shutil.rmtree(directory)

                return output_result
            else:
                self.logger.error(f"No images found in {directory.name}.")
        except Exception as e:
            self.logger.error(f"Convert '{directory.name}' to PDF failed with error.")
            self.logger.error(str(e))
        
        return None

    def make_pdf_from_images(self, name: str, output: Path, options: Options, images: list[Path]) -> Path:
        self.logger.important(f"Start converting '{name}'")

        document = PDFDocument(title=name, author=self.command_name, logger=self.logger)
        
        if not options.resizemode.no_limit:
            size_to_resize = options.resizemode.size
            self.logger.log(f"Resizing images to {size_to_resize}...")

            tmp_compress_path = self.filemanager.unique_temporary_directory()

            for image_path in tqdm.tqdm(images):
                n_image_path = image_path
                n_image_path = tmp_compress_path / image_path.name
                image = Image.open(image_path)
                if image.size[0] >= size_to_resize[0] or image.size[1] >= size_to_resize[1]:
                    image.thumbnail(size_to_resize, Image.Resampling.LANCZOS)
                    image.save(n_image_path)
                    document.append_page(n_image_path)
                else:
                    document.append_page(image_path)
        else:
            for image_path in images:
                document.append_page(image_path)
        output_path = self.filemanager.noduplicate_path(output, basename=name, ext="pdf")

        if not options.compressmode.no_compress:
            tmp_path = self.filemanager.noduplicate_path(self.filemanager.temporary_directory(), basename=name, ext="pdf")
            document.save_pdf(tmp_path)
            self.compressor.compress(options.compressmode.level, tmp_path, output_path)
            os.remove(tmp_path)                                    
        else:
            document.save_pdf(output_path)

        self.logger.important(f"PDF '{name}' generated.")

        return output_path


import sys

if __name__ == "__main__":
    command_name = "pdfmake"
    logger = Logger(command_name=command_name, is_debug=False)
    filemanager = FileManager(command_name=command_name, root=Path(), logger=logger)
    pdfmake = PDFMake(command_name=command_name, filemanager=filemanager, logger=logger)
    pdfmake.run(sys.argv[1:])