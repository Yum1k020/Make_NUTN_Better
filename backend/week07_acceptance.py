"""Week 07 acceptance: exact baseline/candidate processes; synthetic data only by default."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from time import perf_counter
from uuid import uuid4
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "cbbd524"

def run(root, live=False):
    sys.path.insert(0,str(root/'backend'))
    from week06_acceptance import prepare, snapshot
    from app.graduation_explanation_core import valid_draft
    run_id=str(uuid4())
    folder=ROOT/'.cache/week07'
    folder.mkdir(parents=True,exist_ok=True)
    # Identical synthetic resource IDs and timestamps on both exact source versions.
    ids=iter(['synthetic-enrollment-1','synthetic-enrollment-2','synthetic-plan-1'])
    with patch('app.planner_core.uuid4', side_effect=lambda: next(ids)), \
         patch('app.planner_core.timestamp', return_value='2026-10-28T10:00:00+08:00'), \
         patch('app.planner.timestamp', return_value='2026-10-28T10:00:00+08:00'):
        app,inputs=prepare(folder/(run_id+'.sqlite3'))
    client=app.test_client()
    app.config['GRADUATION_CLOCK']=lambda:1000.0
    def fixture(c,p,f):return valid_draft(c),{'provider':'fixture','usage':{},'latency_ms':0}
    configured=bool(os.environ.get('GEMINI_API_KEY') and os.environ.get('GEMINI_MODEL'))
    if not live:app.config['GRADUATION_EXPLANATION_PROVIDER']=fixture
    before=snapshot(app)
    started=perf_counter()
    normal=client.post('/api/v1/graduation-explanation') if not live or configured else None
    elapsed=round((perf_counter()-started)*1000)
    w=normal.json['data']['workflow'] if normal else None
    normal_readonly=snapshot(app)==before
    first_context=client.get('/api/v1/graduation-context')
    client.put('/api/v1/lecture-progress',json={'professional_count':10,'general_count':12})
    after_context=client.get('/api/v1/graduation-context')
    new_progress=client.get('/api/v1/graduation-progress').json['data']
    # Reproduce a source update during model I/O, using the same provider on both versions.
    def updating(c,p,f):
        with sqlite3.connect(app.config['DATABASE']) as db:
            db.execute("UPDATE lecture_progress SET general_count=11,updated_at='synthetic-inflight' WHERE user_id='user-demo-001'")
        return fixture(c,p,f)
    app.config['GRADUATION_EXPLANATION_PROVIDER']=updating
    inflight=client.post('/api/v1/graduation-explanation').json['data']
    calls=[0]
    def forbidden(*args):calls[0]+=1;raise AssertionError('invalid input reached provider')
    app.config['GRADUATION_EXPLANATION_PROVIDER']=forbidden
    invalid=client.post('/api/v1/graduation-explanation',json={'user_id':'synthetic-other'})
    assert invalid.status_code==422 and calls[0]==0 and normal_readonly
    paths=['backend/app/graduation_explanation_api.py','backend/app/graduation_explanation_core.py',
           'backend/app/graduation_validity.py','frontend/src/lib/graduationMemory.js',
           'frontend/src/components/GraduationProgress.jsx']
    return {'run_id':run_id,'root_kind':'candidate' if root==ROOT else 'exact_integrated_baseline',
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'source_sha256':{p:sha256((root/p).read_bytes()).hexdigest() for p in paths if (root/p).exists()},
            'data_kind':'synthetic','inputs':inputs,'normal_kind':'gemini' if live and configured else 'NOT_RUN' if live else 'fixture',
            'live_status':('LIVE_PASS' if w and w['status']=='verified' and all(a['metrics'].get('provider')=='gemini' for a in w['attempts']) else 'LIVE_FAIL') if live and configured else 'LIVE_NOT_RUN',
            'normal':normal.json if normal else None,'normal_latency_ms':elapsed if normal else None,
            'normal_database_unchanged':normal_readonly,
            'before_context':{'status':first_context.status_code,'body':first_context.json},
            'after_context':{'status':after_context.status_code,'body':after_context.json},
            'updated_progress':new_progress,'inflight_update':inflight,
            'invalid':{'status':invalid.status_code,'provider_calls':calls[0],'body':invalid.json},
            'token_note':'fixture usage unavailable; never zero-cost claim',
            'C02':'NOT_RUN: fixed identity, no authenticated user mapping',
            'W01_W02':'N/A: no new business-data write tools; session cookie reset only'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--compare',action='store_true')
    parser.add_argument('--serve-fixture',action='store_true')
    args=parser.parse_args()
    if args.serve_fixture:
        sys.path.insert(0,str(ROOT/'backend'))
        from week06_acceptance import prepare
        from app.graduation_explanation_core import valid_draft
        folder=ROOT/'.cache/week07';folder.mkdir(parents=True,exist_ok=True)
        app,_=prepare(folder/(str(uuid4())+'.sqlite3'))
        app.config['GRADUATION_FIXTURE_ONLY']=True
        app.config['GRADUATION_EXPLANATION_PROVIDER']=lambda c,p,f:(valid_draft(c),{'provider':'fixture','usage':{}})
        os.environ['GRADUATION_ALLOWED_ORIGINS']='http://127.0.0.1:5173,http://localhost:5173'
        print('SYNTHETIC FIXTURE ONLY; not Gemini live evidence',flush=True)
        app.run(host='127.0.0.1',port=5000,debug=False)
        return
    if args.compare:
        folder=ROOT/'docs/week07/evidence';folder.mkdir(parents=True,exist_ok=True)
        for name,root in [('baseline',ROOT/'.cache/week07-baseline'),('candidate',ROOT)]:
            subprocess.run([sys.executable,'-X','utf8',__file__,'--root',str(root),'--out',str(folder/(name+'.json'))],check=True)
        a=json.loads((folder/'baseline.json').read_text(encoding='utf-8'))
        b=json.loads((folder/'candidate.json').read_text(encoding='utf-8'))
        def facts(r):return {k:v for k,v in r['normal']['data']['progress'].items() if k!='evaluated_at'}
        assert facts(a)==facts(b)
        assert a['inflight_update']['workflow']['status']=='verified'
        assert b['inflight_update']['workflow']['status']=='stale'
        assert b['inflight_update']['workflow']['explanation']==[]
        summary={'baseline_sha':a['source_commit'],'candidate_sha':b['source_commit'],
                 'same_normal_facts':True,'baseline_inflight_status':'verified_on_old_snapshot',
                 'candidate_inflight_status':'stale_clauses_removed',
                 'baseline_TTL':'absent','candidate_TTL_seconds':300,
                 'baseline_context_http':a['before_context']['status'],'candidate_context_http':b['before_context']['status'],
                 'baseline_model_calls':a['normal']['data']['workflow']['model_calls'],
                 'candidate_model_calls':b['normal']['data']['workflow']['model_calls'],
                 'normal_latency_ms':{'baseline_fixture':a['normal_latency_ms'],'candidate_fixture':b['normal_latency_ms']},
                 'quality_and_cost_separate':True,'C02':'NOT_RUN','LIVE':'LIVE_NOT_RUN'}
        (folder/'comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False));return
    report=run(args.root.resolve() if args.root else ROOT,args.live)
    out=args.out or ROOT/'docs/week07/evidence/live.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(out),'run_id':report['run_id'],'live':report['live_status']}))

if __name__=='__main__':main()
