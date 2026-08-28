# -*- coding: utf-8 -*-
"""index_materials 测试（标准库 unittest，无第三方依赖）。

运行：python scripts/test_index_materials.py
"""
import json
import tempfile
import unittest
from pathlib import Path

import index_materials as im
from index_materials import build_index, write_index


def make_tree(files: dict) -> Path:
    """files: {相对路径: 字符串内容 或 ("bytes", bytes)}，返回临时目录根。"""
    root = Path(tempfile.mkdtemp(prefix="idx-test-"))
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, tuple) and content[0] == "bytes":
            p.write_bytes(content[1])
        else:
            p.write_text(content, encoding="utf-8")
    return root


class BuildIndexTest(unittest.TestCase):
    def test_md_indexed_with_headings(self):
        root = make_tree({
            "a.md": "# 系统概述\n第一段内容。\n## 架构\n第二段内容。\n",
        })
        idx = build_index(root)
        self.assertEqual(idx["file_count"], 1)
        f = idx["files"][0]
        self.assertEqual(f["path"], "a.md")
        self.assertEqual(f["title"], "系统概述")
        self.assertEqual(f["lines"], 4)
        self.assertEqual(
            [(c["title"], c["start"], c["end"]) for c in f["chunks"]],
            [("系统概述", 1, 2), ("架构", 3, 4)],
        )

    def test_txt_paragraph_chunks(self):
        root = make_tree({
            "b.txt": "第一段第一行\n第一段第二行\n\n第二段第一行\n",
        })
        idx = build_index(root)
        f = idx["files"][0]
        self.assertEqual(f["ext"], ".txt")
        self.assertEqual(
            [(c["title"], c["start"], c["end"]) for c in f["chunks"]],
            [("第一段第一行", 1, 2), ("第二段第一行", 4, 4)],
        )

    def test_preamble_before_first_heading(self):
        root = make_tree({
            "intro.md": "开头前言第一行\n\n# 标题一\n正文\n",
        })
        f = build_index(root)["files"][0]
        self.assertEqual(
            [(c["title"], c["start"], c["end"]) for c in f["chunks"]],
            [("intro", 1, 2), ("标题一", 3, 4)],
        )

    def test_hidden_and_unsupported_ignored(self):
        root = make_tree({
            "a.md": "# A\n内容\n",
            ".DS_Store": "junk",
            ".hidden/x.md": "# X\n内容\n",
            "nested/report.txt": "报告内容\n",
            "notes.docx": "binary",
            "deep/.git/config": "junk",
        })
        idx = build_index(root)
        self.assertEqual(
            [f["path"] for f in idx["files"]],
            ["a.md", "nested/report.txt"],
        )

    def test_root_under_hidden_parent(self):
        base = Path(tempfile.mkdtemp(prefix="idx-root-"))
        root = base / ".agents" / "skills" / "technical-proposal-expert"
        root.mkdir(parents=True)
        (root / "a.md").write_text("# A\n内容\n", encoding="utf-8")
        idx = build_index(root)
        self.assertEqual(idx["file_count"], 1)
        self.assertEqual(idx["files"][0]["path"], "a.md")

    def test_nested_relative_path(self):
        root = make_tree({"top/sub/deep/c.md": "# 深\n内容\n"})
        f = build_index(root)["files"][0]
        self.assertEqual(f["path"], "top/sub/deep/c.md")

    def test_missing_root_ok(self):
        root = Path(tempfile.mkdtemp(prefix="idx-empty-")) / "not-exist"
        idx = build_index(root)
        self.assertEqual(idx["file_count"], 0)
        self.assertEqual(idx["files"], [])

    def test_order_stable(self):
        root = make_tree({"b.md": "# B\n", "a.md": "# A\n", "c.md": "# C\n"})
        idx = build_index(root)
        self.assertEqual([f["path"] for f in idx["files"]], ["a.md", "b.md", "c.md"])

    def test_gbk_txt_supported(self):
        raw = "高可用指标：99.9%\nRTO：分钟级\n".encode("gbk")
        root = make_tree({"gbk.txt": ("bytes", raw)})
        f = build_index(root)["files"][0]
        self.assertGreater(f["chars"], 0)
        self.assertGreater(f["chunks"][0]["chars"], 0)

    def test_chunk_preview_and_chars(self):
        root = make_tree({"p.md": "# 概述\n这是一段足够长的内容，用于验证预览字段会截断到指定长度。\n"})
        f = build_index(root)["files"][0]
        self.assertTrue(f["chunks"][0]["preview"])
        self.assertGreater(f["chunks"][0]["chars"], 0)


class WriteIndexTest(unittest.TestCase):
    def test_write_index_roundtrip(self):
        root = make_tree({"a.md": "# A\n内容\n"})
        out = write_index(root, build_index(root))
        self.assertEqual(out.name, ".index.json")
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["file_count"], 1)
        self.assertEqual(data["files"][0]["path"], "a.md")

    def test_write_index_creates_missing_dir(self):
        root = Path(tempfile.mkdtemp(prefix="idx-out-")) / "sub" / "dir"
        out = write_index(root, build_index(root))
        self.assertTrue(out.exists())
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["file_count"], 0)


class MaterialDirResolutionTest(unittest.TestCase):
    def test_resolve_material_dir_finds_cwd_material_dir(self):
        cwd = make_tree({"素材库/a.md": "# 素材\n"})
        self.assertEqual(im.resolve_material_dir(cwd), cwd / "素材库")

    def test_resolve_material_dir_none_when_missing(self):
        cwd = make_tree({"b.md": "# B\n"})
        self.assertIsNone(im.resolve_material_dir(cwd))

    def test_main_no_args_writes_knowledge_and_cwd_material_indexes(self):
        root = make_tree({"knowledge/a.md": "# 知识\n内容\n"})
        cwd = make_tree({"素材库/x.txt": "项目素材\n"})
        old_root = im.ROOT
        try:
            im.ROOT = root
            rc = im.main([], cwd=cwd)
        finally:
            im.ROOT = old_root
        self.assertEqual(rc, 0)
        self.assertTrue((root / "knowledge" / ".index.json").exists())
        self.assertTrue((cwd / "素材库" / ".index.json").exists())
        self.assertEqual(
            json.loads((root / "knowledge" / ".index.json").read_text(encoding="utf-8"))["file_count"],
            1,
        )

    def test_main_no_args_without_material_dir_still_indexes_knowledge(self):
        root = make_tree({"knowledge/a.md": "# 知识\n内容\n"})
        cwd = make_tree({"other.txt": "无关文件\n"})
        old_root = im.ROOT
        try:
            im.ROOT = root
            rc = im.main([], cwd=cwd)
        finally:
            im.ROOT = old_root
        self.assertEqual(rc, 0)
        self.assertTrue((root / "knowledge" / ".index.json").exists())
        self.assertFalse((cwd / "素材库" / ".index.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
