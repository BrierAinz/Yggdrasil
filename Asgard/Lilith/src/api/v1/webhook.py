import hashlib
import hmac
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_config():
    from src.core.json_safe import safe_load

    root = _project_root()
    rules = safe_load(root / "Config" / "webhook_rules.json", default=[])
    secrets = safe_load(root / "Config" / "webhook_secrets.json", default={})
    return rules, secrets


def _verify_github(body: bytes, secret: str, sig_header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header or "")


def _match_rule(rules, source, event, payload):
    for rule in rules:
        if rule.get("source") != source:
            continue
        if rule.get("event") not in ("*", event):
            continue
        filt = (rule.get("filter") or "").strip()
        if filt:
            # Evaluación simple: "branch == main"
            try:
                key, _, val = filt.partition(" == ")
                if payload.get(key.strip()) != val.strip():
                    continue
            except Exception:
                pass
        return rule
    return None


@router.post("/ingest")
async def webhook_ingest(request: Request) -> Response:
    body = await request.body()
    source = request.headers.get("X-Webhook-Source", "custom").lower()
    event = request.headers.get(
        "X-GitHub-Event", request.headers.get("X-Webhook-Event", "push")
    ).lower()

    rules, secrets = _load_config()

    # Verificar firma si hay secret configurado
    secret = (secrets or {}).get(source, "")
    if secret:
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_github(body, secret, sig):
            raise HTTPException(status_code=403, detail="Firma inválida")

    try:
        payload = json.loads(body)
    except Exception:
        payload = {}

    rule = _match_rule(rules or [], source, event, payload or {})
    if not rule:
        return Response(
            content='{"status":"no_rule_matched"}', media_type="application/json"
        )

    action = rule.get("action", "notify_discord")
    result = await _dispatch(action, rule, payload, source, event)
    return Response(
        content=json.dumps({"status": "ok", "action": action, "result": result}),
        media_type="application/json",
    )


async def _dispatch(action, rule, payload, source, event):
    import asyncio

    if action == "notify_discord":
        try:
            from src.core.transport.discord import notify_owner

            msg_tpl = rule.get("message", "Webhook recibido: {source}/{event}")
            # Interpolación simple con payload plano
            flat = {"source": source, "event": event}
            for k, v in (payload or {}).items():
                if isinstance(v, str):
                    flat[k] = v
            msg = msg_tpl.format_map(flat)
            channel_id = rule.get("channel_id")
            await notify_owner(_project_root(), msg, channel_id=channel_id)
            return "notified"
        except Exception as e:
            return f"notify_error: {e}"

    if action == "run_plan":
        try:
            from src.api.dependencies import get_orchestrator

            query = rule.get("query", f"Webhook {source}/{event}: analiza y resume")
            orch = get_orchestrator()
            result = await asyncio.to_thread(
                orch.execute_plan, query, context="", user_id="webhook"
            )
            return str(result)[:200]
        except Exception as e:
            return f"plan_error: {e}"

    if action == "store_fact":
        try:
            from src.core.tools.builtin.memory_tools import StoreSemanticFactTool

            fact = (rule.get("fact_template", "Webhook {source}/{event}") or "").format(
                source=source, event=event
            )
            StoreSemanticFactTool().execute({"fact": fact})
            return "stored"
        except Exception as e:
            return f"store_error: {e}"

    return "unknown_action"
