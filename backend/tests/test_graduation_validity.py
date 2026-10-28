"""C-route HTTP tests; synthetic data and injected provider, not Gemini live."""
from copy import deepcopy
from hashlib import sha256
import json
import sqlite3
import pytest
from app import create_app
from app.db import init_db
from app.graduation_explanation_core import valid_draft
from app.graduation_validity import source_digest
from app.planner_core import dump

@pytest.fixture
def setup_app(tmp_path):
    now = [1000.0]
    app = create_app({"TESTING": True, "SECRET_KEY": "synthetic-test-only", "DATABASE": str(tmp_path / "db.sqlite3"),
                      "GRADUATION_CLOCK": lambda: now[0], "GRADUATION_ENGINE": "langgraph",
                      "GRADUATION_EXPLANATION_PROVIDER": lambda c,p,f: (valid_draft(c), {"provider":"fixture", "usage":{}})})
    with app.app_context(): init_db()
    client = app.test_client()
    assert client.patch('/api/v1/me', json={"department_id":"dept-nutn-csie", "admission_year":115,
                                           "current_semester_id":"semester-115-1"}).status_code == 200
    return app, client, now

def get_context(client):
    r = client.get('/api/v1/graduation-context')
    assert r.status_code == 200
    assert r.headers['Cache-Control'] == 'no-store'
    return r.json['data']

def test_normal_ttl_no_database_writes(setup_app, evidence):
    app, c, now = setup_app
    with sqlite3.connect(app.config['DATABASE']) as db: before = list(db.iterdump())
    initial = get_context(c)
    r = c.post('/api/v1/graduation-explanation')
    w = r.json['data']['workflow']
    assert w['status'] == 'verified'
    assert w['validity']['expires_at_ms'] == 1300000
    assert w['validity']['scope_id'] == initial['scope_id']
    assert w['validity']['source_sha256'] == initial['source_sha256']
    now[0] = 1300
    current = get_context(c)
    assert current['server_now_ms'] == w['validity']['expires_at_ms']
    with sqlite3.connect(app.config['DATABASE']) as db: assert list(db.iterdump()) == before
    evidence.append({'kind':'fixture_normal_ttl','expected':'verified; deadline reached; no DB writes','actual':r.json,'at_deadline':current})

def test_lecture_update_changes_source(setup_app, evidence):
    app,c,_ = setup_app
    old = get_context(c)
    assert c.put('/api/v1/lecture-progress',json={'professional_count':10,'general_count':12}).status_code == 200
    new = get_context(c)
    assert old['scope_id'] == new['scope_id'] and old['source_sha256'] != new['source_sha256']
    evidence.append({'expected':'source fingerprint changes','before':old,'after':new})

def test_same_rule_id_changed_content_changes_source(setup_app, evidence):
    app,c,_ = setup_app
    old = get_context(c)
    with sqlite3.connect(app.config['DATABASE']) as db:
        rule, text = db.execute('SELECT rule_set_id,document FROM graduation_rule_documents').fetchone()
        d = json.loads(text)
        d['credit_requirements']['minimum_total_credits'] += 1
        encoded = dump(d)
        db.execute('UPDATE graduation_rule_documents SET document=?,digest=? WHERE rule_set_id=?',
                   (encoded,sha256(encoded.encode()).hexdigest(),rule))
    new = get_context(c)
    assert old['source_sha256'] != new['source_sha256']
    evidence.append({'kind':'synthetic_source_update','expected':'same ID, changed content invalidates','before':old,'after':new})

def test_source_changes_during_provider_discards_clauses(setup_app, evidence):
    app,c,_ = setup_app
    def provider(ctx,previous,feedback):
        with sqlite3.connect(app.config['DATABASE']) as db:
            db.execute("INSERT OR REPLACE INTO lecture_progress VALUES ('user-demo-001',10,12,'synthetic-update')")
        return valid_draft(ctx), {'provider':'fixture','usage':{}}
    app.config['GRADUATION_EXPLANATION_PROVIDER'] = provider
    w = c.post('/api/v1/graduation-explanation').json['data']['workflow']
    assert w['status'] == 'stale' and w['stop_reason'] == 'SOURCE_CHANGED' and w['explanation'] == []
    evidence.append({'expected':'in-flight stale clauses discarded','actual':w})

def test_expiry_during_provider_discards_clauses(setup_app):
    app,c,now = setup_app
    def provider(ctx,previous,feedback):
        now[0] += 301
        return valid_draft(ctx), {'provider':'fixture','usage':{}}
    app.config['GRADUATION_EXPLANATION_PROVIDER'] = provider
    w = c.post('/api/v1/graduation-explanation').json['data']['workflow']
    assert w['status'] == 'stale' and w['stop_reason'] == 'EXPIRED' and not w['explanation']

def test_reset_and_separate_browsers_have_distinct_scope(setup_app, evidence):
    app,c,_ = setup_app
    old = get_context(c)
    other = get_context(app.test_client())
    assert other['scope_id'] != old['scope_id']
    new = c.post('/api/v1/graduation-session/reset').json['data']
    assert new['scope_id'] != old['scope_id']
    evidence.append({'kind':'browser_scope_only_NOT_user_auth','expected':'distinct browser/reset scope', 'old':old,'other':other,'new':new})

@pytest.mark.parametrize('route,method,kwargs,status',[
    ('graduation-context?user_id=other','GET',{},422),
    ('graduation-context','GET',{'data':'{}'},422),
    ('graduation-context','GET',{'headers':{'Origin':'https://other.example'}},403),
    ('graduation-session/reset','POST',{'json':{'user_id':'other'}},422),
    ('graduation-session/reset','POST',{'headers':{'Sec-Fetch-Site':'cross-site'}},403),
])
def test_reject_overrides_and_cross_origin(setup_app,route,method,kwargs,status):
    app,c,_=setup_app
    before=get_context(c)
    assert c.open('/api/v1/'+route,method=method,**kwargs).status_code == status
    assert get_context(c)['scope_id'] == before['scope_id']

def test_corrupt_source_fails_closed(setup_app):
    app,c,_=setup_app
    with sqlite3.connect(app.config['DATABASE']) as db: db.execute("UPDATE graduation_rule_documents SET digest='broken'")
    assert c.get('/api/v1/graduation-context').status_code == 500

def test_volatile_evaluation_time_not_source_change():
    a={'evaluated_at':'first','user_id':'synthetic-u1','checks':[]}
    b={**a,'evaluated_at':'second'}
    assert source_digest(a,'r1') == source_digest(b,'r1')
    assert source_digest(a,'r1') != source_digest({**a,'user_id':'synthetic-u2'},'r1')

@pytest.mark.skip(reason='NOT_RUN: baseline has one fixed user and no authentication; browser-scope isolation is not C02 multi-user acceptance')
def test_C02_authenticated_user_isolation():
    pass
