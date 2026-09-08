from dataclasses import dataclass
from enum import Enum

import llm

from cloud_llm import (
    CloudLLM,
    CloudLLMConfig,
)


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

        except Exception as error:

            print(
                "\n⚠️ Cloud unavailable. "
                "Falling back to local."
            )

            print(
                f"Reason: {error}"
            )

            return self.generate_local(
                request
            )