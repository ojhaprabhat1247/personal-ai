from .base import (
    ImageTask,
    QualityTier,
)

from .hardware import (
    HardwareDetector,
)

from .router import (
    ImageModelRouter,
    RoutingRequest,
)

from .providers.paddle_ocr import (
    PaddleOCRProvider,
)


def main():
    hardware = HardwareDetector.detect()

    router = ImageModelRouter(
        hardware=hardware
    )

    paddle_provider = (
        PaddleOCRProvider()
    )

    router.register(
        paddle_provider
    )

    request = RoutingRequest(
        task=ImageTask.OCR,
        quality=QualityTier.BALANCED,
        prefer_local=True,
        allow_remote=False
    )

    selected = router.select(
        request
    )

    print(
        "GPU:",
        hardware.gpu_name
    )

    print(
        "VRAM:",
        hardware.vram_gb
    )

    if selected is None:
        print(
            "Selected provider: None"
        )
        return

    print(
        "Selected provider:",
        selected.name
    )

    result = selected.run(
        ImageTask.OCR,
       image_path="uploads/real_ocr_test.jpg"
    )

    print(
        "OCR success:",
        result.success
    )

    if result.success:
        print(
            "OCR text:"
        )
        print(
            result.data["text"]
        )

    else:
        print(
            "OCR error:",
            result.error
        )


if __name__ == "__main__":
    main()