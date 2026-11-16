"""THE DESCENT v2 server. The browser receives no private rules or outcome code.

Start: python -m uvicorn app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations
import hashlib, json, os, re, secrets, sqlite3, time
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header, Body, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Any
from game_engine import initialize, public, act

BASE = Path(__file__).resolve().parent
DB = Path(os.environ.get("DESCENT_DB", str(BASE/"data"/"sessions.sqlite3")))
DB.parent.mkdir(exist_ok=True, parents=True)
app = FastAPI(title="THE DESCENT", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE/"static"), name="static")


def init_db():
    with sqlite3.connect(str(DB), timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE IF NOT EXISTS game_sessions (token_hash TEXT PRIMARY KEY, state_json TEXT NOT NULL, updated_at REAL NOT NULL, version INTEGER NOT NULL DEFAULT 0)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_updated ON game_sessions(updated_at)")

init_db()

@contextmanager
def db(write=False):
    conn=sqlite3.connect(str(DB),timeout=12)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA busy_timeout=12000")
    if write: conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        if write:conn.commit()
    except Exception:
        if write:conn.rollback()
        raise
    finally:conn.close()


def token_key(token:str)->str:
    if not isinstance(token,str) or not re.fullmatch(r"[A-Za-z0-9_\-]{32,100}",token):
        raise HTTPException(status_code=401,detail="无效会话。")
    return hashlib.sha256(token.encode()).hexdigest()


def get_session(conn,token:str):
    row=conn.execute("SELECT state_json,version FROM game_sessions WHERE token_hash=?",(token_key(token),)).fetchone()
    if row is None:raise HTTPException(status_code=404,detail="会话不存在或已过期。")
    return json.loads(row["state_json"]),row["version"]


def api_response(g, version=None):
    out=public(g)
    if version is not None:out["version"]=version
    return out

class NewGame(BaseModel):
    profile:dict[str,Any]

class Action(BaseModel):
    action:str
    version:int
    mode:str=""

@app.middleware("http")
async def response_headers(req:Request,call_next):
    resp=await call_next(req)
    resp.headers["X-Content-Type-Options"]="nosniff"
    resp.headers["Referrer-Policy"]="no-referrer"
    resp.headers["Cache-Control"]="no-store"
    resp.headers["X-Frame-Options"]="DENY"
    resp.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    return resp

@app.get("/")
def index():
    return FileResponse(str(BASE/"static"/"index.html"),media_type="text/html")

@app.get("/healthz")
def health():
    from horror_director import configured
    return {"ok":True,"name":"THE DESCENT","version":"3.8",
            "model_configured":configured()}

@app.post("/api/new",status_code=201)
def new_game(payload:NewGame):
    try:g=initialize(payload.profile)
    except (ValueError,TypeError) as ex:raise HTTPException(status_code=422,detail=str(ex))
    if g.get("edition")=="v38":
        from horror_director import render
        render(g)
    token=secrets.token_urlsafe(32)
    with db(True) as conn:
        # Expire old sessions after 14 days; nothing is transmitted to analytics.
        conn.execute("DELETE FROM game_sessions WHERE updated_at < ?",(time.time()-14*86400,))
        conn.execute("INSERT INTO game_sessions(token_hash,state_json,updated_at,version) VALUES(?,?,?,0)",
                    (token_key(token),json.dumps(g,ensure_ascii=False),time.time()))
    return {"token":token,"state":api_response(g,0)}

@app.get("/api/state")
def state(x_session:str=Header(default="")):
    with db() as conn:
        g,version=get_session(conn,x_session)
    return api_response(g,version)

@app.post("/api/action")
def action(payload:Action,x_session:str=Header(default="")):
    if len(payload.action)>700:raise HTTPException(status_code=422,detail="单次行动最多 700 字。")
    with db() as conn:
        g,version=get_session(conn,x_session)
    if version!=payload.version:
        raise HTTPException(status_code=409,detail="对局已经更新，请刷新当前场景后再提交。")
    action_text,action_mode=payload.action,payload.mode
    if g.get("edition")=="v38":
        from horror_director import interpret,render
        action_text,action_mode=interpret(g,action_text,action_mode)
    try:act(g,action_text,action_mode)
    except ValueError as ex:raise HTTPException(status_code=422,detail=str(ex))
    if g.get("edition")=="v38":
        render(g)
    # Never hold a SQLite write lock while awaiting a paid model response.
    # Conditional update rejects a second concurrent decision for the same version.
    with db(True) as conn:
        updated=conn.execute(
            "UPDATE game_sessions SET state_json=?,updated_at=?,version=? "
            "WHERE token_hash=? AND version=?",
            (json.dumps(g,ensure_ascii=False),time.time(),version+1,
             token_key(x_session),version))
        if updated.rowcount!=1:
            raise HTTPException(status_code=409,detail="这一轮已被其他请求更新；请刷新对局。")
    return api_response(g,version+1)

@app.get("/api/export")
def export(x_session:str=Header(default="")):
    with db() as conn:g,_=get_session(conn,x_session)
    # Full transcript for the player, including private questionnaire, but not private scoring/rules.
    out={"name":g["profile"]["name"],"questionnaire":g["profile"],"lost":g["lost"],"events":g["history"],"ending":g["ending"]}
    if g.get("edition") in ("v37","v38"):
        story=g["psych"]
        out["experience"]={"interview":story.get("answers",[]),"hypotheticals":story.get("probes",[]),
                           "real_choices":story.get("choices",[]),"consequences":story.get("consequences",[]),
                           "proof":story.get("proof",[]),"cost":story.get("cost"),
                           "first_words":story.get("first_words",""),"final_action":story.get("last_action")}
        if g.get("edition")=="v38":
            out["narrative"]={"mode":g.get("director",{}).get("mode","rules"),
                              "scene":g.get("director",{}).get("scene"),
                              "ending_text":g.get("director",{}).get("ending_text")}
    if "story_v35" in g:
        story=g["story_v35"]
        out["experience"]={"first_words":story.get("first_words",""),
                           "real_local_wins":story.get("wins",[]),
                           "pending_orders":story.get("pending",[]),
                           "final_action":story.get("final_action")}
    return JSONResponse(out,headers={"Content-Disposition":"attachment; filename=the_descent_session.json"})

@app.delete("/api/session")
def delete(x_session:str=Header(default="")):
    with db(True) as conn:
        cur=conn.execute("DELETE FROM game_sessions WHERE token_hash=?",(token_key(x_session),))
    return {"deleted":bool(cur.rowcount)}


# Read-only web tool compatible AI player entry; game logic remains private.
from ai_web import register_ai_routes
register_ai_routes(app, db, token_key, get_session)
