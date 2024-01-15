import time
from dataclasses import dataclass, field
from pathlib import Path
from argparse import ArgumentParser, RawTextHelpFormatter, Namespace

import tqdm
from PIL import Image
from reportlab.pdfgen.canvas import Canvas

import util
import util.parallax as parallax
import util.style as style
import command

@dataclass
class PDFMakeTask:
    @dataclass
    class Options:
        output: Path | None
        resizemode: command.ResizeMode
        compressmode: command.CompressMode

    input_path: Path
    options: Options 

    printer: parallax.SingleLinePrinter
    progress_printer: parallax.SingleLinePrinter
    spinner: parallax.Spinner
    dot_spinner: parallax.Spinner = field(default_factory=parallax.Spinner.ellipsis)
    
    status = "Waiting"
    icon: str | None = None
    show_spinner = False
    show_dot_spinner = False
    finished = False

    @property
    def name(self):
        return self.input_path.absolute().name
    
    @property
    def output_path(self) -> Path:
        return self.options.output or self.input_path.parent
    
    def update_status_message(self):
        message = ""
        if self.show_spinner:
            message += self.spinner.next()
            message += " "
        elif self.icon is not None:
            message += self.icon
            message += " "

        message += self.status

        if self.show_dot_spinner:
            message += self.dot_spinner.next()

        message += ": "
        message += self.name
        
        self.printer.print(message)


class PDFMake:
    filemanager: util.FileManager

    def __init__(self, filemanager: util.FileManager) -> None:
        self.filemanager = filemanager

    def find_images(self, directory_path: Path, task: PDFMakeTask) -> list[Path]:
        task.status = f"Finding images"
        task.show_spinner = True
        task.show_dot_spinner = True
        image_exts =  {"png", "jpeg", "jpg", "webp", "heic"}

        image_pathes: list[Path] = []

        for path in directory_path.iterdir():
            if path.suffix.lstrip('.') in image_exts and not path.name.startswith("."):
                image_pathes.append(path)

        util.natural_sort(image_pathes)

        return image_pathes

    def resize_image(self, image_pathes: list[Path], task: PDFMakeTask) -> list[Path]:
        if task.options.resizemode.no_limit:
            return image_pathes
        
        size_to_resize = task.options.resizemode.size
        task.status = f"Resizing to {size_to_resize}"
        task.show_spinner = True
        task.show_dot_spinner = True

        nimage_pathes: list[Path] = []
        tmp_compress_path = self.filemanager.unique_temporary_directory()

        for image_path in tqdm.tqdm(
            image_pathes,
            file=task.progress_printer, 
            ncols=task.progress_printer.ncols, 
            ascii=False,
            unit="page",
        ):
            nimage_path = image_path
            nimage_path = tmp_compress_path / (image_path.name + ".png")
            image = Image.open(image_path)
            if image.size[0] >= size_to_resize[0] or image.size[1] >= size_to_resize[1]:
                image.thumbnail(size_to_resize, Image.Resampling.LANCZOS)
                image.save(nimage_path)
                nimage_pathes.append(nimage_path)
            else:
                nimage_pathes.append(image_path)

        return nimage_pathes
        
    def save_pdf(self, task: PDFMakeTask, output_path: Path, image_pathes: list[Path]):
        task.status = f"Generating PDF"
        task.show_spinner = True
        task.show_dot_spinner = True
        canvas = Canvas(str(output_path.absolute()))

        for image_path in tqdm.tqdm(
            image_pathes, 
            file=task.progress_printer,
            ncols=task.progress_printer.ncols, 
            ascii=False,
            unit="page",
        ):
            image = Image.open(image_path)
            canvas.setPageSize(image.size)
            canvas.drawImage(image_path, 0, 0)
            canvas.showPage()
        
        canvas.save()


class PDFMakeCommand:
    logger: util.Logger
    filemanager: util.FileManager

    parser: ArgumentParser
    
    parallax_executor: parallax.ParallaxExecutor
    option_parser: command.OptionParser

    make: PDFMake

    def __init__(self, filemanager: util.FileManager, logger: util.Logger, parser: ArgumentParser | None = None) -> None:
        self.logger = logger
        self.filemanager = filemanager
        self.parallax_executor = parallax.ParallaxExecutor()
        self.option_parser = command.OptionParser(logger)
        self.make = PDFMake(filemanager)

        self.parser = parser or ArgumentParser(
            prog=logger.command_name,
            description="Convert images to PDF.",
            formatter_class=RawTextHelpFormatter
        )
        self.parser.add_argument(
            "inputs", nargs="+", 
            help="Input images or directory."
        )
        self.parser.add_argument(
            "-t", "--type", default=None,
            choices=["comic", "illust", "photo", "novel"],
            help="Compress and resize type. (default: comic) \n- comic: -s medium -c default\n- illust: -s large -c very_low\n- photo: -s nolimit -c very_low\n- novel: -s nolimit -c default"
        )
        self.parser.add_argument(
            "-s", "--size", type=str, default="medium", 
            choices=util.RegexChoice(r"nolimit|small|medium|large|\d+x\d+"), 
            help="Image max size in PDF (aspect fit) (default: medium). \n- small: 1200x1200\n- medium: 1500x1500\n- large: 2000x2000\n- nolimit: input size"
        )
        self.parser.add_argument(
            "-c", "--compress", type=str, default="default", 
            choices=["none", "very_low", "low", "default", "high", "very_high"],
            help="PDF Compression Level (default: default).\n- very_low: 72 dpi\n- low: 150 dpi\n- default: auto\n- high: 300 dpi\n- very_high: 300 dpi~"
        )
        self.parser.add_argument(
            "-p", "--parallel", type=int, default=None,
            help="Parallel count. (default: 4)"
        )
        self.parser.add_argument(
            "-o", "--output", default=None, 
            help="Output directory. (default: input file directory)"
        )

    def run(self, args: Namespace):
        parallel_count = args.parallel or 4
        input_pathes = [Path(i) for i in args.inputs]

        output = self.option_parser.parse_output(args.output)
        resizemode, compressmode = self.option_parser.parse_preprocess(args.compress, args.size, args.type)
        
        options = PDFMakeTask.Options(
            output=output,
            resizemode=resizemode, 
            compressmode=compressmode
        )

        self.parallax_executor.max_parallel = parallel_count

        printer = parallax.MultilinePrinter(
            nlines=len(input_pathes),
            root_prefix=style.styled(f"[{self.logger.command_name}] ", style.Color.BLUE)
        )

        tasks: list[PDFMakeTask] = []
        for i, input_path in enumerate(input_pathes):
            subprinter = printer.printer(i)
            task = PDFMakeTask(
                input_path=input_path,
                options=options,
                printer=subprinter,
                progress_printer=subprinter.subprinter(prefix="          └ "),
                spinner=parallax.Spinner.dots(offset=i)
            )
            tasks.append(task)
            self.parallax_executor.register(self._run_task, task)

        while not all([task.finished for task in tasks]):
            try:
                time.sleep(0.1)
            except:
                break
            for task in tasks:
                task.update_status_message()

        printer.terminate()
        
    def _run_task(self, task: PDFMakeTask):
        try: 
            output_path = self.filemanager.noduplicate_path(task.output_path, basename=task.name, ext="pdf")
            image_pathes = self.make.find_images(task.input_path, task)
            image_pathes = self.make.resize_image(image_pathes, task)
            self.make.save_pdf(task, output_path, image_pathes)
            task.icon = style.styled("✓", style.Color.GREEN)
            task.status = style.styled("Success", style.Color.GREEN)
            task.progress_printer.print(f"Saved to {output_path.absolute().name}")
        except Exception as e:
            task.status = style.styled(f"{e.__class__.__name__}", style.Color.RED)
            task.icon = style.styled("✗", style.Color.RED)
            task.progress_printer.print(f"{e}")
        finally:
            task.show_spinner = False
            task.show_dot_spinner = False
            task.finished = True
            task.update_status_message()


if __name__ == "__main__":
    logger = util.Logger(command_name="pdfmake")
    filemanager = util.FileManager(command_name=logger.command_name, root=Path())
    pdfmake = PDFMakeCommand(filemanager, logger)
    args = pdfmake.parser.parse_args()
    pdfmake.run(args)