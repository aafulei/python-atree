#! /usr/bin/env python3

import abc
import argparse
import calendar
import collections
import ctypes
import datetime
import fnmatch
import functools
import hashlib
import heapq
import math
import mimetypes
import operator
import os
import platform
import re
import stat
import sys
import time
import unicodedata

try:
    import grp
    import pwd
except ImportError:
    pass

_ATREE_VERSION = "1.0"
_MACHINE = platform.machine()
_PLATFORM = platform.platform()
_PROCESSOR = platform.processor()
_PYTHON_IMPLEMENTATION = platform.python_implementation()
_PYTHON_VERSION = platform.python_version()
_SYSTEM = platform.system()
_PLATFORM_VERSION = platform.version()
ANSI_COLOR_SUPPORT = True
ANSI_COLOR_AUTO_ENABLED = True
CODE_EXTENSIONS = {
    ".4th", ".ada", ".adb", ".ads", ".agda", ".arr", ".as", ".asa", ".asax",
    ".ascx", ".asm", ".asmx", ".asp", ".aspx", ".at", ".awk", ".bat", ".btm",
    ".c", ".c++", ".cc", ".cfc", ".cl", ".clj", ".cljc", ".cljs", ".cmake",
    ".cmd", ".coffee", ".comp", ".cpp", ".cs", ".csh", ".cshtml", ".css",
    ".cu", ".cuh", ".cxx", ".d", ".dart", ".dhall", ".docker", ".dts", ".dtsi",
    ".e4", ".ec", ".el", ".elm", ".erb", ".erl", ".ex", ".exs", ".f", ".f03",
    ".f08", ".f77", ".f83", ".f90", ".f95", ".fb", ".feature", ".for",
    ".forth", ".fpm", ".fr", ".frag", ".frt", ".fs", ".fsx", ".ft", ".fth",
    ".ftn", ".geom", ".go", ".groovy", ".h", ".handlebars", ".hbs", ".hex",
    ".hh", ".hlean", ".hpp", ".hrl", ".hs", ".html", ".hx", ".hxx", ".idr",
    ".ihex", ".in", ".ini", ".jai", ".java", ".jl", ".js", ".json", ".jsx",
    ".kt", ".kts", ".lds", ".lean", ".less", ".lidr", ".lisp", ".lsp", ".lua",
    ".m", ".makefile", ".markdown", ".master", ".md", ".mjs", ".mk", ".ml",
    ".mli", ".mm", ".mustache", ".nb", ".nim", ".nix", ".oz", ".p", ".pad",
    ".pas", ".pcc", ".pcss", ".pfo", ".pgc", ".php", ".pl", ".pm", ".polly",
    ".postcss", ".pp", ".pro", ".proto", ".ps1", ".psd1", ".psm1", ".purs",
    ".py", ".qcl", ".qml", ".r", ".rake", ".rb", ".re", ".rei", ".rhtml",
    ".rkt", ".rs", ".rst", ".rx", ".s", ".sass", ".sc", ".scala", ".scm",
    ".scss", ".sh", ".sitemap", ".sls", ".sml", ".sol", ".sql", ".ss", ".sss",
    ".sty", ".styl", ".swift", ".tcl", ".tesc", ".tese", ".tex", ".text",
    ".tf", ".thy", ".toml", ".ts", ".tsx", ".uc", ".uci", ".upkg", ".v",
    ".vert", ".vim", ".vue", ".webinfo", ".wl", ".xml", ".y", ".yaml", ".yml",
    ".zig", ".zsh" }                    # note that .txt is not in this set
EMPTY_FILE_MD5_HASH = "~"
EMPTY_FILE_MD5_ORIG = "d41d8cd98f00b204e9800998ecf8427e"
INF_INT = 0xFFFFFFFF
IS_MACOS   = _SYSTEM == "Darwin"
IS_WINDOWS = _SYSTEM == "Windows"
ISO_TIME_FORMAT = "%Y-%m-%d %H:%M"
MIME_TEXT_APPLICATIONS = [
    "application/javascript",
    "application/json",
    "application/sh"]
TEXT_CHARS = {*range(7, 14), 27, *range(32, 127), *range(128, 256)}
WARNINGS_ON = True
WIDTH_MAP = {
    "imode": 5,
    "smode": 10,
    "md5":   32,
}
GLOBALS = [
    "_ATREE_VERSION",
    "_MACHINE",
    "_PLATFORM",
    "_PROCESSOR",
    "_PYTHON_IMPLEMENTATION",
    "_PYTHON_VERSION",
    "_SYSTEM",
    "_PLATFORM_VERSION",
    "ANSI_COLOR_SUPPORT",
    "ANSI_COLOR_AUTO_ENABLED",
    "IS_MACOS",
    "IS_WINDOWS",
    "WARNINGS_ON"]

# ===== UTILITIES =====================================================================================================

def unique_list(lst):
    return list(dict.fromkeys(lst))

def char_to_int(ch):
    if "0" <= ch <= "9":
        return int(ch)
    if "a" <= ch <= "f":
        return ord(ch) - ord("a") + 10
    return INF_INT

def fields_to_by(fields, metric):
    by = []
    m = {"best": "u", "self": "d", "total": "a"}[metric]
    for attr in unique_list(fields):
        attr = attr.lstrip("f")
        if attr in ["lines", "size", "mtime", "atime", "ctime"]:
            by.append(m + attr)
        else:
            by.append(attr)
    return by

# ----- Utilities: String Functions -----------------------------------------------------------------------------------
def visual_width(char):
    return 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1

def visual_len(string):
    return sum(visual_width(c) for c in string)

def visual_within(string, limit):
    strlen = 0
    vislen = 0
    for i, c in enumerate(string):
        w = visual_width(c)
        if w + vislen > limit:
            break
        vislen += w
        strlen += 1
    return strlen, vislen

def make_maxlen(line, maxlen):
    if len(line) <= maxlen:
        return line
    return line[:(maxlen-4)] + " ..."

def make_plural(num, single, plural=None):
    if plural is None:
        if single[-1] in ["y"]:
            plural = single[:-1] + "ies"
        elif single[-1] in ["s", "x", "z"] or single[-2:] in ["ch", "sh"]:
            plural = single + "es"
        else:
            plural = single + "s"
    return single if 0 < abs(num) <= 1 else plural

def make_desc(text, length=100, char="-"):
    desc = char * 5 + f" {text} "
    desc += char * (length - len(desc))
    return desc

# ----- Utilities: Time Functions -------------------------------------------------------------------------------------
def datetime_to_time(dt):
    return time.mktime(dt.timetuple())

def add_mon(dt, months):
    months_count = dt.year * 12 + dt.month + months - 1
    year = months_count // 12
    month = months_count % 12 + 1
    day = dt.day
    last_day_of_month = calendar.monthrange(year, month)[1]
    if day > last_day_of_month:
        day = last_day_of_month
    return datetime.datetime(year, month, day, dt.hour, dt.minute, dt.second)

def measurement_to_size(num, unit):
    unit = unit.upper()
    return num * {"T": 2**40, "G": 2**30, "M": 2**20, "K": 2**10, "B": 1}[unit]

def measurement_to_time(num, unit):
    now = datetime.datetime.now()
    unit = unit.lower()
    if "hours".startswith(unit) or "hrs".startswith(unit):
        dt = now - datetime.timedelta(hours=num)
    elif "minutes".startswith(unit):
        dt = now - datetime.timedelta(minutes=num)
    elif "seconds".startswith(unit):
        dt = now - datetime.timedelta(seconds=num)
    elif "years".startswith(unit) or "yrs".startswith(unit):
        dt = add_mon(now, -12 * num)
    elif "months".startswith(unit):
        dt = add_mon(now, -num)
    elif "weeks".startswith(unit):
        dt = now - datetime.timedelta(weeks=num)
    elif "days".startswith(unit):
        dt = now - datetime.timedelta(days=num)
    else:
        raise RuntimeError(f"{unit}? Not sure what time unit you're talkin' bout.")
    return datetime_to_time(dt)

# ----- Utilities: File Functions -------------------------------------------------------------------------------------
def has_hidden_attr(path):
    try:
        return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
    except OSError as e:
        warning_print(f"{e}")
        # if WARNINGS_ON:
        #     print(f"Warning: {e}")
        return None

def guess_text(path, head=2048):
    mime_type = mimetypes.guess_type(path)[0]
    if mime_type is not None:
        return mime_type.startswith("text") or mime_type in MIME_TEXT_APPLICATIONS
    try:
        with open(path, "rb") as file:
            return all((x in TEXT_CHARS for x in file.read(head)))
    except OSError as e:
        warning_print(f"{e}")
        return None

def count_lines(path):
    try:
        with open(path, "r", errors="ignore") as file:
            return sum(1 for line in file)
    except PermissionError:
        if WARNINGS_ON:
            print(f"Warning: no permission to access {path}")
        return None
    except OSError as e:
        warning_print(f"{e}")
        return None

def compute_md5(path, chunk_size=4096):
    hash_md5 = hashlib.md5()
    try:
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(chunk_size), b""):
                hash_md5.update(chunk)
        result = hash_md5.hexdigest()
        if result == EMPTY_FILE_MD5_ORIG:
            return EMPTY_FILE_MD5_HASH
        else:
            return result
    except PermissionError:
        print(f"Warning: no permission to access {path}")
        return None

# ----- Utilities: Compare Functions ----------------------------------------------------------------------------------
def fields_to_cmp(fields):
    # for numbers: large < small < none
    # for strings: abc < def < none
    def cmp(a, b):
        i = int(a is not None) + 2 * int(b is not None)
        if i < 3:
            return (0, -1, 1)[i]
        for f in fields:
            af = getattr(a, f, None)
            bf = getattr(b, f, None)
            i = int(af is not None) + int(bf is not None) * 2
            if 0 < i < 3:
                return (0, -1, 1)[i]
            elif i == 3:
                result = (af > bf) - (af < bf)
                if result != 0:
                    if isinstance(af, (int, float)):
                        return -result
                    return result
        return 0
    return cmp

def cmp_to_key(cmp):
    """Convert a cmp= function into a key= function"""
    class K:
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return cmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return cmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return cmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return cmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return cmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return cmp(self.obj, other.obj) != 0
    return K

def lt(a, b):
    i = int(a is not None) + 2 * int(b is not None)
    return (i == 2) or (i == 3 and a < b)

def le(a, b):
    i = int(a is not None) + 2 * int(b is not None)
    return (i == 0) or (i == 2) or (i == 3 and a <=b)

def gt(a, b):
    return lt(b, a)

def ge(a, b):
    return le(b, a)

def min_of(a, b):
    return a if lt(a, b) else b

def max_of(a, b):
    return b if lt(a, b) else a

def nn_lt(a, b):
    return a is not None and lt(a, b)

def nn_le(a, b):
    return a is not None and le(a, b)

def add(a, b):
    i = int(a is not None) + 2 * int(b is not None)
    if i == 0:
        return None
    elif i == 1:
        return a
    elif i == 2:
        return b
    else:
        return a + b

def best_of(nodes, attr):
    attrs = ((getattr(n, attr, None) for n in nodes))
    try:
        return max(a for a in attrs if a is not None)
    except ValueError:
        return None

def sum_of(nodes, attr):
    attrs = ((getattr(n, attr, None) for n in nodes))
    return sum(a for a in attrs if a is not None)

# ----- Utilities: Formatters -----------------------------------------------------------------------------------------
# formatter protocol: each formatter return correct width for None
def int_formatter(value, comma=False, width=10):
    fmt = "{}"
    if comma:
        fmt = "{:,}"
        width += width // 3
    if value is None:
        return " " * width
    value = int(value)
    return fmt.format(value).rjust(width)

def size_formatter(value):
    if value is None:
        return " " * 10
    for unit in ("B", "K", "M", "G"):
        if value < 1024:
            if value < 10 and unit != "B":
                return f"{value:9.1f}{unit}"
            else:
                return f"{value:9.0f}{unit}"
        value /= 1024
    if value < 10:
        return f"{value:9.1f}T"
    else:
        return f"{value:9.0f}T"

def time_formatter(value, fmt):
    if value is None:
        return " " * len(time.strftime(fmt, time.localtime(0)))
    return time.strftime(fmt, time.localtime(value))

def var_time_formatter(value):
    if value is None:
        return " " * 12
    now = time.time()
    if abs(now - value) <= 6 * 30 * 24 * 60 * 60:
        fmt = "%b %e %H:%M"
    else:
        fmt = "%b %e  %Y"
    return time.strftime(fmt, time.localtime(value))

def bool_formatter(value, width=8):
    if value is None:
        return " " * width
    result = "Yes" if value else "No"
    return result.rjust(width)

def width_formatter(value, attr, default_width=8):
    width = WIDTH_MAP.get(attr, default_width)
    if value is None:
        return " " * width
    return "{{:>{}}}".format(width).format(value)[:width]

def md5_formatter(value):
    if value == EMPTY_FILE_MD5_HASH:
        value = "(empty)" + " " * 25
    return width_formatter(value, attr="md5")

def color_md5_formatter(value, hue, reset):
    if value is None:
        return " " * 32
    color = hue.get(value, "")
    if value == EMPTY_FILE_MD5_HASH:
        value = "(empty)" + " " * 25
    return color + value + reset

# ----- Utilities: Debug ----------------------------------------------------------------------------------------------
def debug_print(kwargs, title="DEBUG", replace=True):
    print(make_desc(title))
    for k, v in sorted(kwargs.items()):
        arg_name = k.replace("_", "-") if replace else k
        arg_value = "No Limit" if isinstance(v, int) and v == INF_INT else v
        print(f"{arg_name:50} {arg_value}")

def warning_print(message):
    if WARNINGS_ON:
        print("Warning:", message)

# ----- Utilities: Color Support --------------------------------------------------------------------------------------
if IS_WINDOWS:
    if platform.version() < "10.0.10586":
        ANSI_COLOR_SUPPORT = False
        warning_print(f"ANSI colors not supported in Windows {platform.version()}.")
    elif platform.version() >= "10.0.14393":
        ANSI_COLOR_AUTO_ENABLED = False
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# ===== NODE ==========================================================================================================

class FakeNode:
    def __init__(self, path, father):
        self.path = path
        self.name = os.path.basename(path)
        self.father = father
        self.children = None
        self.is_link = False
        self.is_dir = False
        self.is_file = False

def cached(func):
    @functools.wraps(func)
    def decorated(self):
        name = "_" + func.__name__
        if hasattr(self, name):
            return getattr(self, name)
        else:
            value = func(self)
            setattr(self, name, value)
            return value
    return decorated

class Node:
    uname_cache = {}
    gname_cache = {}
    smode_cache = {}

    def __repr__(self):
        return self.path

    def __init__(self, path, father):
        self.path = path
        self.name = os.path.basename(path)
        self.father = father
        if self.is_dir:
            self.children = set()
        else:
            self.children = None

    def __getattr__(self, attr):
        matched = re.match(r"[fdua](lines|size|[abcm]time)", attr)
        if matched:
            if attr[0] == "f":
                if self.is_file or self.is_link:
                    return self.__getattr__(attr[1:])
                else:
                    return None
            if attr[0] == "d":
                if self.is_dir:
                    return self.__getattr__(attr[1:])
                else:
                    return None
            if attr[0] == "u":
                if self.is_dir:
                    return self.__getattr__("b" + attr[1:])
                else:
                    return self.__getattr__(attr[1:])
            if attr[0] == "a":
                if self.is_dir:
                    return self.__getattr__("r" + attr[1:])
                else:
                    return self.__getattr__(attr[1:])
        return self.__getattribute__(attr)

    @property
    @cached
    def lstat(self):
        return os.lstat(self.path)

    @property
    @cached
    def is_link(self):
        try:
            return stat.S_ISLNK(self.lstat.st_mode)
        except OSError as e:
            warning_print(f"{e}")
            return False

    @property
    @cached
    def is_dir(self):
        try:
            return stat.S_ISDIR(self.lstat.st_mode)
        except OSError as e:
            warning_print(f"{e}")
            return False

    @property
    @cached
    def is_file(self):
        try:
            return stat.S_ISREG(self.lstat.st_mode)
        except OSError as e:
            warning_print(f"{e}")
            return False

    @property
    @cached
    def stat(self):
        return os.stat(self.path)

    @property
    @cached
    def is_to_dir(self):
        try:
            return stat.S_ISDIR(self.stat.st_mode)
        except OSError as e:
            warning_print(f"{e}")
            return False

    @property
    @cached
    def is_text(self):
        return self.is_file and guess_text(self.path)

    @property
    @cached
    def is_code(self):
        _, ext = os.path.splitext(self.path)
        return self.is_file and ext in CODE_EXTENSIONS

    @property
    @cached
    def lines(self):
        if self.is_text:
            return count_lines(self.path)
        else:
            return None

    @property
    @cached
    def size(self):
        return self.lstat.st_size

    @property
    @cached
    def atime(self):
        return self.lstat.st_atime

    @property
    @cached
    def btime(self):
        try:
            return self.lstat.st_birthtime
        except AttributeError:
            return self.lstat.st_ctime

    @property
    @cached
    def ctime(self):
        return self.lstat.st_ctime

    @property
    @cached
    def mtime(self):
        return self.lstat.st_mtime

    @property
    @cached
    def inode(self):
        return self.lstat.st_ino

    @property
    @cached
    def owner(self):
        if IS_WINDOWS:
            raise NotImplementedError("Ownder field is not implemented on Windows.")
        st_uid = self.lstat.st_uid
        try:
            return Node.uname_cache[st_uid]
        except KeyError:
            uname = pwd.getpwuid(st_uid).pw_name
            Node.uname_cache[st_uid] = uname
            return uname

    @property
    @cached
    def group(self):
        if IS_WINDOWS:
            raise NotImplementedError("Group field is not implemented on Windows.")
        st_gid = self.lstat.st_gid
        try:
            return Node.gname_cache[st_gid]
        except KeyError:
            gname = grp.getgrgid(st_gid).gr_name
            Node.gname_cache[st_gid] = gname
            return gname

    @property
    @cached
    def imode(self):
        return str(oct(stat.S_IMODE(self.lstat.st_mode) & 0o777))[2:]

    @property
    @cached
    def smode(self):
        mode = self.lstat.st_mode
        try:
            return Node.smode_cache[mode]
        except KeyError:
            result = ""
            if self.is_link:
                result = "l"
            elif self.is_dir:
                result = "d"
            else:
                result = "-"
            imode = stat.S_IMODE(self.lstat.st_mode)
            for i in range(3):
                result += "r" if imode & (1 << (8 - i * 3)) else "-"
                result += "w" if imode & (1 << (7 - i * 3)) else "-"
                result += "x" if imode & (1 << (6 - i * 3)) else "-"
            Node.smode_cache[mode] = result
            return result

    @property
    @cached
    def md5(self):
        if self.is_file:
            return compute_md5(self.path)
        else:
            return None

# ===== TREE ==========================================================================================================

class Value_and_Which:
    def __init__(self, value, which):
        self.value = value
        self.which = which

    def __lt__(self, other):
        return self.value < other.value

class Top_K_and_Which:
    def __init__(self, capacity):
        self.capacity = capacity
        self._list = []

    def __iter__(self):
        return self._list.__iter__()

    def push(self, value, which):
        if len(self._list) < self.capacity:
            return heapq.heappush(self._list, Value_and_Which(value, which))
        else:
            return heapq.heappushpop(self._list, Value_and_Which(value, which))

    @property
    def next_to_pop(self):
        if len(self._list) < self.capacity:
            return None
        else:
            return self._list[0].value

class Colors:
    BOLD_CYAN = "\033[1;36m"
    BOLD_DIM  = "\033[1;2m"
    if IS_WINDOWS:
        CYAN  = "\033[1;36m"
    else:
        CYAN  = "\033[36m"
    YELLOW    = "\033[33m"
    RESET     = "\033[0m"
    _SEED     = 1

    @staticmethod
    def next():
        color = f"\033[3{Colors._SEED}m"
        Colors._SEED += 1
        if Colors._SEED >= 7:
            Colors._SEED = 1
        return color

class NoColors:
    BOLD_CYAN = ""
    BOLD_DIM  = ""
    CYAN      = ""
    YELLOW    = ""
    RESET     = ""

    @staticmethod
    def next():
        return ""

class BoxDrawings:
    BLANK = "    "
    UP_RIGHT = "└── "
    VERTICAL = "│   "
    VERTICAL_RIGHT = "├── "

class UglyBoxDrawings:
    BLANK = "    "
    UP_RIGHT = "\\-- "
    VERTICAL = "|   "
    VERTICAL_RIGHT = "|-- "

class NoBoxDrawings:
    BLANK = ""
    UP_RIGHT = ""
    VERTICAL = ""
    VERTICAL_RIGHT = ""

class Tree():
    def __init__(self, root_path, list_dirs_only, access_level,
            fpred, dpred, dpost, max_level, max_files, max_dirs, always_show_dirs,
            fields, top_mode, top_count, dup_mode, dup_nonempty,
            by, dirs_first, unsorted, reverse, width, do_not_force_width,
            no_color, no_progress, no_warnings, no_header, no_readlink, no_more,
            no_report, verbose_report, report_only,
            no_indent, ugly_indent, file_path, full_path, real_path,
            quotes, raw, comma, human, iso, timefmt):
        # root
        if not os.path.isdir(root_path):
            raise NotADirectoryError(f"Root path {root_path} is not a valid directory.")
        if real_path:
            root_path = os.path.realpath(root_path)
        self.root = Node(path=root_path, father=None)
        # access
        self.list_dirs_only = list_dirs_only
        self.access_level = access_level
        self.fpred = fpred
        self.dpred = dpred
        self.dpost = dpost
        # display
        self.max_level = max_level
        self.max_files = max_files
        self.max_dirs = max_dirs
        self.always_show_dirs = always_show_dirs
        # fields
        self.fields = fields
        # top
        self.top_mode = top_mode
        if self.top_mode:
            self.top_heap = Top_K_and_Which(top_count)
            self.top_attr = "b" +self.top_mode.lstrip("f")
        # duplicates
        self.dup_mode = dup_mode
        self.dup_nonempty = dup_nonempty
        if self.dup_mode:
            self.dup_map = {}
            self.dup_set = set()
            self.dup_hue = {}
        # post prune
        self.save_set = {self.root}
        self.show_set = set()
        # sort
        self.by = by
        self.dirs_first = dirs_first
        self.unsorted = unsorted
        self.reverse = reverse
        # format
        self.width = width
        self.do_not_force_width = do_not_force_width
        self.no_progress = no_progress
        self.no_warnings = no_warnings
        self.no_readlink = no_readlink
        self.no_more = no_more
        self.no_header = no_header
        self.no_color = no_color
        self.no_indent = no_indent
        self.ugly_indent = ugly_indent
        self.file_path = file_path
        self.full_path = full_path
        self.real_path = real_path
        self.quotes =  "\"" if quotes else ""
        self.raw = raw
        self.comma = comma
        self.human = human
        self.iso = iso
        self.timefmt = timefmt
        self.no_report = no_report
        self.verbose_report = verbose_report
        self.report_only = report_only
        self.colors = NoColors if self.no_color or not ANSI_COLOR_SUPPORT else Colors
        global WARNINGS_ON
        if self.no_warnings:
            WARNINGS_ON = False
        if self.no_indent:
            self.drawings = NoBoxDrawings
        elif self.ugly_indent:
            self.drawings = UglyBoxDrawings
        else:
            self.drawings = BoxDrawings
        # formatters
        self.formatters = []
        for attr in self.fields:
            if attr.endswith("lines"):
                self.formatters.append(lambda val: int_formatter(val, comma=self.comma))
            elif attr.endswith("size"):
                if self.human and not self.raw:
                    self.formatters.append(size_formatter)
                else:
                    self.formatters.append(lambda val: int_formatter(val, comma=self.comma))
            elif attr.endswith("time"):
                if self.raw:
                    self.formatters.append(lambda val: int_formatter(val, comma=self.comma))
                elif self.timefmt:
                    self.formatters.append(lambda val: time_formatter(val, fmt=self.timefmt))
                elif self.iso:
                    self.formatters.append(lambda val: time_formatter(val, fmt=ISO_TIME_FORMAT))
                else:
                    self.formatters.append(var_time_formatter)
            elif attr.startswith("is"):
                self.formatters.append(lambda val, width=min(16, max(8, len(attr))): bool_formatter(val, width=width))
            elif attr == "md5":
                if self.dup_mode:
                    self.formatters.append(lambda val: color_md5_formatter(val, hue=self.dup_hue, reset=self.colors.RESET))
                else:
                    self.formatters.append(lambda val: md5_formatter(val))
            else:
                self.formatters.append(lambda val, attr=attr: width_formatter(val, attr))
        # open file to read lines
        self.read_lines = any(x.endswith("lines") for x in self.fields + self.by)
        # build
        self._build()

    def _build(self):
        self._level_reached = 0
        self._gather(self.root, level=1)
        print(" " * 150, end="\r")
        if self.top_mode:
            for elem in self.top_heap:
                self.show_set.add(elem.which)
                self._save_father(elem.which)
        if self.dup_mode:
            for checksum in sorted(list(self.dup_set)):
                if checksum == EMPTY_FILE_MD5_HASH:
                    self.dup_hue[checksum] = self.colors.RESET
                else:
                    self.dup_hue[checksum] = self.colors.next()
                for node in self.dup_map[checksum]:
                    self.show_set.add(node)
                    self._save_father(node)
        if self.width:
            self.width_control = self.width
        else:
            lev = min(self._level_reached, self.max_level)
            if self.file_path or self.full_path:
                self.width_control = min(159, (lev * 4) + 24 * max(lev, 2))
            else:
                self.width_control = min(79, (lev * 4) + 48)

    def _save_father(self, node):
        if node.father in self.save_set:
            return
        self.save_set.add(node.father)
        self._save_father(node.father)

    def _gather(self, root, level):
        self._level_reached = max(level, self._level_reached)
        maxlen = 150
        if not self.no_progress:
            print(" " * maxlen, end="\r")
            progress = make_maxlen("Gathering " + root.path, maxlen=maxlen)
            print(progress, end="\r")
        root.fcount = 0
        root.dcount = 0
        root.blines = None
        root.rlines = None
        root.bsize = root.size
        root.rsize = root.size
        root.batime = root.atime
        root.bbtime = root.btime
        root.bctime = root.ctime
        root.bmtime = root.mtime
        if self.top_mode:
            root.top_val = getattr(root, self.top_attr)
        try:
            all_nodes = [Node(path=os.path.join(root.path, x), father=root) for x in os.listdir(root.path)]
        except OSError as e:
            warning_print(f"{e}")
            return
        f_nodes = []
        d_nodes = []
        for node in all_nodes:
            if node.is_to_dir:
                if self.dpred(node):
                    d_nodes.append(node)
            else:
                if self.fpred(node):
                    f_nodes.append(node)
        for f in f_nodes:
            if self.top_mode:
                val = getattr(f, self.top_mode, None)
                if le(val, self.top_heap.next_to_pop):
                    continue
                self.top_heap.push(val, f)
                root.top_val = max_of(val, root.top_val)
            root.children.add(f)
            root.fcount += 1
            if self.read_lines:
                root.blines = max_of(f.lines, root.blines)
                root.rlines = add(root.rlines, f.lines)
            root.bsize = max_of(f.size, root.bsize)
            root.rsize += f.size
            root.batime = max_of(f.atime, root.batime)
            root.bbtime = max_of(f.btime, root.bbtime)
            root.bctime = max_of(f.ctime, root.bctime)
            root.bmtime = max_of(f.mtime, root.bmtime)
            if self.dup_mode:
                checksum = f.md5
                if checksum != EMPTY_FILE_MD5_HASH or not self.dup_nonempty:
                    if checksum and checksum in self.dup_map:
                        self.dup_map[checksum].append(f)
                        self.dup_set.add(checksum)
                    else:
                        self.dup_map[checksum] = [f]
        for d in d_nodes:
            if d.is_link:
                if self.always_show_dirs:
                    root.children.add(d)
                    root.dcount += 1
                continue
            else:
                if level < self.access_level:
                    self._gather(d, level + 1)
                else:
                    d.ignore = True
                    d.fcount = 0
                    d.dcount = 0
                    d.blines = None
                    d.rlines = None
                    d.bsize = d.size
                    d.rsize = d.size
                    d.batime = d.atime
                    d.bbtime = d.btime
                    d.bctime = d.ctime
                    d.bmtime = d.mtime
            if not self.dpost(d):
                continue
            if not self.always_show_dirs and d.fcount == 0 and d.dcount == 0:
                continue
            if self.top_mode:
                if lt(d.top_val, self.top_heap.next_to_pop):
                    continue
                root.top_val = max_of(d.top_val, root.top_val)
            root.children.add(d)
            root.fcount += d.fcount
            root.dcount += d.dcount + 1
            if d.rlines is not None:
                root.blines = max_of(d.blines, root.blines)
                root.rlines = add(root.rlines, d.rlines)
            root.bsize = max_of(d.bsize, root.bsize)
            root.rsize += d.rsize
            root.bmtime = max_of(d.bmtime, root.bmtime)
            root.batime = max_of(d.batime, root.batime)
            root.bctime = max_of(d.bctime, root.bctime)
            root.bbtime = max_of(d.bbtime, root.bbtime)

    def print(self):
        if not self.report_only:
            if self.fields and not self.no_header:
                self._print_header()
            self._print_line(node=self.root, levels=[], prefix="")
            self._print_node(self.root)
        if not self.no_report:
            self._print_report()

    def _print_header(self):
        header = "NODE" + " " * (self.width_control - len("NODE"))
        for i, v in enumerate(self.fields):
            length = len(self.formatters[i](None))
            header += "  " + v.upper()[:length].rjust(length)
        print(header)

    def _print_node(self, node, levels=[]):
        f_nodes = []
        d_nodes = []
        for x in node.children:
            if x.is_to_dir:
                if not (self.top_mode or self.dup_mode) or x in self.save_set:
                    d_nodes.append(x)
            else:
                if not (self.top_mode or self.dup_mode) or x in self.show_set:
                    f_nodes.append(x)
        if self.dirs_first:
            cmp = fields_to_cmp(["is_to_dir"] + self.by)
        else:
            cmp = fields_to_cmp(self.by)
        if not self.unsorted:
            f_nodes.sort(key=cmp_to_key(cmp), reverse=self.reverse)
            d_nodes.sort(key=cmp_to_key(cmp), reverse=self.reverse)
        f_show = f_nodes[:self.max_files]
        d_show = d_nodes[:self.max_dirs]
        n_show = [*f_show, *d_show]
        if not self.unsorted:
            n_show.sort(key=cmp_to_key(cmp), reverse=self.reverse)
        if not self.no_more:
            f_hide = f_nodes[self.max_files:]
            d_hide = d_nodes[self.max_dirs:]
            f_hide_count = len(f_hide)
            d_hide_count = len(d_hide)
            if f_hide_count:
                word = make_plural(f_hide_count, "file")
                path = os.path.join(node.path, f"{f_hide_count} more {word}")
                f_more_node = FakeNode(path, father=node)
                f_more_node.ulines = f_more_node.blines = best_of(f_hide, "lines")
                f_more_node.alines = f_more_node.rlines = sum_of(f_hide, "lines")
                f_more_node.usize = f_more_node.bsize = best_of(f_hide, "size")
                f_more_node.asize = f_more_node.rsize = sum_of(f_hide, "size")
                f_more_node.uatime = f_more_node.batime = best_of(f_hide, "atime")
                f_more_node.ubtime = f_more_node.bbtime = best_of(f_hide, "btime")
                f_more_node.uctime = f_more_node.bctime = best_of(f_hide, "ctime")
                f_more_node.umtime = f_more_node.bmtime = best_of(f_hide, "mtime")
                n_show.append(f_more_node)
            if d_hide_count:
                word = make_plural(d_hide_count, "dir")
                path = os.path.join(node.path, f"{d_hide_count} more {word}")
                d_more_node = FakeNode(path, father=node)
                d_more_node.ulines = d_more_node.blines = best_of(d_hide, "blines")
                d_more_node.alines = d_more_node.rlines = sum_of(d_hide, "rlines")
                d_more_node.usize = d_more_node.bsize = best_of(d_hide, "bsize")
                d_more_node.asize = d_more_node.rsize = sum_of(d_hide, "rsize")
                d_more_node.uatime = d_more_node.batime = best_of(d_hide, "batime")
                d_more_node.ubtime = d_more_node.bbtime = best_of(d_hide, "bbtime")
                d_more_node.uctime = d_more_node.bctime = best_of(d_hide, "bctime")
                d_more_node.umtime = d_more_node.bmtime = best_of(d_hide, "bmtime")
                n_show.append(d_more_node)
        for i, node in enumerate(n_show):
            has_next_node = i != len(n_show) - 1
            if has_next_node:
                prefix = self.drawings.VERTICAL_RIGHT
            else:
                prefix = self.drawings.UP_RIGHT
            self._print_line(node, levels, prefix)
            if node.is_dir and len(levels) + 1 < self.max_level:
                levels.append(has_next_node)
                self._print_node(node, levels=levels)
                levels.pop()

    def _print_line(self, node, levels, prefix):
        inde_line = ""
        for has_next_node in levels:
            if has_next_node:
                inde_line += self.drawings.VERTICAL
            else:
                inde_line += self.drawings.BLANK
        inde_line += prefix
        quotes = self.quotes if isinstance(node, Node) else ""
        if self.full_path or (self.file_path and not node.is_to_dir):
            node_part = node.path
        else:
            node_part = node.name
        node_line = quotes + node_part + quotes
        suff_line = ""
        if getattr(node, "ignore", None):
            suff_line += " [-]"
        elif node.is_dir and len(levels) == self.max_level - 1 and node != self.root:
            suff_line += " [-]" if self.list_dirs_only else " [+]"
        if not self.no_readlink and node.is_link:
            suff_line += f" -> {quotes}{os.readlink(node.path)}{quotes}"
        if self.fields or self.width:
            join_line = inde_line + node_line + suff_line
            diff = self.width_control - visual_len(join_line)
            suff_line += " " * diff
            if diff < 0 and not self.do_not_force_width:
                strlen, vislen = visual_within(join_line, self.width_control - len(" ..."))
                join_line = join_line[:strlen]
                join_line += " " * (self.width_control - len(" ...") - vislen) + " ..."
                if len(join_line) - len(" ...") < len(inde_line):
                    inde_line = join_line
                    node_line = ""
                    suff_line = ""
                elif len(join_line) - len(" ...") < len(inde_line) + len(node_line):
                    node_line = join_line[len(inde_line):]
                    suff_line = ""
                else:
                    suff_line = join_line[(len(inde_line) + len(node_line)):]
        if isinstance(node, FakeNode):
            node_color = self.colors.BOLD_DIM
            attr_color = self.colors.BOLD_DIM
        elif node.is_dir:
            node_color = self.colors.BOLD_CYAN
            attr_color = self.colors.CYAN
        elif node.is_to_dir:
            node_color = self.colors.BOLD_CYAN
            attr_color = ""
        else:
            node_color = ""
            attr_color = ""
        node_line = node_color + node_line + self.colors.RESET
        attr_line = ""
        for i, v in enumerate(self.fields):
            attr_line += "  " + attr_color + self.formatters[i](getattr(node, v, None)) + self.colors.RESET
        print(inde_line + node_line + suff_line + attr_line)

    def _print_report(self):
        print()
        if self.top_mode:
            if self.verbose_report:
                nodes = sorted(list(self.show_set), key=cmp_to_key(fields_to_cmp([self.top_mode])))
                rank_width = int(math.log10(len(nodes))) + 1
                attr_width = max(len(self.formatters[0](getattr(nodes[0], self.top_mode)).lstrip()), len(self.top_mode))
                path_width = min(max([visual_len(x.path) for x in nodes]) + 2, 100)
                rank_header = "#".rjust(rank_width)
                attr_header = self.top_mode.upper().rjust(attr_width)
                path_header = "PATH"
                print(rank_header, " | ", attr_header, " | ", path_header)
                line = "-" * (rank_width + 2) + "+" + "-" * (attr_width + 4) + "+" + "-" * path_width
                print(line)
                for i, x in enumerate(nodes):
                    rank = str(i+1).rjust(rank_width)
                    value = self.formatters[0](getattr(x, self.top_mode)).lstrip().rjust(attr_width)
                    path = x.path
                    print(rank, " | ", value, " | ", path)
                print()
            d_count = len(self.save_set)
            f_count = len(self.show_set)
            d_word = make_plural(d_count, "directory")
            f_word = make_plural(f_count, "file")
            print(d_count, d_word + ",", f_count, f_word)
        elif self.dup_mode:
            if self.verbose_report:
                for checksum in sorted(list(self.dup_set)):
                    print(color_md5_formatter(checksum, hue=self.dup_hue, reset=self.colors.RESET))
                    paths = sorted([node.path for node in self.dup_map[checksum]])
                    for x in paths:
                        print(" " * 4 + x)
                print()
            empt_count = len(self.dup_map.get(EMPTY_FILE_MD5_HASH, []))
            copy_count = 0
            for x in self.dup_set:
                copy_count += len(self.dup_map[x])
            dist_count = len(self.dup_set)
            dist_part = f"{dist_count} distinct " + make_plural(dist_count, "file") + ","
            dupl_part = f"{copy_count} duplicate copies"
            empt_part = "" if self.dup_nonempty else f"(including {empt_count} empty copies)"
            print(dist_part, dupl_part, empt_part)
        elif self.list_dirs_only:
            d_count = self.root.dcount
            d_word = make_plural(d_count, "directory")
            print(d_count, d_word)
        else:
            d_count = self.root.dcount
            f_count = self.root.fcount
            d_word = make_plural(d_count, "directory")
            f_word = make_plural(f_count, "file")
            print(d_count, d_word + ",", f_count, f_word)

# ===== PARSER ========================================================================================================

def MaxTuple(string):
    string = string.lower()
    if len(string) == 3 and all(x in ".0123456789abcdef" for x in string):
        return tuple(char_to_int(x) for x in string)
    else:
        return string

def Root_Path_Or_Max_Tuple(string):
    if os.path.isdir(string):
        root_path = string
        return root_path
    else:
        max_tuple = MaxTuple(string)
        if isinstance(max_tuple, tuple):
            return max_tuple
        else:
            return string
    raise NotADirectoryError(f"{string} is neither a valid directory nor a valid 3-tuple.")

HELP_COLORS = Colors if ANSI_COLOR_SUPPORT else NoColors
epilog                  = f"Need examples? Use {HELP_COLORS.YELLOW}--examples{HELP_COLORS.RESET} to view some quick examples."
help_help               = "Show this message and exit."
debug_help              = "Show debug information and exit."
examples_help           = "Show examples and exit."
version_help            = "Show atree version and exit."
root_path_help          = "Root path for tree."
max_tuple_help          = "A 3-digit number to specify --max-levels/files/dirs in one go."
access_hidden_help      = "Access hidden files and directories."
ignore_links_help       = "Ignore symbolic links."
list_dirs_only_help     = "List directories only. Ignore files."
access_level_help       = "Access only LEVEL directories deep. Ignore deeper levels."
pattern_help            = "Access only the files that match the given patterns."
ignore_help             = "Ignore the files that match the given patterns."
pattern_dir_help        = "Access only the directories that match the given patterns."
ignore_dir_help         = "Ignore the directories that match the given patterns."
ignore_case_help        = "Ignore case when matching patterns."
text_help               = "Access text files only."
code_help               = "Access source code files only."
max_level_help          = "Show at most NUM level of directories. levels are accessed."
max_files_help          = "Show at most NUM files in a directory."
max_dirs_help           = "Show at most NUM sub-directories in a directory."
show_dirs_only_help     = "Show directories only. All files and directories are accessed."
always_show_dirs_help   = "Always show directories. Do not prune empty directories."
show_help               = "Fields to show and filter, e.g. lines,  \"lines>=100\", \"lines@top10\"."
expand_help             = "Expand fields to show more info, e.g. lines --> {rlines, flines}."
unique_help             = "Remove duplicated fields from the list passed to --show."
by_help                 = "Fields to sort by."
sort_help               = "Automatically sort by the fields as listed in --show."
dirs_first_help         = "List directories before files."
unsorted_help           = "Leave files and directories unsorted."
reverse_help            = "Reverse the order of the sort."
metric_help             = "Use a dir's best/self/total value when comparing it with files."
width_help              = "Tree width."
do_not_force_width_help = "Do not force tree width. Might break alignment."
no_color_help           = "Do not print in colors."
no_progress_help        = "Do not print the gathering progress."
no_warnings_help        = "Do not print warnings."
no_header_help          = "Do not print the header for tree."
no_readlink_help        = "Do not print targets for symbolic links."
no_more_help            = "Do not print extra information for files/dirs that are not shown."
no_report_help          = "Do not print report for tree."
verbose_report_help     = "Print verbose report."
report_only_help        = "Print report only. Do not print tree."
no_indent_help          = "Do not print indentation lines."
ugly_indent_help        = "Print with ugly, old-style indentation lines."
file_path_help          = "Print full path for each file."
full_path_help          = "Print full path for each file and directory."
real_path_help          = "Resolve . and .. when printing paths."
quotes_help             = "Quote file and directory names with double quotes."
raw_help                = "Print fields as raw integers whenever possible."
comma_help              = "Enable comma separators for integer fields."
human_help              = "Print size fields in a more human-readable way."
iso_help                = "Print time fields in ISO 8601 format, e.g. 2020-12-20 14:03."
timefmt_help            = "Customize time format, e.g. \"%%Y/%%m/%%d\""
c_help                  = "Equivalent to --pattern *.c *.h --show lines -sec"
cpp_help                = "Equivalent to --pattern *.c *.h *.cpp *.hpp --show lines -sec"
java_help               = "Equivalent to --pattern *.java --show lines -sec"
javascript_help         = "Equivalent to --pattern *.js --show lines -sec"
python_help             = "Equivalent to --pattern *.py --show lines -sec"

def parse():
    formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
    # ----- parser ----------------------------------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Augmented Tree", usage=argparse.SUPPRESS,
                                     add_help=False, formatter_class=formatter_class, epilog=epilog)
    # ----- optionals -------------------------------------------------------------------------------------------------
    o_g = parser.add_argument_group()
    o_g.add_argument("--help", action="help", help=help_help)
    o_g.add_argument("-q", "--debug", action="store_true", default=False, help=debug_help)
    o_g.add_argument("-g", "--examples", action="store_true", default=False, help=examples_help)
    o_g.add_argument("-V", "--version", action="store_true", default=False, help=version_help)
    # ----- positional ------------------------------------------------------------------------------------------------
    p_g = parser.add_argument_group(description=make_desc("Positional Options"))
    p_g.add_argument("root_path", nargs="?", type=Root_Path_Or_Max_Tuple, default=".", help=root_path_help)
    p_g.add_argument("max_tuple", nargs="?", type=MaxTuple, default=None, help=max_tuple_help)
    # ----- access ----------------------------------------------------------------------------------------------------
    a_g = parser.add_argument_group(description=make_desc("Access Options"))
    a_g.add_argument("-H", "--access-hidden", action="store_true", default=False, help=access_hidden_help)
    a_g.add_argument("-K", "--ignore-links", action="store_true", default=False, help=ignore_links_help)
    a_g.add_argument("-D", "--list-dirs-only", action="store_true", default=False, help=list_dirs_only_help)
    a_g.add_argument("-L", "--access-level", type=int, default=INF_INT, metavar="LEVEL", help=access_level_help)
    a_g.add_argument("-P", "--pattern", nargs="*", default=[], metavar="*", help=pattern_help)
    a_g.add_argument("-I", "--ignore", nargs="*", default=[], metavar="*", help=ignore_help)
    a_g.add_argument("--pattern-dir", nargs="*", default=[], metavar="*", help=pattern_dir_help)
    a_g.add_argument("--ignore-dir", nargs="*", default=[], metavar="*", help=ignore_dir_help)
    a_g.add_argument("--ignore-case", action="store_true", default=False, help=ignore_case_help)
    a_g.add_argument("--text", action="store_true", default=False, help=text_help)
    a_g.add_argument("--code", action="store_true", default=False, help=code_help)
    # ----- display ---------------------------------------------------------------------------------------------------
    d_g = parser.add_argument_group(description=make_desc("Display Options"))
    d_g.add_argument("-l", "--max-level", type=int, default=INF_INT, metavar="NUM", help=max_level_help)
    d_g.add_argument("-f", "--max-files", type=int, default=INF_INT, metavar="NUM", help=max_files_help)
    d_g.add_argument("-d", "--max-dirs", type=int, default=INF_INT, metavar="NUM", help=max_dirs_help)
    d_g.add_argument("-0", "--show-dirs-only", action="store_true", default=False, help=show_dirs_only_help)
    d_g.add_argument("-a", "--always-show-dirs", action="store_true", default=False, help=always_show_dirs_help)
    # ----- field -----------------------------------------------------------------------------------------------------
    e_g = parser.add_argument_group(description=make_desc("Field Options"))
    e_g.add_argument("--show", nargs="+", default=[], metavar="FIELD", help=show_help)
    e_g.add_argument("-e", "--expand", action="store_true", default=False, help=expand_help)
    e_g.add_argument("-x", "--unique", action="store_true", default=False, help=unique_help)
    # ----- sorting ---------------------------------------------------------------------------------------------------
    s_g = parser.add_argument_group(description=make_desc("Sorting Options"))
    s_g.add_argument("--by", nargs="+", metavar="FIELD", default=[], help=by_help)
    s_g.add_argument("-s", "--sort", action="store_true", default=False, help=sort_help)
    s_g.add_argument("-1", "--dirs-first", action="store_true", default=False, help=dirs_first_help)
    s_g.add_argument("--unsorted", action="store_true", default=False, help=unsorted_help)
    s_g.add_argument("--reverse", action="store_true", default=False, help=reverse_help)
    s_g.add_argument("--metric", type=str, choices= ["best", "self", "total"], default="best",
                                 metavar="METRIC", help=metric_help)
    # ----- format ----------------------------------------------------------------------------------------------------
    f_g = parser.add_argument_group(description=make_desc("Format Options"))
    f_g.add_argument("-w", "--width", type=int, metavar="NUM", help=width_help)
    f_g.add_argument("-2", "--do-not-force-width", action="store_true", default=False, help=do_not_force_width_help)
    f_g.add_argument("-3", "--no-color", action="store_true", default=False, help=no_color_help)
    f_g.add_argument("-4", "--no-progress", action="store_true", default=False, help=no_progress_help)
    f_g.add_argument("-5", "--no-warnings", action="store_true", default=False, help=no_warnings_help)
    f_g.add_argument("-6", "--no-header", action="store_true", default=False, help=no_header_help)
    f_g.add_argument("-7", "--no-readlink", action="store_true", default=False, help=no_readlink_help)
    f_g.add_argument("-8", "--no-more", action="store_true", default=False, help=no_more_help)
    r_x = f_g.add_mutually_exclusive_group()
    r_x.add_argument("-9", "--no-report", action="store_true", default=False, help=no_report_help)
    f_g.add_argument("-v", "--verbose-report", action="store_true", default=False, help=verbose_report_help)
    r_x.add_argument("-z", "--report-only", action="store_true", default=False, help=report_only_help)
    f_g.add_argument("-i", "--no-indent", action="store_true", default=False, help=no_indent_help)
    f_g.add_argument("-u", "--ugly-indent", action="store_true", default=False, help=ugly_indent_help)
    f_g.add_argument("-F", "--file-path", action="store_true", default=False, help=file_path_help)
    f_g.add_argument("-U", "--full-path", action="store_true", default=False, help=full_path_help)
    f_g.add_argument("-R", "--real-path", action="store_true", default=False, help=real_path_help)
    f_g.add_argument("-Q", "--quotes", action="store_true", default=False, help=quotes_help)
    f_g.add_argument("-r", "--raw", action="store_true", default=False, help=raw_help)
    f_g.add_argument("-c", "--comma", action="store_true", default=False, help=comma_help)
    f_g.add_argument("-h", "--human", action="store_true", default=False, help=human_help)
    t_x = f_g.add_mutually_exclusive_group()
    t_x.add_argument("-o", "--iso", action="store_true", default=False, help=iso_help)
    t_x.add_argument("-t", "--timefmt", type=str, metavar="FMT",help=timefmt_help)
    # ----- shortcut --------------------------------------------------------------------------------------------------
    c_g = parser.add_argument_group(description=make_desc("Shortcut Options"))
    c_g.add_argument("--c", action="store_true", default=False, help=c_help)
    c_g.add_argument("--cpp", action="store_true", default=False, help=cpp_help)
    c_g.add_argument("--java", action="store_true", default=False, help=java_help)
    c_g.add_argument("--javascript", action="store_true", default=False, help=javascript_help)
    c_g.add_argument("--python", action="store_true", default=False, help=python_help)
    # ----- max_tuple -------------------------------------------------------------------------------------------------
    args = parser.parse_args()
    if isinstance(args.root_path, tuple):
        args.max_tuple = args.root_path
        args.root_path = "."
    if isinstance(args.max_tuple, tuple):
        args.max_level, args.max_files, args.max_dirs = args.max_tuple
    if isinstance(args.max_tuple, str):
        raise RuntimeError(f"{args.max_tuple} is not a valid 3-tuple.")
    # ----- mode ------------------------------------------------------------------------------------------------------
    if args.c:
        args.pattern += ["*.c", "*.h"]
    if args.cpp:
        args.pattern += ["*.c", "*.h", "*.cpp", "*.hpp"]
    if args.java:
        args.pattern += ["*.java"]
    if args.javascript:
        args.pattern += ["*.js"]
    if args.python:
        args.pattern += ["*.py"]
    args.pattern = unique_list(args.pattern)
    if any([args.c, args.cpp, args.java, args.javascript, args.python]):
        if "lines" not in args.show:
            args.show += ["lines"]
        args.sort = True
        args.expand = True
        args.comma = True
    # ----- validation ------------------------------------------------------------------------------------------------
    if args.width and args.width <= 4:
        parser.error("--width must be greater than 4")
    if args.no_report and args.verbose_report:
        parser.error("--verbose-report not allowed with argument --no-report")
    # ----- debug -----------------------------------------------------------------------------------------------------
    if args.debug:
        debug_print(vars(args), title="Arguments Accepted By Parser")
    return args

def show_examples():
    print("Placeholder for examples.")

def show_version():
    print(_ATREE_VERSION)

# ----- Parser: Tree-Maker --------------------------------------------------------------------------------------------
class Predicate(abc.ABC):
    @abc.abstractmethod
    def __init__(self):
        pass

    def __call__(self, x):
        return all(f(x) for f in self._pred)

    def __iadd__(self, other):
        self._pred.extend(other._pred)
        return self

class Pattern(Predicate):
    def __init__(self, *preds):
        self._pred = list(preds)

class Ignore(Predicate):
    def __init__(self, *preds):
        self._pred = [lambda x: not p(x) for p in preds]

def match(name, patterns: list, ignore_case=False):
    if ignore_case:
        name = name.lower()
        patterns = [p.lower() for p in patterns]
    return any((fnmatch.fnmatch(name, p) for p in patterns))

def make(args):
    # access options
    fpred = Pattern()
    dpred = Pattern()
    dpost = Pattern()
    list_dirs_only = args.list_dirs_only
    access_level = args.access_level
    always_show_dirs = True
    if list_dirs_only:
        fpred += Pattern(lambda node: False)
    else:
        if not args.access_hidden:
            fpred += Ignore(lambda node: has_hidden_attr(node.path) if IS_WINDOWS else node.name.startswith("."))
        if args.ignore_links:
            fpred += Ignore(lambda node: node.is_link)
        if args.pattern:
            fpred += Pattern(lambda node: match(node.name, args.pattern, args.ignore_case))
            always_show_dirs = False
        if args.ignore:
            fpred += Ignore(lambda node: match(node.name, args.ignore, args.ignore_case))
            always_show_dirs = False
        if args.text:
            fpred += Pattern(lambda node: node.is_text)
            always_show_dirs = False
        if args.code:
            fpred += Pattern(lambda node: node.is_code)
            always_show_dirs = False
    if not args.access_hidden:
        dpred += Ignore(lambda node: has_hidden_attr(node.path) if IS_WINDOWS else node.name.startswith("."))
    if args.ignore_links:
        dpred += Ignore(lambda node: node.is_link)
    if args.pattern_dir:
        dpred += Pattern(lambda node: match(node.name, args.pattern_dir, args.ignore_case))
    if args.ignore_dir:
        dpred += Ignore(lambda node: match(node.name, args.ignore_dir, args.ignore_case))
    # display options
    max_level = args.max_level
    max_files = args.max_files
    max_dirs = args.max_dirs
    if args.show_dirs_only:
        max_files = 0
    # field options
    fields = []
    filter_on = False
    top_mode = None
    top_count = None
    dup_mode = False
    dup_nonempty = False
    oper_dict = {"<": nn_lt, "<=": nn_le, ">": gt, ">=": ge}
    timefmt = args.timefmt
    for x in args.show:
        # top mode
        matched = re.match(r"(f?lines|f?size|f?[abcm]time)(@top)(\d+)", x)
        if matched:
            assert not top_mode, "Top field can be specified only once."
            attr, _, val = matched.groups()
            attr = "f" + attr.lstrip("f")
            val = int(val)
            assert val > 0, f"Expect a positive top count, not {val}"
            top_mode = attr
            top_count = val
            fields = [attr] + fields
            continue
        # lines filter
        matched = re.match(r"(((f?lines)([<>]=?))|(([abru]lines)(>=?)))(\d+)", x)
        if matched:
            _, _, attr1, op1, _, attr2, op2, val = matched.groups()
            attr = attr1 if attr1 else attr2
            op = op1 if op1 else op2
            op = oper_dict[op]
            val = int(val)
            pat = Pattern(lambda node, attr=attr, op=op, val=val: op(getattr(node, attr, None), val))
            if attr[0] in "lfua":
                fpred += pat
            if attr[0] in "brua":
                dpost += pat
            fields.append(attr)
            filter_on = True
            continue
        # size filter
        matched = re.match(r"(((f?size)([<>]=?))|(([abru]size)(>=?)))(((([\d]*[.])?[\d]+)([TtGgMmKk]))|\d+)", x)
        if matched:
            _, _, attr1, op1, _, attr2, op2, expr, _, num, _, unit = matched.groups()
            attr = attr1 if attr1 else attr2
            op = op1 if op1 else op2
            op = oper_dict[op]
            if unit:
                val = measurement_to_size(float(num), unit)
            else:
                val = int(expr)
            pat = Pattern(lambda node, attr=attr, op=op, val=val: op(getattr(node, attr, None), val))
            if attr[0] in "sfua":
                fpred += pat
            if attr[0] in "brua":
                dpost += pat
            fields.append(attr)
            filter_on = True
            continue
        # time filter
        matched = re.match(r"(((f?[abcm]time)([<>]=?))|(([bu][abcm]time)(>=?)))((now-(\d+)([YyMmWwDdHhSs]\w?))|[^\s]+)", x)
        if matched:
            _, _, attr1, op1, _, attr2, op2, string, _, num, unit = matched.groups()
            attr = attr1 if attr1 else attr2
            op = op1 if op1 else op2
            op = oper_dict[op]
            if unit:
                val = measurement_to_time(int(num), unit)
            else:
                try:
                    if timefmt:
                        dt_val = datetime.datetime.strptime(string, timefmt)
                    else:
                        dt_val = datetime.datetime.fromisoformat(string)
                except ValueError:
                    raise RuntimeError(f"{string}? Not sure what time format you're talkin' bout.")
                val = datetime_to_time(dt_val)
            pat = Pattern(lambda node, attr=attr, op=op, val=val: op(getattr(node, attr, None), val))
            if len(attr) == 5 or attr[0] == "u":
                fpred += pat
            if len(attr) == 6 and attr[0] in "bu":
                dpost += pat
            fields.append(attr)
            filter_on = True
            continue
        # fields and duplicates mode
        matched = re.match(r"^[\w-]+$", x)
        if matched:
            attr = matched.group()
            if attr == "duplicates":
                dup_mode = True
                dup_nonempty = False
            elif attr == "nonempty-duplicates":
                dup_mode = True
                dup_nonempty = True
            else:
                if attr in ["name", "path", "father", "children", "lstat"]:
                    raise NotImplementedError(f"Formatter for {attr} field is not implemented.")
                fields.append(attr)
        else:
            raise RuntimeError(f"{x}? Not sure what you're talkin' bout")
    if top_mode and dup_mode:
        raise RuntimeError("Top mode and duplicates mode cannot coexist.")
    if args.code and "lines" not in fields:
        fields.append("lines")
    if dup_mode and "md5" not in fields:
        fields = ["md5"] + fields
    if args.unique:
        fields = unique_list(fields)
    # sort options
    sort = args.sort
    metric = args.metric
    by = args.by
    if not by and sort:
        by = fields_to_by(fields, metric) + ["name"]
    if args.expand:
        expanded_fields = []
        for x in fields:
            if x in ["lines", "size"]:
                expanded_fields.append("r" + x)
                expanded_fields.append("f" + x)
            elif x in ["atime", "btime", "ctime", "mtime"]:
                expanded_fields.append("d" + x)
                expanded_fields.append("f" + x)
            else:
                expanded_fields.append(x)
        fields = expanded_fields
    dirs_first = args.dirs_first
    unsorted = args.unsorted
    reverse = args.reverse
    if filter_on:
        always_show_dirs = False
    if args.always_show_dirs:
        always_show_dirs = True
    # format options
    width = args.width
    do_not_force_width= args.do_not_force_width
    no_color = args.no_color
    no_progress = args.no_progress
    no_warnings = args.no_warnings
    no_header = args.no_header
    no_readlink = args.no_readlink
    no_more = args.no_more
    no_report = args.no_report
    verbose_report = args.verbose_report
    report_only = args.report_only
    no_indent = args.no_indent
    ugly_indent = args.ugly_indent
    file_path = args.file_path
    full_path = args.full_path
    real_path = args.real_path
    quotes = args.quotes
    human = args.human
    raw = args.raw
    comma = args.comma
    iso = args.iso
    timefmt = args.timefmt
    # positional options
    root_path = args.root_path
    tree_args = dict(root_path=root_path,
        list_dirs_only=list_dirs_only, access_level=access_level,
        fpred=fpred, dpred=dpred, dpost=dpost,
        max_level=max_level, max_files=max_files, max_dirs=max_dirs,
        always_show_dirs=always_show_dirs,
        fields=fields, top_mode=top_mode, top_count=top_count,
        dup_mode=dup_mode, dup_nonempty=dup_nonempty,
        by=by, dirs_first=dirs_first, unsorted=unsorted, reverse=reverse,
        width=width, do_not_force_width=do_not_force_width,
        no_color=no_color, no_progress=no_progress, no_warnings=no_warnings,
        no_header=no_header, no_readlink=no_readlink, no_more=no_more,
        no_report=no_report, verbose_report=verbose_report, report_only=report_only,
        no_indent=no_indent, ugly_indent=ugly_indent,
        file_path=file_path, full_path=full_path, real_path=real_path,
        quotes=quotes, raw=raw, comma=comma, human=human,
        iso=iso, timefmt=timefmt)
    if args.debug:
        debug_print(tree_args, title="Arguments To Pass To Tree")
        globals_args = {k: globals()[k] for k in GLOBALS}
        debug_print(globals_args, title="Globals", replace=False)
        sys.exit()
    if args.examples:
        show_examples()
        sys.exit()
    if args.version:
        show_version()
        sys.exit()
    return Tree(**tree_args)

def main():
    args = parse()
    tree = make(args)
    tree.print()

if __name__ == "__main__":
    main()
