# pdfmake

PDF の作成・画像抽出・圧縮を行う CLI ツールキット。

**[English README](README.md)**

## 機能

- **make** — 画像ディレクトリから圧縮 PDF を作成
- **unpack** — PDF ファイルから全画像を抽出
- **compress** — PDF を再エンコードしてファイルサイズを縮小

## インストール

```bash
pip install -e .
```

### Ghostscript（任意、PDF 圧縮用）

| OS      | コマンド                                       |
|---------|-----------------------------------------------|
| macOS   | `brew install ghostscript`                    |
| Windows | `winget install -e --id ArtifexSoftware.GhostScript` |
| Linux   | `apt-get install ghostscript`                 |

> Ghostscript は `make` の `-c`（圧縮）オプションおよび `compress` コマンドでのみ必要です。未インストールの場合、Ghostscript 圧縮なしで PDF が生成されます。

## 使い方

インストール後、`pdfmake` コマンドが使用可能になります:

```bash
# 画像ディレクトリから PDF を作成（デフォルトコマンド）
pdfmake make dir1/ dir2/

# オプション付き
pdfmake make dir1/ -t comic -p 4 -o ./output/

# PDF から画像を抽出
pdfmake unpack file.pdf

# 既存 PDF を圧縮
pdfmake compress file.pdf -t comic -f
```

### `make` — 画像から PDF

```
pdfmake make [inputs...] [-t TYPE] [-s SIZE] [-c COMPRESS] [-p PARALLEL] [-o OUTPUT]
```

- `inputs` — 画像ファイルまたは画像を含むディレクトリ
- `-t, --type` — プリセット: `comic`, `illust`, `photo`, `novel`
- `-s, --size` — 最大画像サイズ: `small`, `medium`, `large`, `nolimit`, または `幅x高さ`
- `-c, --compress` — Ghostscript 圧縮: `none`, `very_low`, `low`, `default`, `high`, `very_high`
- `-p, --parallel` — 並列タスク数（デフォルト: 4）
- `-o, --output` — 出力ディレクトリ

### `unpack` — PDF から画像

```
pdfmake unpack [inputs...] [-o OUTPUT]
```

- `inputs` — 画像を抽出する PDF ファイル
- `-o, --output` — 出力ディレクトリ

### `compress` — PDF 再エンコード

```
pdfmake compress [inputs...] [-t TYPE] [-s SIZE] [-c COMPRESS] [-p PARALLEL] [-o OUTPUT] [-f]
```

- PDF を展開 → 画像をリサイズ → PDF を再生成 → ファイルサイズを比較
- `-f, --force-override` — 元の PDF ファイルを置換（結果が小さい場合のみ）

### 開発

```bash
# インストールなしで実行
python run.py make dir1/
python run.py unpack file.pdf
```

## ライセンス

MIT — Copyright (c) 2023 ObuchiYuki
