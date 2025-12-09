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

CONCURRENT = 8  # sites concurrently
DATA_DIR = Path(__file__).parent / "data"
CONFIG_DIR = DATA_DIR / "supported_sites"
EPORT_PATH = DATA_DIR / "site_health_report.json"
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
#   Worker for a single site
# =========================


def evaluate(text: str, required: list[str], forbidden: list[dict[str, Any]]):
    """Return (ok, reason, text_for_report)."""
    # Required check
    for req in required:
        if req not in text:
            return False, f"missing required: {req}"

    # Forbidden match check
    for entry in forbidden:
        keywords = entry.get("keywords", [])
        reason = entry.get("reason", "")

        if any(kw in text for kw in keywords):
            return False, reason

    # OK
    return True, ""


async def run_health_check_for_site(toml_path: Path) -> list[SiteResult]:
    """Run health checks for a single site.

    - Loads site config (TOML)
    - Runs tests for each backend
    - Serial within site (respecting request_interval)
    - Returns list[SiteResult]
    """

    site_key = toml_path.stem

    # --- Load TOML ---
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
            # Serial tasks within 1 site
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

                # respect per-site interval
                await asyncio.sleep(request_interval)

    return results


# =========================
#   Main
# =========================


async def main() -> None:
    logger.info("Loading site configs from %s", CONFIG_DIR)

    toml_files = list(CONFIG_DIR.glob("*.toml"))
    logger.info("Found %d site configs", len(toml_files))

    grouped: dict[str, list[SiteResult]] = {path.stem: [] for path in toml_files}

    sem = asyncio.Semaphore(CONCURRENT)

    async def worker(path: Path) -> None:
        site_key = path.stem
        async with sem:
            result = await run_health_check_for_site(path)
            grouped[site_key].extend(result)

    await asyncio.gather(*(worker(path) for path in toml_files))

    # Write final grouped JSON
    EPORT_PATH.write_text(json.dumps(grouped, ensure_ascii=False, indent=2))

    logger.info("Health check completed. JSON saved to %s", EPORT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
