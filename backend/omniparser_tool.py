from __future__ import annotations

"""Client for calling the hosted OmniParser model on Hugging Face."""

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageFont


class OmniParserError(RuntimeError):
    pass


class OmniParserClient:
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        bbox_threshold: float = 0.001,
        iou_threshold: float = 0.4,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_url = api_url or os.getenv("HF_OMNIPARSER_URL")
        self.api_token = api_token or os.getenv("HF_API_TOKEN")
        if not self.api_url or not self.api_token:
            raise OmniParserError("OmniParser credentials are not configured")
        self.bbox_threshold = bbox_threshold
        self.iou_threshold = iou_threshold
        self.session = session or requests.Session()

    def analyze(self, image_path: str | Path) -> Dict[str, Any]:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Screenshot not found: {path}")

        with Image.open(path) as img:
            width, height = img.size
        with path.open("rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("utf-8")

        payload = {
            "inputs": {
                "image": encoded,
                "image_size": {"w": width, "h": height},
                "bbox_threshold": self.bbox_threshold,
                "iou_threshold": self.iou_threshold,
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        response = self.session.post(self.api_url, headers=headers, json=payload, timeout=60)
        if response.status_code >= 400:
            raise OmniParserError(f"OmniParser request failed: {response.status_code} {response.text}")

        data = response.json()
        elements = self._normalize_elements(data.get("bboxes", []), width, height)
        return {"elements": elements, "raw": data, "image_size": (width, height)}

    @staticmethod
    def _normalize_elements(raw_boxes: List[Dict[str, Any]], width: int, height: int) -> List[Dict[str, Any]]:
        cleaned: List[Dict[str, Any]] = []
        for idx, box in enumerate(raw_boxes):
            bbox = box.get("bbox", [0, 0, 0, 0])
            pixel_bbox = [
                int(bbox[0] * width),
                int(bbox[1] * height),
                int(bbox[2] * width),
                int(bbox[3] * height),
            ]
            cleaned.append(
                {
                    "element_id": idx + 1,
                    "text": box.get("content", ""),
                    "type": box.get("type", "unknown"),
                    "bbox": pixel_bbox,
                    "center": [
                        int((pixel_bbox[0] + pixel_bbox[2]) / 2),
                        int((pixel_bbox[1] + pixel_bbox[3]) / 2),
                    ],
                    "confidence": box.get("confidence", 0.0),
                }
            )
        return cleaned


def get_screen_elements(image_path: str | Path) -> List[Dict[str, Any]]:
    client = OmniParserClient()
    return client.analyze(image_path)["elements"]


def draw_omniparser_boxes(
    image_path: str | Path,
    elements: List[Dict[str, Any]],
    output_path: str | Path,
) -> None:
    """Overlay OmniParser bounding boxes on a screenshot for debugging."""
    src = Path(image_path)
    dst = Path(output_path)
    if not src.exists():
        raise FileNotFoundError(f"Screenshot not found: {src}")

    with Image.open(src).convert("RGB") as img:
        draw = ImageDraw.Draw(img)
        font = None
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        for elem in elements:
            bbox = elem.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            x1, y1, x2, y2 = bbox
            draw.rectangle((x1, y1, x2, y2), outline="red", width=2)
            label = f"{elem.get('element_id')}:{elem.get('type','')}"
            if font:
                draw.rectangle((x1, max(0, y1 - 14), x1 + len(label) * 6, y1), fill="red")
                draw.text((x1 + 2, y1 - 12), label, fill="white", font=font)

        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test the hosted OmniParser client")
    parser.add_argument("image", help="Screenshot to analyze")
    args = parser.parse_args()

    client = OmniParserClient()
    result = client.analyze(args.image)
    print(json.dumps(result["elements"], indent=2))
