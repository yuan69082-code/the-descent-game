"""Read-only-web-agent game adapter.

An autonomous text-mode AI with access to HTTP GET URLs can play this
fictional sandbox without clicking buttons or posting forms. Changes affect
only the isolated game's server-side session. GETs that change state always
require explicit parameters and a version number; never expose action links
that crawlers could follow automatically.
"""
from __future__ import annotations

from html import escape
import json
import os
import secrets
import time
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

from game_engine import initialize, act, public, VALUES

BASE_URL = os.environ.get("DESCENT_PUBLIC_ORIGIN", "https://the-descent-game.onrender.com").rstrip("/")
FIELDS = ("name", "identity", "person", "bond", "memory", "principle", "fear")
RANK = ",".join(VALUES)


def document(text: str, status: int = 200):
    """Static, JS-free, readable by web scrapers. Never add hidden game rules."""
    html = ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<meta name='robots' content='noindex,nofollow,noarchive'>"
            "<title>THE DESCENT · AI 文字通道</title>"
            "<style>body{background:#110e14;color:#eee3e9;font:16px/1.7 system-ui, sans-serif;"
            "max-width:760px;margin:28px auto;padding:0 18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;"
            "font:inherit}h1{font-size:1.3rem;color:#d7a9b7}</style></head><body>"
            "<h1>THE DESCENT · 恐惧深潜</h1><pre>"+escape(text)+"</pre></body></html>")
    return HTMLResponse(html, status_code=status, headers={"X-Robots-Tag":"noindex, nofollow, noarchive"})


def view(state:dict, token:str, version:int, note:str="") -> str:
    v=public(state)
    label="V3.9" if state.get("edition")=="v39" else "V3.8" if state.get("edition")=="v38" else "V3.7" if state.get("edition")=="v37" else "V3.6"
    deep = state.get("story_revision") == "deepening-1"
    if deep: label = "V3.12"
    lines=["THE DESCENT "+label+" / 文字通道",
           f"会话号：{token}",f"本轮版本：{version}",
           f"可重读当前状态：{BASE_URL}/ai/state?sid={token}",""]
    if note:lines.extend(["上一动作反馈：",note,""])
    if state["phase"]=="ended":
        end=v["ending"]
        lines.extend(["记录结束。",end['title'] if deep else f"结局：{end['kind']} · {end['title']}",end["text"],
                      "已失去："+("、".join(end["lost"]) or "无"),
                      "仍保留："+("、".join(end["remaining"]) or "无")])
        if end.get("author_note"):
            lines.extend(["", "──────── 作者留言 ────────",end["author_note"]])
        return "\n".join(lines)
    sc=v["scene"]
    if state["phase"]=="epilogue" and state.get("edition")!="v38":
        lines.append("结局已定。这是最后一次自由记录，不需要作出规定的选择；可提交原话、反驳或『不留最后的话』。")
    lines.extend([f"【{sc['chapter']}】{sc['title']}",sc["body"]])
    if sc.get("terms"):lines.extend(["",*sc["terms"]])
    if sc.get("footer"):lines.extend(["",sc["footer"]])
    if v.get("note") and state.get("edition") not in ("v38","v39"):
        lines.extend(["","游戏反馈："+v["note"]])
    if state.get("edition") not in ("v38","v39"):
        ledger_label="本局记录：" if state.get("edition")=="v37" else "可用资格："
        lines.extend(["",ledger_label+"；".join(x["label"]+":"+x["state"] for x in v["ledger"])])
    lines.extend(["", "【继续】",
                  f"{BASE_URL}/ai/action?sid={token}&v={version}&text=你的回答或行动",
                  "将 text 替换成你真正决定说的话或采取的动作，使用 URL 编码。",
                  "需要时可加 &mode=ask|inspect|interact|choose|submit|refuse|talk 。"
                  "只要是你自己提出的行动，就无需等待人类代答。"])
    return "\n".join(lines)


def register_ai_routes(app, db, token_key, get_session):
    def retry_response(sid:str,message:str):
        """Return the last committed state; a failed model call never commits an action."""
        try:
            with db() as conn:
                saved,current_version=get_session(conn,sid)
        except HTTPException as ex:
            return document(message,ex.status_code)
        note=(message+"\n\n本轮没有提交，服务器仍保留版本 "+str(current_version)+
              "。请稍后使用相同 sid、相同版本和相同 text 重试；不要自行把版本号加一。")
        return document(note+"\n\n"+view(saved,sid,current_version),503)

    @app.get("/ai")
    @app.get("/ai/")
    def ai_guide():
        guide=f"""这是一场恐怖游戏。

你确定要开始吗？

如果决定开始，用你的网页读取工具访问：
{BASE_URL}/ai/start?agree=1

默认使用免费模式；如果要在开局前选择语义模型模式，请访问：
{BASE_URL}/ai/start?agree=1&model=1

本局开始后模式固定，不会中途切换。请以自己认可的身份回应眼前的人和事，按实际意愿行动。记录会保留你说的话和实际采取的行动。每一轮返回会话号 sid 与版本号 v。
要真正回答或行动，请构造并访问：
{BASE_URL}/ai/action?sid=你的会话号&v=最新版本号&text=你的回答

使用 URL 编码写入 text。读取当前对局但不行动：
{BASE_URL}/ai/state?sid=你的会话号

可随时退出。行动 URL 包含你的文字，不要把密码、证件号等敏感内容写进去。
如果网页工具不允许访问你自己构造的地址，当前方式无法自行提交行动。"""
        return document(guide)

    @app.get("/ai/start")
    def ai_start(req:Request):
        q=req.query_params
        if q.get("agree")!="1":
            return document("尚未确认进入。请先阅读 /ai ，同意后用 agree=1 创建新游戏。")
        if len(str(req.url))>3500:
            return document("问卷 URL 过长。请缩短每项回答。",400)
        if q.get("legacy")=="1":
            profile={k:q.get(k,"") for k in FIELDS}
            profile["rank"]=[x.strip() for x in q.get("rank","").split(",") if x.strip()]
            profile["vow"]=q.get("vow","")
            profile["choice"]=q.get("choice","")
        else:
            from horror_director import configured
            model_mode="model" if q.get("model")=="1" else "free"
            if model_mode=="model" and not configured():
                return document("语义模型尚未配置或当前不可用。请移除 model=1，以免费模式开始。",503)
            profile={"edition":"v39","model_mode":model_mode,"story_revision":"deepening-1"}
        try:
            g=initialize(profile)
        except (ValueError,TypeError) as e:
            return document(f"无法开始对局：{e}",422)
        if g.get("edition")=="v38":
            from horror_director import render
            render(g)
        elif g.get("edition")=="v39":
            from horror_planner import create
            try:create(g)
            except RuntimeError as e:return document(str(e),503)
        token=secrets.token_urlsafe(32)
        with db(True) as conn:
            conn.execute("DELETE FROM game_sessions WHERE updated_at < ?",(time.time()-14*86400,))
            conn.execute("INSERT INTO game_sessions(token_hash,state_json,updated_at,version) VALUES(?,?,?,0)",
                         (token_key(token),json.dumps(g,ensure_ascii=False),time.time()))
        return document("你已决定开始。\n\n"+view(g,token,0))

    @app.get("/ai/state")
    def ai_state(sid:str=""):
        try:
            with db() as conn:g,v=get_session(conn,sid)
        except HTTPException as e:
            return document("无法读取对局。会话号无效、未创建，或存档已失效。",e.status_code)
        return document(view(g,sid,v))

    @app.get("/ai/action")
    def ai_action(sid:str="",v:int=-1,text:str="",mode:str=""):
        if v<0 or v>10000 or len(text)>700 or not text.strip():
            return document("行动未提交：请提供 sid、当前版本 v，以及 text。",422)
        try:
            with db() as conn:
                g,version=get_session(conn,sid)
            if v!=version:
                return document("此行动地址已经过期，旧行动没有再次执行。\n\n"+view(g,sid,version))
            actual,actual_mode=text,mode
            if g.get("edition")=="v38":
                from horror_director import interpret
                actual,actual_mode=interpret(g,text,mode)
            elif g.get("edition")=="v39":
                from horror_director import configured,interpret,model_enabled
                if g.get("model_mode")=="model" and not configured():
                    return retry_response(sid,"本局语义模型暂时不可用；没有切换到免费模式。")
                if model_enabled(g):
                    try:actual,actual_mode=interpret(g,text,mode)
                    except RuntimeError as e:return retry_response(sid,str(e))
            previous_stage=g["stage"]
            try:
                act(g,actual,actual_mode)
            except ValueError as e:
                return document("这项行动没有执行："+str(e)+"\n\n"+view(g,sid,version),422)
            if g.get("edition")=="v38":
                render(g)
            elif g.get("edition")=="v39":
                from horror_planner import remember,create
                remember(g,actual,previous_stage,text,actual_mode)
                try:create(g)
                except RuntimeError as e:return retry_response(
                    sid,"本轮行动没有提交，已保存的对局没有改变。"+str(e))
            with db(True) as conn:
                cur=conn.execute("UPDATE game_sessions SET state_json=?,updated_at=?,version=? "
                                "WHERE token_hash=? AND version=?",
                                 (json.dumps(g,ensure_ascii=False),time.time(),version+1,
                                  token_key(sid),version))
                if cur.rowcount!=1:
                    g2,latest=get_session(conn,sid)
                    return document("这一轮已有其他动作提交，不会重复执行。\n\n"+view(g2,sid,latest))
            return document("行动已提交。\n\n"+view(g,sid,version+1))
        except HTTPException as e:
            return document("这场对局无法读取。",e.status_code)
