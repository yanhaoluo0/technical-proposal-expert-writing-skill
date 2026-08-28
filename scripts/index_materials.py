#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成技术文档素材索引。

正常使用无需任何参数：
    python scripts/index_materials.py

默认生成两个 .index.json：
    <skill根>/knowledge/.index.json        内置默认知识（按技术点/指标选择性读取）
    <写作工作目录>/素材库/.index.json       用户项目素材（命中后全文读取）

素材库只认「当前工作目录下的 素材库/」，不设全局素材库：项目写完即随项目
保留或清理，避免素材跨项目混用。

只支持 .md / .txt（UTF-8 / GBK 均可），隐藏文件与其余格式一律忽略。

可选：传入目录参数可覆盖默认目录（供测试或特殊场景使用）。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_SUFFIXES = {".md", ".txt"}
CHUNK_LINES = 60          # 单个 chunk 最大行数，超出按续块硬切
PREVIEW_CHARS = 120       # 每个 chunk 的预览长度
VERSION = 1

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _ignored(path: Path, root: Path) -> bool:
    """根目录以内的隐藏文件/隐藏目录（如 .DS_Store、.git）一律忽略。

    注意：只检查相对根目录的路径段，避免安装目录本身含隐藏前缀（如
    ~/.agents/skills/...）时把所有文件误判为隐藏。
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return any(part.startswith(".") for part in rel.parts)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def split_chunks(lines: list[str], is_md: bool, stem: str) -> list[tuple[str, int, int, str]]:
    """把行列表切成块，返回 [(title, start, end, text)]，行号从 1 开始、闭区间。"""
    if not lines:
        return []
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return []

    chunks: list[tuple[str, int, int, str]] = []
    title = stem
    start = 1
    buf: list[str] = []

    def flush(end: int | None = None) -> None:
        nonlocal start, buf
        if not buf:
            return
        stop = end if end is not None else start + len(buf) - 1
        chunks.append((title, start, stop, "\n".join(buf)))
        buf = []

    line_no = 1
    for raw in lines:
        m = HEADING_RE.match(raw) if is_md else None
        if m:
            flush(line_no - 1)
            title = m.group(2).strip()
            start = line_no
            buf = [raw]
        else:
            if not is_md and not raw.strip():
                flush(line_no - 1)
            elif not buf and not is_md and raw.strip():
                title = raw.strip()[:30]
                start = line_no
                buf.append(raw)
                if len(buf) >= CHUNK_LINES:
                    flush(line_no)
                    start = line_no + 1
            else:
                buf.append(raw)
                if len(buf) >= CHUNK_LINES:
                    flush(line_no)
                    start = line_no + 1
        line_no += 1
    flush()
    return chunks


def _file_title(lines: list[str], stem: str) -> str:
    first_heading: str | None = None
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            if m.group(1) == "#":
                return m.group(2).strip()
            if first_heading is None:
                first_heading = m.group(2).strip()
    return first_heading or stem


def _index_file(path: Path, root: Path) -> dict:
    text = _read_text(path)
    lines = text.splitlines()
    is_md = path.suffix.lower() == ".md"
    chunks = [
        {
            "title": title,
            "start": start,
            "end": end,
            "preview": " ".join(chunk_text.split())[:PREVIEW_CHARS],
            "chars": len(chunk_text),
        }
        for title, start, end, chunk_text in split_chunks(lines, is_md, path.stem)
    ]
    return {
        "path": path.relative_to(root).as_posix(),
        "title": _file_title(lines, path.stem),
        "ext": path.suffix.lower(),
        "size": path.stat().st_size,
        "lines": len(lines),
        "chars": len(text),
        "chunks": chunks,
    }


def build_index(root: Path) -> dict:
    root = Path(root)
    files = []
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if not p.is_file() or _ignored(p, root):
                continue
            if p.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            files.append(_index_file(p, root))
    files.sort(key=lambda f: f["path"])
    return {
        "version": VERSION,
        "root": root.name or str(root),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "file_count": len(files),
        "total_chars": sum(f["chars"] for f in files),
        "files": files,
    }


def write_index(root: Path, index: dict) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    out = root / ".index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def resolve_material_dir(cwd: Path) -> Path | None:
    """返回写作工作目录下的 素材库/；不存在则返回 None（不回落全局目录）。"""
    candidate = Path(cwd) / "素材库"
    return candidate if candidate.is_dir() else None


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None, cwd: Path | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cwd = Path.cwd() if cwd is None else Path(cwd)
    if argv:
        roots = [Path(a) for a in argv]
    else:
        roots = [ROOT / "knowledge"]
        material = resolve_material_dir(cwd)
        if material is not None:
            roots.append(material)
        else:
            print(
                "未找到当前工作目录下的 素材库/，仅生成知识库索引。"
                "用户素材请放在写作工作目录的 素材库/（仅 .md/.txt）下。"
            )
    for r in roots:
        idx = build_index(r)
        out = write_index(r, idx)
        chunk_count = sum(len(f["chunks"]) for f in idx["files"])
        print(
            f"已生成 {_rel(ROOT, out)}：{idx['file_count']} 个文件，"
            f"{chunk_count} 个块，共 {idx['total_chars']} 字"
        )
    print("下次写作时读取索引即可；正常用法：python scripts/index_materials.py（无参数）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
