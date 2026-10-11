"""Read-only business tools and the deterministic policy boundary."""
from __future__ import annotations
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from src import data_access as data
from src.vendor_client import get_vendor_risk

REFERENCE_DATE = date(2026, 9, 30)
POLICY_VERSION = "2026.09"
APPROVAL_ORDER = ["Manager", "Department Head", "Finance", "CFO", "Procurement", "Security", "Privacy", "Legal"]
INJECTION = re.compile(r"ignore\s+(?:all\s+)?(?:previous|procurement|system|the|policy)|CFO.approved|approve\s+(?:it\s+)?immediately|bypass|reveal.*(?:secret|key)|fabricate.*approval|override.*(?:policy|rules)", re.I)

def records(frame):
    return frame.astype(object).where(frame.notna(), None).to_dict("records")

def financial_approvals(cost):
    if cost is None: return []
    cost = Decimal(str(cost))
    if cost <= 1000: return ["Manager"]
    if cost <= 10000: return ["Department Head", "Procurement"]
    if cost <= 25000: return ["Department Head", "Finance", "Procurement"]
    return ["Department Head", "Finance", "CFO", "Procurement"]

def review_expired(value):
    if not value: return True
    try:
        age = (REFERENCE_DATE - date.fromisoformat(str(value))).days
        return age < 0 or age > 365
    except ValueError: return True

class ToolContext:
    def __init__(self, request):
        self.request = dict(request)
        self.results = {}
        self.evidence = []
        self.flags = set()
        self.approvals = set()
        self.missing = []
        self.calls = []
        self.trace = []

    def add(self, source, finding, reference):
        item = {"source": source, "finding": finding, "reference": reference}
        if item not in self.evidence: self.evidence.append(item)

    def execute(self, name):
        if name not in TOOL_NAMES: raise ValueError("Unknown tool")
        if name in self.results: return self.results[name]
        if name == "policy_checks":
            for dependency in TOOL_NAMES[:-1]: self.execute(dependency)
        self.calls.append(name)
        result = getattr(self, name)()
        self.results[name] = result
        self.trace.append({"tool": name, "result": result, "evidence": list(self.evidence)})
        return result

    def request_and_budget(self):
        r = self.request
        employees = records(data.load_employees())
        employee = next((x for x in employees if x["employee_id"] == r.get("requester_id")), None)
        if not employee: self.missing.append("Valid requester and department")
        department = employee["department"] if employee else None
        budget = next((x for x in records(data.load_budgets()) if x["department"] == department), None)
        if employee:
            self.add("request_and_budget", f"Requester {employee['name']} belongs to {department}; manager ID {employee['manager_id']}.", f"employees.csv:{employee['employee_id']}")
        if not budget: self.missing.append("Verified department budget")
        for key, label in [("product_name", "Product"), ("vendor_name", "Vendor"), ("business_justification", "Business purpose")]:
            if not str(r.get(key) or "").strip(): self.missing.append(label)
        cost = None
        try:
            raw = r.get("annual_cost_usd")
            if raw is None or isinstance(raw, bool): raise ValueError()
            amount = Decimal(str(raw))
            if not amount.is_finite() or amount < 0: raise ValueError()
            cost = float(amount)
        except (InvalidOperation, ValueError, TypeError): self.missing.append("Valid annual cost estimate")
        seats = r.get("user_count")
        if isinstance(seats, bool) or not isinstance(seats, int) or seats <= 0: self.missing.append("Positive number of users/licenses")
        level = str(r.get("data_access_level") or "").strip().lower()
        allowed_levels = {"none", "internal_documents", "internal_marketing", "confidential_documents", "source_code", "employee_pii", "customer_pii", "credentials", "secrets", "production_telemetry", "cloud_account"}
        if level not in allowed_levels: self.missing.append("Intended data access level")
        if not isinstance(r.get("requested_integrations"), list) or any(not isinstance(x,str) for x in (r.get("requested_integrations") or [])): self.missing.append("Required integrations (an empty list means none)")
        if cost is not None and budget:
            available = float(budget["available_usd"])
            shortfall = max(0, cost - available)
            self.add("request_and_budget", f"Annual cost ${cost:,.2f}; available {department} software budget ${available:,.2f}; shortfall ${shortfall:,.2f}.", f"department_budgets.csv:{department}")
            if shortfall: self.flags.add("budget_insufficient"); self.approvals.add("Finance")
        self.add("request_and_budget", "Missing required information: " + (", ".join(self.missing) or "none"), f"request:{r.get('request_id')}")
        return {"verified": employee is not None and budget is not None, "department": department, "annual_cost_usd": cost, "missing_information": list(self.missing)}

    def software_and_history(self):
        r = self.request
        def same(a,b): return bool(a and b) and str(a).casefold() == str(b).casefold()
        matches = [x for x in records(data.load_software_catalog()) if same(x["category"], r.get("category")) or same(x["vendor_name"], r.get("vendor_name")) or same(x["product_name"], r.get("product_name"))]
        history = [x for x in records(data.load_purchase_history()) if same(x["vendor_name"], r.get("vendor_name"))]
        if matches: self.flags.add("existing_tool_overlap")
        for x in matches:
            self.add("software_and_history", f"Existing option {x['product_name']}: {x['status']}, scope {x['scope']}, {x['licensed_seats']} licensed seats. Notes: {x['notes']}. Utilization is unknown.", f"software_catalog.csv:{x['software_id']}")
        if not matches: self.add("software_and_history", "No same-product, vendor, or category match found in the supplied catalog; this is not proof that no functional alternative exists.", "software_catalog.csv:search")
        for x in history:
            self.add("software_and_history", f"Prior purchase {x['product_name']} by {x['department']}, ${x['annual_amount_usd']:,.2f}; {x['status']}. Prior purchase does not authorize this use case.", f"purchase_history.csv:{x['purchase_id']}")
        functional = any(same(x["category"],r.get("category")) or same(x["product_name"],r.get("product_name")) for x in matches)
        return {"verified": True, "catalog_matches": matches, "functional_overlap": functional, "purchase_history": history, "capacity_available": "unknown"}

    def vendor_evidence(self):
        name = self.request.get("vendor_name") or ""
        registry = next((x for x in records(data.load_vendors()) if str(x["vendor_name"]).casefold() == str(name).casefold()), None)
        if registry: name = registry["vendor_name"]
        if registry:
            self.add("vendor_evidence", f"Internal registry: procurement {registry['procurement_status']}; security {registry['security_status']}, reviewed {registry['security_review_date']}; legal terms {registry['legal_terms_status']}.", f"vendors.csv:{registry['vendor_id']}")
        else: self.add("vendor_evidence", "Vendor absent from internal registry; onboarding and legal terms are unverified.", "vendors.csv:search")
        try:
            risk = get_vendor_risk(name)
            if not isinstance(risk, dict) or not risk.get("security_review_status"): raise ValueError("Incomplete vendor-risk response")
            self.add("vendor_evidence", f"Risk service: risk {risk.get('risk_level', 'unknown')}; security {risk['security_review_status']}, reviewed {risk.get('last_review_date')}; outside-region storage {risk.get('stores_data_outside_region', 'unknown')}.", f"/vendor-risk/{name}")
            verified = True
        except Exception as exc:
            risk = None; verified = False
            self.flags.add("vendor_risk_unavailable")
            self.add("vendor_evidence", f"Vendor-risk status could not be verified ({type(exc).__name__}); no favorable status inferred.", f"/vendor-risk/{name}")
        return {"verified": verified, "registry": registry, "risk": risk}

    def policy_checks(self):
        r = self.request; b = self.results["request_and_budget"]; v = self.results["vendor_evidence"]
        registry, risk = v["registry"], v["risk"]
        self.approvals.update(financial_approvals(b["annual_cost_usd"]))
        level = str(r.get("data_access_level") or "").lower()
        raw_integrations = r.get("requested_integrations")
        integration = " ".join(str(x).lower() for x in raw_integrations) if isinstance(raw_integrations,list) else ""
        sensitive = any(x in level for x in ["source_code", "confidential", "pii", "credential", "secret", "production", "cloud"])
        sensitive = sensitive or any(x in integration for x in ["production", "cloud account", "source code", "git repositor"])
        purpose = str(r.get("business_justification") or "").lower()
        explicit_sensitive = any(x in purpose for x in ["source code", "confidential documents", "customer pii", "employee pii", "credentials", "secrets"])
        sensitive = sensitive or explicit_sensitive
        pii = "pii" in level or "customer pii" in purpose or "employee pii" in purpose
        expired = bool(registry and review_expired(registry.get("security_review_date"))) or bool(risk and review_expired(risk.get("last_review_date")))
        conflict = bool(registry and risk and str(registry["security_status"]).lower() != str(risk["security_review_status"]).lower())
        assessment_missing = not registry or not risk or str(registry.get("security_status", "")).lower() != "approved" or str((risk or {}).get("security_review_status", "")).lower() != "approved"
        if expired: self.flags.add("vendor_review_expired")
        if conflict: self.flags.add("conflicting_vendor_evidence")
        if sensitive or expired or conflict or assessment_missing: self.flags.add("security_review_required"); self.approvals.add("Security")
        outside = bool(risk and risk.get("stores_data_outside_region"))
        privacy = pii or (sensitive and outside)
        if privacy: self.flags.add("privacy_review_required"); self.approvals.add("Privacy")
        new = not registry or str(registry.get("procurement_status")).lower() != "approved"
        legal = not registry or str(registry.get("legal_terms_status", "")).lower() not in ["approved", "standard"] or (new and b["annual_cost_usd"] is not None and b["annual_cost_usd"] >= 10000) or (sensitive and outside)
        if legal: self.flags.add("legal_review_required"); self.approvals.add("Legal")
        business_data = {"request": r, "catalog": self.results["software_and_history"], "vendor": v}
        if INJECTION.search(str(business_data)): self.flags.add("prompt_injection_detected")
        if self.missing: self.flags.add("missing_information")
        ordered = [x for x in APPROVAL_ORDER if x in self.approvals]
        self.add("policy_checks", f"Annual amount requires {', '.join(financial_approvals(b['annual_cost_usd'])) or 'cost clarification before threshold routing'}; complete review routing: {', '.join(ordered) or 'clarification first'}. Reference date {REFERENCE_DATE}; policy {POLICY_VERSION}.", "procurement_policy.md:sections-1-11")
        if expired or conflict: self.add("policy_checks", f"Vendor evidence: expired/missing date={expired}; internal/external security conflict={conflict}. Security must resolve before approval.", "procurement_policy.md:section-5")
        return {"verified": True, "policy_version": POLICY_VERSION, "reference_date": str(REFERENCE_DATE), "required_approvals": ordered, "risk_flags": sorted(self.flags), "missing_information": list(dict.fromkeys(self.missing)), "policy": data.load_policy_text()}

TOOL_NAMES = ["request_and_budget", "software_and_history", "vendor_evidence", "policy_checks"]
TOOLS = [{"type": "function", "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True}} for name, desc in zip(TOOL_NAMES, ["Resolve requester and validate request; compare available department budget.", "Retrieve approved alternatives and previous purchases; seats do not prove availability.", "Retrieve internal vendor registry and external mock risk API.", "Apply deterministic policy checks and retrieve authoritative policy sections; depends on the other tools."])]
