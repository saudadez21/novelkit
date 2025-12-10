#!/usr/bin/env python3
"""
Generate MkDocs documentation for supported sites.

Features:

- Render index overview table.
- Render per-site detail pages.

Usage:
    python scripts/gen_site_docs.py
    python scripts/gen_site_docs.py --overwrite
    python scripts/gen_site_docs.py --clean
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

# ================================================================
# Path constants
# ================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DOC_DIR = PROJECT_ROOT / "docs" / "supported-sites"
CONFIG_DIR = PROJECT_ROOT / "scripts" / "data" / "supported_sites"
LANGUAGE_MAP_PATH = PROJECT_ROOT / "scripts" / "data" / "language_map.json"
SITE_HEALTH_PATH = PROJECT_ROOT / "scripts" / "data" / "site_health_report.json"

LANGUAGE_MAP = json.loads(LANGUAGE_MAP_PATH.read_text(encoding="utf-8"))
SITE_HEALTH = json.loads(SITE_HEALTH_PATH.read_text(encoding="utf-8"))

HEALTH_FAST_THRESHOLD = 3.0


# ================================
# Templates
# ================================

TAGS_TEMPLATE = """\
# 标签索引 (站点)

<!-- material/tags { scope: true } -->
"""

INDEX_TEMPLATE = """\
# 支持站点 / Supported Sites

!!! info "说明"
    本页面列出了 NovelKit 当前支持的站点, 并提供各站点的功能支持情况概览。

    点击站点名称进入详情页, 可查看 **URL 示例、站点状态、功能支持级别** 等信息。

---

## 标签分类 (Tags)

参见：[标签索引](./tags.md)

---

## 支持站点总览 (Overview)

下表展示各站点的基础支持情况:

* :material-check: = 支持
* :material-close: = 不支持
* :material-minus-circle: = 部分支持
* :material-open-in-new: = 站点原生支持 (需站内操作)

| 站点名称    | 标识符  | 分卷  | 图片  | 登录 | 搜索  | 状态 |
| ---------- | ------- | ----- | ---- | ---- | ---- | ---- |
{table}
"""

DETAIL_TEMPLATE = """\
---
title: {name}
tags:
{tags}
---

{description}

## 基本信息

* 标识符: `{id}`
* 主页: {homepage}{alt_domains}
* 语言: {languages}
* 站点状态: {status}
* 支持分卷: {volumes}
* 支持插图: {images}
* 支持登录: {login}
* 支持搜索: {search}

---

## 健康检查报告

{health_report}

---

## URL 示例

{url_examples}

{notes}
"""


# ================================================================
# Status and Support Mapping
# ================================================================

SUPPORT_MAP = {
    "yes": (":material-check:", "是"),
    "no": (":material-close:", "否"),
    "partial": (":material-minus-circle:", "部分支持"),
    "external": (":material-open-in-new:", "站点支持，需站内操作"),
}

STATUS_MAP = {
    "archived": (":red_circle:", "已归档"),
    "unstable": (":orange_circle:", "不稳定"),
    "active": (":green_circle:", "活跃"),
    "unknown": (":black_circle:", "未知"),
}


# ================================================================
# Structures for TOML config
# ================================================================


class SiteMeta(TypedDict):
    key: str
    name: str
    homepage: str
    alt_domains: list[str]
    site_status: Literal["active", "unstable", "archived"]
    languages: list[str]
    tags: list[str]
    description: str


class SiteCapabilities(TypedDict):
    volumes: Literal["yes", "no", "partial", "external"]
    images: Literal["yes", "no", "partial", "external"]
    login: Literal["yes", "no", "partial", "external"]
    search: Literal["yes", "no", "partial", "external"]


class SiteExample(TypedDict):
    title: str
    url: str
    book_id: NotRequired[str]
    chapter_id: NotRequired[str]
    doc: NotRequired[bool]


class SiteNote(TypedDict):
    title: str
    content: str


class SiteConfig(TypedDict):
    meta: SiteMeta
    capabilities: SiteCapabilities
    examples: list[SiteExample]
    notes: NotRequired[list[SiteNote]]


# ================================
# Utility
# ================================


def lang_to_cn(code: str) -> str:
    """Normalize language code to human-readable Chinese."""
    normalized = code.strip().lower()
    return LANGUAGE_MAP.get(normalized, code)


def render_status(status: str, *, icon_only=False) -> str:
    """Render site status (active, unstable, archived)."""
    icon, text = STATUS_MAP.get(status, (":black_circle:", status))
    return icon if icon_only else f"{icon} {text}"


def render_support(value: str, *, icon_only=False) -> str:
    """Render support level (yes, no, partial, external)."""
    icon, text = SUPPORT_MAP.get(value, (":material-close:", value))
    return icon if icon_only else f"{icon} {text}"


def render_health_overview_icon(site_key: str, meta: SiteMeta) -> str:
    """Determine the health icon shown in the overview table"""
    status = meta["site_status"]

    if status == "archived":
        return ":red_circle:"

    if status == "unstable":
        return ":orange_circle:"

    report = SITE_HEALTH.get(site_key)
    if report is None:
        return ":black_circle:"

    if report["site_any_ok"]:
        if report["site_avg_elapsed"] < HEALTH_FAST_THRESHOLD:
            return ":green_circle:"
        else:
            return ":yellow_circle:"
    else:
        return ":red_circle:"


def render_backend_status(backend: str, data: dict) -> str:
    """Determine per-backend health icon in detail view."""
    if not data["all_ok"]:
        return ":red_circle:"
    if data["avg_elapsed"] < HEALTH_FAST_THRESHOLD:
        return ":green_circle:"
    return ":yellow_circle:"


# ================================================================
# Supported Site Builder
# ================================================================


class SupportedSiteBuilder:
    """Responsible for generating table rows and detail pages."""

    def __init__(self):
        self.rows: list[tuple[str, str]] = []  # (site_id, table_row_str)
        self.detail_pages: dict[str, str] = {}  # "site-details/<id>.md" -> md

    def add_site(self, site: SiteConfig) -> None:
        """Register one site and generate table row + detail page."""
        site_id = site["meta"]["key"]

        row = self._make_overview_row(site)
        self.rows.append((site_id, row))

        detail = self._make_detail_page(site)
        self.detail_pages[f"{site_id}.md"] = detail

    def build(self, target_dir: Path, overwrite: bool = False) -> None:
        """Write index.md, tags.md, and detail pages."""
        target_dir.mkdir(parents=True, exist_ok=True)

        sorted_rows = [row for _, row in sorted(self.rows, key=lambda x: x[0].lower())]
        index_md = INDEX_TEMPLATE.format(table="\n".join(sorted_rows))
        self._write_file(target_dir / "index.md", index_md, overwrite)

        self._write_file(target_dir / "tags.md", TAGS_TEMPLATE, overwrite)

        for rel, content in self.detail_pages.items():
            self._write_file(target_dir / "site-details" / rel, content, overwrite)

    def _write_file(self, path: Path, content: str, overwrite: bool) -> None:
        """Write file with optional overwrite control."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            print(f"[skip] {path}")
            return
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"[write] {path}")

    def _make_overview_row(self, site: SiteConfig) -> str:
        """Render a table row for the index overview page."""
        meta = site["meta"]
        cap = site["capabilities"]

        sid = meta["key"]
        name = meta["name"]

        status_icon = render_health_overview_icon(sid, meta)
        return (
            f"| [{name}](./site-details/{sid}.md) "
            f"| `{sid}` "
            f"| {render_support(cap['volumes'], icon_only=True)} "
            f"| {render_support(cap['images'], icon_only=True)} "
            f"| {render_support(cap['login'], icon_only=True)} "
            f"| {render_support(cap['search'], icon_only=True)} "
            f"| {status_icon} |"
        )

    def _make_detail_page(self, site: SiteConfig) -> str:
        """Render a full detail page for one site."""
        meta = site["meta"]
        sid = meta["key"]

        languages = ", ".join(lang_to_cn(x) for x in meta["languages"])
        alt_domains_block = ""
        if meta["alt_domains"]:
            alt_lines = ["\n* 备用域名:"]
            for d in meta["alt_domains"]:
                alt_lines.append(f"    * {d}")
            alt_domains_block = "\n".join(alt_lines)

        # tags = languages + explicit tags
        all_tags = [lang_to_cn(x) for x in meta["languages"]] + meta["tags"]
        tags_str = "\n".join(f"- {t}" for t in all_tags)

        examples_md = self._render_examples(site["examples"])
        notes_md = self._render_notes(site.get("notes", []))
        health_md = self._render_health_report(sid)

        detail_md = DETAIL_TEMPLATE.format(
            name=meta["name"].strip(),
            tags=tags_str,
            description=meta["description"].strip(),
            id=sid,
            homepage=meta["homepage"],
            alt_domains=alt_domains_block,
            languages=languages,
            status=render_status(meta["site_status"]),
            volumes=render_support(site["capabilities"]["volumes"]),
            images=render_support(site["capabilities"]["images"]),
            login=render_support(site["capabilities"]["login"]),
            search=render_support(site["capabilities"]["search"]),
            url_examples=examples_md,
            notes=notes_md,
            health_report=health_md,
        )

        return detail_md.rstrip() + "\n"

    def _render_examples(self, items: list[SiteExample]) -> str:
        """Render the examples section."""
        if not items:
            return "*无示例*"

        blocks: list[str] = []

        for ex in items:
            if not ex.get("doc"):
                continue

            lines = [
                f"### {ex['title']}",
                "",
                f"* URL: <{ex['url']}>",
            ]
            if "book_id" in ex:
                lines.append(f"* Book ID: `{ex['book_id']}`")
            if "chapter_id" in ex:
                lines.append(f"* Chapter ID: `{ex['chapter_id']}`")
            blocks.append("\n".join(lines))

        return "\n\n".join(blocks)

    def _render_notes(self, items: list[SiteNote]) -> str:
        """Render optional notes section."""
        if not items:
            return ""

        lines = ["---", "## 备注"]
        for note in items:
            lines.append(f"### {note['title']}")
            lines.append(note["content"].strip())

        return "\n\n".join(lines)

    def _render_health_report(self, site_key: str) -> str:
        """Render the health report section for a site."""
        report = SITE_HEALTH.get(site_key)

        if report is None:
            return "*无可用数据*"

        lines: list[str] = [
            "| 后端    | 状态     |",
            "| ------- | -------- |",
        ]
        backend_summary = report["backend_summary"]
        for backend in sorted(backend_summary.keys()):
            data = backend_summary[backend]
            icon = render_backend_status(backend, data)
            lines.append(f"| `{backend}` | {icon} |")

        return "\n".join(lines)


# ================================
# Main
# ================================


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--config", type=Path, default=CONFIG_DIR)
    parser.add_argument("--target", type=Path, default=DOC_DIR)
    args = parser.parse_args()

    if args.clean and args.target.exists():
        import shutil

        shutil.rmtree(args.target)
        print(f"[clean] removed {args.target}")

    builder = SupportedSiteBuilder()

    for toml_file in args.config.glob("*.toml"):
        config: SiteConfig = tomllib.loads(toml_file.read_text(encoding="utf-8"))  # type: ignore
        builder.add_site(config)

    builder.build(args.target, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
