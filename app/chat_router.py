from dataclasses import dataclass
from enum import Enum
import logging

import llm

from cloud_llm import (
    CloudLLM,
    CloudLLMConfig,
)

logger = logging.getLogger(__name__)


def close_stream(stream):
    close = getattr(stream, "close", None)
    if close is not None:
        close()


def completed_chunks(stream):
    """EOF without a provider terminal marker is an interrupted response."""
    try:
        for chunk in stream:
            yield chunk
            if chunk.get("done", False):
                return
        raise RuntimeError("Generation stream ended before completion.")
    finally:
        close_stream(stream)


class PrivacyMode(str, Enum):
    LOCAL_ONLY = "local_only"
    PRIVACY_FIRST = "privacy_first"
    AUTO = "auto"
    MAX_QUALITY = "max_quality"


class ExecutionTarget(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class ChatRoutingRequest:
    messages: list
    privacy_mode: PrivacyMode = PrivacyMode.AUTO
    sensitive: bool = False
    stream: bool = False


class ChatRouter:

    def __init__(
        self,
        cloud: CloudLLM | None = None
    ):
        self.cloud = (
            cloud
            or CloudLLM(
                CloudLLMConfig()
            )
        )

    def select_target(
        self,
        request: ChatRoutingRequest
    ) -> ExecutionTarget:

        # Sensitive information always
        # stays local in the prototype.
        if request.sensitive:
            return ExecutionTarget.LOCAL

        if (
            request.privacy_mode
            == PrivacyMode.LOCAL_ONLY
        ):
            return ExecutionTarget.LOCAL

        if (
            request.privacy_mode
            == PrivacyMode.PRIVACY_FIRST
        ):
            return ExecutionTarget.LOCAL

        # AUTO and MAX_QUALITY can use
        # cloud only when one is available.
        if request.privacy_mode in (
            PrivacyMode.AUTO,
            PrivacyMode.MAX_QUALITY,
        ):
            if self.cloud.is_available():
                return ExecutionTarget.CLOUD

        return ExecutionTarget.LOCAL

    def generate_local(
        self,
        request: ChatRoutingRequest
    ):
        return llm.generate(
            messages=request.messages,
            stream=request.stream
        )

    def generate(
        self,
        request: ChatRoutingRequest
    ):
        if request.stream:
            return self._generate_stream(request)

        target = self.select_target(
            request
        )

        if target == ExecutionTarget.LOCAL:
            return self.generate_local(
                request
            )

        try:
            return self.cloud.generate(
                messages=request.messages,
                stream=request.stream
            )

        except Exception:
            logger.warning("Cloud unavailable; falling back to local.")

            return self.generate_local(
                request
            )

    def _generate_stream(self, request):
        if self.select_target(request) == ExecutionTarget.LOCAL:
            yield from completed_chunks(self.generate_local(request))
            return

        emitted_text = False
        try:
            stream = completed_chunks(
                self.cloud.generate(messages=request.messages, stream=True)
            )
            try:
                for chunk in stream:
                    if chunk["message"]["content"]:
                        emitted_text = True
                    yield chunk
            finally:
                close_stream(stream)
        except Exception:
            if emitted_text:
                raise
            logger.warning("Cloud stream unavailable; falling back to local.")
            yield from completed_chunks(self.generate_local(request))
