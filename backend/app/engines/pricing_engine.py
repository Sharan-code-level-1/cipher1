"""Pricing engine — OEM parts catalogue + repair-cost estimator.

The catalogue is a simplified OEM price book (INR); a production system would
back `PartsCatalogue` with a live pricing service. `PricingEngine.estimate`
turns fused damage into an itemized estimate (parts, labour, painting, taxes).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

LABOUR_RATE = 850.0  # INR / hour
TAX_RATE = 0.18
SEVERITY_MULTIPLIER = {
    "minor": 0.55,
    "moderate": 0.85,
    "major": 1.0,
    "critical": 1.25,
    "total_loss": 1.0,
}


class PartsCatalogue:
    """OEM parts price book. Swap for a live pricing service in production."""

    OEM_PARTS: Dict[str, Dict[str, float]] = {
        "bumper": {"part": 12000, "labour_hours": 3.0, "paint": 4500},
        "door": {"part": 18000, "labour_hours": 4.5, "paint": 6000},
        "hood": {"part": 15000, "labour_hours": 3.5, "paint": 5000},
        "roof": {"part": 25000, "labour_hours": 6.0, "paint": 9000},
        "mirror": {"part": 3500, "labour_hours": 1.0, "paint": 800},
        "windshield": {"part": 9000, "labour_hours": 1.5, "paint": 0},
        "headlights": {"part": 8000, "labour_hours": 1.2, "paint": 0},
        "tail_lights": {"part": 4500, "labour_hours": 1.0, "paint": 0},
        "windows": {"part": 5000, "labour_hours": 1.5, "paint": 0},
        "wheel": {"part": 7000, "labour_hours": 1.0, "paint": 0},
        "tyres": {"part": 6000, "labour_hours": 0.5, "paint": 0},
    }

    def lookup(self, part: str) -> Dict[str, float]:
        return self.OEM_PARTS.get(part, self.OEM_PARTS["bumper"])


@dataclass
class PricingResult:
    currency: str = "INR"
    parts_total: float = 0
    labour_total: float = 0
    painting_total: float = 0
    taxes_total: float = 0
    grand_total: float = 0
    repair_days: int = 1
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    invoice_json: Dict[str, Any] = field(default_factory=dict)
    explanation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PricingEngine:
    def __init__(self, catalogue: PartsCatalogue | None = None):
        self.catalogue = catalogue or PartsCatalogue()

    def estimate(
        self, *, severity: str, damages: List[Dict[str, Any]], make: str = "Generic"
    ) -> PricingResult:
        mult = SEVERITY_MULTIPLIER.get(severity, 1.0)
        line_items: List[Dict[str, Any]] = []
        parts_total = labour_total = painting_total = 0.0
        hours = 0.0
        seen_parts: set[str] = set()

        for dmg in damages:
            part = dmg.get("part") or "bumper"
            book = self.catalogue.lookup(part)
            if part in seen_parts:
                labour = book["labour_hours"] * LABOUR_RATE * 0.4 * mult
                labour_total += labour
                hours += book["labour_hours"] * 0.4
                line_items.append({
                    "description": f"Additional repair — {part} ({dmg.get('type')})",
                    "category": "labour",
                    "amount": round(labour, 2),
                })
                continue
            seen_parts.add(part)
            area = float(dmg.get("area_pct") or 5)
            replace = area >= 15 or dmg.get("type") in {
                "broken_glass", "broken_light", "bent_metal", "total_loss"
            }
            part_cost = book["part"] * mult if replace else book["part"] * 0.25 * mult
            labour = book["labour_hours"] * LABOUR_RATE * mult
            paint = (
                book["paint"] * mult
                if dmg.get("type") in {"scratch", "paint_damage", "dent", "bent_metal"}
                else 0
            )
            parts_total += part_cost
            labour_total += labour
            painting_total += paint
            hours += book["labour_hours"]
            line_items.append({
                "description": f"{'Replace' if replace else 'Repair'} {part} — {dmg.get('type')}",
                "category": "parts", "oem": True, "amount": round(part_cost, 2),
            })
            line_items.append({
                "description": f"Labour — {part}", "category": "labour",
                "hours": book["labour_hours"], "rate": LABOUR_RATE, "amount": round(labour, 2),
            })
            if paint:
                line_items.append({
                    "description": f"Painting — {part}", "category": "painting",
                    "amount": round(paint, 2),
                })

        if severity == "total_loss":
            parts_total = max(parts_total, 250000)
            labour_total = 0
            painting_total = 0
            line_items = [{
                "description": "Total loss settlement estimate",
                "category": "replacement", "amount": round(parts_total, 2),
            }]

        subtotal = parts_total + labour_total + painting_total
        taxes = subtotal * TAX_RATE
        grand = subtotal + taxes
        days = max(1, int(round(hours / 6)) + (2 if severity in {"major", "critical"} else 0))

        invoice = {
            "currency": "INR", "make_factor": make, "subtotal": round(subtotal, 2),
            "tax_rate": TAX_RATE, "tax": round(taxes, 2), "grand_total": round(grand, 2),
            "line_items": line_items,
        }
        explanation = {
            "method": "OEM parts book + labour rate + GST",
            "labour_rate_inr": LABOUR_RATE, "severity_multiplier": mult,
            "tax_rate": TAX_RATE, "repair_days": days,
            "notes": "Estimates are indicative; surveyor may adjust after physical inspection.",
        }
        return PricingResult(
            parts_total=round(parts_total, 2),
            labour_total=round(labour_total, 2),
            painting_total=round(painting_total, 2),
            taxes_total=round(taxes, 2),
            grand_total=round(grand, 2),
            repair_days=days,
            line_items=line_items,
            invoice_json=invoice,
            explanation=explanation,
        )
