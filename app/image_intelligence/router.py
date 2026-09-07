from dataclasses import dataclass

from .base import (
    ImageProvider,
    ImageTask,
    QualityTier,
)

from .hardware import (
    HardwareProfile,
)


@dataclass
class RoutingRequest:
    task: ImageTask

    quality: QualityTier = (
        QualityTier.BALANCED
    )

    prefer_local: bool = True

    allow_remote: bool = False


class ImageModelRouter:

    def __init__(
        self,
        hardware: HardwareProfile
    ):
        self.hardware = hardware

        self.providers: list[
            ImageProvider
        ] = []

    def register(
        self,
        provider: ImageProvider
    ):
        if provider in self.providers:
            return

        self.providers.append(
            provider
        )

    def unregister(
        self,
        provider: ImageProvider
    ):
        if provider in self.providers:
            self.providers.remove(
                provider
            )

    def compatible(
        self,
        provider: ImageProvider,
        request: RoutingRequest
    ) -> bool:

        capabilities = (
            provider.capabilities()
        )

        if not provider.supports(
            request.task
        ):
            return False

        # Remote providers are blocked
        # unless explicitly allowed.
        if (
            not capabilities.local
            and not request.allow_remote
        ):
            return False

        # Local provider must support
        # at least CPU or GPU execution.
        if capabilities.local:
            if (
                not capabilities.supports_cpu
                and not capabilities.supports_gpu
            ):
                return False

        # GPU-only provider requires
        # compatible GPU hardware.
        if (
            capabilities.supports_gpu
            and not capabilities.supports_cpu
        ):
            if not self.hardware.gpu_available:
                return False

            if (
                self.hardware.vram_gb
                < capabilities.min_vram_gb
            ):
                return False

        return True

    def score(
        self,
        provider: ImageProvider,
        request: RoutingRequest
    ) -> int:

        capabilities = (
            provider.capabilities()
        )

        score = 0

        # Privacy/local preference
        if request.prefer_local:
            if capabilities.local:
                score += 100
            else:
                score -= 50

        else:
            if not capabilities.local:
                score += 50

        # Hardware acceleration preference
        if (
            self.hardware.gpu_available
            and capabilities.supports_gpu
            and self.hardware.vram_gb
            >= capabilities.min_vram_gb
        ):
            score += 25

        # CPU fallback is useful
        if capabilities.supports_cpu:
            score += 10

        # Prototype quality preference
        if (
            request.quality
            == QualityTier.FAST
        ):
            if capabilities.supports_cpu:
                score += 5

        elif (
            request.quality
            == QualityTier.MAX_QUALITY
        ):
            if capabilities.supports_gpu:
                score += 10

        return score

    def select(
        self,
        request: RoutingRequest
    ):

        candidates = []

        for provider in self.providers:

            if not self.compatible(
                provider,
                request
            ):
                continue

            provider_score = (
                self.score(
                    provider,
                    request
                )
            )

            candidates.append(
                (
                    provider_score,
                    provider
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return candidates[0][1]