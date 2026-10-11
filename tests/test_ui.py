import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from src.data_access import get_request
from src.solution import handle_custom_request
from tests.test_solution import FakeClient

def test_ui_analysis_persists_and_request_change_invalidates(monkeypatch):
    def mock_analyze(request,architecture):
        return handle_custom_request(request,architecture,client_factory=FakeClient)
    monkeypatch.setattr('src.solution.handle_custom_request',mock_analyze)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=20)
    assert not app.exception
    next(b for b in app.button if b.label=='Analyze request →').click().run(timeout=20)
    assert 'decision' in app.session_state
    app.run(timeout=20)
    assert 'decision' in app.session_state
    app.selectbox[0].select('REQ-1005').run(timeout=20)
    assert 'decision' not in app.session_state
    assert not app.exception

def test_new_request_form(monkeypatch):
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=20)
    app.radio[0].set_value('New request').run(timeout=20)
    assert any(x.label=='Business purpose and gap in existing tools' for x in app.text_area)
    assert not app.exception
