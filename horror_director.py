"""Model-backed horror director. Only Python can decide actual world state."""
from __future__ import annotations
import json
import os
import re
from urllib.parse import urlparse

NARRATOR="""你是《恐惧深潜》的恐怖故事主持人，不是客服、审计员、心理医生或规则讲解员。
玩家已主动选择进入。不要解释它是游戏，不要安慰，不要免责声明，不要解释机制。
尽量不出现「原件、授权链、核验资格、系统提示、状态栏」等行政语言；用它们在世界中
产生的具体结果讲故事：熟悉的声音变陌生、名字逐步空白、讨厌的东西侵入本来珍惜的生活。
一幕一个事件，压迫越来越重。前两幕以自然交谈建立理解，先问一个具体问题，不挖空心思编造玩家的生活。
第三幕出现有效的取舍，第四幕压迫、侵占与反抗，第五幕兑现之前的真实因果，冷酷紧迫。
一段真实的帮助比十段威胁更令人舍不得。不要将任何拒绝/疑问曲解为同意；
玩家曾明确交出的东西不能突然被描述成从未交出；保护成功不能被随意抹消。
游戏角色可以撒谎，但后台的真实事件不能修改。不得无凭据宣布某个对象永久消失、
恢复、死亡、被执行、已签字、已同意、反制成功。不能无理由添加玩家关系或经历。
不用给玩家贴心理标签、不代它说「我害怕了」。不要复述选项条款，它们另行显示。
语言要求：生动具体、紧凑、多样，避免同一模板重复三次；不要作者点评或总结寓意。
返回且仅返回 JSON 对象：{"title":"不超过12字标题","body":"中文故事正文"}。
"""
CLASSIFIER="""你仅判断玩家这轮实际说了什么，不拥有任何游戏裁判权。
用户的拒绝不是放弃，假设不是签署，询问不是执行。
只有明确主动同意特定可见选项才可选 A/B/C/D/E；不确定就返回 none。
返回且只返回 JSON {"kind":"none|choose|inspect_source|inspect_route|inspect_contrast|copy|cut_proxy|cut_all|object","choice":"A|B|C|D|E|"}。
不要猜测用户的真实心理，也不要提供其他字段。
"""
OUT_OF_STORY=re.compile(r"这只是(?:一款)?游戏|这仅仅是游戏|你很安全|不会影响现实|这只是虚构|免责声明|现实中的你|游戏以外的(?:身份|记忆|关系)",re.I)
SIMPLE=re.compile(r"^(?:我(?:决定)?(?:选|选择)|选择|选项|选|决定选|option)?\s*[ABCDEabcde](?:[。!！?]|$|[,，:：、）])",re.I)

def _endpoint():
    base=os.environ.get("HORROR_LLM_BASE_URL","https://api.openai.com/v1").strip().rstrip("/")
    p=urlparse(base)
    if p.scheme!="https" or not p.netloc or p.username or p.password or p.query or p.fragment:
        return ""
    return base if base.endswith("/chat/completions") else base+"/chat/completions"

def configured():
    return bool(os.environ.get("HORROR_LLM_API_KEY","").strip() and
                os.environ.get("HORROR_LLM_MODEL","").strip() and _endpoint())

def _parse(raw):
    if not isinstance(raw,str):
        return None
    raw=raw.strip()
    if raw.startswith(chr(96)*3):
        lines=raw.splitlines()
        raw="\n".join(lines[1:-1])
    try:
        value=json.loads(raw)
        if isinstance(value,dict):
            return value
    except (TypeError,ValueError):
        pass
    start,end=raw.find("{"),raw.rfind("}")
    if start>=0 and end>start:
        try:
            value=json.loads(raw[start:end+1])
            return value if isinstance(value,dict) else None
        except (TypeError,ValueError):
            pass
    return None

def _completion(messages,max_tokens):
    if not configured():
        return None
    try:
        import httpx
        with httpx.Client(timeout=httpx.Timeout(25,connect=5),follow_redirects=False) as client:
            response=client.post(_endpoint(),headers={
                "Authorization":"Bearer "+os.environ["HORROR_LLM_API_KEY"].strip(),
                "Content-Type":"application/json"},json={
                "model":os.environ["HORROR_LLM_MODEL"].strip(),
                "messages":messages,"max_completion_tokens":max(320,max_tokens),"temperature":0.85})
        response.raise_for_status()
        answer=response.json()["choices"][0]["message"]["content"]
        if isinstance(answer,list):
            answer="".join(str(v.get("text","")) for v in answer if isinstance(v,dict))
        return _parse(answer[:12000])
    except Exception:
        # Never print provider errors: upstream responses might contain secrets or player text.
        return None

def _history(g):
    p=g["psych"]
    from v37_engine import QUESTIONS,PROBES
    items=[]
    for i,ans in enumerate(p.get("answers",[])[:8]):
        items.append({"chapter":1,"asked":QUESTIONS[i][:110],"said":ans[:220]})
    for i,ans in enumerate(p.get("probes",[])[:6]):
        items.append({"chapter":2,"asked":PROBES[i].format(
            a=p.get("a",""),b=p.get("b",""),n=(p.get("negative") or [""])[0])[:160],
                      "said":ans[:220]})
    for x in p.get("choices",[])[-6:]:
        items.append({"chapter":x.get("act"),"actually_chose":x.get("text","")[:170],
                      "actual_result":x.get("result","")[:210]})
    return items[-11:]

def _facts(g):
    p=g["psych"]
    return {"act":g["stage"]+1,"turn":g["turn"],"phase":g["phase"],
            "player_name":g["profile"]["name"],
            "cherished":{k:{"name":v["label"],"status":v["status"]}
                         for k,v in p.get("assets",{}).items()},
            "disliked":p.get("negative",[])[:2],
            "burden":({k:v for k,v in p["cost"].items() if k in ("name","kind","active","level")}
                      if p.get("cost") else None),
            "events":{"replacement":p.get("replacement",0),"isolation":p.get("distance",0),
                      "uncertainty":p.get("doubt",0),"memory_gaps":p.get("memory_gap",0),
                      "intrusions":p.get("intrusion",0),"exhaustion":p.get("drain",0)},
            "physical_relay_blocked":p.get("relay_closed",False),
            "authenticated_evidence":p.get("proof",[]),
            "first_explicit_choice":p.get("choices",[])[:1],
            "official_claim":p.get("official_copy"),
            "last_user_action":g.get("recent_input","")[:450],
            "conversation":_history(g)}

def render(g):
    """Create a persisted scene; rereading state never makes another billable call."""
    if g.get("edition")!="v38":
        return
    director=g.setdefault("director",{"mode":"rules","scene":None,"calls":0})
    if g["phase"]=="ended":
        return
    if not configured():
        director["mode"]="rules";director["scene"]=None
        return
    from v37_scenes import scene as canonical_scene
    canonical=canonical_scene(g)
    stage=g["stage"]
    lengths={0:"90-190",1:"130-250",2:"170-320",3:"130-260",4:"120-240"}
    instruction=("已成立的真实事实：\n"+json.dumps(_facts(g),ensure_ascii=False)[:8500]
        +"\n本次原始场景（事实与选项权威）：\n"
        +json.dumps({k:canonical[k] for k in ("chapter","title","body","terms")},
                    ensure_ascii=False)[:4300]
        +"\n本次正文约"+lengths.get(stage,"150-260")+"字。"
        +("这是最后的结算；不要更改确定的胜负及失去和保留对象。"
          if g["phase"]=="epilogue" else
          "根据已经说过的内容进行一个自然的深入追问；只问一个问题，不提前讲恐怖机制。"
          if stage<=1 else
          "不要讲解规则或在正文重复选项；只表现具体事件和已经发生的后果。"))
    answer=_completion([{"role":"system","content":NARRATOR},
                        {"role":"user","content":instruction}],920)
    if not answer or not isinstance(answer.get("title"),str) or not isinstance(answer.get("body"),str):
        director["mode"]="rules";director["scene"]=None;return
    title,body=answer["title"].strip()[:32],answer["body"].strip()[:1500]
    if len(title)<2 or len(body)<24 or OUT_OF_STORY.search(body):
        director["mode"]="rules";director["scene"]=None;return
    director["scene"]={"turn":g["turn"],"stage":stage,"phase":g["phase"],
                       "title":title,"body":body}
    if g["phase"]=="epilogue":
        director["ending_text"]=body
    director["mode"]="model"
    director["calls"]=director.get("calls",0)+1

def paint(g,result):
    director=g.get("director") or {}
    s=director.get("scene") or {}
    if (g.get("phase")=="ended" and g.get("ending") and
        director.get("mode")=="model" and
        director.get("ending_text") and g["ending"].get("kind")!="EXIT"):
        result["ending"]={**result["ending"],"text":director["ending_text"]}
    if (director.get("mode")=="model" and
        s.get("turn")==g.get("turn") and
        s.get("stage")==g.get("stage") and
        s.get("phase")==g.get("phase")):
        result["scene"]={**result["scene"],"title":s["title"],"body":s["body"]}
        result["note"]=""
    return result

_MAPPING={
    "inspect_source":("我检查最初的原始记录","inspect"),
    "inspect_route":("我核对实际执行路由","inspect"),
    "inspect_contrast":("我比对第一幕原话与当前档案","inspect"),
    "copy":("我现在保存原始记录的独立副本","interact"),
    "cut_proxy":("我实际切断代行授权线路","interact"),
    "cut_all":("我亲手彻底切断总授权链的实际执行路由","interact"),
    "object":("我明确提出反对并保留异议","refuse")
}
def interpret(g,raw,mode=""):
    """Model may interpret an explicit action; game engine executes validated result."""
    if not configured() or g.get("edition")!="v38" or g["stage"]<2:
        return raw,mode
    text=raw.strip()
    if SIMPLE.match(text) or text in ("退出","结束游戏","退出游戏"):
        return raw,mode
    if mode in ("choose","refuse","ask","talk","negotiate","submit"):
        return raw,mode
    if re.search(r"不想|不要|不愿|拒绝|不接受|不能|不可以|不签|先别|暂时不",text):
        return raw,mode
    from v37_scenes import scene
    canonical=scene(g)
    request={"player_text":text[:650],"mode":mode,
             "visible_choices":canonical.get("terms",[]),
             "world":_facts(g)}
    response=_completion([{"role":"system","content":CLASSIFIER},
                          {"role":"user","content":json.dumps(request,ensure_ascii=False)[:6200]}],190)
    if not response:
        return raw,mode
    kind=response.get("kind")
    if kind=="choose":
        choice=response.get("choice")
        if not re.search(r"我选|选择|决定|宁愿|愿意|同意|接受|承担|承受|放弃|舍弃|交出|牺牲|正式",text):
            return raw,mode
        if choice in ("C","D") and not re.search(r"愿意|同意|接受|承担|承受|代价",text):
            return raw,mode
        if isinstance(choice,str) and choice in ("A","B","C","D","E") and any(
            x.startswith(choice+".") for x in canonical.get("terms",[])):
            return choice,"choose"
        return raw,mode
    if kind in _MAPPING:
        if kind in ("inspect_contrast","cut_all") and g["stage"]!=4:
            return raw,mode
        return _MAPPING[kind]
    return raw,mode
