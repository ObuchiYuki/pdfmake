#
# __main__.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

import sys


def _check_dependencies():
    """Verify required packages are installed before importing heavy modules."""
    try:
        import PIL        # noqa: F401
        import tqdm       # noqa: F401
        import reportlab  # noqa: F401
    except ImportError:
        print("\033[0;31mRequired dependencies are missing.\033[0m")
        print()
        print("  pip install pdfmake")
        print("  # or for development:")
        print("  pip install -e .")
        sys.exit(1)


def main():
    _check_dependencies()

    from pdfmake.cli import build_parser, dispatch
    parser = build_parser()
    args = parser.parse_args()
    dispatch(args, parser)


if __name__ == "__main__":
    main()
