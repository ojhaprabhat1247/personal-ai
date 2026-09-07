from pathlib import Path

from ollama import chat

from ..base import (
    ImageProvider,
    ImageResult,
    ImageTask,
    ProviderCapabilities,
)


class QwenVisionProvider(ImageProvider):
    name = "qwen_vision"

    def __init__(
        self,
        model: str = "qwen3.5:0.8b"
    ):
        self.model = model

    def capabilities(
        self
    ) -> ProviderCapabilities:
        return ProviderCapabilities(
            tasks={ImageTask.VISION},
            supports_cpu=True,
            supports_gpu=True,
            min_vram_gb=0.0,
            local=True
        )

    def run(
        self,
        task: ImageTask,
        **kwargs
    ) -> ImageResult:

        if task != ImageTask.VISION:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=(
                    "QwenVisionProvider only "
                    "supports vision."
                )
            )

        image_path = kwargs.get(
            "image_path"
        )

        if not image_path:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error="image_path is required."
            )

        image_path = Path(
            image_path
        ).resolve()

        if not image_path.exists():
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=(
                    f"Image not found: "
                    f"{image_path}"
                )
            )

        prompt = kwargs.get(
            "prompt",
            (
                "Describe this image "
                "accurately and concisely."
            )
        )

        try:
            response = chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [
                            str(image_path)
                        ],
                    }
                ],
            )

            answer = (
                response["message"][
                    "content"
                ]
            )

        except Exception as error:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=str(error)
            )

        return ImageResult(
            success=True,
            task=task,
            provider=self.name,
            data={
                "answer": answer
            },
            metadata={
                "model": self.model,
                "image_path": str(
                    image_path
                )
            }
        )