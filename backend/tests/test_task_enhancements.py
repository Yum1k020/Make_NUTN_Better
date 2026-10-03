"""Regression coverage for features ported from the archived FastAPI prototype."""
import json

import pytest

from app import create_app
from app.db import get_db, init_db


@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'tasks.sqlite3')})
    with app.app_context():
        init_db()
    return app


def add(client, **fields):
    response = client.post('/api/v1/tasks', json={'title': 'task', **fields})
    assert response.status_code == 201, response.json
    return response.json['data']


def test_fields_patch_and_restart(app):
    client = app.test_client()
    task = add(client, description=' details ', priority='high')
    assert (task['description'], task['priority'], task['type'], task['due_date']) == ('details', 'high', 'todo', None)
    url = '/api/v1/tasks/' + task['task_id']
    assert client.patch(url, json={'completed': True}).json['data']['description'] == 'details'
    assert client.patch(url, json={'description': ''}).json['data']['description'] == ''
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert restarted.get(url).json['data']['priority'] == 'high'


def test_legacy_read_does_not_write(app):
    client = app.test_client()
    task = add(client, due_date='2026-10-05')
    with app.app_context():
        db = get_db()
        row = json.loads(db.execute('SELECT body FROM planner_resources WHERE id=?', (task['task_id'],)).fetchone()[0])
        del row['description'], row['priority']
        body = json.dumps(row)
        db.execute('UPDATE planner_resources SET body=? WHERE id=?', (body, task['task_id']))
        db.commit()
    url = '/api/v1/tasks/' + task['task_id']
    fetched = client.get(url).json['data']
    assert fetched['description'] == '' and fetched['priority'] == 'medium'
    with app.app_context():
        assert get_db().execute('SELECT body FROM planner_resources WHERE id=?', (task['task_id'],)).fetchone()[0] == body
    assert client.patch(url, json={'priority': 'low'}).status_code == 200


def test_undated_calendar_dashboard_and_clear(app):
    client = app.test_client()
    undated = add(client)
    dated = add(client, due_date='2026-10-05', due_time='09:00')
    url = '/api/v1/tasks/' + dated['task_id']
    assert client.get('/api/v1/tasks?from=2026-10-05&to=2026-10-05').json['meta']['total'] == 1
    calendar = client.get('/api/v1/calendar?from=2026-10-05&to=2026-10-05')
    assert calendar.status_code == 200
    assert len(calendar.json['data']['task_deadlines']) == 1
    assert client.get('/api/v1/dashboard?date=2026-10-05').status_code == 200
    result = client.patch(url, json={'due_date': None})
    assert result.status_code == 200 and result.json['data']['due_time'] is None
    assert client.get('/api/v1/tasks').json['meta']['total'] == 2
    assert client.patch('/api/v1/tasks/' + undated['task_id'], json={'due_time': '09:00'}).status_code == 422


@pytest.mark.parametrize('payload', [
    {'description': None}, {'description': 1}, {'description': 'x' * 5001},
    {'priority': None}, {'priority': 'urgent'}, {'due_date': 'invalid'},
])
def test_invalid_patch_is_atomic(app, payload):
    client = app.test_client()
    task = add(client)
    url = '/api/v1/tasks/' + task['task_id']
    assert client.patch(url, json=payload).status_code == 422
    assert client.get(url).json['data'] == task


def test_pagination_defaults_filters_and_stable_order(app):
    client = app.test_client()
    for i in range(52):
        add(client, title=str(i), completed=i == 51)
    first = client.get('/api/v1/tasks').json
    second = client.get('/api/v1/tasks?limit=50&offset=50').json
    assert first['meta'] == {'count': 50, 'total': 52, 'limit': 50, 'offset': 0}
    assert second['meta']['count'] == 2
    assert len({t['task_id'] for t in first['data'] + second['data']}) == 52
    assert client.get('/api/v1/tasks?completed=true&limit=1').json['meta']['total'] == 1
    assert client.get('/api/v1/tasks?offset=100').json['data'] == []
    assert client.get('/api/v1/tasks').json == first
    for query in ('limit=0', 'limit=201', 'offset=-1', 'limit=1.5', 'limit=true', 'limit=1&limit=2'):
        assert client.get('/api/v1/tasks?' + query).status_code == 422


def test_linked_exam_cannot_lose_date(app):
    client = app.test_client()
    task = add(client, type='exam', due_date='2026-10-06', course_id='course-demo-001')
    response = client.post('/api/v1/study-plans', json={
        'course_id': 'course-demo-001', 'exam_task_id': task['task_id'],
        'start_date': '2026-10-05', 'exam_date': '2026-10-06', 'target_minutes': 60,
        'session_minutes': 60, 'allowed_windows': [{'weekday': 1, 'start_time': '09:00', 'end_time': '12:00'}]})
    assert response.status_code == 201
    assert client.patch('/api/v1/tasks/' + task['task_id'], json={'due_date': None}).status_code == 409


def test_openapi_contract(app):
    paths = app.test_client().get('/openapi.json').json['paths']
    schema = paths['/api/v1/tasks']['post']['requestBody']['content']['application/json']['schema']
    assert schema['required'] == ['title']
    assert schema['properties']['description']['maxLength'] == 5000
    assert schema['properties']['due_date']['nullable']
    assert {'limit', 'offset'} <= {p['name'] for p in paths['/api/v1/tasks']['get']['parameters']}


def test_database_health_detects_missing_table(app):
    client = app.test_client()
    assert client.get('/api/v1/health').json == {'status': 'ok'}
    with app.app_context():
        get_db().execute('DROP TABLE planner_resources')
        get_db().commit()
    assert client.get('/api/v1/health').status_code == 500
