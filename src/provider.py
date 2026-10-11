"""Bounded model calls with a durable shared INR spend ledger."""
from __future__ import annotations
import json, os, sqlite3, uuid
from pathlib import Path
from datetime import datetime, timezone
import requests
import tiktoken
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
MODEL = os.getenv("MODEL_NAME", "openai/gpt-4.1-mini")
class BudgetExceeded(RuntimeError): pass

def database():
    RUNTIME.mkdir(exist_ok=True)
    conn = sqlite3.connect(RUNTIME / "spend.sqlite3", timeout=15)
    conn.execute("CREATE TABLE IF NOT EXISTS charges (id TEXT PRIMARY KEY, amount REAL NOT NULL, state TEXT, created TEXT)")
    conn.commit()
    return conn

def total_spend():
    with database() as conn: return float(conn.execute("SELECT COALESCE(SUM(amount),0) FROM charges").fetchone()[0])

def prices():
    cache = RUNTIME / "pricing.json"
    RUNTIME.mkdir(exist_ok=True)
    if cache.exists():
        payload = json.loads(cache.read_text())
        if payload.get("model") == MODEL: return payload
    response = requests.get("https://api.aicredits.in/api/models", timeout=8)
    response.raise_for_status()
    model = next(x for x in response.json()["data"] if x["id"] == MODEL)
    payload = {"model": MODEL, "input": model["input_cost_per_token_inr"], "output": model["output_cost_per_token_inr"], "fetched_at": datetime.now(timezone.utc).isoformat()}
    if payload["input"] <= 0 or payload["output"] <= 0: raise ValueError("Invalid model pricing")
    cache.write_text(json.dumps(payload, indent=2))
    return payload

class ModelClient:
    def __init__(self, telemetry):
        self.telemetry = telemetry
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "missing"), base_url=os.getenv("OPENAI_BASE_URL", "https://api.aicredits.in/v1"), timeout=35, max_retries=0)

    def call(self, messages, tools=None):
        rate = prices()
        encoded = json.dumps({"messages": messages, "tools": tools}, ensure_ascii=False)
        if len(encoded) > 80000: raise ValueError("Input exceeds bounded context size")
        tokens = len(tiktoken.get_encoding("cl100k_base").encode(encoded)) + 512
        reserved = tokens * rate["input"] + 1000 * rate["output"]
        charge_id = str(uuid.uuid4())
        cap = min(20.0, float(os.getenv("MAX_SPEND_INR", "20")))
        with database() as conn:
            conn.execute("BEGIN IMMEDIATE")
            spent = conn.execute("SELECT COALESCE(SUM(amount),0) FROM charges").fetchone()[0]
            if spent + reserved > cap: raise BudgetExceeded("INR budget cannot safely reserve another model call")
            conn.execute("INSERT INTO charges VALUES (?,?,?,?)", (charge_id, reserved, "reserved", datetime.now(timezone.utc).isoformat()))
        self.telemetry.llm_calls = (self.telemetry.llm_calls or 0) + 1
        kwargs = {"model": MODEL, "messages": messages, "temperature": 0, "max_tokens": 1000, "extra_body": {"no_cache": True}}
        if tools: kwargs.update(tools=tools, tool_choice="required", parallel_tool_calls=True)
        else: kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self.client.chat.completions.create(**kwargs)
            if not response.usage: raise ValueError("Missing provider usage; reservation retained")
            usage = response.usage
            actual = usage.prompt_tokens * rate["input"] + usage.completion_tokens * rate["output"]
            with database() as conn: conn.execute("UPDATE charges SET amount=?, state='settled' WHERE id=?", (actual, charge_id))
            self.telemetry.input_tokens += usage.prompt_tokens
            self.telemetry.output_tokens += usage.completion_tokens
            self.telemetry.estimated_cost_inr += actual
            choice = response.choices[0]
            if choice.finish_reason == "length": raise ValueError("Model response truncated")
            return choice.message
        except Exception:
            with database() as conn: conn.execute("UPDATE charges SET state='uncertain' WHERE id=? AND state='reserved'", (charge_id,))
            raise
