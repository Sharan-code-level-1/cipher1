"""AI engine — BYOK vision-LLM report generation.

Loads the admin-configured default provider (OpenAI / Anthropic / Google /
custom OpenAI-compatible), decrypts its API key, builds a structured multimodal
prompt from the pipeline output, calls the provider, and parses the response
into a narrative summary + structured report.

If no provider is configured (or a call fails) the engine returns a deterministic
local report assembled from the pipeline data, so the claim always has a report.
"""
from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import b64_decrypt
from app.models.ai import AIProviderSettings

logger = get_logger("ai_engine")

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class AIReportResult:
    status: str = "skipped"  # generated | skipped | error
    provider_id: Optional[str] = None
    provider_name: str = "unconfigured"
    model: str = "none"
    summary: Optional[str] = None
    report_json: Dict[str, Any] = field(default_factory=dict)
    prompt: Optional[str] = None
    raw_response: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderTestResult:
    status: str  # success | failure
    latency_ms: Optional[int] = None
    message: str = ""
    request_summary: Dict[str, Any] = field(default_factory=dict)
    response_summary: Dict[str, Any] = field(default_factory=dict)


class AIEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- provider resolution ----------------------------------------
    async def get_default_provider(self) -> Optional[AIProviderSettings]:
        q = await self.db.execute(
            select(AIProviderSettings)
            .where(AIProviderSettings.is_enabled.is_(True), AIProviderSettings.is_default.is_(True))
            .limit(1)
        )
        provider = q.scalar_one_or_none()
        if provider:
            return provider
        # Fall back to any enabled provider.
        q2 = await self.db.execute(
            select(AIProviderSettings).where(AIProviderSettings.is_enabled.is_(True)).limit(1)
        )
        return q2.scalar_one_or_none()

    @staticmethod
    def _decrypt_key(provider: AIProviderSettings) -> Optional[str]:
        if not provider.api_key_encrypted:
            return None
        try:
            return b64_decrypt(provider.api_key_encrypted)
        except Exception:
            logger.warning("ai_key_decrypt_failed", provider_id=provider.id)
            return None

    # ---- prompt building --------------------------------------------
    def build_prompt(self, context: Dict[str, Any]) -> str:
        return (
            "You are an expert motor-insurance claims assessor. Analyze the "
            "attached vehicle photos together with the automated pipeline findings "
            "and produce a concise, professional assessment.\n\n"
            f"CLAIM CONTEXT:\n{json.dumps(context, indent=2, default=str)}\n\n"
            "Respond with a single JSON object using exactly these keys:\n"
            '{\n'
            '  "summary": "2-4 sentence narrative assessment",\n'
            '  "damage_assessment": "description of observed damage",\n'
            '  "consistency": "whether photos are consistent with the stated incident",\n'
            '  "recommended_action": "approve | manual_review | reject",\n'
            '  "confidence": 0.0\n'
            "}\n"
            "Only output the JSON object."
        )

    # ---- report generation ------------------------------------------
    async def generate_report(
        self,
        *,
        context: Dict[str, Any],
        images: List[bytes],
        provider: Optional[AIProviderSettings] = None,
    ) -> AIReportResult:
        provider = provider or await self.get_default_provider()
        prompt = self.build_prompt(context)

        if not provider:
            return self._local_report(context, prompt, reason="No AI provider configured")

        api_key = self._decrypt_key(provider)
        if not api_key and provider.provider != "custom":
            return self._local_report(
                context, prompt, reason=f"Provider '{provider.label}' has no API key set",
                provider=provider,
            )

        try:
            raw, usage = await self._call_provider(provider, api_key, prompt, images)
            report_json = self._parse(raw)
            return AIReportResult(
                status="generated",
                provider_id=provider.id,
                provider_name=provider.label,
                model=provider.model,
                summary=report_json.get("summary") or raw[:500],
                report_json=report_json,
                prompt=prompt,
                raw_response=raw,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )
        except Exception as exc:  # noqa: BLE001 — surface as an error report
            logger.warning("ai_report_failed", provider_id=provider.id, error=str(exc))
            fallback = self._local_report(
                context, prompt, reason=f"Provider call failed: {exc}", provider=provider
            )
            fallback.status = "error"
            fallback.error_message = str(exc)
            return fallback

    async def test_provider(self, provider: AIProviderSettings) -> ProviderTestResult:
        api_key = self._decrypt_key(provider)
        if not api_key and provider.provider != "custom":
            return ProviderTestResult(status="failure", message="No API key configured")
        started = time.perf_counter()
        try:
            raw, usage = await self._call_provider(
                provider, api_key,
                "Reply with the single word: OK",
                images=[],
            )
            latency = int((time.perf_counter() - started) * 1000)
            return ProviderTestResult(
                status="success",
                latency_ms=latency,
                message="Provider responded successfully",
                request_summary={"provider": provider.provider, "model": provider.model},
                response_summary={"text": raw[:200], "usage": usage},
            )
        except Exception as exc:  # noqa: BLE001
            latency = int((time.perf_counter() - started) * 1000)
            return ProviderTestResult(
                status="failure",
                latency_ms=latency,
                message=str(exc),
                request_summary={"provider": provider.provider, "model": provider.model},
            )

    # ---- provider transport -----------------------------------------
    async def _call_provider(
        self,
        provider: AIProviderSettings,
        api_key: Optional[str],
        prompt: str,
        images: List[bytes],
    ) -> tuple[str, Dict[str, Any]]:
        cfg = provider.config or {}
        timeout = float(cfg.get("timeout_seconds", 45))
        max_tokens = int(cfg.get("max_tokens", 1024))
        temperature = float(cfg.get("temperature", 0.2))
        img_b64 = [base64.b64encode(b).decode("ascii") for b in images[:6]]

        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider.provider == "anthropic":
                return await self._call_anthropic(
                    client, provider, api_key, prompt, img_b64, max_tokens, temperature
                )
            if provider.provider == "google":
                return await self._call_google(
                    client, provider, api_key, prompt, img_b64, max_tokens, temperature
                )
            # openai + custom (OpenAI-compatible)
            return await self._call_openai(
                client, provider, api_key, prompt, img_b64, max_tokens, temperature
            )

    async def _call_openai(self, client, provider, api_key, prompt, img_b64, max_tokens, temperature):
        base = (provider.base_url or "https://api.openai.com/v1").rstrip("/")
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for b in img_b64:
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}}
            )
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": provider.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        r = await client.post(f"{base}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }

    async def _call_anthropic(self, client, provider, api_key, prompt, img_b64, max_tokens, temperature):
        base = (provider.base_url or "https://api.anthropic.com/v1").rstrip("/")
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for b in img_b64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b},
            })
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": provider.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": content}],
        }
        r = await client.post(f"{base}/messages", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        text = "".join(part.get("text", "") for part in data.get("content", []))
        usage = data.get("usage", {})
        return text, {
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
        }

    async def _call_google(self, client, provider, api_key, prompt, img_b64, max_tokens, temperature):
        base = (provider.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        parts: List[Dict[str, Any]] = [{"text": prompt}]
        for b in img_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b}})
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
        url = f"{base}/models/{provider.model}:generateContent?key={api_key or ''}"
        r = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        r.raise_for_status()
        data = r.json()
        cand = (data.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        usage = data.get("usageMetadata", {})
        return text, {
            "prompt_tokens": usage.get("promptTokenCount"),
            "completion_tokens": usage.get("candidatesTokenCount"),
        }

    # ---- parsing + fallback -----------------------------------------
    def _parse(self, raw: str) -> Dict[str, Any]:
        match = _JSON_BLOCK_RE.search(raw or "")
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"summary": (raw or "").strip()[:1000], "parse_error": True}

    def _local_report(
        self,
        context: Dict[str, Any],
        prompt: str,
        *,
        reason: str,
        provider: Optional[AIProviderSettings] = None,
    ) -> AIReportResult:
        damage = context.get("damage", {})
        pricing = context.get("pricing", {})
        risk = context.get("risk", {})
        severity = damage.get("severity", "unknown")
        parts = ", ".join(damage.get("affected_parts", []) or []) or "no clearly identified parts"
        summary = (
            f"Automated assessment (no vision-LLM used): detected {severity} damage affecting "
            f"{parts}. Estimated repair cost {pricing.get('currency', 'INR')} "
            f"{pricing.get('grand_total', 0)}. Evidence risk is "
            f"{risk.get('risk_level', 'unknown')} ({risk.get('risk_score', 0)}/100)."
        )
        action = "manual_review"
        if risk.get("risk_level") in ("high", "critical"):
            action = "manual_review"
        elif severity in ("minor", "moderate"):
            action = "approve"
        report_json = {
            "summary": summary,
            "damage_assessment": damage.get("reason", ""),
            "consistency": "Not evaluated by a vision model.",
            "recommended_action": action,
            "confidence": damage.get("confidence", 0.0),
            "generated_locally": True,
            "reason": reason,
        }
        return AIReportResult(
            status="skipped",
            provider_id=provider.id if provider else None,
            provider_name=provider.label if provider else "local-fallback",
            model=provider.model if provider else "heuristic",
            summary=summary,
            report_json=report_json,
            prompt=prompt,
            error_message=reason,
        )
