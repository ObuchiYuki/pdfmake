#
# unpack.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

import os
from pathlib import Path
from argparse import ArgumentParser, Namespace

import tqdm

from pdfmake.core import Logger, FileManager, CommandError


def _require_fitz():
    """Lazy import of PyMuPDF."""
    try:
        import fitz
        return fitz
    except ImportError:
        print("\033[0;31mPyMuPDF is required for PDF unpacking.\033[0m")
        print()
        print("  pip install PyMuPDF")
        raise SystemExit(1)


class PDFUnpacker:
    """Core logic: extract images from a PDF."""

    logger: Logger
    filemanager: FileManager

    def __init__(self, filemanager: FileManager, logger: Logger) -> None:
        self.logger = logger
        self.filemanager = filemanager

    def unpack_pdf(self, pdf_path: Path, output_path: Path):
        fitz = _require_fitz()

        self.logger.important(f"Unpack PDF '{pdf_path.name}'")
        if not output_path.exists() or not output_path.is_dir():
            raise CommandError("Output directory not found.")
        if not pdf_path.exists():
            raise CommandError("File not found.")

        document = fitz.Document(pdf_path)
        extracted_xrefs: set[int] = set()
        page_to_xref: list[int] = []

        self.logger.log("Extracting images...")
        for page in tqdm.tqdm(document):  # type: ignore[arg-type]
            for image in page.get_images():
                xref = image[0]
                if xref not in extracted_xrefs:
                    extracted_xrefs.add(xref)
                    page_to_xref.append(xref)

        self.logger.log(f"Saving {len(page_to_xref)} images...")
        for count, xref in enumerate(tqdm.tqdm(page_to_xref), start=1):
            img = document.extract_image(xref)
            with open(output_path / f"page_{count:04}.png", "wb") as f:
                f.write(img["image"])

        self.logger.important(f"Unpack PDF '{pdf_path.name}' Done")


class UnpackCommand:
    """CLI command: extract images from PDF files."""

    logger: Logger
    filemanager: FileManager
    parser: ArgumentParser
    unpacker: PDFUnpacker

    def __init__(self, filemanager: FileManager, logger: Logger, parser: ArgumentParser | None = None) -> None:
        self.logger = logger
        self.filemanager = filemanager
        self.unpacker = PDFUnpacker(filemanager, logger)

        self.parser = parser or ArgumentParser(
            prog=logger.command_name,
            description="Extract images from PDF files.",
        )
        self._setup_arguments(self.parser)

    @staticmethod
    def _setup_arguments(parser: ArgumentParser):
        parser.add_argument("inputs", nargs="+", help="Input PDF files.")
        parser.add_argument("-o", "--output", default=None, help="Output directory.")

    def run(self, args: Namespace):
        output = Path()
        if isinstance(args.output, str):
            output_path = Path(args.output)
            if not output_path.exists():
                raise CommandError(f"Output path '{args.output}' does not exist.")
            output = output_path

        input_paths = [Path(i) for i in args.inputs]

        for path in input_paths:
            try:
                filename = self.filemanager.noduplicate_path(output, path.stem, ext=None)
                output_directory = output / filename.name
                os.makedirs(output_directory, exist_ok=True)
                self.unpacker.unpack_pdf(path, output_directory)
            except Exception as e:
                self.logger.error(f"Unpack '{path.name}' failed: {e}")
