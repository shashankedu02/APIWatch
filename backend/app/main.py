from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from . import database
from .security import validate_url
from .services import check

app=FastAPI(title='APIWatch',description='Local API health and performance monitor')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['*'],allow_headers=['*'])
class EndpointIn(BaseModel):
 name:str=Field(min_length=1,max_length=80);url:str=Field(max_length=2048);method:Literal['GET','POST','HEAD']='GET';timeout:float=Field(5,ge=1,le=30)
@app.get('/api/health')
def health():return {'status':'ok','service':'APIWatch'}
@app.get('/api/endpoints')
def list_endpoints():return database.endpoints()
@app.post('/api/endpoints',status_code=201)
def create_endpoint(body:EndpointIn):
 url=validate_url(str(body.url));now=datetime.now(timezone.utc).isoformat()
 with database.connect() as db:
  cur=db.execute('INSERT INTO endpoints(name,url,method,timeout,created_at) VALUES(?,?,?,?,?)',(body.name.strip(),url,body.method,body.timeout,now));id=cur.lastrowid
 return database.endpoint(id)
@app.get('/api/endpoints/{id}')
def get_endpoint(id:int):
 value=database.endpoint(id)
 if not value:raise HTTPException(404,'Endpoint not found.')
 return value|{'history':database.history(id)}
@app.delete('/api/endpoints/{id}',status_code=204)
def delete_endpoint(id:int):
 with database.connect() as db:
  if not db.execute('DELETE FROM endpoints WHERE id=?',(id,)).rowcount:raise HTTPException(404,'Endpoint not found.')
@app.post('/api/endpoints/{id}/check')
async def check_one(id:int):
 item=database.endpoint(id)
 if not item:raise HTTPException(404,'Endpoint not found.')
 return await check(item)
@app.post('/api/check-all')
async def check_all():
 results=[]
 for item in database.endpoints():
  try:results.append(await check(item))
  except Exception as exc:results.append({'endpoint_id':item['id'],'success':False,'error_message':'Internal check failure'})
 return results
@app.get('/api/endpoints/{id}/history')
def endpoint_history(id:int):
 if not database.endpoint(id):raise HTTPException(404,'Endpoint not found.')
 return database.history(id)
@app.get('/api/dashboard/stats')
def stats():
 endpoints=database.endpoints();checks=database.history();recent=checks[:50];times=[c['response_time_ms'] for c in recent if c['response_time_ms'] is not None]
 healthy=sum(1 for e in endpoints if e.get('success')==1);unhealthy=sum(1 for e in endpoints if e.get('success')==0)
 return {'total_endpoints':len(endpoints),'healthy_endpoints':healthy,'unhealthy_endpoints':unhealthy,'average_response_time_ms':round(sum(times)/len(times),2) if times else None,'recent_checks':recent,'success_count':sum(1 for c in recent if c['success']),'failure_count':sum(1 for c in recent if not c['success'])}
@app.delete('/api/history')
def clear_history():
 with database.connect() as db:db.execute('DELETE FROM checks')
 return {'message':'History cleared'}
