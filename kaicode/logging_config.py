"""Logging configuration for KaiCode."""

from __future__ import annotations

import logging
import os


def configure_logging(debug: bool = False) -> None:
    """Configure process-wide logging without leaking internals by default."""
    enabled = debug or os.environ.get("KAICODE_DEBUG", "").lower() in {"1", "true", "yes"}
    level = logging.DEBUG if enabled else logging.CRITICAL
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )
