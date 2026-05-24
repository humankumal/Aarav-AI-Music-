"""Base class for all AI music pipeline agents."""

import json
import logging
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"


class AgentStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AgentResult:
    job_id: str
    agent_name: str
    artist_id: str
    status: AgentStatus
    result_payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "agent_name": self.agent_name,
            "artist_id": self.artist_id,
            "status": self.status.value,
            "result_payload": self.result_payload,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }


class BaseAgent(ABC):
    """Abstract base for all pipeline agents.

    Every concrete agent must implement `_execute()`. The public `run()` method
    handles timing, error wrapping, retry logic, and result formatting.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self._artist_configs: dict[str, dict] = {}

    def load_artist_config(self, artist_id: str) -> dict:
        if artist_id not in self._artist_configs:
            config_path = CONFIG_DIR / "artists" / f"{artist_id}.json"
            if not config_path.exists():
                raise FileNotFoundError(f"No artist config for '{artist_id}' at {config_path}")
            with open(config_path) as f:
                self._artist_configs[artist_id] = json.load(f)
        return self._artist_configs[artist_id]

    def load_platform_config(self, platform: str) -> dict:
        config_path = CONFIG_DIR / "platforms" / f"{platform}.json"
        if not config_path.exists():
            raise FileNotFoundError(f"No platform config for '{platform}'")
        with open(config_path) as f:
            return json.load(f)

    def run(
        self,
        artist_id: str,
        context_payload: dict[str, Any],
        job_id: str | None = None,
    ) -> AgentResult:
        job_id = job_id or str(uuid.uuid4())
        start = time.monotonic()
        self.logger.info(f"[{job_id}] {self.agent_name} starting for artist={artist_id}")

        try:
            artist_config = self.load_artist_config(artist_id)
            result_payload = self._execute(
                artist_id=artist_id,
                artist_config=artist_config,
                context=context_payload,
                job_id=job_id,
            )
            duration = time.monotonic() - start
            self.logger.info(f"[{job_id}] {self.agent_name} completed in {duration:.1f}s")
            return AgentResult(
                job_id=job_id,
                agent_name=self.agent_name,
                artist_id=artist_id,
                status=AgentStatus.COMPLETED,
                result_payload=result_payload,
                duration_seconds=duration,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            self.logger.error(
                f"[{job_id}] {self.agent_name} failed after {duration:.1f}s: {exc}"
            )
            self.logger.debug(traceback.format_exc())
            return AgentResult(
                job_id=job_id,
                agent_name=self.agent_name,
                artist_id=artist_id,
                status=AgentStatus.FAILED,
                error=str(exc),
                duration_seconds=duration,
            )

    @abstractmethod
    def _execute(
        self,
        artist_id: str,
        artist_config: dict,
        context: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        """Core agent logic. Must return a result_payload dict."""
        ...
