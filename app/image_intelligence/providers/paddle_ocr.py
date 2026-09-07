import json
import subprocess
from pathlib import Path

from ..base import (
    ImageProvider,
    ImageResult,
    ImageTask,
    ProviderCapabilities,
)


class PaddleOCRProvider(ImageProvider):

    name = "paddle_ocr"

    def __init__(
        self,
        project_root=None
    ):
        if project_root is None:
            project_root = (
                Path(__file__)
                .resolve()
                .parents[3]
            )

        self.project_root = Path(
            project_root
        ).resolve()

        self.ocr_python = (
            self.project_root
            / ".venv-ocr"
            / "Scripts"
            / "python.exe"
        )

        self.worker_path = (
            self.project_root
            / "app"
            / "image_intelligence"
            / "providers"
            / "paddle_ocr_worker.py"
        )

    def capabilities(
        self
    ) -> ProviderCapabilities:
        return ProviderCapabilities(
            tasks={
                ImageTask.OCR
            },
            supports_cpu=True,
            supports_gpu=False,
            min_vram_gb=0.0,
            local=True
        )

    def validate_environment(self):
        if not self.ocr_python.exists():
            return (
                False,
                f"OCR Python not found: "
                f"{self.ocr_python}"
            )

        if not self.worker_path.exists():
            return (
                False,
                f"OCR worker not found: "
                f"{self.worker_path}"
            )

        return True, None

    def run(
        self,
        task: ImageTask,
        **kwargs
    ) -> ImageResult:

        if task != ImageTask.OCR:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=(
                    "PaddleOCRProvider only "
                    "supports OCR."
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
                error=(
                    "image_path is required."
                )
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

        environment_ok, error = (
            self.validate_environment()
        )

        if not environment_ok:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=error
            )

        command = [
            str(self.ocr_python),
            "-m",
            "app.image_intelligence.providers.paddle_ocr_worker",
            str(image_path)
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=str(
                    self.project_root
                ),
                timeout=300,
                check=False
            )

        except subprocess.TimeoutExpired:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=(
                    "OCR process timed out."
                )
            )

        except OSError as error:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=str(error)
            )

        stdout = (
            process.stdout.strip()
        )

        if not stdout:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                metadata={
                    "stderr": (
                        process.stderr.strip()
                    )
                },
                error=(
                    "OCR worker returned "
                    "no output."
                )
            )

        json_line = None

        for line in reversed(
            stdout.splitlines()
        ):
            line = line.strip()

            if (
                line.startswith("{")
                and line.endswith("}")
            ):
                json_line = line
                break

        if json_line is None:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                metadata={
                    "stdout": stdout,
                    "stderr": (
                        process.stderr.strip()
                    )
                },
                error=(
                    "Could not find valid "
                    "OCR JSON output."
                )
            )

        try:
            response = json.loads(
                json_line
            )

        except json.JSONDecodeError as error:
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                error=(
                    f"Invalid OCR JSON: "
                    f"{error}"
                )
            )

        if not response.get(
            "success"
        ):
            return ImageResult(
                success=False,
                task=task,
                provider=self.name,
                metadata={
                    "worker_response": response
                },
                error=response.get(
                    "error",
                    "OCR failed."
                )
            )

        return ImageResult(
            success=True,
            task=task,
            provider=self.name,
            data={
                "text": response.get(
                    "text",
                    ""
                ),
                "lines": response.get(
                    "lines",
                    []
                )
            },
            metadata={
                "image_path": response.get(
                    "image_path"
                )
            }
        )