#
# logger.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#


class Logger:
    is_debug: bool
    command_name: str

    def __init__(self, command_name: str, is_debug: bool = False) -> None:
        self.command_name = command_name
        self.is_debug = is_debug

    def debug(self, message: str):
        if self.is_debug:
            print(f"\033[0;33m[{self.command_name}]\033[0m {message}")

    def important(self, message: str):
        print(f"\033[0;32m[{self.command_name}] === {message} ===\033[0m")

    def log(self, message: str):
        print(f"\033[0;34m[{self.command_name}]\033[0m {message}")

    def error(self, message: str):
        print(f"\033[0;31m[{self.command_name}] {message}\033[0m")

    def exception(self, exception: Exception):
        print(f"\033[0;31m[{self.command_name}] {exception}\033[0m")
