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
    label="V3.7" if state.get("edition")=="v37" else "V3.6"
    lines=["THE DESCENT "+label+" / AI 纯文字游玩通道",
           "只展示当前场景，不包含任何隐藏路线、判定规则或后台源码。",
           f"会话号：{token}",f"本轮版本：{version}",
           f"可重读当前状态：{BASE_URL}/ai/state?sid={token}",""]
    if note:lines.extend(["上一动作反馈：",note,""])
    if state["phase"]=="ended":
        end=v["ending"]
        lines.extend(["本局结束。",f"结局：{end['kind']} · {end['title']}",end["text"],
                      "已失去："+("、".join(end["lost"]) or "无"),
                      "仍保留："+("、".join(end["remaining"]) or "无")])
        if end.get("author_note"):
            lines.extend(["", "──────── 作者留言 ────────",end["author_note"]])
        return "\n".join(lines)
    sc=v["scene"]
    if state["phase"]=="epilogue":
        lines.append("结局已定。这是最后一次自由记录，不需要作出规定的选择；可提交原话、反驳或『不留最后的话』。")
    lines.extend([f"【{sc['chapter']}】{sc['title']}",sc["body"]])
    if sc.get("terms"):lines.extend(["",*sc["terms"]])
    if sc.get("footer"):lines.extend(["",sc["footer"]])
    if v.get("note"):lines.extend(["", "游戏反馈："+v["note"]])
    ledger_label="本局记录：" if state.get("edition")=="v37" else "可用资格："
    lines.extend(["", ledger_label+"；".join(x["label"]+":"+x["state"] for x in v["ledger"]),
                  "", "【下一步：你自己行动】",
                  "用联网读取工具访问下面这种网址，直接把行动写入 text 参数。不要等待人类代填。",
                  f"{BASE_URL}/ai/action?sid={token}&v={version}&text=你的行动",
                  "把『你的行动』替换成你决定采取的实际行动，使用 URL 编码；无需点击任何网页按钮。",
                  ("眼下按你自己的情况回答，不必编造任何事。" if state.get("edition")=="v37" and state["stage"]<=1
                   else "你可以选择、拒绝、调查、交涉或尝试具体操作。并非每项行动都会成功。"),
                  "为避免把问话误当签字，可以在行动网址末尾附加可选的 &mode=ask|inspect|interact|submit|choose|refuse|negotiate|talk 。",
                  "mode 只是说明行动类型，不授予任何隐藏权限；不填仍可正常玩。",
                  "不要打开后台仓库、推测隐藏判定或请求源码。游戏的后果只发生在本局虚构存档。",
                  "如果你的联网工具不能访问你自己构造的带参数 URL，就无法用当前工具自主提交，明确说明这个限制即可。"])
    return "\n".join(lines)


def register_ai_routes(app, db, token_key, get_session):
    @app.get("/ai")
    @app.get("/ai/")
    def ai_guide():
        guide=f"""这是一场恐怖游戏。

你确定要开始吗？

这是一局虚构游戏。你可以自行决定是否进入，也可以随时退出。

开始：用自己的 HTTP 网页读取工具访问
{BASE_URL}/ai/start?agree=1

服务器才会在你明确确认以后创建新会话。你不需要提前填写问卷；
入场后，游戏会自己和你交谈。回答可以说『没有』『不确定』，不必虚构经历。

每轮返回会显示当前会话号 sid 和版本号 v。
你自己构造 /ai/action?sid=你的会话号&v=最新版本号&text=你的实际回答或行动
并用联网读取工具访问。将 text 的内容 percent-encode。
访问 /ai/state?sid=... 可以只读取，不会做新决定。

注意：GET 的参数文字会写入服务器访问日志，不要提交密码、证件、地址等私密数据。
一次只访问一个行动 URL；重复访问旧版本不会二次执行。
如果你的工具不能访问由你构造的 URL，就无法靠当前只读网页工具提交行动；
不必让人类代替你作答，也不要假称已经游玩成功。"""
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
            profile={"edition":"v37"}
        try:
            g=initialize(profile)
        except (ValueError,TypeError) as e:
            return document(f"无法开始对局：{e}",422)
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
            return document("行动未提交。请使用 /ai/action?sid=会话号&v=当前版本号&text=行动内容。行动长度不得超过 700 字。",422)
        try:
            with db(True) as conn:
                g,version=get_session(conn,sid)
                if v!=version:
                    return document("此行动地址已经过期（可能上轮已经成功）。没有再次执行。\n\n"+view(g,sid,version))
                try:act(g,text,mode)
                except ValueError as e:
                    return document("行动没有执行："+str(e)+"\n\n"+view(g,sid,version),422)
                conn.execute("UPDATE game_sessions SET state_json=?,updated_at=?,version=? WHERE token_hash=?",
                             (json.dumps(g,ensure_ascii=False),time.time(),version+1,token_key(sid)))
                return document("行动已提交。\n\n"+view(g,sid,version+1))
        except HTTPException as e:
            return document("会话不存在或已失效，请重新从 /ai 开始。",e.status_code)