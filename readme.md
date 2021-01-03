# atree

An augmented version of the `tree` command.

Like `tree`, but this command-line program can show more attributes, while supporting advanced filtering.

For example, the command below shows all the `.py` files that have 5000 or more lines in the CPython repository.

```
$ atree ~/R/cpython --pattern="*.py" --show "lines>=5000"

NODE                                                                                  LINES
cpython
├── Tools
│   └── clinic
│       └── clinic.py                                                                  5144
└── Lib
    ├── _pydecimal.py                                                                  6410
    ├── pydoc_data
    │   └── topics.py                                                                 14061
    └── test
        ├── test_decimal.py                                                            5934
        ├── datetimetester.py                                                          6317
        ├── _test_multiprocessing.py                                                   5823
        ├── test_socket.py                                                             6679
        ├── test_argparse.py                                                           5370
        ├── test_logging.py                                                            5502
        ├── test_descr.py                                                              5688
        └── test_email
            └── test_email.py                                                          5484

6 directories, 11 files
```

Other use cases include

```
atree --show lines@top10
```

which shows the top 10 files that contain the most lines.

```
atree --show "mtime>=now-1week"
```

which shows all the files that are modified within one week.

```
atree --show duplicates
```

which shows all the duplicate files, in a tree-like format.

## Install

`pip install atree`


#### Pre-built binaries

It is recommended to install `atree` via `pip`. However, if you don't have `pip` or `python` in your environment, or the PATH is not properly configured, you may choose to download the pre-built binary for your platform.

###### Windows

- [atree.exe](https://github.com/aafulei/atree/releases/download/v1.0-alpha/atree.exe)

## How to Use

For some quick examples,

```
atree --examples
```

For a full list of command-line options,

```
atree --help
```

For more information, please refer to the docs.

## License

MIT

Copyright (c) 2021 Aaron Fu Lei
