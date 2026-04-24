# AGENTS.md

## Project Overview

`pdfmake` is a Python CLI toolkit for PDF manipulation. Three subcommands:

- `make` — Convert image directories/files to compressed PDF
- `unpack` — Extract images from existing PDF files (requires PyMuPDF)
- `compress` — Re-encode PDFs for smaller size (unpack → resize → regenerate)

## Architecture

```
pdfmake/
├── __main__.py        # Entry point, dependency check
├── cli.py             # argparse subcommand routing
├── commands/
│   ├── make.py        # Image→PDF with parallel progress
│   ├── unpack.py      # PDF→Images using PyMuPDF (fitz)
│   └── compress.py    # PDF re-encoding (unpack→resize→make)
├── core/
│   ├── errors.py      # Exception classes
│   ├── file_manager.py# Temp dirs, dedup filenames
│   ├── logger.py      # Colored terminal logging
│   └── option_parser.py # Shared option parsing (size, compress, type)
└── util/
    ├── style.py       # ANSI color/format helpers
    ├── natural_sort.py
    ├── regex_choice.py# Regex-based argparse choices
    ├── remove_escape_sequences.py
    ├── pdf/
    │   ├── compress_level.py  # Ghostscript compression levels
    │   ├── compressor.py      # Ghostscript subprocess wrapper
    │   └── document.py        # reportlab PDF builder
    └── parallax/
        ├── actor.py              # Actor base class (mailbox + dedicated thread)
        ├── multiline_printer.py  # Actor-based fixed-line terminal output (tqdm compat)
        ├── parallax_printer.py   # Actor-based dynamic add/remove line printer
        ├── parallax_executor.py  # ThreadPoolExecutor wrapper
        └── spinner.py            # Terminal spinner animations
```

## Key Patterns

- **Absolute imports** throughout: `from pdfmake.core import Logger`
- **Lazy imports** for optional deps: `fitz` (PyMuPDF) imported only in unpack/compress
- **Actor model for terminal output**: `MultilinePrinter` and `ParallaxPrinter` extend
  `Actor`. All mutable display state lives on the actor thread; worker threads communicate
  exclusively via message-passing (`handle.print()` → mailbox → actor renders).
  `SingleLinePrinter` / `Line` are lightweight handles that never touch shared state.
- **ThreadPoolExecutor**: `ParallaxExecutor` delegates to `concurrent.futures` for
  correct worker lifecycle and task queuing.
- **Ghostscript optional**: Compression features degrade gracefully without `gs`

## External Dependencies

- `Pillow` — Image processing
- `reportlab` — PDF generation
- `tqdm` — Progress bars
- `PyMuPDF` (fitz) — PDF image extraction (unpack/compress only)
- `ghostscript` (system) — PDF compression (optional)

## Development

```bash
python run.py make dir/     # Run without installing
pip install -e .            # Editable install
```
