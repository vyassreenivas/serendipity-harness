"""The one place where the harness calls an AI model.

Every call is saved in full: the exact instructions and input sent, the model
name and settings, the complete reply, and the token counts. A saved call is
reused when the identical request is made again, so a run can be replayed
without the model and without further cost.

No fallback model is configured: if the model declines a request, the decline
is recorded and the item is left unprocessed, so every output is known to
come from the model named in the run setup.
"""
import hashlib
import json
import urllib.request

from pydantic import ValidationError

from .runlog import HARNESS, Run

CACHE = HARNESS / "cache"
OLLAMA = "http://localhost:11434"


def ollama(cfg: dict, system: str, user: str, schema, max_tokens: int) -> dict:
    """Call a model through Ollama. A model whose name ends in "cloud" runs on Ollama's
    servers, so the text sent to it leaves this computer. That is refused unless the
    run setup allows it for that model with text_may_leave_this_machine = true."""
    if "cloud" in cfg["model"] and not cfg.get("text_may_leave_this_machine"):
        raise SystemExit(f"{cfg['model']} runs on Ollama's servers, not this machine. "
                         "Interview text stays local unless the run setup sets "
                         "text_may_leave_this_machine = true for this model.")
    tags = json.load(urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=30))["models"]
    digest = next((m["digest"] for m in tags if m["name"] == cfg["model"]), None)
    if digest is None:
        raise SystemExit(f"Ollama has no model named {cfg['model']}")
    body = {"model": cfg["model"], "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0, "seed": cfg.get("seed", 0),
                        "num_ctx": cfg["context_tokens"], "num_predict": max_tokens}}
    if schema:
        body["format"] = schema.model_json_schema()
    request = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    reply = json.load(urllib.request.urlopen(request, timeout=1800))
    used = reply.get("prompt_eval_count", 0) + reply.get("eval_count", 0)
    # Ollama drops the start of a prompt that does not fit, without an error.
    stop = ("context_overflow" if used >= cfg["context_tokens"]
            else "end_turn" if reply.get("done_reason") == "stop"
            else reply.get("done_reason") or "unknown")
    return {"id": None, "model": f"{cfg['model']}@{digest[:12]}", "stop_reason": stop,
            "text": reply["message"]["content"],
            "usage": {"input_tokens": reply.get("prompt_eval_count", 0),
                      "output_tokens": reply.get("eval_count", 0),
                      "seconds": round(reply.get("total_duration", 0) / 1e9, 1)}}


def anthropic_api(cfg: dict, system: str, user: str, schema, max_tokens: int,
                  cache_system: bool) -> dict:
    import anthropic

    # Instructions repeated across many calls are billed at a reduced rate
    # after the first call. This changes the cost, not what the model sees.
    system_param = ([{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
                    if cache_system else system)
    kwargs = dict(model=cfg["model"], max_tokens=max_tokens, system=system_param,
                  messages=[{"role": "user", "content": user}],
                  output_config={"effort": cfg["effort"]})
    # A long reply can take many minutes. Without an explicit limit the library
    # refuses large requests unless they are streamed.
    client = anthropic.Anthropic(timeout=1800)
    if schema:
        try:
            response = client.messages.parse(output_format=schema, **kwargs)
        except ValidationError:
            # The reply stopped before it was complete, usually because it ran out
            # of its reply allowance. It is reported as incomplete, not used.
            return {"id": None, "model": cfg["model"], "stop_reason": "incomplete_reply",
                    "text": "", "usage": {}}
    else:
        response = client.messages.create(**kwargs)
    return {"id": response.id, "model": response.model, "stop_reason": response.stop_reason,
            "text": "".join(b.text for b in response.content if b.type == "text"),
            "usage": response.usage.to_dict()}


def call(run: Run, stage: str, key: str, *, system: str, user: str, schema=None,
         max_tokens: int = 16000, cache_system: bool = False) -> dict:
    cfg = run.config()["models"][stage]
    local = cfg.get("provider") == "ollama"
    # A model that reasons before it answers spends reply tokens on the reasoning,
    # so the run setup can give it a larger reply allowance.
    max_tokens = cfg.get("max_tokens", max_tokens)
    request = {"provider": cfg.get("provider", "anthropic"), "model": cfg["model"],
               "settings": {k: v for k, v in cfg.items() if k not in ("provider", "model")},
               "max_tokens": max_tokens, "system": system, "user": user,
               "schema": schema.model_json_schema() if schema else None}
    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    cached = CACHE / f"{digest}.json"

    if cached.exists():
        record = json.loads(cached.read_text(encoding="utf-8"))
        reused = True
    else:
        if local:
            response, cost = ollama(cfg, system, user, schema, max_tokens), 0.0
        else:
            response = anthropic_api(cfg, system, user, schema, max_tokens, cache_system)
            usage = response["usage"]
            price = run.config()["prices_usd_per_million_tokens"][cfg["model"]]
            cost = (usage.get("input_tokens", 0) * price["input"]
                    + (usage.get("cache_creation_input_tokens") or 0) * price["input"] * 1.25
                    + (usage.get("cache_read_input_tokens") or 0) * price["input"] * 0.1
                    + usage.get("output_tokens", 0) * price["output"]) / 1e6
        record = {"request_sha256": digest, "request": request, "response": response,
                  "cost_usd": round(cost, 4)}
        if response["stop_reason"] == "end_turn":  # keep only complete replies for reuse
            CACHE.mkdir(exist_ok=True)
            cached.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        reused = False

    run.write_json(f"calls/{stage}/{key}.json", record)
    run.log("model_call", stage=stage, key=key, model=record["response"]["model"],
            settings=request["settings"], request_sha256=digest, reused=reused,
            stop_reason=record["response"]["stop_reason"],
            input_tokens=record["response"]["usage"].get("input_tokens"),
            output_tokens=record["response"]["usage"].get("output_tokens"),
            cost_usd=0.0 if reused else record["cost_usd"])
    return record
