from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ImageTask(str, Enum):
    OCR = "ocr"
    VISION = "vision"
    GENERATE = "generate"
    EDIT = "edit"
    UPSCALE = "upscale"


class QualityTier(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"
    MAX_QUALITY = "max_quality"


@dataclass
class ProviderCapabilities:
    tasks: set[ImageTask]

    supports_cpu: bool = True
    supports_gpu: bool = False

    min_vram_gb: float = 0.0

    local: bool = True


@dataclass
class ImageResult:
    success: bool

    task: ImageTask

    provider: str

    data: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    error: str | None = None


class ImageProvider(ABC):

    name = "base"

    @abstractmethod
    def capabilities(
        self
    ) -> ProviderCapabilities:
        pass

    def supports(
        self,
        task: ImageTask
    ) -> bool:
        return (
            task
            in self.capabilities().tasks
        )

    @abstractmethod
    def run(
        self,
        task: ImageTask,
        **kwargs
    ) -> ImageResult:
        pass