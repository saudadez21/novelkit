#!/usr/bin/env python3
"""
Async health check for novel sites.

Usage:
  python scripts/check_sites_health.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import tomllib
from pathlib import Path
from time import perf_counter
from typing import Any, TypedDict

from novelkit.plugins.registry import hub
from novelkit.schemas import FetcherConfig

# =========================
#   Config
# =========================

CONCURRENT = 8
DATA_DIR = Path(__file__).parent / "data"
CONFIG_DIR = DATA_DIR / "supported_sites"

RAW_PATH = DATA_DIR / "site_health_raw.json"
REPORT_PATH = DATA_DIR / "site_health_report.json"

BACKENDS = {"aiohttp", "curl_cffi", "httpx"}

logger = logging.getLogger("site_health")
logging.basicConfig(level=logging.INFO)


# =========================
#   Result dataclass
# =========================


class SiteResult(TypedDict):
    site_key: str
    backend: str
    check_name: str
    url: str
    elapsed: float
    ok: bool
    reason: str


# =========================
#   Helpers
# =========================


def evaluate(text: str, required: list[str], forbidden: list[dict[str, Any]]):
    """Return (ok, reason)."""
    for req in required:
        if req not in text:
            return False, f"missing required: {req}"

    for entry in forbidden:
        keywords = entry.get("keywords", [])
        reason = entry.get("reason", "")
        if any(kw in text for kw in keywords):
            return False, reason

    return True, ""


# =========================
#   Worker: run checks for one site
# =========================


async def run_health_check_for_site(toml_path: Path) -> list[SiteResult]:
    site_key = toml_path.stem

    with toml_path.open("rb") as f:
        conf = tomllib.load(f)

    health_tests = conf.get("health", [])
    network_conf = conf.get("network", {})
    request_interval = network_conf.get("request_interval", 0.2)
    timeout = network_conf.get("timeout", 10.0)

    results: list[SiteResult] = []

    for backend in BACKENDS:
        fetcher_cfg = FetcherConfig(
            backend=backend,
            request_interval=request_interval,
        )

        logger.info("Site %s - backend=%s", site_key, backend)

        async with hub.build_fetcher(site_key, config=fetcher_cfg) as fetcher:
            for item in health_tests:
                name = item.get("name", "unknown")
                url = item["url"]
                encoding = item.get("encoding", "utf-8")

                required = item.get("required", [])
                forbidden = item.get("forbidden", [])

                t0 = perf_counter()
                try:
                    text = await fetcher.fetch_text(
                        url, encoding=encoding, timeout=timeout
                    )
                    elapsed = perf_counter() - t0

                    ok, reason = evaluate(text, required, forbidden)

                except Exception as e:
                    elapsed = perf_counter() - t0
                    ok = False
                    reason = ""
                    logger.warning(
                        "Health check error | site=%s backend=%s url=%s error=%s",
                        site_key,
                        backend,
                        url,
                        e,
                    )

                results.append(
                    {
                        "site_key": site_key,
                        "backend": backend,
                        "check_name": name,
                        "url": url,
                        "elapsed": elapsed,
                        "ok": ok,
                        "reason": reason,
                    }
                )

                await asyncio.sleep(request_interval)

    return results


# =========================
#   Summary generator
# =========================


def summarize_grouped(grouped: dict[str, list[SiteResult]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    for site_key, checks in grouped.items():
        backend_groups: dict[str, list[SiteResult]] = {}
        for c in checks:
            backend_groups.setdefault(c["backend"], []).append(c)

        backend_summary = {}
        all_elapsed = []
        all_ok_flags = []

        for backend, items in backend_groups.items():
            elapsed_list = [it["elapsed"] for it in items]
            ok_list = [it["ok"] for it in items]

            avg_elapsed = sum(elapsed_list) / len(elapsed_list)
            all_ok = all(ok_list)

            backend_summary[backend] = {
                "avg_elapsed": avg_elapsed,
                "all_ok": all_ok,
            }

            all_elapsed.extend(elapsed_list)
            all_ok_flags.extend(ok_list)

        site_avg_elapsed = sum(all_elapsed) / len(all_elapsed) if all_elapsed else 0.0
        site_all_ok = all(all_ok_flags)
        site_any_ok = any(all_ok_flags)

        summary[site_key] = {
            "backend_summary": backend_summary,
            "site_avg_elapsed": site_avg_elapsed,
            "site_all_ok": site_all_ok,
            "site_any_ok": site_any_ok,
        }

    return summary


# =========================
#   Main
# =========================


async def main() -> None:
    logger.info("Loading site configs from %s", CONFIG_DIR)

    toml_files = list(CONFIG_DIR.glob("*.toml"))
    logger.info("Found %d site configs", len(toml_files))

    grouped_raw: dict[str, list[SiteResult]] = {path.stem: [] for path in toml_files}

    sem = asyncio.Semaphore(CONCURRENT)

    async def worker(path: Path) -> None:
        site_key = path.stem
        async with sem:
            result = await run_health_check_for_site(path)
            grouped_raw[site_key].extend(result)

    await asyncio.gather(*(worker(path) for path in toml_files))

    # === Save RAW ===
    RAW_PATH.write_text(json.dumps(grouped_raw, ensure_ascii=False, indent=2))
    logger.info("Raw health data saved to %s", RAW_PATH)

    # === Summary  ===
    report = summarize_grouped(grouped_raw)

    # === Save REPORT ===
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    logger.info("Summary report saved to %s", REPORT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
