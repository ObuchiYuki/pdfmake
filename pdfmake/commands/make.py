#
# make.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

import time
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


@dataclass
class MakeTask:
    @dataclass
    class Options:
        output: Path | None
        resizemode: ResizeMode
        compressmode: CompressMode

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
        return self.input_path.absolute().name

    @property
    def output_path(self) -> Path:
        return self.options.output or self.input_path.parent

    def update_status_message(self):
        message = ""
        if self.show_spinner:
            message += self.spinner.next() + " "
        elif self.icon is not None:
            message += self.icon + " "

        message += styled(self.status, Color.YELLOW)
        message += ": "
        message += self.name
        self.printer.print(message)


class PDFMaker:
    """Core logic: find images, resize, generate PDF, compress."""

    filemanager: FileManager
    compressor: PDFCompressor

    def __init__(self, filemanager: FileManager, logger: Logger) -> None:
        self.filemanager = filemanager
        self.compressor = PDFCompressor(filemanager=filemanager, logger=logger)

    def find_images(self, directory_path: Path, task: MakeTask) -> list[Path]:
        task.status = "Finding images..."
        task.show_spinner = True

        image_paths: list[Path] = [
            p for p in directory_path.iterdir()
            if p.suffix.lstrip('.') in IMAGE_EXTENSIONS and not p.name.startswith(".")
        ]
        natural_sort(image_paths)
        return image_paths

    def resize_images(self, image_paths: list[Path], task: MakeTask) -> list[Path]:
        if task.options.resizemode.no_limit:
            return image_paths

        size_to_resize = task.options.resizemode.size
        task.status = f"Resizing to {size_to_resize}..."
        task.show_spinner = True

        result: list[Path] = []
        tmp_dir = self.filemanager.unique_temporary_directory()

        for image_path in tqdm.tqdm(image_paths, unit="page", **task.progress_printer.tqdm_wrapper()):
            image = Image.open(image_path)
            if image.size[0] >= size_to_resize[0] or image.size[1] >= size_to_resize[1]:
                resized_path = tmp_dir / (image_path.name + ".png")
                image.thumbnail(size_to_resize, Image.Resampling.LANCZOS)
                image.save(resized_path)
                result.append(resized_path)
            else:
                result.append(image_path)

        return result

    def save_pdf(self, task: MakeTask, output_path: Path, image_paths: list[Path]):
        task.status = "Generating PDF..."
        task.show_spinner = True
        canvas = Canvas(str(output_path.absolute()))

        for image_path in tqdm.tqdm(image_paths, unit="page", **task.progress_printer.tqdm_wrapper()):
            image = Image.open(image_path)
            canvas.setPageSize(image.size)
            canvas.drawImage(image_path, 0, 0)
            canvas.showPage()

        task.status = "Saving PDF"
        canvas.save()

    def compress_pdf(self, task: MakeTask, input_path: Path, output_path: Path):
        task.status = "Compressing PDF..."
        task.show_spinner = True
        task.progress_printer.print(f"Compress level: {task.options.compressmode.level.display_string()}")
        self.compressor.compress(task.options.compressmode.level, input_path, output_path)


class MakeCommand:
    """CLI command: convert images/directories to PDF."""

    logger: Logger
    filemanager: FileManager
    parser: ArgumentParser
    parallax_executor: ParallaxExecutor
    option_parser: OptionParser
    maker: PDFMaker

    def __init__(self, filemanager: FileManager, logger: Logger, parser: ArgumentParser | None = None) -> None:
        self.logger = logger
        self.filemanager = filemanager
        self.parallax_executor = ParallaxExecutor()
        self.option_parser = OptionParser(logger)
        self.maker = PDFMaker(filemanager, logger)

        self.parser = parser or ArgumentParser(
            prog=logger.command_name,
            description="Convert images to PDF.",
            formatter_class=RawTextHelpFormatter,
        )
        self._setup_arguments(self.parser)

    @staticmethod
    def _setup_arguments(parser: ArgumentParser):
        parser.add_argument(
            "inputs", nargs="+",
            help="Input images or directory.",
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
            "-s", "--size", type=str, default="large",
            choices=RegexChoice(r"nolimit|small|medium|large|\d+x\d+"),
            help=(
                "Image max size in PDF (aspect fit) (default: large).\n"
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

    def run(self, args: Namespace):
        parallel_count = args.parallel or 4
        input_paths = [Path(i) for i in args.inputs]

        output = self.option_parser.parse_output(args.output)
        resizemode, compressmode = self.option_parser.parse_preprocess(args.compress, args.size, args.type)

        options = MakeTask.Options(
            output=output,
            resizemode=resizemode,
            compressmode=compressmode,
        )

        self.parallax_executor.max_workers = parallel_count

        printer = MultilinePrinter(
            ncols=len(input_paths),
            root_prefix=styled(f"[{self.logger.command_name}] ", Color.BLUE),
        )

        tasks: list[MakeTask] = []

        for i, input_path in enumerate(input_paths):
            subprinter = printer.printer(i)
            task = MakeTask(
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

    def _run_task(self, task: MakeTask):
        try:
            if not task.input_path.exists():
                raise CommandError(f"Input path '{task.input_path}' does not exist.")
            if not task.input_path.is_dir():
                raise CommandError(f"Input path '{task.input_path}' is not a directory.")

            output_path = self.filemanager.noduplicate_path(task.output_path, basename=task.name, ext="pdf")
            image_paths = self.maker.find_images(task.input_path, task)

            if not image_paths:
                raise CommandError(f"No images found in '{task.name}'.")

            image_paths = self.maker.resize_images(image_paths, task)

            if task.options.compressmode.no_compress:
                pdf_output_path = output_path
            else:
                pdf_output_path = self.filemanager.unique_temporary_directory() / output_path.name

            self.maker.save_pdf(task, pdf_output_path, image_paths)

            if not task.options.compressmode.no_compress:
                self.maker.compress_pdf(task, pdf_output_path, output_path)

            task.icon = styled("✓", Color.GREEN)
            task.status = styled("Completed!", Color.GREEN)
            task.progress_printer.print(f"Saved to {output_path.name}")
        except Exception as e:
            task.status = styled(f"{e.__class__.__name__}", Color.RED)
            task.icon = styled("✗", Color.RED)
            task.progress_printer.print(str(e))
        finally:
            task.show_spinner = False
            task.finished = True
            task.update_status_message()
