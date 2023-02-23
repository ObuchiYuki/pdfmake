# PDFMAKE

pdfmake is a command line tools (CLI)

A package of 3 tools. 
- pdfmake: Make compressed pdf from directories/images.
- pdfunpack: Extract all images from pdf files.
- pdfcompress: Extract all images and remake pdfs.

## install

```shell
$ pip install -r requirements.txt
```

## Usage

##### PDFMake

```shell
$ python PDFMake.py [args...]
```

```
usage: pdfmake [-h] [-s {nolimit|small|medium|large|\d+x\d+}] [-o OUTPUT] [-d] [-c {none,default,high,very_high}] inputs [inputs ...]

Convert images to PDF.

positional arguments:
  inputs                Input images or directory.

options:
  -h, --help            show this help message and exit
  -s {nolimit|small|medium|large|\d+x\d+}, --size {nolimit|small|medium|large|\d+x\d+}
                        Image max size in PDF. small: 1200x1200, medium: 1500x1500, large: 2000x2000 (default: nolimit)
  -o OUTPUT, --output OUTPUT
                        Output directory. (default: input file directory)
  -d, --delete          Delete images/directories after convert.
  -c {none,default,high,very_high}, --compress {none,default,high,very_high}
                        PDF Compression Level.
```

##### PDFUnpack

```shell
$ python PDFUnpack.py [args...]
```

```
usage: pdfunpack [-h] [-o OUTPUT] inputs [inputs ...]

Convert images to PDF.

positional arguments:
  inputs                Input images or directory.

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory.
```



##### PDFCompress

```shell
$ python PDFCompress.py [args...]
```

```
usage: pdfcompress [-h] [-s {nolimit|small|medium|large|\d+x\d+}] [-o OUTPUT] [-d] [-c {none,default,high,very_high}] [-f] inputs [inputs ...]

Convert images to PDF.

positional arguments:
  inputs                input images or directory.

options:
  -h, --help            show this help message and exit
  -s {nolimit|small|medium|large|\d+x\d+}, --size {nolimit|small|medium|large|\d+x\d+}
                        Image max size in PDF. small: 1200x1200, medium: 1500x1500, large: 2000x2000 (default: nolimit)
  -o OUTPUT, --output OUTPUT
                        Output directory. (default: input file directory)
  -d, --delete          delete images/directories after convert.
  -c {none,default,high,very_high}, --compress {none,default,high,very_high}
                        PDF Compression Level.
  -f, --force_override  override an original pdf.
```

