# pdfmake

CLI toolkit for creating, extracting, and compressing PDFs.

**[日本語版 README はこちら](README-ja.md)**

## Features

- **make** — Convert image directories to compressed PDF
- **unpack** — Extract all images from PDF files
- **compress** — Re-encode PDFs for smaller file size

## Install

```bash
pip install -e .
```

### Ghostscript (optional, for PDF compression)

| OS      | Command                                       |
|---------|-----------------------------------------------|
| macOS   | `brew install ghostscript`                    |
| Windows | `winget install -e --id ArtifexSoftware.GhostScript` |
| Linux   | `apt-get install ghostscript`                 |

> Ghostscript is only required for the `-c` (compress) option in `make` and for the `compress` command. Without it, PDFs are generated without Ghostscript compression.

## Usage

After installation, the `pdfmake` command is available:

```bash
# Convert directories of images to PDFs (default command)
pdfmake make dir1/ dir2/

# With options
pdfmake make dir1/ -t comic -p 4 -o ./output/

# Extract images from PDFs
pdfmake unpack file.pdf

# Compress existing PDFs
pdfmake compress file.pdf -t comic -f
```

### `make` — Images to PDF

```
pdfmake make [inputs...] [-t TYPE] [-s SIZE] [-c COMPRESS] [-p PARALLEL] [-o OUTPUT]
```

- `inputs` — Image files or directories containing images
- `-t, --type` — Preset: `comic`, `illust`, `photo`, `novel`
- `-s, --size` — Max image size: `small`, `medium`, `large`, `nolimit`, or `WxH`
- `-c, --compress` — Ghostscript compression: `none`, `very_low`, `low`, `default`, `high`, `very_high`
- `-p, --parallel` — Parallel task count (default: 4)
- `-o, --output` — Output directory

### `unpack` — PDF to Images

```
pdfmake unpack [inputs...] [-o OUTPUT]
```

- `inputs` — PDF files to extract images from
- `-o, --output` — Output directory

### `compress` — Re-encode PDF

```
pdfmake compress [inputs...] [-t TYPE] [-s SIZE] [-c COMPRESS] [-p PARALLEL] [-o OUTPUT] [-f]
```

- Unpacks PDF → resizes images → regenerates PDF → compares file size
- `-f, --force-override` — Replace original PDF file (only if result is smaller)

### Development

```bash
# Run without installing
python run.py make dir1/
python run.py unpack file.pdf
```

## License

MIT — Copyright (c) 2023 ObuchiYuki
