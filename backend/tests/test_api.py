from fastapi.testclient import TestClient
from app.main import app
from app import database
import app.services as services
client=TestClient(app)
def reset():
 with database.connect() as db:db.execute('DELETE FROM checks');db.execute('DELETE FROM endpoints')
def test_health_and_crud(monkeypatch):
 reset();assert client.get('/api/health').status_code==200
 monkeypatch.setattr('app.security.socket.getaddrinfo',lambda *x,**y:[(None,None,None,None,('8.8.8.8',0))])
 r=client.post('/api/endpoints',json={'name':'Google DNS','url':'https://example.com','method':'GET','timeout':2});assert r.status_code==201;id=r.json()['id'];assert len(client.get('/api/endpoints').json())==1;assert client.delete(f'/api/endpoints/{id}').status_code==204
def test_blocks_private_targets():
 assert client.post('/api/endpoints',json={'name':'bad','url':'http://127.0.0.1','method':'GET'}).status_code==422
def test_check_and_stats(monkeypatch):
 reset();monkeypatch.setattr('app.security.socket.getaddrinfo',lambda *x,**y:[(None,None,None,None,('8.8.8.8',0))]);id=client.post('/api/endpoints',json={'name':'Public','url':'https://example.com'}).json()['id']
 async def fake(item):
  with database.connect() as db:db.execute("INSERT INTO checks(endpoint_id,timestamp,status_code,response_time_ms,success,error_message) VALUES(?,?,?,?,?,?)",(item['id'],'2026-01-01T00:00:00Z',200,12.3,1,None))
  return {'endpoint_id':item['id'],'success':True}
 monkeypatch.setattr('app.main.check',fake);assert client.post(f'/api/endpoints/{id}/check').status_code==200;assert client.get(f'/api/endpoints/{id}/history').json();assert client.get('/api/dashboard/stats').json()['healthy_endpoints']==1
def test_check_all_resilience(monkeypatch):
 reset();monkeypatch.setattr('app.security.socket.getaddrinfo',lambda *x,**y:[(None,None,None,None,('8.8.8.8',0))])
 for name in ['a','b']:client.post('/api/endpoints',json={'name':name,'url':'https://example.com'})
 async def bad(item):raise RuntimeError('boom')
 monkeypatch.setattr('app.main.check',bad);assert len(client.post('/api/check-all').json())==2
