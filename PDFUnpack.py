import os, sys
from pathlib import Path
from argparse import ArgumentParser

import tqdm
import fitz

from Core.Error import CommandError
from Core.Logger import Logger
from Core.FileManager import FileManager

class PDFUnpack:
    command_name: str
    logger: Logger

    def __init__(self, command_name: str, filemanager: FileManager, logger: Logger) -> None:    
        self.command_name = command_name
        self.logger = logger
        self.filemanager = filemanager

    def run(self, arguments: list[str]):
        parser = ArgumentParser(prog=self.command_name, description="Convert images to PDF.")
        parser.add_argument("inputs", nargs="+", help="Input images or directory.")
        parser.add_argument("-o", "--output", default=None, help="Output directory.")
        
        res = parser.parse_args(arguments)

        # === Output === #
        output = Path()
        if isinstance(res.output, str):
            output_path = Path(res.output)
            if not output_path.exists():
                raise CommandError(f"Output path '{res.output}' dose not exist.")
            output = output_path

        # === Input === #
        input_pathes = [Path(i) for i in res.inputs]

        for path in input_pathes:
            try:
                filename = self.filemanager.noduplicate_path(output, path.stem, ext=None)
                output_directory = output / filename
                os.mkdir(output_directory)
                self.unpack_pdf(path, output_directory)
            except Exception as e:
                self.logger.error(f"Unpack '{path.name}' to images failed with error.")
                self.logger.error(str(e))
        

    def unpack_pdf(self, pdf_path: Path, output_path: Path):
        self.logger.important(f"Unpack PDF '{pdf_path.name}'")
        if not output_path.exists() or not output_path.is_dir():
            raise CommandError("Output directory not found.")
        if not pdf_path.exists():
            raise CommandError("File not found.")
        document = fitz.Document(pdf_path)
        extracted_xrefs = set()
        page_to_xref: list[int] = []

        self.logger.log(f"Extracting images...")
        for i, page in enumerate(tqdm.tqdm(document)): # type: ignore
            for image in page.get_images():
                xref = image[0]
                if xref in extracted_xrefs:
                    continue
                extracted_xrefs.add(xref)
                page_to_xref.append(xref)

        count = 1
        self.logger.log(f"Saving {len(page_to_xref)} images...")
        for xref in tqdm.tqdm(page_to_xref):
            img = document.extract_image(xref)
            with open(output_path / f"page_{count:04}.png", "wb") as f:
                f.write(img["image"])
            count += 1

        self.logger.important(f"Unpack PDF '{pdf_path.name}' Done")

if __name__ == "__main__":
    command_name = "pdfunpack"
    logger = Logger(command_name=command_name, is_debug=False)
    filemanager = FileManager(command_name=command_name, root=Path(), logger=logger)
    pdfmake = PDFUnpack(command_name=command_name, filemanager=filemanager, logger=logger)

    pdfmake.run(sys.argv[1:])