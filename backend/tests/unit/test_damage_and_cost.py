"""AI module unit tests."""
import io

import numpy as np
from PIL import Image, ImageDraw

from app.ai.damage_detector import DamageDetector
from app.ai.cost_estimator import CostEstimator
from app.ai.severity import classify_severity


def _damaged_car_image() -> bytes:
    """Synthesize an image with strong edges/scratches so CV finds damage."""
    rng = np.random.default_rng(42)
    base = np.full((480, 640, 3), 200, dtype=np.uint8)
    img = Image.fromarray(base)
    draw = ImageDraw.Draw(img)
    # Simulate scratches / cracks with high-contrast strokes
    for _ in range(40):
        x1, y1 = int(rng.integers(0, 640)), int(rng.integers(0, 480))
        x2, y2 = x1 + int(rng.integers(-60, 60)), y1 + int(rng.integers(-60, 60))
        draw.line((x1, y1, x2, y2), fill=(20, 20, 20), width=2)
    draw.rectangle((240, 300, 420, 440), outline=(0, 0, 0), width=4)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_damage_detector_returns_real_analysis():
    det = DamageDetector()
    data = _damaged_car_image()
    result = det.detect(data)
    assert result.damages, "should detect at least one damage region"
    assert 0 < result.confidence <= 1
    assert result.severity in ["minor", "moderate", "major", "critical", "total_loss"]
    assert "edge_density" in result.explanation["metrics"]


def test_damage_detector_deterministic_for_same_image():
    det = DamageDetector()
    data = _damaged_car_image()
    a = det.detect(data)
    b = det.detect(data)
    assert a.severity == b.severity
    assert a.damage_area_pct == b.damage_area_pct


def test_cost_estimator_totals():
    est = CostEstimator()
    result = est.estimate(
        severity="moderate",
        damages=[{"part": "bumper", "type": "dent", "area_pct": 12}],
        make="Toyota",
    )
    assert result.grand_total > 0
    assert result.taxes_total > 0
    assert result.invoice_json["grand_total"] == result.grand_total


def test_severity_rules():
    assert classify_severity([{"type": "scratch"}], 3) == "minor"
    assert classify_severity([{"type": "bent_metal"}], 45) == "critical"
