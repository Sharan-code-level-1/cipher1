"""Damage engine — detection (RT-DETRv2 stub), segmentation (SegFormer stub), fusion.

`RTDetrV2Detector` performs real OpenCV/NumPy pixel analysis to localize and
classify damage regions, standing in for an RT-DETRv2 object detector.
`SegFormerSegmenter` produces a coarse damage segmentation mask from the same
pixel cues, standing in for a SegFormer semantic-segmentation head. `DamageEngine`
runs both per image and then fuses per-image detections into a single
claim-level result. All public return types match what a real model pipeline
would emit, so the stubs can be replaced without touching the orchestrator.
"""
from __future__ import annotations

import io
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image

PARTS = [
    "bumper", "door", "hood", "roof", "mirror", "windshield",
    "headlights", "tail_lights", "windows", "wheel", "tyres",
]
DAMAGE_TYPES = [
    "dent", "scratch", "paint_damage", "broken_glass", "crack",
    "broken_light", "bent_metal", "flood_damage", "fire_damage", "total_loss",
]
SEVERITIES = ["minor", "moderate", "major", "critical", "total_loss"]


def _part_for_region(cx: float, cy: float) -> str:
    if cy < 0.33:
        return "roof" if 0.33 < cx < 0.66 else ("windshield" if cx <= 0.33 else "hood")
    if cy < 0.66:
        return "door" if 0.2 < cx < 0.8 else "mirror"
    return "bumper" if 0.2 < cx < 0.8 else "wheel"


@dataclass
class DamageResult:
    """Per-image damage output."""

    parts: List[Dict[str, Any]] = field(default_factory=list)
    damages: List[Dict[str, Any]] = field(default_factory=list)
    severity: str = "minor"
    damage_area_pct: float = 0.0
    confidence: float = 0.0
    explanation: Dict[str, Any] = field(default_factory=dict)
    model_version: str = "rtdetrv2-seg-stub-1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FusedDamage:
    """Claim-level damage fused across all images."""

    parts: List[Dict[str, Any]] = field(default_factory=list)
    damages: List[Dict[str, Any]] = field(default_factory=list)
    severity: str = "minor"
    damage_area_pct: float = 0.0
    confidence: float = 0.0
    image_count: int = 0
    fusion_method: str = "max_confidence_union"
    explanation: Dict[str, Any] = field(default_factory=dict)
    model_version: str = "fusion-1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class _CVBase:
    def __init__(self, max_dim: int = 1024):
        self.max_dim = max_dim

    def _load(self, image_bytes: bytes) -> np.ndarray:
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]
        scale = self.max_dim / float(max(h, w))
        if scale < 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        return img


class SegFormerSegmenter(_CVBase):
    """SegFormer stub: coarse damage segmentation from edge/texture energy."""

    def segment(self, image_bytes: bytes) -> Dict[str, Any]:
        img = self._load(image_bytes)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        mask = cv2.dilate(edges, kernel, iterations=2)
        damaged_px = int(np.count_nonzero(mask))
        total_px = int(mask.size)
        return {
            "mask_area_pct": round(100.0 * damaged_px / max(total_px, 1), 2),
            "method": "edge_energy_segmentation",
            "model": "segformer-stub-1.0",
        }


class RTDetrV2Detector(_CVBase):
    """RT-DETRv2 stub: localize + classify damage regions via CV heuristics."""

    def __init__(self, max_dim: int = 1024):
        super().__init__(max_dim)
        self.model_version = "rtdetrv2-stub-1.0"

    def detect(self, image_bytes: bytes) -> Tuple[List[Dict], List[Dict], float, float, Dict]:
        img = self._load(image_bytes)
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        edge_density = float(np.count_nonzero(edges)) / float(edges.size)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        regions = self._localize(edges, w, h)
        damages: List[Dict[str, Any]] = []
        parts: List[Dict[str, Any]] = []
        total_area = 0.0
        for (x, y, rw, rh, region_score) in regions:
            cx, cy = (x + rw / 2) / w, (y + rh / 2) / h
            part = _part_for_region(cx, cy)
            dmg_type, conf = self._classify(img, x, y, rw, rh, lap_var)
            area_pct = round(100.0 * (rw * rh) / (w * h), 2)
            total_area += area_pct
            bbox = {
                "x1": round(x / w, 3), "y1": round(y / h, 3),
                "x2": round((x + rw) / w, 3), "y2": round((y + rh) / h, 3),
            }
            parts.append({"label": part, "confidence": conf, "bbox": bbox})
            damages.append({
                "type": dmg_type, "part": part, "confidence": conf, "bbox": bbox,
                "area_pct": area_pct, "region_score": round(region_score, 3),
                "segmentation_mask": None,
            })

        if not damages:
            dmg_type = "scratch" if edge_density > 0.06 else "paint_damage"
            conf = round(min(0.6, 0.4 + edge_density), 4)
            bbox = {"x1": 0.3, "y1": 0.3, "x2": 0.7, "y2": 0.7}
            damages.append({
                "type": dmg_type, "part": "door", "confidence": conf, "bbox": bbox,
                "area_pct": round(edge_density * 100, 2), "region_score": edge_density,
                "segmentation_mask": None,
            })
            parts.append({"label": "door", "confidence": conf, "bbox": bbox})
            total_area = damages[0]["area_pct"]

        metrics = {
            "edge_density": round(edge_density, 4),
            "laplacian_variance": round(lap_var, 2),
            "region_count": len(damages),
        }
        return parts, damages, round(min(100.0, total_area), 2), edge_density, metrics

    def _localize(
        self, edges: np.ndarray, w: int, h: int
    ) -> List[Tuple[int, int, int, int, float]]:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        frame_area = float(w * h)
        scored: List[Tuple[int, int, int, int, float]] = []
        for c in contours:
            x, y, rw, rh = cv2.boundingRect(c)
            frac = (rw * rh) / frame_area
            if frac < 0.01 or frac > 0.9:
                continue
            roi = edges[y:y + rh, x:x + rw]
            local_density = float(np.count_nonzero(roi)) / float(max(roi.size, 1))
            if local_density > 0.05:
                scored.append((x, y, rw, rh, local_density * (0.5 + frac)))
        scored.sort(key=lambda t: t[4], reverse=True)
        return scored[:6]

    def _classify(
        self, img: np.ndarray, x: int, y: int, rw: int, rh: int, lap_var: float
    ) -> Tuple[str, float]:
        roi = img[y:y + rh, x:x + rw]
        if roi.size == 0:
            return "scratch", 0.5
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat = float(hsv[:, :, 1].mean())
        val = float(hsv[:, :, 2].mean())
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        local_edges = cv2.Canny(gray_roi, 50, 150)
        local_density = float(np.count_nonzero(local_edges)) / float(local_edges.size)
        aspect = rw / float(rh + 1e-5)

        if val < 45:
            dmg = "broken_glass" if sat < 40 else "broken_light"
        elif local_density > 0.22 and (aspect > 2.2 or aspect < 0.45):
            dmg = "scratch"
        elif local_density > 0.22:
            dmg = "crack"
        elif lap_var < 60:
            dmg = "dent"
        elif sat < 35:
            dmg = "paint_damage"
        else:
            dmg = "bent_metal" if local_density > 0.15 else "dent"
        conf = round(min(0.98, 0.55 + local_density + (0.1 if val < 60 else 0)), 4)
        return dmg, conf


def classify_severity(damages: List[Dict[str, Any]], damage_area_pct: float) -> str:
    types = {d.get("type") for d in damages}
    if "total_loss" in types or "fire_damage" in types or damage_area_pct >= 60:
        return "total_loss"
    if damage_area_pct >= 40 or "bent_metal" in types or "flood_damage" in types:
        return "critical"
    if damage_area_pct >= 20 or ("broken_glass" in types and "crack" in types):
        return "major"
    if damage_area_pct >= 8:
        return "moderate"
    return "minor"


def _repair_hint(severity: str) -> str:
    return {
        "total_loss": "Vehicle likely a write-off; assess salvage value.",
        "critical": "Major panel replacement and structural inspection required.",
        "major": "Panel repair/replacement plus refinishing recommended.",
        "moderate": "Localized bodywork and paint blend should restore condition.",
        "minor": "Minor cosmetic repair; PDR or touch-up may suffice.",
    }.get(severity, "Assessment pending.")


class DamageEngine:
    """Runs detection + segmentation per image and fuses to a claim-level result."""

    def __init__(self, max_dim: int = 1024):
        self.detector = RTDetrV2Detector(max_dim)
        self.segmenter = SegFormerSegmenter(max_dim)
        self.model_version = "rtdetrv2-seg-stub-1.0"

    def detect(self, image_bytes: bytes, *, filename: str = "image.jpg") -> DamageResult:
        parts, damages, area, edge_density, metrics = self.detector.detect(image_bytes)
        seg = self.segmenter.segment(image_bytes)
        # Blend detector area with segmentation mask area for a robust estimate.
        damage_area_pct = round(min(100.0, max(area, seg["mask_area_pct"] * 0.5)), 2)
        severity = classify_severity(damages, damage_area_pct)
        confidence = round(float(np.mean([d["confidence"] for d in damages])), 4)
        explanation = {
            "reason": (
                f"Detection localized {len(damages)} damage region(s) covering "
                f"~{damage_area_pct}% of the frame (edge density {round(edge_density, 4)}). "
                f"Severity classified as '{severity}'."
            ),
            "metrics": metrics,
            "segmentation": seg,
            "affected_parts": sorted({p["label"] for p in parts}),
            "damage_types": sorted({d["type"] for d in damages}),
            "confidence": confidence,
            "repair_explanation": _repair_hint(severity),
        }
        return DamageResult(
            parts=parts, damages=damages, severity=severity,
            damage_area_pct=damage_area_pct, confidence=confidence,
            explanation=explanation, model_version=self.model_version,
        )

    def fuse(self, results: List[DamageResult]) -> FusedDamage:
        """Union damages across images, keeping the highest-confidence per part."""
        if not results:
            return FusedDamage(explanation={"reason": "No images available for damage fusion."})

        best_by_part: Dict[str, Dict[str, Any]] = {}
        all_damages: List[Dict[str, Any]] = []
        for res in results:
            for d in res.damages:
                all_damages.append(d)
                part = d.get("part", "unknown")
                if part not in best_by_part or d.get("confidence", 0) > best_by_part[part].get(
                    "confidence", 0
                ):
                    best_by_part[part] = d

        fused_damages = list(best_by_part.values())
        parts = [
            {"label": p, "confidence": d.get("confidence", 0), "bbox": d.get("bbox")}
            for p, d in best_by_part.items()
        ]
        # Claim-level area = max single-image area (avoids double counting same damage).
        damage_area_pct = round(max((r.damage_area_pct for r in results), default=0.0), 2)
        severity = classify_severity(fused_damages, damage_area_pct)
        confidence = round(
            float(np.mean([d.get("confidence", 0) for d in fused_damages])) if fused_damages else 0.0,
            4,
        )
        explanation = {
            "reason": (
                f"Fused {len(results)} image(s) into {len(fused_damages)} distinct damaged part(s). "
                f"Claim severity '{severity}' at ~{damage_area_pct}% peak area."
            ),
            "affected_parts": sorted(best_by_part.keys()),
            "damage_types": sorted({d.get("type") for d in fused_damages}),
            "per_image_severity": [r.severity for r in results],
            "repair_explanation": _repair_hint(severity),
        }
        return FusedDamage(
            parts=parts,
            damages=fused_damages,
            severity=severity,
            damage_area_pct=damage_area_pct,
            confidence=confidence,
            image_count=len(results),
            explanation=explanation,
        )
