"""Severity classification engine."""
from __future__ import annotations

from typing import Any, Dict, List


def classify_severity(damages: List[Dict[str, Any]], damage_area_pct: float) -> str:
    types = {d.get("type") for d in damages}
    if "total_loss" in types or "fire_damage" in types or damage_area_pct >= 60:
        return "total_loss"
    if damage_area_pct >= 40 or "bent_metal" in types or "flood_damage" in types:
        return "critical"
    if damage_area_pct >= 20:
        return "major"
    if damage_area_pct >= 8:
        return "moderate"
    return "minor"
