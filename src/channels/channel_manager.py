"""
Channel Manager - Centralized orchestration of all channel adapters.
"""

from typing import Dict, Optional, List
from src.channels.base_channel import BaseChannelAdapter
from src.utils.logger import get_logger

logger = get_logger("channel-manager")


class ChannelManager:
    """Manages all channel adapters lifecycle and routing"""

    def __init__(self):
        self.channels: Dict[str, BaseChannelAdapter] = {}
        self._started = False

    def register(self, adapter: BaseChannelAdapter) -> None:
        """Register a channel adapter"""
        if adapter.platform_name in self.channels:
            logger.warning(f"Overwriting existing adapter: {adapter.platform_name}")
        self.channels[adapter.platform_name] = adapter
        logger.info(f"Registered channel adapter: {adapter.platform_name}")

    def get(self, platform: str) -> Optional[BaseChannelAdapter]:
        """Get adapter for specific platform"""
        return self.channels.get(platform)

    def list_platforms(self) -> List[str]:
        """List all registered platforms"""
        return list(self.channels.keys())

    async def start_all(self) -> None:
        """Start all registered channel adapters"""
        if self._started:
            logger.warning("Channel manager already started")
            return

        for name, adapter in self.channels.items():
            try:
                await adapter.start()
                logger.info(f"Started channel: {name}")
            except Exception as e:
                logger.error(f"Failed to start channel {name}: {e}")

        self._started = True

    async def stop_all(self) -> None:
        """Stop all channel adapters gracefully"""
        for name, adapter in self.channels.items():
            try:
                await adapter.stop()
                logger.info(f"Stopped channel: {name}")
            except Exception as e:
                logger.error(f"Error stopping channel {name}: {e}")

        self._started = False


# Global instance
channel_manager = ChannelManager()
