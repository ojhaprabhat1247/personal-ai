from dataclasses import dataclass
from typing import Any


@dataclass
class CloudLLMConfig:
    enabled: bool = False
    provider: str | None = None
    model: str | None = None


class CloudLLM:

    def __init__(
        self,
        config: CloudLLMConfig | None = None
    ):
        self.config = (
            config or CloudLLMConfig()
        )

    def is_available(self) -> bool:
        """
        Return True only when a cloud
        provider has been configured.

        Actual provider health checks
        will be added later.
        """
        return (
            self.config.enabled
            and self.config.provider is not None
            and self.config.model is not None
        )

    def generate(
        self,
        messages: list[dict[str, Any]],
        stream: bool = False
    ):
        """
        Cloud generation entry point.

        Prototype currently has no
        mandatory paid cloud provider.
        """

        if not self.is_available():
            raise RuntimeError(
                "Cloud LLM is not configured."
            )

        raise RuntimeError(
            f"Cloud provider "
            f"'{self.config.provider}' "
            f"is configured but its runtime "
            f"adapter is not implemented yet."
        )