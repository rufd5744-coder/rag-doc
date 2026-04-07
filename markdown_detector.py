"""Markdown 文件检测器

检测文件是否为 Markdown 格式，支持：
- 文件扩展名检测（.md, .markdown, .mdown, .mkd, .mkdn）
- 文件内容特征检测（标题、列表、链接、代码块等）
"""

import os
import re
from pathlib import Path


MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".mkdn"}

# Markdown 语法特征的正则表达式
_PATTERNS = [
    re.compile(r"^#{1,6}\s+\S"),           # ATX 标题: # Title
    re.compile(r"^[=-]{3,}\s*$"),           # Setext 标题下划线: === 或 ---
    re.compile(r"^\s*[-*+]\s+\S"),          # 无序列表: - item
    re.compile(r"^\s*\d+\.\s+\S"),          # 有序列表: 1. item
    re.compile(r"^\s*>\s"),                 # 引用块: > text
    re.compile(r"```"),                     # 代码块围栏: ```
    re.compile(r"!?\[.+?\]\(.+?\)"),        # 链接/图片: [text](url)
    re.compile(r"\*\*.+?\*\*"),             # 粗体: **bold**
    re.compile(r"(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*)"),  # 斜体: *italic*
    re.compile(r"^\|.+\|.+\|"),            # 表格: | col | col |
]

_THRESHOLD = 2  # 至少匹配几种特征才判定为 Markdown


def is_markdown_by_extension(file_path: str | Path) -> bool:
    """通过文件扩展名判断是否为 Markdown 文件。"""
    return Path(file_path).suffix.lower() in MARKDOWN_EXTENSIONS


def is_markdown_by_content(text: str) -> tuple[bool, list[str]]:
    """通过内容特征判断文本是否为 Markdown 格式。

    Returns:
        (is_markdown, matched_features) — 是否为 Markdown 及匹配到的特征列表。
    """
    lines = text.splitlines()[:200]  # 只检查前 200 行
    matched = set()
    feature_names = [
        "ATX 标题", "Setext 下划线", "无序列表", "有序列表",
        "引用块", "代码块", "链接/图片", "粗体", "斜体", "表格",
    ]

    for line in lines:
        for i, pattern in enumerate(_PATTERNS):
            if pattern.search(line):
                matched.add(feature_names[i])

    return len(matched) >= _THRESHOLD, sorted(matched)


def detect(file_path: str | Path) -> dict:
    """检测文件是否为 Markdown。

    Returns:
        dict with keys:
          - path: 文件路径
          - exists: 文件是否存在
          - is_markdown: 是否为 Markdown
          - method: 检测方法 ("extension" | "content" | "both")
          - features: 匹配到的内容特征（如有）
    """
    path = Path(file_path)
    result = {
        "path": str(path),
        "exists": path.exists(),
        "is_markdown": False,
        "method": None,
        "features": [],
    }

    if not path.exists():
        return result

    ext_match = is_markdown_by_extension(path)

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        result["is_markdown"] = ext_match
        result["method"] = "extension" if ext_match else None
        return result

    content_match, features = is_markdown_by_content(text)
    result["features"] = features

    if ext_match and content_match:
        result["is_markdown"] = True
        result["method"] = "both"
    elif ext_match:
        result["is_markdown"] = True
        result["method"] = "extension"
    elif content_match:
        result["is_markdown"] = True
        result["method"] = "content"

    return result


def scan_directory(directory: str | Path, recursive: bool = True) -> list[dict]:
    """扫描目录，返回所有检测为 Markdown 的文件信息。"""
    directory = Path(directory)
    results = []
    pattern = "**/*" if recursive else "*"

    for path in sorted(directory.glob(pattern)):
        if path.is_file() and not path.name.startswith("."):
            info = detect(path)
            if info["is_markdown"]:
                results.append(info)

    return results


# --------------- CLI ---------------
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Markdown 文件检测器")
    parser.add_argument("paths", nargs="+", help="要检测的文件或目录")
    parser.add_argument("-r", "--recursive", action="store_true", default=True,
                        help="递归扫描目录（默认开启）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    all_results = []
    for p in args.paths:
        target = Path(p)
        if target.is_dir():
            all_results.extend(scan_directory(target, recursive=args.recursive))
        elif target.is_file():
            all_results.append(detect(target))
        else:
            all_results.append({"path": p, "exists": False, "is_markdown": False})

    if args.json:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))
    else:
        for r in all_results:
            status = "✓ Markdown" if r["is_markdown"] else "✗ 非 Markdown"
            line = f"  {status}  {r['path']}"
            if r.get("method"):
                line += f"  (检测方式: {r['method']})"
            if r.get("features"):
                line += f"  [特征: {', '.join(r['features'])}]"
            print(line)

        md_count = sum(1 for r in all_results if r["is_markdown"])
        print(f"\n共扫描 {len(all_results)} 个文件，其中 {md_count} 个为 Markdown 文件。")
