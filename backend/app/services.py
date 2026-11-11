from datetime import datetime, timezone
from time import perf_counter
from urllib.parse import urljoin
import httpx
from .security import validate_url
from .database import connect

MAX_BYTES=1_000_000
async def check(item: dict) -> dict:
    url=validate_url(item['url']); started=perf_counter(); status=None; error=None; success=False
    try:
      async with httpx.AsyncClient(follow_redirects=False, timeout=item['timeout']) as client:
        for _ in range(4):
          validate_url(url)
          async with client.stream(item['method'],url,headers={'User-Agent':'APIWatch/1.0'}) as response:
            status=response.status_code; total=0
            async for chunk in response.aiter_bytes():
              total+=len(chunk)
              if total>MAX_BYTES: raise ValueError('Response exceeded the 1 MB safety limit.')
            if status in {301,302,303,307,308}:
              location=response.headers.get('location')
              if not location: break
              url=urljoin(url,location);continue
            success=200<=status<400;break
        else: error='Too many redirects.'
    except (httpx.HTTPError,ValueError) as exc: error=str(exc)[:300]
    elapsed=round((perf_counter()-started)*1000,2); timestamp=datetime.now(timezone.utc).isoformat()
    with connect() as db:
      db.execute("INSERT INTO checks(endpoint_id,timestamp,status_code,response_time_ms,success,error_message) VALUES(?,?,?,?,?,?)",(item['id'],timestamp,status,elapsed,int(success),error))
    return {'endpoint_id':item['id'],'timestamp':timestamp,'status_code':status,'response_time_ms':elapsed,'success':success,'error_message':error}
