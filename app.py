from __future__ import annotations
import hashlib, html, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import streamlit as st
from src.data_access import load_requests, load_employees
from src.solution import handle_custom_request
from src.provider import RUNTIME, total_spend, MODEL

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Procure | Request Copilot", page_icon="◈", layout="wide")
st.markdown('''<style>
.stApp {background:#f5f7fb;color:#14243a}
.block-container{padding-top:2rem;padding-bottom:2rem;max-width:1400px}
h1,h2,h3{letter-spacing:-.035em;color:#14243a}
[data-testid="stSidebar"]{background:#13263c}
[data-testid="stSidebar"] *{color:#e4ebf4}
[data-testid="stMetric"]{background:white;border:1px solid #e1e7f0;border-radius:12px;padding:16px}
[data-testid="stMetricValue"],[data-testid="stMetricLabel"]{color:#14243a!important}
[data-testid="stMetricValue"]{font-size:1.35rem!important;white-space:normal!important;overflow:visible!important}
[data-testid="stSidebar"] [data-testid="stMetric"]{background:#203b58;border-color:#344e67}
[data-testid="stSidebar"] [data-testid="stMetricValue"],[data-testid="stSidebar"] [data-testid="stMetricLabel"]{color:#e4ebf4!important}
.hero{background:#142b43;border-radius:18px;padding:28px 32px;color:white;margin-bottom:24px}
.hero h1{color:white;font-size:34px;margin:6px 0}.hero p{color:#c4d2e1;margin:0}
.eyebrow{color:#58d4c3;font-size:12px;font-weight:700;letter-spacing:2px}
.card{background:white;border:1px solid #dfe6ef;border-radius:14px;padding:22px;margin-bottom:16px}
.card p{margin:5px 0;color:#576780}.card h3{font-size:22px;margin:2px 0 14px}
.pill{display:inline-block;background:#e6f5f1;color:#146b5e;border-radius:20px;padding:5px 11px;font-size:12px;margin:3px}
.evidence{border-left:3px solid #21a58e;background:white;padding:12px 16px;margin:10px 0;border-radius:0 8px 8px 0}
.evidence small{color:#677a93}.evidence p{margin:6px 0}
</style>''', unsafe_allow_html=True)
escape = lambda x: html.escape(str(x))
requests = load_requests(); by_id = {r['request_id']:r for r in requests}
employees = load_employees(); employee_ids = employees['employee_id'].tolist()
with st.sidebar:
    st.markdown("## ◈ Procure")
    st.caption("REQUEST INTELLIGENCE")
    mode = st.radio("Workspace", ["Sample requests", "New request"])
    architecture = st.radio("Analysis architecture", ["single", "staged"], format_func=lambda x: "Single agent" if x=='single' else "Analyst + reviewer")
    st.divider()
    st.caption("Policy 2026.09 · Snapshot 30 Sep 2026")
    st.caption("Synthetic assessment data")
    st.metric("Tracked API spend", f"₹{total_spend():.3f}", "₹20 maximum", delta_color="off")
    st.caption(MODEL)

st.markdown('<div class="hero"><div class="eyebrow">PROCUREMENT REQUEST COPILOT</div><h1>Every next step, backed by evidence.</h1><p>Understand the need. Verify the facts. Keep approval with people.</p></div>', unsafe_allow_html=True)
if mode == 'Sample requests':
    rid = st.selectbox("Purchase request", list(by_id), format_func=lambda x:f"{x} · {by_id[x]['product_name']}")
    req = dict(by_id[rid])
else:
    with st.expander("Request details", expanded=True):
        a,b = st.columns(2)
        with a:
            requester = st.selectbox("Requester", employee_ids, format_func=lambda x:f"{x} · {employees.loc[employees.employee_id==x,'name'].iloc[0]}")
            product = st.text_input("Product or service")
            vendor = st.text_input("Vendor")
            category = st.text_input("Category", placeholder="e.g. Project Management")
        with b:
            cost = st.number_input("Annual cost (USD)", min_value=0.0, step=100.0)
            cost_known = st.checkbox("Annual estimate confirmed", value=True)
            users = st.number_input("Number of users/licenses", min_value=1, value=1, step=1)
            level = st.selectbox("Data access", ['unknown','none','internal_documents','internal_marketing','confidential_documents','source_code','employee_pii','customer_pii','credentials','production_telemetry'])
            integrations = st.text_input("Integrations (comma separated; leave empty for none)")
        purpose = st.text_area("Business purpose and gap in existing tools", placeholder="What outcome do you need? Why do existing tools fall short?")
        req = {'request_id':'CUSTOM-'+hashlib.sha256((product+vendor+requester).encode()).hexdigest()[:8].upper(),'requester_id':requester,'product_name':product,'vendor_name':vendor,'category':category,'annual_cost_usd':cost if cost_known else None,'user_count':users,'business_justification':purpose,'data_access_level':level,'requested_integrations':[x.strip() for x in integrations.split(',') if x.strip()],'urgency':'normal'}

fingerprint = hashlib.sha256(json.dumps({'request':req,'architecture':architecture},sort_keys=True).encode()).hexdigest()
if st.session_state.get('fingerprint') != fingerprint:
    st.session_state.pop('decision',None)
    st.session_state['fingerprint'] = fingerprint
employee = employees.loc[employees.employee_id==req.get('requester_id')]
department = employee.iloc[0]['department'] if not employee.empty else 'Unverified'
a,b,c,d = st.columns(4)
a.metric('Department',department)
b.metric('Annual request', f"${req['annual_cost_usd']:,.0f}" if req.get('annual_cost_usd') is not None else 'Unknown')
c.metric('Users / licenses',req.get('user_count') or 'Unknown')
d.metric('Data access',str(req.get('data_access_level','unknown')).replace('_',' ').title().replace('Pii','PII'))
st.write('')
left,right = st.columns([1,1.5],gap='large')
with left:
    st.markdown(f'<div class="card"><div class="eyebrow">THE REQUEST</div><h3>{escape(req.get("product_name") or "New purchase request")}</h3><p><b>Vendor</b> · {escape(req.get("vendor_name") or "Unknown")}</p><p>{escape(req.get("business_justification") or "Business purpose not yet provided.")}</p><p><b>Integrations</b> · {escape(", ".join(req.get("requested_integrations") or []) or "None requested")}</p></div>',unsafe_allow_html=True)
    if st.button('Analyze request →',type='primary',use_container_width=True):
        with st.spinner('Gathering evidence and checking procurement policy…'):
            try: st.session_state['decision'] = handle_custom_request(req,architecture).model_dump()
            except Exception as exc: st.error(f'Analysis could not complete: {type(exc).__name__}. Verify local data and service configuration.')
    st.caption('Recommendations are advisory. No purchase or approval is performed.')
    with st.expander('Inspect request fields'): st.json(req)

with right:
    result = st.session_state.get('decision')
    if not result:
        st.markdown('<div class="card"><div class="eyebrow">NEXT ACTION</div><h3>Ready when you are.</h3><p>Run analysis to compare the request with budget, existing tools, vendor evidence and procurement policy.</p><p>The evidence packet will show required reviews and anything still unverified.</p></div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="card"><div class="eyebrow">RECOMMENDATION</div><h3>{escape(result["recommendation"])}</h3><p>{escape(result["next_step"])}</p>'+''.join(f'<span class="pill">{escape(x)}</span>' for x in result['required_approvals'])+'</div>',unsafe_allow_html=True)
        if not result['telemetry']['live_success']: st.warning('Degraded analysis: '+str(result['telemetry']['degraded_reason'])+'. Manual review required; this is not a successful live-agent run.')
        analysis,handoff,trace = st.tabs(['Evidence & risks','Human handoff','Run details'])
        with analysis:
            if result['missing_information']:
                st.error('Needs clarification: '+'; '.join(result['missing_information']))
            if result['risk_flags']: st.caption('RISK FLAGS · '+' · '.join(x.replace('_',' ') for x in result['risk_flags']))
            for source in dict.fromkeys(x['source'] for x in result['evidence']):
                with st.expander(source.replace('_',' ').title(),expanded=True):
                    for item in result['evidence']:
                        if item['source']==source:
                            st.markdown(f'<div class="evidence"><p>{escape(item["finding"])}</p><small>{escape(item["reference"])}</small></div>',unsafe_allow_html=True)
        with handoff:
            st.info('Local review demonstration. Reviewer identity is self-reported; this does not constitute authenticated enterprise approval.')
            run_id=result['telemetry']['run_id']
            packet_path=RUNTIME/'runs'/f'{run_id}.json'
            packet=packet_path.read_text(encoding='utf-8')
            st.download_button('Download full evidence packet',packet,file_name=f'review-{req["request_id"]}.json',mime='application/json')
            with st.form('handoff'):
                reviewer=st.text_input('Reviewer name')
                action=st.selectbox('Handoff action',['Route for review','Request clarification','Return with reviewer notes'])
                notes=st.text_area('Reviewer notes')
                if st.form_submit_button('Record handoff'):
                    if not reviewer.strip(): st.error('Enter a reviewer name to record the handoff.')
                    else:
                        event={'run_id':run_id,'request_id':req['request_id'],'reviewer':reviewer.strip(),'action':action,'notes':notes,'timestamp':datetime.now(timezone.utc).isoformat(),'authority':'local_demo_only'}
                        RUNTIME.mkdir(exist_ok=True)
                        with (RUNTIME/'handoffs.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
                        st.success('Handoff recorded locally. Required approvals remain outstanding.')
        with trace:
            t=result['telemetry']; x,y,z=st.columns(3)
            x.metric('LLM calls',t['llm_calls']);y.metric('Tools executed',t['tool_calls']);z.metric('Latency',f"{t['latency_ms']/1000:.1f}s")
            st.caption(f"Input/output tokens: {t['input_tokens']} / {t['output_tokens']} · Estimated run cost ₹{t['estimated_cost_inr']:.4f}")
            st.json(t)
            with st.expander('Validated output'): st.json(result)
st.divider()
st.caption('AI interprets the need · Code enforces policy · Humans own sensitive reviews and final approval')
