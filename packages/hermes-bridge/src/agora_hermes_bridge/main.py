"""CLI entry point for the Hermes Bridge daemon."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from .config import BridgeConfig
from .daemon import HermesBridgeDaemon

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agora-hermes-bridge",
        description="Bridge daemon connecting Hermes profiles to Agora",
    )
    parser.add_argument(
        "--config", default="hermes-bridge.yaml",
        help="Path to bridge configuration YAML (default: hermes-bridge.yaml)",
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="Run as daemon (background process)",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


async def _run(config_path: str) -> None:
    config = BridgeConfig.from_yaml(config_path)
    daemon = HermesBridgeDaemon(config)
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(daemon.stop()))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(daemon.stop()))
    await daemon.start()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(_run(args.config))
    except KeyboardInterrupt:
        logger.info("Interrupted, shutting down")
        sys.exit(0)


if __name__ == "__main__":
    main()
