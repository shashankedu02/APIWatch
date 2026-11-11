import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "apiwatch.db"
def connect():
    db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
    db.executescript("""CREATE TABLE IF NOT EXISTS endpoints(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,url TEXT NOT NULL,method TEXT NOT NULL,timeout REAL NOT NULL,created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY AUTOINCREMENT,endpoint_id INTEGER NOT NULL,timestamp TEXT NOT NULL,status_code INTEGER,response_time_ms REAL,success INTEGER NOT NULL,error_message TEXT,FOREIGN KEY(endpoint_id) REFERENCES endpoints(id) ON DELETE CASCADE); CREATE INDEX IF NOT EXISTS idx_checks_endpoint_time ON checks(endpoint_id,timestamp DESC);""")
    return db
def row(row): return dict(row) if row else None
def endpoint(id):
    with connect() as db:return row(db.execute("SELECT * FROM endpoints WHERE id=?",(id,)).fetchone())
def endpoints():
    with connect() as db:return [row(x) for x in db.execute("SELECT e.*,c.status_code,c.response_time_ms,c.success,c.timestamp last_checked FROM endpoints e LEFT JOIN checks c ON c.id=(SELECT id FROM checks WHERE endpoint_id=e.id ORDER BY timestamp DESC LIMIT 1) ORDER BY e.id DESC")]
def history(id=None):
    with connect() as db:
      sql="SELECT c.*,e.name endpoint_name FROM checks c JOIN endpoints e ON e.id=c.endpoint_id"; args=()
      if id: sql+=" WHERE endpoint_id=?";args=(id,)
      return [row(x) for x in db.execute(sql+" ORDER BY timestamp DESC LIMIT 200",args)]
