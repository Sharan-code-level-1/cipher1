"""Verification engine (Layer 2).

Detects a number-plate region, runs OCR over it, and matches the recognized
plate against the claimed vehicle's registration.

Model stubs: `_detect_plate_region` is a CV-based candidate detector standing in
for a trained plate detector (e.g. YOLO-plate), and `_ocr` is a placeholder for
a real OCR backend (e.g. PaddleOCR / Tesseract). Both return the same contract a
production model would, so swapping them in later requires no downstream change.
"""
from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

_PLATE_CLEAN_RE = re.compile(r"[^A-Z0-9]")


@dataclass
class VerificationResult:
    plate_detected: bool = False
    plate_bbox: Optional[Dict[str, float]] = None
    plate_text: Optional[str] = None
    plate_confidence: float = 0.0
    vehicle_match: Optional[bool] = None
    match_score: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VerificationEngine:
    def __init__(self, max_dim: int = 1024):
        self.max_dim = max_dim
        self.model_version = "plate-detect-stub-1.0"

    def _load(self, data: bytes) -> np.ndarray:
        pil = Image.open(io.BytesIO(data)).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]
        scale = self.max_dim / float(max(h, w))
        if scale < 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        return img

    def _detect_plate_region(
        self, img: np.ndarray
    ) -> Optional[Tuple[int, int, int, int, float]]:
        """CV stub: find the most plate-like rectangular region.

        Plates are wide, bright, high-contrast rectangles. We look for contours
        with a plate-like aspect ratio (roughly 2:1 to 6:1).
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        edges = cv2.Canny(gray, 30, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        h, w = gray.shape[:2]
        best: Optional[Tuple[int, int, int, int, float]] = None
        best_score = 0.0
        for c in contours:
            x, y, rw, rh = cv2.boundingRect(c)
            if rh == 0:
                continue
            aspect = rw / float(rh)
            frac = (rw * rh) / float(w * h)
            if 2.0 <= aspect <= 6.5 and 0.005 <= frac <= 0.25:
                roi = gray[y : y + rh, x : x + rw]
                contrast = float(roi.std()) if roi.size else 0.0
                score = contrast * (0.5 + frac)
                if score > best_score:
                    best_score = score
                    best = (x, y, rw, rh, round(min(0.95, 0.4 + frac * 2), 4))
        return best

    def _ocr(self, roi: np.ndarray) -> Tuple[Optional[str], float]:
        """OCR stub. A real backend returns recognized text + confidence.

        Without a bundled OCR model we cannot reliably read arbitrary plates, so
        this returns no text but keeps the contract; the region detection still
        provides useful verification signal.
        """
        return None, 0.0

    @staticmethod
    def _normalize_plate(text: Optional[str]) -> str:
        return _PLATE_CLEAN_RE.sub("", (text or "").upper())

    @staticmethod
    def _match_score(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        # Simple character-overlap ratio on normalized plates.
        matches = sum(1 for x, y in zip(a, b) if x == y)
        return round(matches / max(len(a), len(b)), 3)

    def verify(
        self, data: bytes, *, registration_number: Optional[str] = None
    ) -> VerificationResult:
        result = VerificationResult()
        img = self._load(data)
        h, w = img.shape[:2]

        region = self._detect_plate_region(img)
        if not region:
            result.notes.append("No plate-like region detected in this image")
            return result

        x, y, rw, rh, conf = region
        result.plate_detected = True
        result.plate_confidence = conf
        result.plate_bbox = {
            "x1": round(x / w, 3),
            "y1": round(y / h, 3),
            "x2": round((x + rw) / w, 3),
            "y2": round((y + rh) / h, 3),
        }

        roi = img[y : y + rh, x : x + rw]
        text, ocr_conf = self._ocr(roi)
        result.plate_text = text

        if registration_number and text:
            reg = self._normalize_plate(registration_number)
            got = self._normalize_plate(text)
            result.match_score = self._match_score(reg, got)
            result.vehicle_match = result.match_score >= 0.7
            result.notes.append(
                f"Plate OCR '{got}' vs registration '{reg}' (score {result.match_score})"
            )
        else:
            result.notes.append(
                "Plate region located; OCR text unavailable for registration match"
            )
        return result
