#
# cli.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

"""CLI entry point with subcommands: make (default), unpack, compress."""

import sys
from pathlib import Path
from argparse import ArgumentParser, RawTextHelpFormatter, Namespace

from pdfmake.core import Logger, FileManager


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="pdfmake",
        description="PDF toolkit: make PDFs from images, extract images, compress PDFs.",
        formatter_class=RawTextHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- make (default) ---
    from pdfmake.commands.make import MakeCommand
    make_parser = subparsers.add_parser(
        "make",
        help="Convert images/directories to PDF. (default command)",
        formatter_class=RawTextHelpFormatter,
    )
    MakeCommand._setup_arguments(make_parser)

    # --- unpack ---
    from pdfmake.commands.unpack import UnpackCommand
    unpack_parser = subparsers.add_parser(
        "unpack",
        help="Extract images from PDF files.",
    )
    UnpackCommand._setup_arguments(unpack_parser)

    # --- compress ---
    from pdfmake.commands.compress import CompressCommand
    compress_parser = subparsers.add_parser(
        "compress",
        help="Compress PDF files by re-encoding images.",
        formatter_class=RawTextHelpFormatter,
    )
    CompressCommand._setup_arguments(compress_parser)

    return parser


def dispatch(args: Namespace, parser: ArgumentParser):
    command = args.command

    # Default to "make" when no subcommand given
    if command is None:
        if hasattr(args, "inputs"):
            command = "make"
        else:
            parser.print_help()
            sys.exit(0)

    logger = Logger(command_name=f"pdf{command}")
    filemanager = FileManager(command_name=f"pdf{command}", root=Path())

    if command == "make":
        from pdfmake.commands.make import MakeCommand
        cmd = MakeCommand(filemanager, logger, parser=None)
        cmd.run(args)

    elif command == "unpack":
        from pdfmake.commands.unpack import UnpackCommand
        cmd = UnpackCommand(filemanager, logger, parser=None)
        cmd.run(args)

    elif command == "compress":
        from pdfmake.commands.compress import CompressCommand
        cmd = CompressCommand(filemanager, logger, parser=None)
        cmd.run(args)
