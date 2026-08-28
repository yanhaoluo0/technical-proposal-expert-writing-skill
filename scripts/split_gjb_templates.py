#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GJB 438C-2021 军用软件开发文档通用要求 拆成 20 份模板。

每份模板 = 第 5 章对应小节（概述）+ 对应附录（正文格式）。
输出到 f:/GithubDownload/technical-proposal-expert-writing-skill/素材库/01-模板/
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path("f:/GithubDownload/technical-proposal-expert-writing-skill/素材库/01-模板/军用软件开发文档通用要求-GJB-438C-2021.md")
OUT_DIR = SRC.parent

# 第 5 章各小节起止行号（基于 grep 结果，从 1 开始）
CHAPTER5 = {
    # chapter_key: (start, end)
    "SDP":  (385, 389),
    "SIP":  (389, 401),
    "STrP": (401, 417),
    "STP":  (417, 423),
    "OCD":  (423, 427),
    "SSS":  (427, 435),
    "IRS":  (435, 439),
    "SSDD": (439, 445),
    "IDD":  (445, 449),
    "SRS":  (449, 453),
    "SDD":  (453, 457),
    "DBDD": (457, 461),
    "STD":  (461, 467),
    "STR":  (467, 477),
    "SPS":  (477, 481),
    "SVD":  (481, 485),
    "SUM":  (485, 497),
    "CPM":  (497, 507),
    "FSM":  (507, 527),
    "SDSR": (527, 543),  # 到 # 附录A 之前
}

# 附录起止行号
APPENDIX = {
    # chapter_key: (start, end)
    "SDP":  (563, 845),
    "SIP":  (845, 1021),
    "STrP": (1021, 1171),
    "STP":  (1171, 1377),
    "OCD":  (1377, 1557),
    "SSS":  (1557, 1849),
    "IRS":  (1849, 2029),
    "SSDD": (2029, 2247),
    "IDD":  (2247, 2403),
    "SRS":  (2403, 2683),
    "SDD":  (2683, 2933),
    "DBDD": (2933, 3155),
    "STD":  (3155, 3381),
    "STR":  (3381, 3501),
    "SPS":  (3501, 3619),
    "SVD":  (3619, 3699),
    "SUM":  (3699, 3883),
    "CPM":  (3883, 4025),
    "FSM":  (4025, 4115),
    "SDSR": (4115, 4265),
}

# 文档元数据：编号、中文名、英文缩写、附录类型、适用文档
DOCS = [
    ("01", "软件开发计划",       "SDP",  "规范性附录", "技术标书、方案设计报告"),
    ("02", "软件安装计划",       "SIP",  "资料性附录", "方案设计报告、运维手册"),
    ("03", "软件移交计划",       "STrP", "资料性附录", "方案设计报告、运维手册"),
    ("04", "软件测试计划",       "STP",  "规范性附录", "测试报告、方案设计报告"),
    ("05", "运行方案说明",       "OCD",  "规范性附录", "方案设计报告、运维方案"),
    ("06", "系统·子系统规格说明","SSS",  "规范性附录", "技术标书、方案设计报告"),
    ("07", "接口需求规格说明",   "IRS",  "规范性附录", "方案设计报告、接口文档"),
    ("08", "系统·子系统设计说明","SSDD", "规范性附录", "方案设计报告、设计说明"),
    ("09", "接口设计说明",       "IDD",  "规范性附录", "方案设计报告、接口文档"),
    ("10", "软件需求规格说明",   "SRS",  "规范性附录", "方案设计报告、需求文档"),
    ("11", "软件设计说明",       "SDD",  "规范性附录", "方案设计报告、设计说明"),
    ("12", "数据库设计说明",     "DBDD", "规范性附录", "方案设计报告、设计说明"),
    ("13", "软件测试说明",       "STD",  "规范性附录", "测试报告、方案设计报告"),
    ("14", "软件测试报告",       "STR",  "规范性附录", "测试报告"),
    ("15", "软件产品规格说明",   "SPS",  "规范性附录", "技术标书、产品说明"),
    ("16", "软件版本说明",       "SVD",  "规范性附录", "交付清单、版本管理"),
    ("17", "软件用户手册",       "SUM",  "资料性附录", "用户手册、培训材料"),
    ("18", "计算机编程手册",     "CPM",  "资料性附录", "开发手册、维护手册"),
    ("19", "固件保障手册",       "FSM",  "资料性附录", "运维方案、保障方案"),
    ("20", "软件研制总结报告",   "SDSR", "资料性附录", "方案设计报告、验收文档"),
]

# 标题反查（key 由 DOCS 缩写给出）
KEY_BY_ABBR = {abbr: key for key, _, abbr, _, _ in DOCS for key in [abbr]}

PAGE_LINE_RE = re.compile(r"^\s*\d{1,3}\s*$")
HEADER_FOOTER_RE = re.compile(r"^GJB\s+438C-2021\s*$")


def is_noise(line: str) -> bool:
    """页眉页脚与纯页码行，跳过"""
    s = line.strip()
    if not s:
        return True
    if PAGE_LINE_RE.match(s):
        return True
    if HEADER_FOOTER_RE.match(s):
        return True
    return False


def clean_lines(lines: list[str]) -> list[str]:
    """剔除页眉/页脚/纯页码，保留空行作为段落分隔"""
    out = []
    prev_blank = False
    for line in lines:
        if is_noise(line):
            # 连续空行只保留一个
            if not prev_blank:
                out.append("")
                prev_blank = True
            continue
        out.append(line.rstrip())
        prev_blank = False
    # 去掉首尾空行
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    lines = raw.splitlines()
    print(f"源文件 {SRC.name}: {len(lines)} 行")

    for num, name, abbr, appx_type, doc_types in DOCS:
        # 关键 key：缩写（与 CHAPTER5/APPENDIX 一致）
        key = KEY_BY_ABBR[abbr]
        ch_start, ch_end = CHAPTER5[key]
        ap_start, ap_end = APPENDIX[key]

        # 提取第 5 章概述（注意：5.1 到 5.20 起止行号是基于 grep 的 1-based）
        # Python 列表是 0-based，所以索引要 - 1
        ch5_lines = lines[ch_start - 1 : ch_end - 1]
        # 提取附录正文
        ap_lines = lines[ap_start - 1 : ap_end - 1]

        # 清理
        ch5_clean = clean_lines(ch5_lines)
        ap_clean = clean_lines(ap_lines)

        # 拼接：5 章概述 + 附录正文
        # 但去掉附录开头的几行重复元数据（# 附录 X / # (规范性附录) / # 《X》的正文格式）
        # 这些已经被 # 5.X 章节点过；附录标题保留即可
        body_lines = ch5_clean + ["", "---", ""] + ap_clean

        # 文件头元信息
        header = [
            f"# {num}-{name}-{abbr}",
            "",
            f"> **文档全称**：《{name}》",
            f"> **英文缩写**：{abbr}",
            f"> **出处标准**：GJB 438C-2021《军用软件开发文档通用要求》（{appx_type}）",
            f"> **拆分日期**：2026-08-28",
            f"> **整理方式**：按 GJB 438C-2021 拆分（原文件 4265 行 / 199 KB）",
            f"> **适用文档类型**：{doc_types}",
            f"> **可支撑的技术点**：{name}, {abbr}, 软件文档结构, 章节骨架, 文档剪裁",
            "",
            "## 写作说明",
            "",
            f"本文件为 GJB 438C-2021 标准中《{name}》（{abbr}）的**章节骨架模板**。内容由两部分组成：",
            "",
            "1. 第 5 章概述：该文档的用途、内容范围与编写要求",
            "2. 附录正文格式：标准的完整章节骨架（每节需填实内容）",
            "",
            "写作时按本文的章节顺序与命名展开，对应招标条款或需求条目；不写实的子节可标「本节不适用：…」或「待确认」。",
            "",
            "## 5 章概述（来自 GJB 438C-2021 第 5 章）",
            "",
        ]

        out_path = OUT_DIR / f"{num}-{name}-{abbr}.md"
        content = "\n".join(header + body_lines) + "\n"
        out_path.write_text(content, encoding="utf-8")
        print(f"  {num:>2}. {out_path.name} ({len(content.encode('utf-8'))} 字节, {body_lines.count(chr(10)) + 1} 行)")

    print(f"\n完成：{len(DOCS)} 份模板")


if __name__ == "__main__":
    main()