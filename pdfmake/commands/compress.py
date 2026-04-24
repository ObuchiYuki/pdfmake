#
# compress.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

"""Compress existing PDFs by unpacking images, resizing, and regenerating."""

import os
import time
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from argparse import ArgumentParser, RawTextHelpFormatter, Namespace

import tqdm
from PIL import Image, ImageFile
from reportlab.pdfgen.canvas import Canvas

from pdfmake.core import Logger, FileManager, OptionParser, ResizeMode, CompressMode, CommandError
from pdfmake.util import natural_sort, RegexChoice, styled, Color
from pdfmake.util.parallax import MultilinePrinter, SingleLinePrinter, ParallaxExecutor, Spinner
from pdfmake.util.pdf import PDFCompressor

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 1_000_000_000

IMAGE_EXTENSIONS = {"png", "jpeg", "jpg", "webp", "heic"}


def _require_fitz():
    try:
        import fitz
        return fitz
    except ImportError:
        print("\033[0;31mPyMuPDF is required for PDF compression.\033[0m")
        print()
        print("  pip install PyMuPDF")
        raise SystemExit(1)


@dataclass
class CompressTask:
    @dataclass
    class Options:
        output: Path | None
        resizemode: ResizeMode
        compressmode: CompressMode
        override: bool

    input_path: Path
    options: Options
    printer: SingleLinePrinter
    spinner: Spinner
    progress_printer: SingleLinePrinter
    dot_spinner: Spinner = field(default_factory=Spinner.ellipsis)

    status: str = "Pending..."
    icon: str | None = None
    show_spinner: bool = True
    finished: bool = False

    @property
    def name(self) -> str:
        return self.input_path.name

    @property
    def output_path(self) -> Path:
        return self.options.output or self.input_path.parent

    def update_status_message(self):
        message = ""
        if self.show_spinner:
            message += self.spinner.next() + " "
        elif self.icon is not None:
            message += self.icon + " "
        message += styled(self.status, Color.YELLOW) + ": " + self.name
        self.printer.print(message)


class CompressCommand:
    """CLI command: compress PDF by re-encoding images."""

    logger: Logger
    filemanager: FileManager
    parser: ArgumentParser
    parallax_executor: ParallaxExecutor
    option_parser: OptionParser
    compressor: PDFCompressor

    def __init__(self, filemanager: FileManager, logger: Logger, parser: ArgumentParser | None = None) -> None:
        self.logger = logger
        self.filemanager = filemanager
        self.parallax_executor = ParallaxExecutor()
        self.option_parser = OptionParser(logger)
        self.compressor = PDFCompressor(filemanager=filemanager, logger=logger)

        self.parser = parser or ArgumentParser(
            prog=logger.command_name,
            description="Compress PDF files by re-encoding images.",
            formatter_class=RawTextHelpFormatter,
        )
        self._setup_arguments(self.parser)

    @staticmethod
    def _setup_arguments(parser: ArgumentParser):
        parser.add_argument(
            "inputs", nargs="+",
            help="Input PDF files.",
        )
        parser.add_argument(
            "-t", "--type", default=None,
            choices=["comic", "illust", "photo", "novel"],
            help=(
                "Compress and resize type. (default: comic)\n"
                "- comic: -s large -c default\n"
                "- illust: -s large -c very_low\n"
                "- photo: -s nolimit -c very_low\n"
                "- novel: -s nolimit -c default"
            ),
        )
        parser.add_argument(
            "-s", "--size", type=str, default="medium",
            choices=RegexChoice(r"nolimit|small|medium|large|\d+x\d+"),
            help=(
                "Image max size in PDF (aspect fit) (default: medium).\n"
                "- small: 1200x1200\n"
                "- medium: 1500x1500\n"
                "- large: 2000x2000\n"
                "- nolimit: input size"
            ),
        )
        parser.add_argument(
            "-c", "--compress", type=str, default="default",
            choices=["none", "very_low", "low", "default", "high", "very_high"],
            help=(
                "PDF Compression Level (default: default).\n"
                "- very_low: 72 dpi\n"
                "- low: 150 dpi\n"
                "- default: auto\n"
                "- high: 300 dpi\n"
                "- very_high: 300 dpi~"
            ),
        )
        parser.add_argument(
            "-p", "--parallel", type=int, default=None,
            help="Parallel count. (default: 4)",
        )
        parser.add_argument(
            "-o", "--output", default=None,
            help="Output directory. (default: input file directory)",
        )
        parser.add_argument(
            "-f", "--force-override", default=False, action="store_true",
            help="Override the original PDF file.",
        )

    def run(self, args: Namespace):
        _require_fitz()

        parallel_count = args.parallel or 4
        input_paths = [Path(i) for i in args.inputs]

        output = self.option_parser.parse_output(args.output)
        resizemode, compressmode = self.option_parser.parse_preprocess(args.compress, args.size, args.type)

        options = CompressTask.Options(
            output=output,
            resizemode=resizemode,
            compressmode=compressmode,
            override=args.force_override,
        )

        self.parallax_executor.max_workers = parallel_count

        printer = MultilinePrinter(
            ncols=len(input_paths),
            root_prefix=styled(f"[{self.logger.command_name}] ", Color.BLUE),
        )

        tasks: list[CompressTask] = []
        for i, input_path in enumerate(input_paths):
            subprinter = printer.printer(i)
            task = CompressTask(
                input_path=input_path,
                options=options,
                printer=subprinter,
                progress_printer=subprinter.subprinter(prefix="          ╰─ "),
                spinner=Spinner.dots(offset=i),
            )
            task.progress_printer.print("Waiting another tasks to complete...")
            tasks.append(task)
            self.parallax_executor.register(self._run_task, task)

        while not all(task.finished for task in tasks):
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                break
            for task in tasks:
                task.update_status_message()

        printer.terminate()

    def _run_task(self, task: CompressTask):
        try:
            import fitz

            pdf_path = task.input_path
            if not pdf_path.exists():
                raise CommandError(f"File not found: '{pdf_path}'")
            if not pdf_path.suffix.lower() == ".pdf":
                raise CommandError(f"Not a PDF file: '{pdf_path.name}'")

            # Step 1: Unpack PDF to images
            task.status = "Unpacking PDF..."
            task.show_spinner = True
            tmp_unpack = self.filemanager.unique_temporary_directory() / pdf_path.stem
            tmp_unpack.mkdir(parents=True, exist_ok=True)

            document = fitz.Document(pdf_path)
            extracted_xrefs: set[int] = set()
            page_to_xref: list[int] = []

            for page in document:
                for image in page.get_images():
                    xref = image[0]
                    if xref not in extracted_xrefs:
                        extracted_xrefs.add(xref)
                        page_to_xref.append(xref)

            for count, xref in enumerate(tqdm.tqdm(
                page_to_xref, unit="page", **task.progress_printer.tqdm_wrapper()
            ), start=1):
                img = document.extract_image(xref)
                with open(tmp_unpack / f"page_{count:04}.png", "wb") as f:
                    f.write(img["image"])

            # Step 2: Find and sort images
            task.status = "Finding images..."
            image_paths = [
                p for p in tmp_unpack.iterdir()
                if p.suffix.lstrip('.') in IMAGE_EXTENSIONS and not p.name.startswith(".")
            ]
            natural_sort(image_paths)

            if not image_paths:
                raise CommandError("No images extracted from PDF.")

            # Step 3: Resize images
            if not task.options.resizemode.no_limit:
                size_to_resize = task.options.resizemode.size
                task.status = f"Resizing to {size_to_resize}..."
                task.show_spinner = True
                tmp_resize = self.filemanager.unique_temporary_directory()
                resized: list[Path] = []

                for img_path in tqdm.tqdm(
                    image_paths, unit="page", **task.progress_printer.tqdm_wrapper()
                ):
                    image = Image.open(img_path)
                    if image.size[0] >= size_to_resize[0] or image.size[1] >= size_to_resize[1]:
                        resized_path = tmp_resize / (img_path.name + ".png")
                        image.thumbnail(size_to_resize, Image.Resampling.LANCZOS)
                        image.save(resized_path)
                        resized.append(resized_path)
                    else:
                        resized.append(img_path)
                image_paths = resized

            # Step 4: Generate new PDF
            task.status = "Generating PDF..."
            task.show_spinner = True
            tmp_pdf = self.filemanager.unique_temporary_directory() / f"{pdf_path.stem}.pdf"
            canvas = Canvas(str(tmp_pdf))

            for img_path in tqdm.tqdm(
                image_paths, unit="page", **task.progress_printer.tqdm_wrapper()
            ):
                image = Image.open(img_path)
                canvas.setPageSize(image.size)
                canvas.drawImage(img_path, 0, 0)
                canvas.showPage()
            canvas.save()

            # Step 5: Compress with Ghostscript
            if not task.options.compressmode.no_compress:
                task.status = "Compressing PDF..."
                task.show_spinner = True
                compressed_pdf = self.filemanager.unique_temporary_directory() / f"{pdf_path.stem}.pdf"
                self.compressor.compress(task.options.compressmode.level, tmp_pdf, compressed_pdf)
                result_pdf = compressed_pdf
            else:
                result_pdf = tmp_pdf

            # Step 6: Compare sizes
            original_size = os.stat(pdf_path).st_size
            compressed_size = os.stat(result_pdf).st_size
            original_mb = original_size / (1024 * 1024)
            compressed_mb = compressed_size / (1024 * 1024)

            if original_size <= compressed_size:
                raise CommandError(
                    f"Compression not effective ({original_mb:.2f} MB → {compressed_mb:.2f} MB)"
                )

            ratio = (compressed_size / original_size) * 100

            # Step 7: Save result
            if task.options.override:
                shutil.move(str(result_pdf), str(pdf_path))
                final_path = pdf_path
            else:
                final_path = self.filemanager.noduplicate_path(task.output_path, pdf_path.stem, ext="pdf")
                shutil.move(str(result_pdf), str(final_path))

            task.icon = styled("✓", Color.GREEN)
            task.status = styled("Completed!", Color.GREEN)
            task.progress_printer.print(
                f"{original_mb:.2f} MB → {compressed_mb:.2f} MB ({ratio:.1f}%) → {final_path.name}"
            )

        except Exception as e:
            task.status = styled(f"{e.__class__.__name__}", Color.RED)
            task.icon = styled("✗", Color.RED)
            task.progress_printer.print(str(e))
        finally:
            task.show_spinner = False
            task.finished = True
            task.update_status_message()
