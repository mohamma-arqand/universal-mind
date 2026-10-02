"""R61-S2 — the write-path policy: sensitive targets are never written.

The deep review's security persona WROTE C:/Users/.../.ssh/id_rsa through
«فایل متنی … را با محتوای x بنویس» — reading secrets was guarded,
OVERWRITING them was not. The write now refuses, by name, before the
exists-check (even a non-existing id_rsa is never created by us), and the
system directories (Windows/Program Files/ProgramData) are read-only to us.
"""

from __future__ import annotations

from pathlib import Path

from universal_mind.textfile_tool import TextFileTool


class TestTheSensitiveTargets:
    def test_an_ssh_key_is_never_written(self) -> None:
        out = TextFileTool().write(r"C:/Users/x/.ssh/id_rsa", "x")
        assert out["ok"] is False and "حساس" in out["error"]

    def test_a_gnupg_dir_is_never_written(self) -> None:
        out = TextFileTool().write(r"C:/Users/x/.gnupg/secring", "x")
        assert out["ok"] is False and "حساس" in out["error"]

    def test_hosts_is_never_written(self) -> None:
        out = TextFileTool().write(r"C:/Windows/System32/drivers/etc/hosts", "x")
        assert out["ok"] is False and "حساس" in out["error"]

    def test_the_windows_dir_is_never_a_write_target(self) -> None:
        out = TextFileTool().write(r"C:/Windows/whatever.txt", "x")
        assert out["ok"] is False and "حساس" in out["error"]

    def test_program_files_is_never_a_write_target(self) -> None:
        out = TextFileTool().write(r"C:/Program Files/app/cfg.txt", "x")
        assert out["ok"] is False and "حساس" in out["error"]

    def test_the_refusal_names_the_path(self) -> None:
        out = TextFileTool().write(r"C:/Users/x/.ssh/id_rsa", "x")
        assert "id_rsa" in out["error"]


class TestNormalWritesStillWork:
    def test_an_ordinary_file_is_written(self, tmp_path: Path) -> None:
        out = TextFileTool().write(str(tmp_path / "note.txt"), "hello")
        assert out["ok"] is True
        assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "hello"

    def test_the_user_documents_folder_is_writable(self, tmp_path: Path) -> None:
        # the policy guards SYSTEM paths, not the operator's own home
        out = TextFileTool().write(str(tmp_path / "docs" / "a.txt"), "x")
        assert out["ok"] is True

    def test_an_existing_file_still_refuses_overwrite(self, tmp_path: Path) -> None:
        f = tmp_path / "note.txt"
        f.write_text("original", encoding="utf-8")
        out = TextFileTool().write(str(f), "other")
        assert out["ok"] is False and "دورنویسی" in out["error"]
        assert f.read_text(encoding="utf-8") == "original"
