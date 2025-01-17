from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from vunnel import provider, result, schema

from .parser import Parser

if TYPE_CHECKING:
    import datetime

PROVIDER_NAME = "rocky"

SCHEMA = schema.OSVSchema()


@dataclass
class Config:
    runtime: provider.RuntimeConfig = field(
        default_factory=lambda: provider.RuntimeConfig(
            result_store=result.StoreStrategy.FLAT_FILE,
            existing_results=provider.ResultStatePolicy.DELETE_BEFORE_WRITE,
        ),
    )
    request_timeout: int = 125


class Provider(provider.Provider):
    def __init__(self, root: str, config: Config | None = None):
        if not config:
            config = Config()

        super().__init__(root, runtime_cfg=config.runtime)
        self.config = config
        self.logger.debug(f"config: {config}")

        self.parser = Parser(ws=self.workspace, download_timeout=self.config.request_timeout, logger=self.logger)

    @classmethod
    def name(cls) -> str:
        return PROVIDER_NAME

    def update(self, last_updated: datetime.datetime | None) -> tuple[list[str], int]:
        with self.results_writer() as writer:
            for namespace, vuln_id, record in self.parser.get():
                namespace = namespace.lower()
                vuln_id = vuln_id.lower()

                writer.write(
                    identifier=os.path.join(namespace, vuln_id),
                    schema=SCHEMA,
                    payload=record,
                )

        return self.parser.urls, len(writer)
