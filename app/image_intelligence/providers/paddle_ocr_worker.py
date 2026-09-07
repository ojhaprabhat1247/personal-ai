import json
import sys
from pathlib import Path

from paddleocr import PaddleOCR

from app.image_intelligence.preprocessing import (
    TemporaryImageVariants,
)


MIN_GOOD_CONFIDENCE = 0.85
MIN_GOOD_CHARACTERS = 3


def build_ocr():
    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )


def extract_result(result):
    output = {
        "text": "",
        "lines": [],
        "average_confidence": 0.0
    }

    if not result:
        return output

    collected_text = []
    confidences = []

    for item in result:
        if not hasattr(item, "json"):
            continue

        data = item.json

        if callable(data):
            data = data()

        if not isinstance(data, dict):
            continue

        result_data = data.get(
            "res",
            data
        )

        texts = result_data.get(
            "rec_texts",
            []
        )

        scores = result_data.get(
            "rec_scores",
            []
        )

        boxes = result_data.get(
            "rec_boxes",
            []
        )

        for index, text in enumerate(texts):
            if not text:
                continue

            score = None
            box = None

            if index < len(scores):
                try:
                    score = float(
                        scores[index]
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    score = None

            if index < len(boxes):
                current_box = boxes[index]

                if hasattr(
                    current_box,
                    "tolist"
                ):
                    current_box = (
                        current_box.tolist()
                    )

                box = current_box

            output["lines"].append({
                "text": text,
                "confidence": score,
                "box": box
            })

            collected_text.append(
                text
            )

            if score is not None:
                confidences.append(
                    score
                )

    output["text"] = "\n".join(
        collected_text
    )

    if confidences:
        output[
            "average_confidence"
        ] = (
            sum(confidences)
            / len(confidences)
        )

    return output


def run_ocr(
    ocr,
    image_path
):
    result = ocr.predict(
        input=str(image_path)
    )

    return extract_result(
        result
    )


def is_good_result(result):
    text = result.get(
        "text",
        ""
    ).strip()

    average_confidence = result.get(
        "average_confidence",
        0.0
    )

    return (
        len(text) >= MIN_GOOD_CHARACTERS
        and len(
            result.get(
                "lines",
                []
            )
        ) > 0
        and average_confidence
        >= MIN_GOOD_CONFIDENCE
    )


def score_result(result):
    text = result.get(
        "text",
        ""
    )

    lines = result.get(
        "lines",
        []
    )

    confidence = result.get(
        "average_confidence",
        0.0
    )

    character_count = len(
        text.replace(
            "\n",
            ""
        ).strip()
    )

    return (
        character_count
        + (len(lines) * 10)
        + (confidence * 50)
    )


def build_response(
    extracted,
    image_path,
    variant,
    attempts
):
    return {
        "success": True,
        "text": extracted.get(
            "text",
            ""
        ),
        "lines": extracted.get(
            "lines",
            []
        ),
        "average_confidence": (
            extracted.get(
                "average_confidence",
                0.0
            )
        ),
        "variant": variant,
        "attempts": attempts,
        "image_path": str(
            image_path
        )
    }


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps({
                "success": False,
                "error": (
                    "Image path argument "
                    "is required."
                )
            })
        )

        return 1

    image_path = Path(
        sys.argv[1]
    ).resolve()

    if not image_path.exists():
        print(
            json.dumps({
                "success": False,
                "error": (
                    f"Image not found: "
                    f"{image_path}"
                )
            })
        )

        return 1

    try:
        ocr = build_ocr()

        attempts = 1

        # Fast pass:
        # always try original image first.
        original_result = run_ocr(
            ocr,
            image_path
        )

        if is_good_result(
            original_result
        ):
            response = build_response(
                extracted=original_result,
                image_path=image_path,
                variant="original_fast_pass",
                attempts=attempts
            )

            print(
                json.dumps(
                    response,
                    ensure_ascii=True
                )
            )

            return 0

        best_result = (
            original_result
        )

        best_variant = (
            "original_fast_pass"
        )

        best_score = score_result(
            original_result
        )

        # Adaptive fallback:
        # only happens when original OCR
        # is blank or low-confidence.
        with TemporaryImageVariants() as temp:
            variants = temp.create(
                image_path
            )

            for variant in variants:
                # We already tested the
                # original image above.
                if variant.name == "original":
                    continue

                attempts += 1

                current_result = run_ocr(
                    ocr,
                    variant.path
                )

                current_score = score_result(
                    current_result
                )

                if current_score > best_score:
                    best_result = (
                        current_result
                    )

                    best_variant = (
                        variant.name
                    )

                    best_score = (
                        current_score
                    )

        if not is_good_result(
            best_result
        ):
            response = {
                "success": False,
                "error": (
                    "No reliable OCR text "
                    "was detected."
                ),
                "candidate_text": (
                    best_result.get(
                        "text",
                        ""
                    )
                ),
                "average_confidence": (
                    best_result.get(
                        "average_confidence",
                        0.0
                    )
                ),
                "variant": best_variant,
                "attempts": attempts,
                "image_path": str(
                    image_path
                )
            }

            print(
                json.dumps(
                    response,
                    ensure_ascii=True
                )
            )

            return 1


        response = build_response(
            extracted=best_result,
            image_path=image_path,
            variant=best_variant,
            attempts=attempts
        )

        print(
            json.dumps(
                response,
                ensure_ascii=True
            )
        )

        return 0

    except Exception as error:
        print(
            json.dumps({
                "success": False,
                "error": str(error)
            })
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )