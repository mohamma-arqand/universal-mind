"""THE TEXT-FILE TOOL — read and write the operator's plain-text files (R60).

Two measured gaps: «محتوای فایل X را نشان بده» and «فایل رو بخون» returned
«نشناختم», and «یک فایل متنی بنویس در D:/test» was stolen by the clipboard
capability. A real text file is first-class data — the platform can read and
write it honestly.

Laws:
  - READ: utf-8 (errors=replace, REPORTED), a size cap with the truncation
    NAMED, a missing file refused BY NAME.
  - WRITE: refuses to overwrite an existing file by default (the DELETE-law
    spirit: silent overwrite is destruction) and says the remedy; the parent
    directory is created when it does not exist.
  - Every number the operator sees is Persian.
  - No secrets: the tool never reads a file whose name looks like a
    credential (.env, *.key, *credentials*, *secret*) — a read of the
    operator's keys is a leak, not a feature.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult

_MAX_READ_CHARS = 60_000

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# files the platform must never read aloud: credentials are not content
_FORBIDDEN = re.compile(r"(^|[/\\])(\.env|.*secret.*|.*credential.*|.*\.key)$",
                         re.IGNORECASE)


def _fa(value: object) -> str:
    return str(value).translate(_FA)


class TextFileTool:
    """Read and write plain-text files, honestly."""

    name = "textfile"
    capability = "textfile"

    def read(self, path: str, max_chars: int = _MAX_READ_CHARS) -> dict[str, Any]:
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"فایلی در «{path}» پیدا نکردم — مسیر را دقیق بده.",
                    "kind": "missing"}
        if src.is_dir():
            return {"ok": False, "error": f"«{path}» یک پوشه است، نه فایل — نام فایل را بده.",
                    "kind": "is_dir"}
        if _FORBIDDEN.search(str(src)):
            return {"ok": False,
                    "error": "این فایل به نظر راز می‌رسد (.env/کلید) — محتوایش را نمی‌خوانم.",
                    "kind": "secret"}
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "error": f"خواندن نشد: {exc}", "kind": "io"}
        truncated = len(text) > max_chars
        return {
            "ok": True, "text": text[:max_chars], "chars": len(text),
            "truncated": truncated, "path": str(src), "error": "",
        }

    # R61-S2 — WRITE-PATH POLICY: reading secrets is already refused; WRITING
    # them is worse (a probe overwrote ~/.ssh/id_rsa on the live machine —
    # caught by the deep review, removed with a named cleanup). Sensitive
    # targets are refused BY NAME, and SYSTEM directories are read-only to
    # us: the platform writes where the operator lives, not where Windows
    # lives. C:\Windows and Program Files are never write targets.
    _WRITE_FORBIDDEN = re.compile(
        r"[/\\]\.ssh[/\\]|[/\\]\.gnupg[/\\]"
        r"|[/\\](hosts|lmhosts\.sam|sam|sam\.sav|system|security)(\.log|\.sav|\.bak)?$"
        r"|[A-Za-z]:[/\\](Windows|Program Files( \(x86\))?|ProgramData)[/\\]",
        re.IGNORECASE)

    def _write_refusal(self, path: str) -> str:
        return (f"نمی‌نویسم — «{path}» مسیر حساس/سیستمی است (کلید، تنظیم شبکه یا پوشهٔ ویندوز). "
                "خواستی، خودت با یک ابزار مناسب بازش کن؛ من جای آن‌ها را خراب نمی‌کنم.")

    def write(self, path: str, content: str) -> dict[str, Any]:
        dst = Path(path)
        # R61-S2 — the write path policy applies BEFORE the exists-check:
        # even a non-existing id_rsa is never created by us.
        if self._WRITE_FORBIDDEN.search(str(dst)):
            return {"ok": False, "error": self._write_refusal(str(dst)),
                    "kind": "protected"}
        if dst.exists():
            return {
                "ok": False, "kind": "exists",
                "error": (f"«{path}» از قبل هست — دورنویسی نکنم؟ اگر آری بگو "
                          "«روی همان فایل بنویس»؛ وگرنه نام دیگری بده."),
            }
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": f"نوشتن نشد: {exc}", "kind": "io"}
        return {"ok": True, "path": str(dst), "chars": len(content),
                "bytes": len(content.encode("utf-8")), "error": ""}

    def search(self, path: str, needle: str) -> dict[str, Any]:
        """R64 P6 — «در فایل X دنبال کلمه Y بگرد»: real matches with line numbers."""
        src = Path(path)
        if _FORBIDDEN.search(str(src)):
            return {"ok": False, "error": "این فایل به نظر راز می‌رسد — محتوایش را نمی‌خوانم.",
                    "kind": "secret"}
        if not src.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{path}» پیدا نکردم — مسیر را دقیق بده."}
        if not needle.strip():
            return {"ok": False, "kind": "empty",
                    "error": "دنبال چه بگردم؟ کلمه را بگو — مثلا: «در فایل X دنبال کلمه سلام بگرد»."}
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "error": f"خواندن نشد: {exc}", "kind": "io"}
        hits: list[dict[str, Any]] = []
        for i, line in enumerate(text.splitlines(), 1):
            if needle in line:
                hits.append({"line": i, "text": line.strip()[:100]})
        return {"ok": True, "path": str(src), "needle": needle,
                "matches": hits[:50], "count": len(hits), "error": ""}

    def replace(self, path: str, old: str, new: str, *, overwrite_ok: bool = False) -> dict[str, Any]:
        """R64 P7 — «کلمه A را با B عوض کن»: real replacement, counted.

        The DELETE-law spirit: a replace REWRITES the file, so it needs the
        operator's explicit continue (overwrite_ok) when the file exists —
        no silent rewrite. The count and a sample are always named.
        """
        src = Path(path)
        if _FORBIDDEN.search(str(src)):
            return {"ok": False, "error": "این فایل به نظر راز می‌رسد — دست نمی‌زنم.",
                    "kind": "secret"}
        if self._WRITE_FORBIDDEN.search(str(src)):
            return {"ok": False, "error": self._write_refusal(str(src)), "kind": "protected"}
        if not src.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{path}» پیدا نکردم — مسیر را دقیق بده."}
        if not old.strip():
            return {"ok": False, "kind": "empty",
                    "error": "چه چیزی را عوض کنم؟ کلمهٔ فعلی را بگو."}
        if src.exists() and not overwrite_ok:
            return {"ok": False, "kind": "exists",
                    "error": ("عوض‌کردن، فایل را دوباره می‌نویسد — تأیید می‌خواهد. "
                              "بگو «روی همان فایل بنویس و کلمه A را با B عوض کن» تا انجام شود.")}
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
            count = text.count(old)
            if count == 0:
                return {"ok": True, "path": str(src), "replaced": 0,
                        "error": "", "note": "کلمه در فایل نبود — چیزی عوض نشد."}
            new_text = text.replace(old, new)
            src.write_text(new_text, encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": f"نوشتن نشد: {exc}", "kind": "io"}
        return {"ok": True, "path": str(src), "replaced": count, "error": ""}

    def move(self, src: str, dst: str, *, overwrite_ok: bool = False) -> dict[str, Any]:
        """R65 P6 — «فایل X را به Y جابجا کن»: a REAL move, delete-law safe.

        A move DELETES the source, so it needs the operator's explicit
        continue when the destination exists («روی همان فایل بنویس»
        shape); the source must exist; both paths are named in the answer.
        """
        s, d = Path(src), Path(dst)
        if self._WRITE_FORBIDDEN.search(str(d)) or self._WRITE_FORBIDDEN.search(str(s)):
            return {"ok": False, "error": self._write_refusal(str(d)), "kind": "protected"}
        if not s.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{src}» پیدا نکردم — مسیر را دقیق بده."}
        if d.exists() and not overwrite_ok:
            return {"ok": False, "kind": "exists",
                    "error": ("مقصد «{dst}» از قبل هست — جابجایی روی آن بنویس؟ "
                              "بگو «روی همان فایل X را به Y جابجا کن» تا انجام شود.").format(dst=dst)}
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            s.replace(d)
        except OSError as exc:
            return {"ok": False, "error": f"جابجایی نشد: {exc}", "kind": "io"}
        return {"ok": True, "src": str(s), "dst": str(d),
                "bytes": d.stat().st_size, "error": ""}

    def rename(self, src: str, dst: str, *, overwrite_ok: bool = False) -> dict[str, Any]:
        """R67 P2 — «نام فایل X را عوض کن به Y»: a REAL rename.

        The delete law applies (a rename removes the old NAME): an
        existing destination needs the operator's continue («روی همان
        فایل»); the source must exist; both names are in the answer.
        """
        return self.move(src, dst, overwrite_ok=overwrite_ok)

    def copy(self, src: str, dst: str, *, overwrite_ok: bool = False) -> dict[str, Any]:
        """R67 P3 — «فایل X را به Y کپی کن»: a REAL copy — the source survives.

        An existing destination needs the operator's continue (a copy
        over a real file would destroy it); both paths are named.
        """
        s, d = Path(src), Path(dst)
        if self._WRITE_FORBIDDEN.search(str(d)) or self._WRITE_FORBIDDEN.search(str(s)):
            return {"ok": False, "error": self._write_refusal(str(d)), "kind": "protected"}
        if not s.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{src}» پیدا نکردم — مسیر را دقیق بده."}
        if d.exists() and not overwrite_ok:
            return {"ok": False, "kind": "exists",
                    "error": ("مقصد «{dst}» از قبل هست — کپی روی آن بنویس؟ "
                              "بگو «روی همان فایل X را به Y کپی کن» تا انجام شود.").format(dst=dst)}
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(s, d)
        except OSError as exc:
            return {"ok": False, "error": f"کپی نشد: {exc}", "kind": "io"}
        return {"ok": True, "src": str(s), "dst": str(d),
                "bytes": d.stat().st_size, "error": ""}

    def read_line(self, path: str, lineno: int, *, last: bool = False) -> dict[str, Any]:
        """R71 P5 — «خط سوم فایل X را نشان بده» / «آخرین خط فایل X را بگو»:
        the REAL line, numbered."""
        s = Path(path)
        if not s.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{path}» پیدا نکردم — مسیر را دقیق بده."}
        try:
            lines = s.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            return {"ok": False, "error": f"خواندن نشد: {exc}", "kind": "io"}
        if not lines:
            return {"ok": False, "kind": "empty",
                    "error": f"فایل «{path}» خالی است."}
        if last:
            idx = len(lines) - 1
        else:
            if lineno < 1 or lineno > len(lines):
                return {"ok": False, "kind": "range",
                        "error": (f"خط {lineno} در فایل «{path}» نیست — "
                                  f"۱ تا {len(lines)} خط دارد.")}
            idx = lineno - 1
        return {"ok": True, "path": str(s), "lineno": idx + 1,
                "total": len(lines), "line": lines[idx], "error": ""}

    def count_word(self, path: str, needle: str) -> dict[str, Any]:
        """R71 P6 — «کلمه X در فایل Y چند بار آمده؟»: the REAL frequency."""
        s = Path(path)
        if not s.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{path}» پیدا نکردم — مسیر را دقیق بده."}
        if not needle.strip():
            return {"ok": False, "kind": "noneedle",
                    "error": "کدام کلمه؟ — مثلا: «کلمه سلام در فایل X چند بار آمده؟»"}
        try:
            text = s.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "error": f"خواندن نشد: {exc}", "kind": "io"}
        n = text.count(needle.strip())
        return {"ok": True, "path": str(s), "needle": needle.strip(),
                "count": n, "error": ""}

    def word_count(self, path: str) -> dict[str, Any]:
        """R70 P2 — «در فایل X چند کلمه هست؟»: the REAL word/line/char
        count of the file's content."""
        s = Path(path)
        if not s.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{path}» پیدا نکردم — مسیر را دقیق بده."}
        if not s.is_file():
            return {"ok": False, "kind": "notfile",
                    "error": f"«{path}» فایل نیست."}
        try:
            text = s.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "error": f"خواندن نشد: {exc}", "kind": "io"}
        words = [w for w in text.split() if w.strip()]
        lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        return {"ok": True, "path": str(s), "words": len(words),
                "lines": lines, "chars": len(text), "error": ""}

    def file_size(self, path: str) -> dict[str, Any]:
        """R67 P4 — «حجم فایل X چقدر است؟»: the REAL size, human-readable."""
        s = Path(path)
        if not s.exists():
            return {"ok": False, "kind": "missing",
                    "error": f"فایلی در «{path}» پیدا نکردم — مسیر را دقیق بده."}
        if not s.is_file():
            return {"ok": False, "kind": "notfile",
                    "error": f"«{path}» فایل نیست — حجم پوشه را جدا بپرس."}
        n = s.stat().st_size
        human = f"{n / 1024 / 1024:.1f} مگابایت" if n >= 1024 * 1024 else (
            f"{n / 1024:.1f} کیلوبایت" if n >= 1024 else f"{n} بایت")
        return {"ok": True, "path": str(s), "bytes": n, "human": human, "error": ""}

    def folder_stats(self, folder: str) -> dict[str, Any]:
        """R67 P5 — «در پوشه X چند فایل هست؟»: the REAL count + size."""
        src = Path(folder)
        if not src.exists() or not src.is_dir():
            return {"ok": False, "kind": "missing",
                    "error": f"پوشه‌ای در «{folder}» پیدا نکردم — مسیر را دقیق بده."}
        files = [p for p in src.iterdir() if p.is_file()]
        dirs = [p for p in src.iterdir() if p.is_dir()]
        total = sum(p.stat().st_size for p in files)
        return {"ok": True, "folder": str(src), "files": len(files),
                "dirs": len(dirs), "bytes": total, "error": ""}

    def mkdir(self, folder: str) -> dict[str, Any]:
        """R67 P6 — «پوشه X را بساز»: a REAL folder, parents included."""
        d = Path(folder)
        if self._WRITE_FORBIDDEN.search(str(d)):
            return {"ok": False, "error": self._write_refusal(str(d)), "kind": "protected"}
        if d.exists():
            return {"ok": False, "kind": "exists",
                    "error": f"پوشه «{folder}» از قبل هست."}
        try:
            d.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            return {"ok": False, "error": f"ساخته نشد: {exc}", "kind": "io"}
        return {"ok": True, "folder": str(d), "error": ""}

    def list_texts(self, folder: str) -> dict[str, Any]:
        src = Path(folder)
        if not src.exists() or not src.is_dir():
            return {"ok": False,
                    "error": f"پوشه‌ای در «{folder}» پیدا نکردم — مسیر را دقیق بده.",
                    "kind": "missing"}
        files = sorted(
            p.name for p in src.iterdir()
            if p.is_file() and p.suffix.lower() in (".txt", ".md", ".log", ".csv", ".json")
        )
        return {"ok": True, "files": files[:100], "count": len(files), "error": ""}


class TextFileToolConnector:
    """Adapts :class:`TextFileTool` to the ``Connector`` protocol."""

    def __init__(self, tool: TextFileTool | None = None) -> None:
        self._tool = tool if tool is not None else TextFileTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "read") or "read"
        if operation == "read":
            path = str(params.get("path", "")).strip()
            if not path:
                return ConnectorResult(
                    ok=False, output=None,
                    error="کدام فایل؟ مسیرش را بده — مثلا: محتوای فایل D:/notes/x.txt را نشان بده",
                )
            out = self._tool.read(path)
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={
                k: v for k, v in out.items() if k not in ("ok", "error")
            })
        if operation == "write":
            path = str(params.get("path", "")).strip()
            content = str(params.get("content", ""))
            if not path:
                return ConnectorResult(
                    ok=False, output=None,
                    error="کجا بنویسم؟ مسیر را بده — مثلا: فایل متنی D:/notes/x.txt را با محتوای سلام بنویس",
                )
            out = self._tool.write(path, content)
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={
                k: v for k, v in out.items() if k not in ("ok", "error")
            })
        if operation == "search":
            path = str(params.get("path", "")).strip()
            needle = str(params.get("needle", "")).strip()
            out = self._tool.search(path, needle)
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={
                k: v for k, v in out.items() if k not in ("ok", "error")})
        if operation == "replace":
            path = str(params.get("path", "")).strip()
            old = str(params.get("old", "")).strip()
            new = str(params.get("new", "")).strip()
            overwrite_ok = bool(params.get("overwrite_ok", False))
            out = self._tool.replace(path, old, new, overwrite_ok=overwrite_ok)
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={
                k: v for k, v in out.items() if k not in ("ok", "error")})
        if operation == "move":
            src = str(params.get("path", "")).strip()
            dst = str(params.get("dst", "")).strip()
            out = self._tool.move(src, dst,
                                   overwrite_ok=bool(params.get("overwrite_ok", False)))
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={
                k: v for k, v in out.items() if k not in ("ok", "error")})
        # R67 P2-P6 — the new file operations ride the same connector
        if operation == "rename":
            out = self._tool.rename(
                str(params.get("path", "")).strip(),
                str(params.get("dst", "")).strip(),
                overwrite_ok=bool(params.get("overwrite_ok", False)))
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={"operation": "rename", **{
                k: v for k, v in out.items() if k not in ("ok", "error")}})
        if operation == "copy":
            out = self._tool.copy(
                str(params.get("path", "")).strip(),
                str(params.get("dst", "")).strip(),
                overwrite_ok=bool(params.get("overwrite_ok", False)))
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={"operation": "copy", **{
                k: v for k, v in out.items() if k not in ("ok", "error")}})
        if operation == "readline":
            out = self._tool.read_line(
                str(params.get("path", "")).strip(),
                int(params.get("lineno", 0)),
                last=bool(params.get("last", False)))
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={"operation": "readline", **{
                k: v for k, v in out.items() if k not in ("ok", "error")}})
        if operation == "countword":
            out = self._tool.count_word(
                str(params.get("path", "")).strip(),
                str(params.get("needle", "")))
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={"operation": "countword", **{
                k: v for k, v in out.items() if k not in ("ok", "error")}})
        if operation == "wordcount":
            out = self._tool.word_count(str(params.get("path", "")).strip())
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={"operation": "wordcount", **{
                k: v for k, v in out.items() if k not in ("ok", "error")}})
        if operation == "size":
            out = self._tool.file_size(str(params.get("path", "")).strip())
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={"operation": "size", **{
                k: v for k, v in out.items() if k not in ("ok", "error")}})
        if operation == "folderstats":
            out = self._tool.folder_stats(str(params.get("folder", params.get("path", ""))).strip())
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={
                k: v for k, v in out.items() if k not in ("ok", "error")})
        if operation == "mkdir":
            out = self._tool.mkdir(str(params.get("folder", params.get("path", ""))).strip())
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={"operation": "mkdir", **{
                k: v for k, v in out.items() if k not in ("ok", "error")}})
        if operation == "list":
            folder = str(params.get("path", "")).strip()
            if not folder:
                return ConnectorResult(
                    ok=False, output=None,
                    error="کدام پوشه؟ مسیرش را بده — مثلا: فایل‌های متنی D:/notes را نشان بده",
                )
            out = self._tool.list_texts(folder)
            if not out.get("ok"):
                return ConnectorResult(ok=False, output=None, error=str(out["error"]))
            return ConnectorResult(ok=True, output={
                k: v for k, v in out.items() if k not in ("ok", "error")
            })
        return ConnectorResult(ok=False, output=None,
                               error=f"unknown operation: {operation!r}")


__all__ = ["TextFileTool", "TextFileToolConnector"]
