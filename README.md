# VARAT: Variable Annotation Tool for Engineering-domain Documents

## System requirements

* Python 3 (3.9.7 or later)
* Preferred: A Web Browser with MathML support
  * [Firefox](https://www.mozilla.org/firefox/) is recommended.

## Installation

The dependencies related to python library will be installed with one shot:

```shell
python -m pip install -r requirements.txt
```

In case you don't want to install the dependencies into your system, you should consider utilizing a virtual environment,
such as [venv](https://docs.python.org/3/library/venv.html) or [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv).

The TeX files are used as the input document for this tool.
[LaTeXML](https://dlmf.nist.gov/LaTeXML/) is required to use this tool.


## Usage
```shell
streamlit run streamlit_annotation.py
```


## Project structure

### Files in this repository

* `lib/` contains the project library.
* `tools/` contains our utility Python scripts.

### Files not in this repository

The annotation data is not included in this repository due to several constraints.

* `data/Anno` contains folders whose names are processes' names.
* `data/Anno/[Process name]` contains folders whose names indicate papers' authors and publication year.
  * Each folder contains the original documents (.tex), the annotation data (.xlsx), and the preprocessed docuemnts (.html and .txt).


## License

Copyright 2022 Shota KATO

This software is licenced under [the MIT license](./LICENSE).

---

Shota KATO