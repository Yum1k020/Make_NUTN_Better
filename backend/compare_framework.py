"""Reproducible same-data graduation A/B comparison through original APIs."""
import argparse
from contextlib import closing
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from importlib.metadata import version
import json
import logging
from pathlib import Path
import platform
import shutil
import sqlite3
import tempfile
from time import perf_counter
from zoneinfo import ZoneInfo
from app import create_app
from app.db import get_db, init_db
from app.planner_core import course_snapshot, dump, timestamp
from app.planner_graduation import document

RULE, SEM = 'nutn-csie-115-mvp-v1', 'semester-115-1'
BASE = '/api/v1'


def digest(path):
    with closing(sqlite3.connect(path)) as db:
        return sha256('\n'.join(db.iterdump()).encode()).hexdigest()


def normalized(body):
    body = deepcopy(body)
    if 'data' in body:
        body['data'].pop('evaluated_at', None)
    return body


def fully_mapped(app):
    """Synthetic 133-credit fixture; zero-credit program items are test-only."""
    with app.app_context():
        db = get_db()
        d = document(db, RULE)
        counter = 0
        def passed(name, credits, category, key=None, domain=None):
            nonlocal counter
            counter += 1
            cid = 'test-confirmed-' + str(counter)
            db.execute('INSERT INTO courses VALUES (?,?,?,?,?,?,?,?)',
                       (cid, None, name, credits, 'dept-nutn-csie', 'unknown', None, None))
            db.execute('INSERT INTO course_classifications VALUES (?,?,?)', (cid, RULE, category))
            if key:
                db.execute('INSERT INTO graduation_course_mappings VALUES (?,?,?)', (RULE, key, cid))
            if domain:
                db.execute('INSERT INTO graduation_course_domains VALUES (?,?,?)', (RULE, cid, domain))
            payload = dict(course_id=cid, semester_id=SEM, offering_id=None, enrollment_status='finished',
                           passed=True, grade=None, course_snapshot=course_snapshot(db, cid))
            now = timestamp()
            db.execute('INSERT INTO planner_resources VALUES (?,?,?,?,?,?)',
                       ('enrollments', 'test-record-'+str(counter), 'user-demo-001', dump(payload), now, now))
        cr = d['credit_requirements']
        for c in cr['department_required']['courses']:
            passed(c['name'], c['credits'], 'department_required', 'required:'+c['course_code'])
        for i,c in enumerate(cr['general_education']['core']['requirements']):
            passed(c['name'], c['required_credits'], 'general_core', f'general_core:{i}')
        passed('科技法律', 2, 'college_required', 'college:0')
        for domain in ('文史哲藝術','社會脈動','生命科學'):
            passed('合成領域課 '+domain, 4, 'general_domain', domain=domain)
        passed('合成多元課', 6, 'general_diverse')
        passed('合成系選修', 12, 'department_elective')
        passed('合成自由選修', 20, 'free_elective')
        for p in d['program_requirements']['programs']:
            for i,name in enumerate(p['courses'][:3]):
                passed(name+'（零學分合成項目）', 0, 'free_elective', f"program:{p['id']}:{i}")
        db.commit()


def setup(folder, case):
    path=folder/(case+'.sqlite3')
    app=create_app(dict(TESTING=True,DATABASE=str(path),GRADUATION_ENGINE='legacy'))
    with app.app_context():
        init_db()
    client=app.test_client()
    events=[]
    def call(method,endpoint,payload,status):
        r=client.open(BASE+endpoint,method=method,json=payload)
        assert r.status_code==status,r.json
        events.append(dict(method=method,path=BASE+endpoint,input=payload,actual_body=r.json))
    if case!='missing_rule':
        call('PATCH','/me',dict(department_id='dept-nutn-csie',admission_year=115,current_semester_id=SEM),200)
    if case in ('full_met','lecture_gap'):
        fully_mapped(app)
        events.append({'fixture':'fully_mapped(): synthetic 133 credits and explicit mappings, zero-credit program items test-only'})
        call('PUT','/lecture-progress',dict(professional_count=10,general_count=11 if case=='lecture_gap' else 12),200)
    if case in ('partial','overflow','unknown_classification'):
        credits=24 if case=='overflow' else 3
        with closing(sqlite3.connect(path)) as db:
            db.execute("UPDATE courses SET credits=? WHERE course_id='course-demo-001'",(credits,))
            if case!='unknown_classification':
                db.execute('INSERT INTO course_classifications VALUES (?,?,?)',('course-demo-001',RULE,'department_elective'))
            db.commit()
        events.append(dict(fixture='course-demo-001',credits=credits,classification=None if case=='unknown_classification' else 'department_elective'))
        call('POST','/enrollments',dict(course_id='course-demo-001',semester_id=SEM,enrollment_status='finished',passed=True,grade=80),201)
        call('POST','/enrollments',dict(course_id='course-demo-002',semester_id=SEM,enrollment_status='in_progress'),201)
        call('POST','/planned-courses',dict(course_id='course-demo-003',target_semester_id=SEM),201)
    if case in ('checksum_error','storage_error'):
        sql="UPDATE graduation_rule_documents SET digest='tampered'" if case=='checksum_error' else 'DROP TABLE graduation_rule_documents'
        with closing(sqlite3.connect(path)) as db:
            db.execute(sql)
            db.commit()
        events.append(dict(injected_failure_sql=sql))
    return path,events


def verify(case,response):
    status=500 if case in ('checksum_error','storage_error') else 200
    assert response.status_code==status,response.json
    if status==500:
        assert response.json['error']['code']=='INTERNAL_ERROR'
        return dict(http_status=500,error='INTERNAL_ERROR')
    d=response.json['data']
    if case=='missing_rule':
        assert d['earned_credits'] is None and d['overall_status']=='needs_confirmation'
        assert d['data_errors'][0]['code']=='RULE_UNAVAILABLE'
        return dict(http_status=200,earned_credits=None,overall_status='needs_confirmation')
    earned=133 if case in ('full_met','lecture_gap') else 24 if case=='overflow' else 3
    assert d['earned_credits']==earned
    checks={c['check_id']:c for c in d['checks']}
    assert checks['total_credits']['remaining_value']==max(0,133-earned)
    assert d['overall_status']==('met' if case=='full_met' else 'not_met')
    if case=='full_met':
        assert all(c['status']=='met' for c in d['checks']) and d['missing_required_courses']==[]
    if case=='lecture_gap':
        assert checks['lecture_general']['remaining_value']==1
    if case=='overflow':
        assert d['credit_allocation'][0]['allocations']==[dict(category='department_elective',credits=12),dict(category='free_elective',credits=12)]
    if case=='unknown_classification':
        assert any(e['code']=='CLASSIFICATION_UNKNOWN' for e in d['data_errors'])
        assert checks['department_elective']['status']=='needs_confirmation'
    assert all(sum(p['credits'] for p in row['allocations'])<=row['credits'] for row in d['credit_allocation'])
    return dict(http_status=200,earned_credits=earned,overall_status='met' if case=='full_met' else 'not_met',no_double_allocation=True)


def run_case(folder,case):
    source,events=setup(folder,case)
    runs=[]
    for engine in ('legacy','langgraph'):
        target=folder/(case+'-'+engine+'.sqlite3')
        shutil.copy2(source,target)
        app=create_app(dict(TESTING=True,DATABASE=str(target),GRADUATION_ENGINE=engine))
        client=app.test_client()
        nodes=[]
        class Capture(logging.Handler):
            def emit(self,record):
                if hasattr(record,'workflow_node'):
                    nodes.append(record.workflow_node)
        handler=Capture()
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        before=digest(target)
        start=perf_counter()
        response=client.get(BASE+'/graduation-progress')
        elapsed=perf_counter()-start
        app.logger.removeHandler(handler)
        expected=verify(case,response)
        assert digest(target)==before
        wanted=['load_rules'] if response.status_code==500 else ['load_rules','unavailable'] if case=='missing_rule' else ['load_rules','collect','allocate','evaluate','summarize']
        assert nodes==(wanted if engine=='langgraph' else []),nodes
        replay=client.get(BASE+'/graduation-progress')
        assert replay.status_code==response.status_code and normalized(replay.json)==normalized(response.json)
        dashboard=client.get(BASE+'/dashboard?date=2026-10-05')
        assert dashboard.status_code==response.status_code
        if response.status_code==200:
            g=dashboard.json['data']['graduation_summary']
            assert g['earned_credits']==response.json['data']['earned_credits']
            assert g['overall_status']==response.json['data']['overall_status']
        assert digest(target)==before
        runs.append(dict(engine=engine,request=dict(method='GET',path=BASE+'/graduation-progress'),expected=expected,
            actual_status=response.status_code,actual_body=response.json,database_before_sha256=before,
            database_after_sha256=digest(target),nodes=nodes,elapsed_seconds=elapsed,repeat_read_unchanged=True,
            dashboard_body=dashboard.json,model_calls=0,outcome='PASS'))
    assert normalized(runs[0]['actual_body'])==normalized(runs[1]['actual_body'])
    assert runs[0]['dashboard_body']==runs[1]['dashboard_body']
    return dict(case=case,setup=events,same_result_excluding_evaluated_at=True,runs=runs)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='graduation-evidence.json')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        cases=[run_case(Path(tmp),c) for c in ('partial','missing_rule','overflow','lecture_gap','full_met',
                                              'unknown_classification','checksum_error','storage_error')]
    root=Path(__file__).resolve().parent
    result=dict(generated_at=datetime.now(ZoneInfo('Asia/Taipei')).isoformat(),topic='graduation planning',
        base_commit='c06b69f50d4ee66cdc38cf43e1843057c0728f3c',python=platform.python_version(),platform=platform.platform(),
        framework_version=version('langgraph'),mode='OFFLINE_NO_LLM',live_status='NOT_IMPLEMENTED_NO_MODEL_ADAPTER',
        model_calls=0,transport='Flask test client; real SQLite and real LangGraph',
        comparison_normalization='Only evaluated_at excluded; raw timestamps preserved.',
        source_sha256={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/'app').glob('*.py'))},
        cases=cases,passed_cases=len(cases),failed_cases=0)
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(cases)}/{len(cases)} graduation A/B cases PASS; OFFLINE_NO_LLM')


if __name__=='__main__':
    main()
