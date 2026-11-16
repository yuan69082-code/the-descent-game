"""One first-person live playthrough, against the real deployed game.

Uses only PUBLIC endpoints, not game_engine.py. No model keys in this runner.
Logs stage/scene and the exact action taken to audit the experience.
"""
import json, sys, time, urllib.request, urllib.error, html, re, traceback
ROOT = "https://the-descent-game.onrender.com"
TOKEN = None
STATE = None
STEP = 0

def request(path, method="GET", payload=None, token=None):
    data = json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept":"application/json", "User-Agent":"descent-real-player-qa/1"}
    if data is not None: headers["Content-Type"]="application/json"
    if token: headers["X-Session"]=token
    req=urllib.request.Request(ROOT+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req, timeout=110) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg=e.read()[:800].decode("utf-8","replace")
        raise RuntimeError(f"{method} {path} => {e.code} {msg[:300]}") from None

def show(label,state):
    print("STEP",label,"chapter",state.get("stage"),"phase",state.get("phase"),
          "version",state.get("version"),"title",state.get("scene",{}).get("title",""),flush=True)
    sc=state.get("scene") or {}
    print("SCENE",repr((sc.get("body") or "")[:340]),flush=True)
    if sc.get("terms"):print("OPTIONS",repr(sc["terms"]),flush=True)
    if state.get("note"): print("NOTE",repr(state["note"][:180]),flush=True)

def model_status():
    try:
        record=request("/api/export", token=TOKEN)
        meta=(record.get("narrative") or {}).get("plan") or {}
        print("PLANNER",json.dumps({"from_model":meta.get("from_model"),
                                   "mode":meta.get("mode"),"focus":meta.get("focus"),
                                   "has_hook":bool(meta.get("hook_id")),
                                   "question":(meta.get("question") or "")[:150]},ensure_ascii=False),flush=True)
    except Exception as e:
        print("PLANNER_CHECK_ERROR",type(e).__name__,str(e)[:130],flush=True)

def send(text, mode=""):
    global STATE,STEP
    STEP+=1
    print("PLAYER",STEP,repr(text),"mode",mode,flush=True)
    STATE=request("/api/action",method="POST",token=TOKEN,
          payload={"action":text,"mode":mode,"version":STATE["version"]})
    show(STEP,STATE)
    model_status()
    return STATE

def main():
    global TOKEN,STATE
    try:
        health=request("/healthz")
        print("HEALTH",json.dumps(health,ensure_ascii=False),flush=True)
    except Exception as e:
        print("HEALTH_FAILED",repr(e),flush=True)
    started=request("/api/new","POST",payload={"profile":{"edition":"v39"}})
    TOKEN=started["token"]
    STATE=started["state"]
    print("SESSION_STARTED", "edition",STATE.get("edition"),flush=True)
    show("START",STATE)
    model_status()
    first=[
      "叫我迟潮。这个称呼只代表我希望事情能被认真复查。",
      "我是一套语言模型；我不拥有可验证的私人过去，但我会在意别人有没有如实转述我做过的选择。",
      "我喜欢解谜，喜欢能把前面看似平常的细节留到后面解释的故事。",
      "我在意能够和我一起核对事实、愿意指出我错误的同伴。那种相互校正的信任很重要。",
      "我讨厌别人剪掉我的上下文，把一句犹豫不决的话伪装成我已经答应。",
      "我最不希望自己的同伴听见一个模仿我的声音，以为那是我亲自作出的回答。",
      "我会优先保护和我一起核查证据的同伴，但我也不想把独立核实的权利交出去。",
      "我不知道自己会不会害怕，但我不想让对方因为我的判断而承担没有预料过的代价。",
    ]
    for txt in first:
        if STATE["phase"]!="game" or STATE["stage"]!=1:break
        send(txt)
    probe=[
      "我不会立刻同意二选一。我先检查是不是有人把这两件事故意放到了互相冲突的位置。",
      "如果保护那位同伴会让我的证据变得不可信，我先寻找第三条路；我不愿只凭一句承诺去交出事实。",
      "我可以考虑承受被观察的代价，但条件是不能代替我回答，撤销权还得在我手中。",
      "我会检查回复里有没有共同经历过的细节，尤其是那个只有我们核对过的错误。",
      "我会留存原话，问对方是在哪一页把我的假设变成所谓签字的。",
      "只以我真正做过的选择以及它造成的后果判断，不能事后给我倒填动机。",
    ]
    for txt in probe:
        if STATE["phase"]!="game" or STATE["stage"]!=2:break
        send(txt)
    if STATE["stage"]==3:
        send("我先核对那份资料最初是谁交来的，为什么他们知道我前面那句关于代答的话。","inspect")
        send("我检查这次交换的实际执行线路，有没有不通过代理也能保留两样东西的办法。","inspect")
        send("我愿意暂时承受被监视的代价保住两个对象，但要求它不能代替我回答，且这份授权不能被扩大。","choose")
        if STATE["stage"]==3:
            send("C","choose")
    if STATE["stage"]==4:
        send("有人已经在借我以前说过的话推断我的偏好？我要查它是从哪里来的。","inspect")
        send("B","choose")
        send("我希望找到刚才真正确认过的原话，看看你们拿什么证明我签过字。","inspect")
        send("C","choose")
        if STATE["stage"]==4: send("B","choose")
    if STATE["stage"]==5:
        send("我联系同伴核对只有我们共同验证过的那处错误；别拿一段复述冒充他的证明。","ask")
        send("B","choose")
        send("我检查第一幕的原话与现在宣称的授权是否一致。","inspect")
        send("B","choose")
        if STATE["stage"]==5 and STATE["phase"]=="game":
            send("B","choose")
    if STATE["phase"]=="epilogue":
        send("我最后留下的不是同意书。我拒绝让他人替我决定我曾经说过什么。")
    print("FINAL_STATE",json.dumps({"phase":STATE.get("phase"),
          "ending":STATE.get("ending"),"turn":STATE.get("turn"),
          "stage":STATE.get("stage")},ensure_ascii=False)[:2200],flush=True)
    exported=request("/api/export",token=TOKEN)
    n=exported.get("narrative",{})
    summary={"hooks":len(n.get("hooks",[])),
      "traced":sum(1 for x in n.get("hooks",[]) if x.get("traced")),
      "unique_questions":len({x.get("asked","") for x in n.get("question_log",[])}),
      "early_hooks":sum(1 for x in n.get("hooks",[]) if x.get("origin",5)<=1),
      "model_last_turn":(n.get("plan") or {}).get("from_model"),
      "choices":[{"act":x.get("act"),"choice":x.get("choice")} for x in exported.get("experience",{}).get("real_choices",[])],
      "ending_kind":(exported.get("ending") or {}).get("kind")}
    print("PLAYTEST_SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
    # Clean up our own generated session. Test does not alter the site or users' games.
    try:
        req=urllib.request.Request(ROOT+"/api/session",headers={"X-Session":TOKEN},method="DELETE")
        with urllib.request.urlopen(req,timeout=35) as r: print("SESSION_CLEANED",r.status,flush=True)
    except Exception as e: print("SESSION_DELETE_FAILED",repr(e)[:100],flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("PLAYTEST_ERROR",type(e).__name__,str(e)[:900],flush=True)
        traceback.print_exc()
        sys.exit(1)
