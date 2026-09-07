from .base import ImageTask
from .providers.paddle_ocr import (
    PaddleOCRProvider,
)


def main():
    provider = PaddleOCRProvider()

    result = provider.run(
        ImageTask.OCR,
        image_path="uploads/ocr_test.png"
    )

    print("Success:", result.success)
    print("Provider:", result.provider)

    if result.success:
        print("Text:")
        print(result.data["text"])

        print("\nLines:")
        for line in result.data["lines"]:
            print(
                "-",
                line["text"],
                "| confidence:",
                line["confidence"]
            )

    else:
        print("Error:", result.error)


if __name__ == "__main__":
    main()