"""
This module provides dynamic registration and discovery of plugin components,
including client, fetcher, parser, and processor classes.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from novelkit.infra.sessions import BaseSession
    from novelkit.plugins.protocols import (
        ClientProtocol,
        FetcherProtocol,
        ParserProtocol,
        ProcessorProtocol,
    )
    from novelkit.schemas import (
        ClientConfig,
        FetcherConfig,
        ParserConfig,
    )

    C = TypeVar("C", bound=ClientProtocol)
    F = TypeVar("F", bound=FetcherProtocol)
    P = TypeVar("P", bound=ParserProtocol)
    R = TypeVar("R", bound=ProcessorProtocol)

_PLUGINS_PKG = "novelkit.plugins"


class PluginHub:
    """Central registry for all plugin components.

    The ``PluginHub`` tracks plugin classes for client, fetcher, parser,
    and processor implementations. Plugins may be registered explicitly via
    decorators or automatically discovered from runtime plugin namespaces.

    A plugin path has the structure:

        novelkit.plugins.sites.<site_key>.<kind>

    where ``kind`` is one of: ``client``, ``fetcher``, ``parser``, ``processor``.
    """

    def __init__(self) -> None:
        self._client: dict[str, type[ClientProtocol]] = {}
        self._fetchers: dict[str, type[FetcherProtocol]] = {}
        self._parsers: dict[str, type[ParserProtocol]] = {}
        self._processors: dict[str, type[ProcessorProtocol]] = {}

        # Namespaces to search for plugin modules
        self._sources: list[str] = [_PLUGINS_PKG]

    def register_fetcher(
        self,
        site_key: str | None = None,
    ) -> Callable[[type[F]], type[F]]:
        """Decorator for registering a fetcher class."""

        def deco(cls: type[F]) -> type[F]:
            key = (site_key or cls.__module__.split(".")[-2]).lower()
            self._fetchers[key] = cls
            return cls

        return deco

    def register_parser(
        self,
        site_key: str | None = None,
    ) -> Callable[[type[P]], type[P]]:
        """Decorator for registering a parser class."""

        def deco(cls: type[P]) -> type[P]:
            key = (site_key or cls.__module__.split(".")[-2]).lower()
            self._parsers[key] = cls
            return cls

        return deco

    def register_client(
        self,
        site_key: str | None = None,
    ) -> Callable[[type[C]], type[C]]:
        """Decorator for registering a client class."""

        def deco(cls: type[C]) -> type[C]:
            key = (site_key or cls.__module__.split(".")[-2]).lower()
            self._client[key] = cls
            return cls

        return deco

    def register_processor(
        self,
        name: str | None = None,
    ) -> Callable[[type[R]], type[R]]:
        """Decorator for registering a processor class."""

        def deco(cls: type[R]) -> type[R]:
            key = (name or self._derive_processor_key(cls.__module__)).lower()
            self._processors[key] = cls
            return cls

        return deco

    def build_fetcher(
        self,
        site: str,
        config: FetcherConfig | None = None,
        *,
        session: BaseSession | None = None,
        **kwargs: Any,
    ) -> FetcherProtocol:
        """Instantiate a fetcher for a given site key."""
        key = self._normalize_key(site)
        cls = self._fetchers.get(key)
        if cls is None:
            self._try_import_site(key, "fetcher")
            cls = self._fetchers.get(key)

        if cls is None:
            raise ValueError(f"Unsupported site: {site!r}")

        return cls(
            config=config,
            session=session,
            **kwargs,
        )

    def build_parser(
        self,
        site: str,
        config: ParserConfig | None = None,
        **kwargs: Any,
    ) -> ParserProtocol:
        """Instantiate a parser for the given site."""
        key = self._normalize_key(site)
        cls = self._parsers.get(key)
        if cls is None:
            self._try_import_site(key, "parser")
            cls = self._parsers.get(key)

        if cls is None:
            raise ValueError(f"Unsupported site: {site!r}")

        return cls(config=config, **kwargs)

    def build_client(
        self,
        site: str,
        config: ClientConfig | None = None,
        *,
        session: BaseSession | None = None,
        **kwargs: Any,
    ) -> ClientProtocol:
        """Instantiate a client for the given site.

        If no site-specific client is available, CommonClient is used as fallback.
        """
        key = self._normalize_key(site)
        cls = self._client.get(key)
        if cls is None:
            self._try_import_site(key, "client")
            cls = self._client.get(key)

        if cls is None:
            from novelkit.plugins.base.client import CommonClient

            return CommonClient(
                site_key=site,
                config=config,
                session=session,
                **kwargs,
            )

        return cls(
            config=config,
            session=session,
            **kwargs,
        )

    def build_processor(self, name: str, config: dict[str, Any]) -> ProcessorProtocol:
        """Instantiate a processor by name."""
        key = name.strip().lower()
        cls = self._processors.get(key)
        if cls is None:
            self._try_import_processor(key)
            cls = self._processors.get(key)

        if cls is None:
            raise ValueError(f"Unsupported processor: {name!r}")

        return cls(config)

    def list_clients(
        self,
        sites: list[str] | None = None,
        *,
        load_all: bool = False,
        r18: bool | None = None,
        support_search: bool | None = None,
    ) -> list[type[ClientProtocol]]:
        """Return uninitialized client classes matching the given filters.

        Args:
            sites: Optional list of site names to include.
            r18: Optional filter by ``r18`` boolean flag.
            support_search: Optional filter by search capability.

        Returns:
            A list of matching client *classes*.
        """
        if load_all:
            self._load_all_sites("client")

        result: list[type[ClientProtocol]] = []

        wanted_sites: set[str] | None = None
        if sites is not None:
            wanted_sites = {s.strip().lower() for s in sites}

        for key, cls in self._client.items():
            # site filter
            if wanted_sites is not None and key not in wanted_sites:
                continue

            # r18 filter
            if wanted_sites is None and r18 is not None and cls.r18 is not r18:
                continue

            # search filter
            if support_search is not None and cls.support_search is not support_search:
                continue

            result.append(cls)

        return result

    @staticmethod
    def _normalize_key(site_key: str) -> str:
        """Normalize a site key for plugin module lookup."""
        key = site_key.strip().lower()
        if not key:
            raise ValueError("Site key cannot be empty")
        if key[0].isdigit():
            return f"n{key}"
        return key

    @staticmethod
    def _derive_processor_key(modname: str) -> str:
        """Derive processor key from module name."""
        if ".processors." in modname:
            return modname.split(".processors.", 1)[1]
        return modname.split(".")[-1]

    def _try_import_site(self, site_key: str, kind: str) -> None:
        """Attempt to import a site plugin module."""
        for base in self._sources:
            modname = f"{base}.sites.{site_key}.{kind}"
            try:
                import_module(modname)
                return
            except ModuleNotFoundError as e:
                if e.name and modname.startswith(e.name):
                    continue
                raise

    def _try_import_processor(self, key: str) -> None:
        """Attempt to import a processor plugin module."""
        for base in self._sources:
            modname = f"{base}.processors.{key}"
            try:
                import_module(modname)
                return
            except ModuleNotFoundError as e:
                if e.name and modname.startswith(e.name):
                    continue
                raise

    def _load_all_sites(self, kind: str) -> None:
        """Load all plugin modules of a given kind."""
        import importlib.resources as res

        for base in self._sources:
            try:
                pkg = import_module(f"{base}.sites")
            except ModuleNotFoundError:
                continue

            for name in res.contents(pkg):
                if name.startswith("_"):
                    continue

                modname = f"{pkg.__name__}.{name}.{kind}"
                try:
                    import_module(modname)
                except ModuleNotFoundError as e:
                    if e.name and modname.startswith(e.name):
                        continue
                    raise

    def enable_local_plugins(
        self,
        local_plugins_path: str | None = None,
        override: bool = False,
    ) -> None:
        """Enable user-provided plugins under a ``novel_plugins`` namespace.

        Args:
            local_plugins_path: Path to the user plugin directory.
            override: If True, user plugins have priority over built-ins.
        """
        import os
        import sys

        if local_plugins_path:
            base = os.path.abspath(local_plugins_path)
            parent = os.path.dirname(base)
            namespace = os.path.basename(base)
        else:
            parent = os.getcwd()
            namespace = "novel_plugins"

        if parent not in sys.path:
            sys.path.append(parent)

        if namespace not in self._sources:
            if override:
                self._sources.insert(0, namespace)
            else:
                self._sources.append(namespace)


hub = PluginHub()
