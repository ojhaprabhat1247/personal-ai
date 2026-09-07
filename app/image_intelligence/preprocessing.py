from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np

from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    ImageOps,
)


@dataclass
class ImageVariant:
    name: str
    path: Path


class ImagePreprocessor:

    def __init__(
        self,
        max_dimension=2600
    ):
        self.max_dimension = max_dimension

    # -------------------------------------------------
    # Basic image loading / conversion
    # -------------------------------------------------

    @staticmethod
    def open_image(image_path):
        image = Image.open(
            image_path
        )

        image = ImageOps.exif_transpose(
            image
        )

        return image.convert("RGB")

    @staticmethod
    def pil_to_bgr(image):
        array = np.array(
            image
        )

        return cv2.cvtColor(
            array,
            cv2.COLOR_RGB2BGR
        )

    @staticmethod
    def bgr_to_pil(image):
        rgb = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        return Image.fromarray(
            rgb
        )

    # -------------------------------------------------
    # Perspective correction
    # -------------------------------------------------

    @staticmethod
    def order_points(points):
        points = np.asarray(
            points,
            dtype=np.float32
        )

        ordered = np.zeros(
            (4, 2),
            dtype=np.float32
        )

        point_sum = points.sum(
            axis=1
        )

        point_diff = np.diff(
            points,
            axis=1
        ).reshape(-1)

        ordered[0] = points[
            np.argmin(point_sum)
        ]

        ordered[2] = points[
            np.argmax(point_sum)
        ]

        ordered[1] = points[
            np.argmin(point_diff)
        ]

        ordered[3] = points[
            np.argmax(point_diff)
        ]

        return ordered

    @classmethod
    def four_point_transform(
        cls,
        image,
        points
    ):
        rectangle = cls.order_points(
            points
        )

        (
            top_left,
            top_right,
            bottom_right,
            bottom_left
        ) = rectangle

        width_a = np.linalg.norm(
            bottom_right - bottom_left
        )

        width_b = np.linalg.norm(
            top_right - top_left
        )

        max_width = int(
            max(
                width_a,
                width_b
            )
        )

        height_a = np.linalg.norm(
            top_right - bottom_right
        )

        height_b = np.linalg.norm(
            top_left - bottom_left
        )

        max_height = int(
            max(
                height_a,
                height_b
            )
        )

        if (
            max_width < 10
            or max_height < 10
        ):
            return image

        destination = np.array(
            [
                [0, 0],
                [max_width - 1, 0],
                [
                    max_width - 1,
                    max_height - 1
                ],
                [0, max_height - 1]
            ],
            dtype=np.float32
        )

        matrix = cv2.getPerspectiveTransform(
            rectangle,
            destination
        )

        return cv2.warpPerspective(
            image,
            matrix,
            (
                max_width,
                max_height
            )
        )

    @classmethod
    def correct_perspective(
        cls,
        image
    ):
        original = image.copy()

        height, width = (
            image.shape[:2]
        )

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        blurred = cv2.GaussianBlur(
            gray,
            (5, 5),
            0
        )

        edges = cv2.Canny(
            blurred,
            60,
            180
        )

        contours, _ = (
            cv2.findContours(
                edges,
                cv2.RETR_LIST,
                cv2.CHAIN_APPROX_SIMPLE
            )
        )

        contours = sorted(
            contours,
            key=cv2.contourArea,
            reverse=True
        )[:10]

        image_area = (
            width * height
        )

        for contour in contours:
            perimeter = (
                cv2.arcLength(
                    contour,
                    True
                )
            )

            approximation = (
                cv2.approxPolyDP(
                    contour,
                    0.02 * perimeter,
                    True
                )
            )

            if len(
                approximation
            ) != 4:
                continue

            contour_area = (
                cv2.contourArea(
                    approximation
                )
            )

            if (
                contour_area
                < image_area * 0.20
            ):
                continue

            points = (
                approximation
                .reshape(4, 2)
            )

            return (
                cls.four_point_transform(
                    original,
                    points
                )
            )

        return original

    # -------------------------------------------------
    # Deskew
    # -------------------------------------------------

    @staticmethod
    def deskew(image):
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        binary = cv2.threshold(
            gray,
            0,
            255,
            (
                cv2.THRESH_BINARY_INV
                | cv2.THRESH_OTSU
            )
        )[1]

        coordinates = (
            np.column_stack(
                np.where(
                    binary > 0
                )
            )
        )

        if len(coordinates) < 100:
            return image

        coordinates = (
            coordinates[:, ::-1]
            .astype(np.float32)
        )

        angle = cv2.minAreaRect(
            coordinates
        )[-1]

        if angle > 45:
            angle -= 90

        if angle < -45:
            angle += 90

        # Don't use deskew to fix a
        # completely sideways image.
        if abs(angle) > 15:
            return image

        if abs(angle) < 0.2:
            return image

        height, width = (
            image.shape[:2]
        )

        center = (
            width / 2,
            height / 2
        )

        matrix = (
            cv2.getRotationMatrix2D(
                center,
                angle,
                1.0
            )
        )

        return cv2.warpAffine(
            image,
            matrix,
            (
                width,
                height
            ),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

    # -------------------------------------------------
    # OCR enhancement
    # -------------------------------------------------

    @staticmethod
    def clahe_enhance(image):
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        enhanced = clahe.apply(
            gray
        )

        return cv2.cvtColor(
            enhanced,
            cv2.COLOR_GRAY2BGR
        )

    @staticmethod
    def adaptive_threshold(
        image
    ):
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.GaussianBlur(
            gray,
            (3, 3),
            0
        )

        thresholded = (
            cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                11
            )
        )

        return cv2.cvtColor(
            thresholded,
            cv2.COLOR_GRAY2BGR
        )

    @staticmethod
    def denoise(image):
        return cv2.fastNlMeansDenoisingColored(
            image,
            None,
            5,
            5,
            7,
            21
        )

    @staticmethod
    def sharpen(image):
        kernel = np.array(
            [
                [0, -1, 0],
                [-1, 5, -1],
                [0, -1, 0]
            ],
            dtype=np.float32
        )

        return cv2.filter2D(
            image,
            -1,
            kernel
        )

    def upscale_if_needed(
        self,
        image
    ):
        height, width = (
            image.shape[:2]
        )

        longest_side = max(
            width,
            height
        )

        if longest_side >= 2000:
            return image.copy()

        scale = min(
            2.0,
            self.max_dimension
            / longest_side
        )

        new_width = int(
            width * scale
        )

        new_height = int(
            height * scale
        )

        return cv2.resize(
            image,
            (
                new_width,
                new_height
            ),
            interpolation=cv2.INTER_CUBIC
        )

    # -------------------------------------------------
    # Variant generation
    # -------------------------------------------------

    def create_variants(
        self,
        image_path,
        output_directory
    ):
        image_path = Path(
            image_path
        ).resolve()

        output_directory = Path(
            output_directory
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        pil_image = self.open_image(
            image_path
        )

        original = self.pil_to_bgr(
            pil_image
        )

        variants = []

        def save_variant(
            name,
            image
        ):
            path = (
                output_directory
                / f"{name}.png"
            )

            success = cv2.imwrite(
                str(path),
                image
            )

            if not success:
                return

            variants.append(
                ImageVariant(
                    name=name,
                    path=path
                )
            )

        # 1. EXIF-corrected original.
        save_variant(
            "original",
            original
        )

        # 2. Detect photographed paper/document.
        perspective = (
            self.correct_perspective(
                original
            )
        )

        save_variant(
            "perspective",
            perspective
        )

        # 3. Correct small camera/page skew.
        deskewed = self.deskew(
            perspective
        )

        save_variant(
            "deskewed",
            deskewed
        )

        # 4. Improve local contrast.
        clahe = self.clahe_enhance(
            deskewed
        )

        save_variant(
            "clahe",
            clahe
        )

        # 5. Strong document / scan pass.
        thresholded = (
            self.adaptive_threshold(
                deskewed
            )
        )

        save_variant(
            "adaptive_threshold",
            thresholded
        )

        # 6. Denoise + sharpen.
        denoised = self.denoise(
            clahe
        )

        sharpened = self.sharpen(
            denoised
        )

        save_variant(
            "enhanced",
            sharpened
        )

        # 7. Upscaling for small text.
        upscaled = (
            self.upscale_if_needed(
                sharpened
            )
        )

        if (
            upscaled.shape[:2]
            != sharpened.shape[:2]
        ):
            save_variant(
                "upscaled",
                upscaled
            )

        # Orientation fallbacks are kept
        # separate from deskew.
        for degrees in (
            90,
            180,
            270
        ):
            if degrees == 90:
                rotated = cv2.rotate(
                    sharpened,
                    cv2.ROTATE_90_CLOCKWISE
                )

            elif degrees == 180:
                rotated = cv2.rotate(
                    sharpened,
                    cv2.ROTATE_180
                )

            else:
                rotated = cv2.rotate(
                    sharpened,
                    cv2.ROTATE_90_COUNTERCLOCKWISE
                )

            save_variant(
                f"rotate_{degrees}",
                rotated
            )

        return variants


class TemporaryImageVariants:

    def __init__(
        self,
        preprocessor=None
    ):
        self.preprocessor = (
            preprocessor
            or ImagePreprocessor()
        )

        self.temp_directory = None

    def __enter__(self):
        self.temp_directory = (
            TemporaryDirectory(
                prefix="personal_ai_ocr_"
            )
        )

        return self

    def create(
        self,
        image_path
    ):
        return (
            self.preprocessor
            .create_variants(
                image_path=image_path,
                output_directory=(
                    self.temp_directory.name
                )
            )
        )

    def __exit__(
        self,
        _exc_type,
        _exc_value,
        _traceback
    ):
        if self.temp_directory:
            self.temp_directory.cleanup()