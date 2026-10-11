from types import SimpleNamespace
import pytest
from src.contracts import RunTelemetry
from src import provider

class FakeCompletions:
    def create(self,**kwargs):
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100,completion_tokens=20),choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}'))])

@pytest.fixture
def isolated(monkeypatch,tmp_path):
    monkeypatch.setattr(provider,'RUNTIME',tmp_path)
    monkeypatch.setattr(provider,'prices',lambda:{'input':0.00005,'output':0.0002})
    monkeypatch.setattr(provider,'OpenAI',lambda **kwargs:SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions())))
    return tmp_path

def test_ledger_reserves_and_settles_actual_usage(isolated):
    t=RunTelemetry();provider.ModelClient(t).call([{'role':'user','content':'JSON'}])
    assert provider.total_spend()==pytest.approx(.009)
    assert t.llm_calls==1;assert t.input_tokens==100;assert t.output_tokens==20

def test_cap_is_checked_before_paid_call(isolated,monkeypatch):
    monkeypatch.setenv('MAX_SPEND_INR','0.01');t=RunTelemetry()
    with pytest.raises(provider.BudgetExceeded):provider.ModelClient(t).call([{'role':'user','content':'JSON'}])
    assert not t.llm_calls;assert provider.total_spend()==0

def test_provider_failure_retains_reservation(isolated,monkeypatch):
    def fail(**kwargs):raise TimeoutError()
    monkeypatch.setattr(FakeCompletions,'create',lambda self,**kwargs:fail())
    t=RunTelemetry()
    with pytest.raises(TimeoutError):provider.ModelClient(t).call([{'role':'user','content':'JSON'}])
    assert provider.total_spend()>.009

def test_concurrent_reservation_cannot_oversubscribe(isolated,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setenv('MAX_SPEND_INR','0.30')
    with provider.database() as conn:conn.execute('INSERT INTO charges VALUES (?,?,?,?)',('pending',.29,'reserved','now'))
    def reserve():
        try:provider.ModelClient(RunTelemetry()).call([{'role':'user','content':'JSON'}]);return True
        except provider.BudgetExceeded:return False
    with ThreadPoolExecutor(2) as pool:assert list(pool.map(lambda _:reserve(),range(2)))==[False,False]
    assert provider.total_spend()==pytest.approx(.29)
