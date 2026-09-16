import os
from typing import Set, Optional, Dict, List
from backend.app.analyzers.architecture.parser import RawImport

# Common Python standard library modules to discard
PYTHON_STDLIB = {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "binascii", "bisect", "builtins",
    "bz2", "calendar", "cgi", "cmath", "cmd", "code", "codecs", "collections", "colorsys",
    "compileall", "concurrent", "configparser", "contextlib", "contextvars", "copy", "copyreg",
    "cProfile", "csv", "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings", "ensurepip", "enum",
    "errno", "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch", "fractions",
    "ftplib", "functools", "gc", "getopt", "getpass", "gettext", "glob", "graphlib",
    "grp", "gzip", "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
    "imghdr", "imp", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "lib2to3", "linecache", "locale", "logging", "lzma", "mailbox", "mailcap",
    "marshal", "math", "mimetypes", "mmap", "modulefinder", "msilib", "msvcrt", "multiprocessing",
    "netrc", "nis", "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
    "pyclbr", "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
    "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
    "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics", "string",
    "stringprep", "struct", "subprocess", "sunau", "symbol", "symtable", "sys",
    "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
    "test", "textwrap", "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo",
    "types", "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
    "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
    "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib", "_thread"
}

# Common Node.js standard libraries to discard
NODE_STDLIB = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console", "constants",
    "crypto", "dgram", "diagnostics_channel", "dns", "domain", "events", "fs", "fs/promises",
    "http", "http2", "https", "inspector", "module", "net", "os", "path", "path/posix",
    "path/win32", "perf_hooks", "process", "punycode", "querystring", "readline", "repl",
    "stream", "stream/consumers", "stream/promises", "stream/web", "string_decoder",
    "timers", "timers/promises", "tls", "trace_events", "tty", "url", "util", "util/types",
    "v8", "vm", "wasi", "worker_threads", "zlib"
}

JS_EXTENSIONS = [
    "",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    "/index.ts",
    "/index.tsx",
    "/index.js",
    "/index.jsx",
]


class ImportResolver:
    def __init__(self, all_project_files: Set[str]):
        """
        all_project_files: set of normalized relative paths (e.g. {'backend/app/main.py', 'src/App.tsx'})
        """
        self.all_files = {f.replace("\\", "/").lstrip("./") for f in all_project_files}

        # Build index for fast matching
        # 1. Base name map: "main.py" -> ["backend/app/main.py"]
        self.basename_map: Dict[str, List[str]] = {}
        # 2. Module dot-path map: "backend.app.main" -> "backend/app/main.py"
        self.module_map: Dict[str, str] = {}

        for f in self.all_files:
            bname = os.path.basename(f)
            self.basename_map.setdefault(bname, []).append(f)

            # Strip extension for module matching
            root, ext = os.path.splitext(f)
            if ext in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                dot_path = root.replace("/", ".")
                self.module_map[dot_path] = f
                # Also index suffix without leading folders e.g. "app.main"
                parts = dot_path.split(".")
                for i in range(1, len(parts)):
                    sub_dot = ".".join(parts[i:])
                    if sub_dot not in self.module_map:
                        self.module_map[sub_dot] = f

    def resolve(self, raw_import: RawImport, language: str) -> Optional[str]:
        """Resolve a RawImport to a matching project file path.
        Returns normalized relative path or None if external / not found.
        """
        lang = language.lower()
        if lang == "python":
            return self._resolve_python(raw_import)
        elif lang in {"javascript", "typescript", "jsx", "tsx"}:
            return self._resolve_js_ts(raw_import)
        return None

    def _resolve_python(self, raw_import: RawImport) -> Optional[str]:
        mod = raw_import.imported_module
        source_file = raw_import.source_file.replace("\\", "/").lstrip("./")

        # 1. Check if top-level standard library
        first_segment = mod.split(".")[0] if mod else ""
        if not raw_import.is_relative and first_segment in PYTHON_STDLIB:
            return None

        # 2. Handle Relative Imports (from . import db, from ..services import user)
        if raw_import.is_relative:
            source_dir = os.path.dirname(source_file)
            level = raw_import.level
            # Move up (level - 1) directories from source_dir
            curr = source_dir
            for _ in range(level - 1):
                curr = os.path.dirname(curr)

            # Look for module or imported names
            candidates = []
            if mod:
                sub_path = mod.replace(".", "/")
                candidates.append(os.path.normpath(os.path.join(curr, sub_path + ".py")).replace("\\", "/"))
                candidates.append(os.path.normpath(os.path.join(curr, sub_path, "__init__.py")).replace("\\", "/"))
            else:
                # e.g. from . import user
                for name in raw_import.imported_names:
                    candidates.append(os.path.normpath(os.path.join(curr, name + ".py")).replace("\\", "/"))
                    candidates.append(os.path.normpath(os.path.join(curr, name, "__init__.py")).replace("\\", "/"))

            for cand in candidates:
                cand_clean = cand.lstrip("./")
                if cand_clean in self.all_files and cand_clean != source_file:
                    return cand_clean
            return None

        # 3. Handle Absolute / Root-relative Python imports
        if not mod:
            return None

        # Direct dot-path match
        if mod in self.module_map:
            target = self.module_map[mod]
            if target != source_file:
                return target

        # Check if mod path directly exists
        as_path = mod.replace(".", "/") + ".py"
        for f in self.all_files:
            if f.endswith(as_path) and f != source_file:
                return f

        # Check `__init__.py` in package
        as_init = mod.replace(".", "/") + "/__init__.py"
        for f in self.all_files:
            if f.endswith(as_init) and f != source_file:
                return f

        # Check if one of the imported_names is a local file in that module folder
        if raw_import.imported_names:
            for name in raw_import.imported_names:
                combo = f"{mod.replace('.', '/')}/{name}.py"
                for f in self.all_files:
                    if f.endswith(combo) and f != source_file:
                        return f

        # Check same-directory import without leading dot (common in Python packages)
        source_dir = os.path.dirname(source_file)
        local_cand = os.path.normpath(os.path.join(source_dir, mod.replace(".", "/") + ".py")).replace("\\", "/").lstrip("./")
        if local_cand in self.all_files and local_cand != source_file:
            return local_cand

        return None

    def _resolve_js_ts(self, raw_import: RawImport) -> Optional[str]:
        mod = raw_import.imported_module
        source_file = raw_import.source_file.replace("\\", "/").lstrip("./")

        # 1. Discard Node.js standard libraries
        first_segment = mod.split("/")[0] if mod else ""
        if first_segment in NODE_STDLIB or mod in NODE_STDLIB:
            return None

        # 2. Relative Imports (./ or ../)
        if mod.startswith("."):
            source_dir = os.path.dirname(source_file)
            base_cand = os.path.normpath(os.path.join(source_dir, mod)).replace("\\", "/")

            for ext in JS_EXTENSIONS:
                cand = (base_cand + ext).lstrip("./")
                if cand in self.all_files and cand != source_file:
                    return cand

        # 3. Path aliases: @/ or ~/ (e.g. "@/components/Button")
        if mod.startswith("@/") or mod.startswith("~/"):
            stripped = mod[2:]
            for ext in JS_EXTENSIONS:
                # Try under root
                c1 = (stripped + ext).lstrip("./")
                if c1 in self.all_files and c1 != source_file:
                    return c1
                # Try under src/
                c2 = ("src/" + stripped + ext).lstrip("./")
                if c2 in self.all_files and c2 != source_file:
                    return c2

        return None
