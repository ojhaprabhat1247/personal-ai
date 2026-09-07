from dataclasses import dataclass
import os
import platform
import shutil
import subprocess


@dataclass
class HardwareProfile:
    os_name: str
    cpu_name: str
    cpu_count: int
    ram_gb: float

    # Physical GPU information
    gpu_available: bool
    gpu_name: str | None
    vram_gb: float

    # NVIDIA / CUDA environment
    nvidia_driver_available: bool
    driver_version: str | None
    driver_cuda_version: str | None
    cuda_toolkit_available: bool
    nvcc_version: str | None


class HardwareDetector:

    @staticmethod
    def get_cpu_name():
        cpu_name = platform.processor()

        if cpu_name:
            return cpu_name

        return "Unknown CPU"

    @staticmethod
    def get_ram_gb():
        try:
            import psutil

            total_bytes = (
                psutil.virtual_memory().total
            )

            return round(
                total_bytes / (1024 ** 3),
                2
            )

        except ImportError:
            return 0.0

    @staticmethod
    def run_command(command):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            if result.returncode != 0:
                return None

            output = result.stdout.strip()

            if not output:
                return None

            return output

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            OSError
        ):
            return None

    @classmethod
    def get_nvidia_info(cls):
        command = [
            "nvidia-smi",
            "--query-gpu="
            "name,memory.total,"
            "driver_version",
            "--format=csv,noheader,nounits"
        ]

        output = cls.run_command(
            command
        )

        if not output:
            return {
                "available": False,
                "name": None,
                "vram_gb": 0.0,
                "driver_version": None
            }

        first_gpu = (
            output.splitlines()[0]
        )

        parts = [
            part.strip()
            for part in first_gpu.split(",")
        ]

        if len(parts) < 3:
            return {
                "available": False,
                "name": None,
                "vram_gb": 0.0,
                "driver_version": None
            }

        gpu_name = parts[0]

        try:
            memory_mb = float(
                parts[1]
            )

            vram_gb = round(
                memory_mb / 1024,
                2
            )

        except ValueError:
            vram_gb = 0.0

        return {
            "available": True,
            "name": gpu_name,
            "vram_gb": vram_gb,
            "driver_version": parts[2]
        }

    @classmethod
    def get_driver_cuda_version(cls):
        output = cls.run_command(
            ["nvidia-smi"]
        )

        if not output:
            return None

        marker = "CUDA Version:"

        if marker not in output:
            return None

        try:
            value = (
                output.split(
                    marker,
                    1
                )[1]
                .split()[0]
            )

            return value

        except (
            IndexError,
            AttributeError
        ):
            return None

    @classmethod
    def get_nvcc_version(cls):
        # shutil.which avoids confusing
        # "command not found" situations.
        nvcc_path = shutil.which(
            "nvcc"
        )

        if not nvcc_path:
            return None

        output = cls.run_command(
            [
                nvcc_path,
                "--version"
            ]
        )

        if not output:
            return None

        # Typical line:
        # Cuda compilation tools,
        # release 12.9, V12.9.xxx
        for line in output.splitlines():
            if "release" not in line:
                continue

            try:
                release_part = (
                    line.split(
                        "release",
                        1
                    )[1]
                )

                version = (
                    release_part
                    .split(",", 1)[0]
                    .strip()
                )

                return version

            except IndexError:
                continue

        return None

    @classmethod
    def detect(cls):
        nvidia = (
            cls.get_nvidia_info()
        )

        driver_cuda_version = (
            cls.get_driver_cuda_version()
        )

        nvcc_version = (
            cls.get_nvcc_version()
        )

        return HardwareProfile(
            os_name=platform.system(),
            cpu_name=cls.get_cpu_name(),
            cpu_count=os.cpu_count() or 1,
            ram_gb=cls.get_ram_gb(),

            gpu_available=(
                nvidia["available"]
            ),
            gpu_name=nvidia["name"],
            vram_gb=nvidia["vram_gb"],

            nvidia_driver_available=(
                nvidia["available"]
            ),
            driver_version=(
                nvidia["driver_version"]
            ),
            driver_cuda_version=(
                driver_cuda_version
            ),

            cuda_toolkit_available=(
                nvcc_version is not None
            ),
            nvcc_version=nvcc_version
        )