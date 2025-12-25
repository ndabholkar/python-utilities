import unittest
import os
import json
import hashlib
from pathlib import Path
import tempfile

from python_utilities import FileUtils


class FileUtilsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.base = Path(self.td.name)
        self.fs = FileUtils(base_dir=self.base)

    def test_write_read_text_and_lines(self):
        p = self.fs.write_text("a/b/c.txt", "hello")
        self.assertTrue(p.exists())
        self.assertEqual(self.fs.read_text("a/b/c.txt"), "hello")

        # lines
        self.fs.write_lines("a/lines.txt", ["one", "two"])  # newline ends with \n
        lines = self.fs.read_lines("a/lines.txt")
        self.assertEqual(lines, ["one", "two"])

        # append
        self.fs.append_text("a/lines.txt", "three\n")
        lines2 = self.fs.read_text("a/lines.txt").splitlines()
        self.assertEqual(lines2[-1], "three")

    def test_json_roundtrip(self):
        obj = {"x": 1, "name": "π"}
        self.fs.write_json("data/config.json", obj, indent=2, ensure_ascii=False)
        got = self.fs.read_json("data/config.json")
        self.assertEqual(got, obj)

    def test_atomic_write_text_and_json(self):
        p = self.fs.atomic_write_text("safe/file.txt", "alpha")
        self.assertTrue(p.exists())
        self.assertEqual(self.fs.read_text("safe/file.txt"), "alpha")

        pj = self.fs.atomic_write_json("safe/obj.json", {"a": 2})
        self.assertTrue(pj.exists())
        self.assertEqual(self.fs.read_json("safe/obj.json"), {"a": 2})

    def test_fs_ops_exists_isdir_isfile_size(self):
        self.assertFalse(self.fs.exists("x/y.txt"))
        self.fs.touch("x/y.txt")
        self.assertTrue(self.fs.exists("x/y.txt"))
        self.assertTrue(self.fs.is_file("x/y.txt"))
        self.assertFalse(self.fs.is_dir("x/y.txt"))
        self.assertEqual(self.fs.size("x/y.txt"), 0)

        self.fs.mkdirs("x/dir1/dir2")
        self.assertTrue(self.fs.is_dir("x/dir1/dir2"))

    def test_listdir_and_glob(self):
        self.fs.mkdirs("d")
        for name in ["a.txt", "b.log", "c.txt"]:
            self.fs.write_text(self.base / "d" / name, name)
        entries = [p.name for p in self.fs.listdir("d")]
        self.assertEqual(entries, ["a.txt", "b.log", "c.txt"])  # sorted

        gl = [p.name for p in self.fs.glob("d", "*.txt")]
        self.assertEqual(gl, ["a.txt", "c.txt"])  # sorted

    def test_copy_move_rename_remove_rmtree(self):
        src = self.fs.write_text("s/source.txt", "data")
        # copy into directory
        dst_dir = self.fs.mkdirs("d1")
        copied = self.fs.copy(src, dst_dir / "source.txt")
        self.assertTrue(copied.exists())
        self.assertEqual(self.fs.read_text(copied), "data")

        # move to another directory
        self.fs.mkdirs("d2")
        moved = self.fs.move(copied, self.base / "d2" / "moved.txt")
        self.assertTrue(moved.exists())
        self.assertFalse(copied.exists())

        # rename within same dir
        renamed = self.fs.rename(moved, moved.with_name("renamed.txt"))
        self.assertTrue(renamed.exists())
        self.assertFalse(moved.exists())

        # remove file
        self.fs.remove(renamed)
        self.assertFalse(renamed.exists())
        # missing_ok
        self.fs.remove(renamed, missing_ok=True)

        # rmtree directory
        self.fs.mkdirs("to_rm/a")
        self.fs.write_text("to_rm/a/f.txt", "x")
        self.assertTrue(self.fs.exists("to_rm"))
        self.fs.rmtree("to_rm")
        self.assertFalse(self.fs.exists("to_rm"))
        # missing_ok
        self.fs.rmtree("to_rm", missing_ok=True)

    def test_hashing(self):
        # create a file with predictable content
        data = ("abc123\n" * 10000).encode("utf-8")
        p = self.fs.write_bytes("h/big.bin", data)

        sha = hashlib.sha256(data).hexdigest()
        md5 = hashlib.md5(data).hexdigest()
        self.assertEqual(self.fs.sha256_file(p), sha)
        self.assertEqual(self.fs.md5_file(p), md5)

    def test_temporary_directory(self):
        with self.fs.temporary_directory(prefix="t_", dir=self.base) as td:
            path = td / "file.txt"
            path.write_text("x", encoding="utf-8")
            self.assertTrue(path.exists())
        # After context, directory removed
        self.assertFalse(td.exists())

    def test_path_helpers(self):
        p = self.fs.ensure_suffix("file", ".log")
        self.assertTrue(str(p).endswith(".log"))
        p2 = self.fs.change_ext("file.txt", ".json")
        self.assertTrue(str(p2).endswith(".json"))


if __name__ == "__main__":
    unittest.main()
