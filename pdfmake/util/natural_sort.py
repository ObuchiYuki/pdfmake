#
# natural_sort.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

import re
import typing
from pathlib import Path

T = typing.TypeVar('T', str, int, Path)


def _alphanum_key(key: typing.Any) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', str(key))]


def natural_sorted(lst: list[T]) -> list[T]:
    return sorted(lst, key=_alphanum_key)


def natural_sort(lst: list[T]) -> None:
    lst.sort(key=_alphanum_key)
