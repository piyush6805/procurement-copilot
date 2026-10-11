"""One paid tool-call smoke check, tracked in the shared budget ledger."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.contracts import RunTelemetry
from src.provider import ModelClient,total_spend
from src.tools import TOOLS
tel=RunTelemetry(llm_calls=0)
try:
    response=ModelClient(tel).call([{"role":"system","content":"Call request_and_budget with empty arguments. Do not generate text."},{"role":"user","content":"Tool compatibility check."}],tools=TOOLS[:1])
    assert response.tool_calls and response.tool_calls[0].function.name=="request_and_budget"
    print(json.dumps({"status":"passed","tool_call":response.tool_calls[0].function.name,"cost_inr":tel.estimated_cost_inr,"ledger_inr":total_spend()}))
except Exception as exc:
    print(json.dumps({"status":"failed","error_type":type(exc).__name__,"ledger_inr":total_spend()}));sys.exit(1)
