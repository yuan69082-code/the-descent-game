"""Model-backed horror director. Only Python can decide actual world state."""
from __future__ import annotations
import json
import os
import re
import logging
import time
from contextvars import ContextVar
from urllib.parse import urlparse

_model_log=logging.getLogger("the_descent.model")
_last_failure = ContextVar("descent_model_failure", default=None)


def failure_hint():
    """Request-local diagnostics only; no keys, prompts, replies or session IDs."""
    item = _last_failure.get()
    if not item:
        return ""
    reasons = {"timeout": "上游模型响应超时", "truncated": "上游模型输出被截断",
               "empty_json": "上游模型没有返回正文", "empty_content": "上游模型没有返回正文",
               "invalid_json": "上游模型未返回有效结构数据", "network_error": "上游模型连接中断",
               "http_error": "上游模型服务返回错误", "provider_error": "上游模型返回错误"}
    reason = reasons.get(item["category"], "上游模型本次未完成")
    return reason + "（服务端已尝试" + str(item["attempt"]) + "次）。"


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


def model_enabled(g):
    """Explicit V3.9 mode is fixed at game creation; None preserves legacy sessions."""
    mode=g.get("model_mode")
    return configured() if mode is None else mode=="model" and configured()

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

def _completion(messages,max_tokens,fast=False):
    """Bounded, provider-aware model request. Never logs keys, prompts or replies."""
    _last_failure.set(None)
    if not configured():
        return None
    import httpx
    endpoint=_endpoint()
    host=urlparse(endpoint).hostname or "unknown"
    is_deepseek=host=="api.deepseek.com"
    planning=max_tokens>=400
    payload={"model":os.environ["HORROR_LLM_MODEL"].strip(),
             "messages":messages,"temperature":0.85}
    if is_deepseek:
        if fast:
            # Low effort still enables thinking. Short JSON planning and intent
            # extraction explicitly use the same model in non-thinking mode.
            payload["max_tokens"]=1024 if planning else 384
            payload["thinking"]={"type":"disabled"}
            payload["reasoning_effort"]="none"
        else:
            # Preserve the established V3.8 director request profile.
            payload["max_tokens"]=max(3072 if planning else 1024,max_tokens*4)
            payload["reasoning_effort"]="high" if planning else "low"
        payload["response_format"]={"type":"json_object"}
    else:
        payload["max_completion_tokens"]=max(320,max_tokens)

    # Keep V3.9's worst-case pair (classifier + planner retry) below the
    # hosting request ceiling. Legacy V3.8 keeps its original timeout profile.
    read_timeout=((32 if planning else 15) if fast else 25) if is_deepseek else 25
    attempts=2 if is_deepseek and planning and fast else 1
    timeout=httpx.Timeout(connect=8,read=read_timeout,write=15,pool=8)

    def retry_pause(response=None):
        delay=0.6
        if response is not None:
            raw=response.headers.get("Retry-After","")
            try:
                delay=max(delay,min(float(raw),1.5))
            except (TypeError,ValueError):
                pass
        time.sleep(delay)

    def safe_failure(category,attempt,exc=None,status=None):
        _last_failure.set({"category": category, "attempt": attempt, "status": status})
        _model_log.warning(
            "model_request_failed provider=%s category=%s class=%s http_status=%s attempt=%s/%s",
            host,category,type(exc).__name__ if exc else "none",
            str(status) if status is not None else "none",attempt,attempts)

    with httpx.Client(timeout=timeout,follow_redirects=False) as client:
        for attempt in range(1,attempts+1):
            try:
                response=client.post(endpoint,headers={
                    "Authorization":"Bearer "+os.environ["HORROR_LLM_API_KEY"].strip(),
                    "Content-Type":"application/json"},json=payload)
                response.raise_for_status()
                data=response.json()
                # DeepSeek may return a generation error inside an HTTP 200 body.
                if isinstance(data,dict) and data.get("error"):
                    err=data.get("error") or {}
                    code=str(err.get("code") or err.get("type") or "provider_error")
                    retryable=code in ("server_error","timeout","rate_limit_exceeded")
                    if retryable and attempt<attempts:
                        _model_log.warning("model_request_retry provider=%s category=%s attempt=%s/%s",
                                           host,code,attempt,attempts)
                        retry_pause()
                        continue
                    safe_failure("provider_error",attempt,status=200)
                    return None
                choices=data.get("choices") if isinstance(data,dict) else None
                if not isinstance(choices,list) or not choices:
                    if attempt<attempts:
                        _model_log.warning("model_request_retry provider=%s category=missing_choices attempt=%s/%s",
                                           host,attempt,attempts)
                        retry_pause()
                        continue
                    safe_failure("missing_choices",attempt)
                    return None
                choice=choices[0] if isinstance(choices[0],dict) else {}
                finish_reason=choice.get("finish_reason")
                if finish_reason=="length":
                    # Retrying with the same token ceiling would repeat the same truncation.
                    safe_failure("truncated",attempt)
                    return None
                if finish_reason=="content_filter":
                    safe_failure("content_filter",attempt)
                    return None
                if finish_reason in ("insufficient_system_resource","aborted"):
                    if attempt<attempts:
                        _model_log.warning("model_request_retry provider=%s category=%s attempt=%s/%s",
                                           host,finish_reason,attempt,attempts)
                        retry_pause()
                        continue
                    safe_failure(finish_reason,attempt)
                    return None
                message=choice.get("message") or {}
                answer=message.get("content")
                if isinstance(answer,list):
                    answer="".join(str(v.get("text","")) for v in answer if isinstance(v,dict))
                if not isinstance(answer,str) or not answer.strip():
                    category="empty_json" if is_deepseek else "empty_content"
                    if attempt<attempts:
                        _model_log.warning("model_request_retry provider=%s category=%s attempt=%s/%s finish_reason=%s",
                                           host,category,attempt,attempts,finish_reason or "none")
                        retry_pause()
                        continue
                    safe_failure(category,attempt)
                    return None
                parsed=_parse(answer[:12000])
                if parsed is None:
                    if attempt<attempts:
                        _model_log.warning("model_request_retry provider=%s category=invalid_json attempt=%s/%s",
                                           host,attempt,attempts)
                        retry_pause()
                        continue
                    safe_failure("invalid_json",attempt)
                    return None
                return parsed
            except json.JSONDecodeError as ex:
                if attempt<attempts:
                    _model_log.warning("model_request_retry provider=%s category=invalid_response_json attempt=%s/%s",
                                       host,attempt,attempts)
                    retry_pause()
                    continue
                safe_failure("invalid_response_json",attempt,ex)
                return None
            except httpx.HTTPStatusError as ex:
                status=ex.response.status_code if ex.response is not None else None
                retryable=status in (408,425,429,500,502,503,504)
                if retryable and attempt<attempts:
                    _model_log.warning("model_request_retry provider=%s category=http_%s attempt=%s/%s",
                                       host,status,attempt,attempts)
                    retry_pause(ex.response)
                    continue
                safe_failure("http_error",attempt,ex,status)
                return None
            except httpx.TimeoutException as ex:
                if attempt<attempts:
                    _model_log.warning("model_request_retry provider=%s category=%s attempt=%s/%s",
                                       host,type(ex).__name__,attempt,attempts)
                    retry_pause()
                    continue
                safe_failure("timeout",attempt,ex)
                return None
            except (httpx.NetworkError,httpx.RemoteProtocolError) as ex:
                if attempt<attempts:
                    _model_log.warning("model_request_retry provider=%s category=%s attempt=%s/%s",
                                       host,type(ex).__name__,attempt,attempts)
                    retry_pause()
                    continue
                safe_failure("network_error",attempt,ex)
                return None
            except Exception as ex:
                safe_failure("unexpected_error",attempt,ex)
                return None
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
    edition=g.get("edition")
    if edition not in ("v38","v39") or g["stage"]<2:
        return raw,mode
    if edition=="v39" and g.get("model_mode")=="free":
        return raw,mode
    if edition=="v39" and g.get("model_mode")=="model" and not configured():
        raise RuntimeError("本局选择了语义模型模式，但模型服务当前不可用；没有切换到免费模式。")
    if not configured():
        return raw,mode
    text=raw.strip()
    if edition=="v39" and re.search(r"更正|纠正|我刚才说错|前面那句不对|不是.{1,24}(?:而是|其实是|是)",text):
        return raw,mode
    if edition=="v39":
        from horror_deals import is_revocation_request
        if is_revocation_request(text):
            return raw,mode
    if g.get("edition")=="v39" and g["stage"]==2:
        from horror_deals import parse as read_offer
        if read_offer(g,text,mode) is not None:
            return raw,mode
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
                          {"role":"user","content":json.dumps(request,ensure_ascii=False)[:6200]}],
                         190,fast=edition=="v39")
    if not response:
        if edition=="v39" and g.get("model_mode")=="model":
            raise RuntimeError(failure_hint()+"语义模型暂时没有返回有效的理解结果；本轮没有切换到免费模式。建议10秒后重试同一行动。")
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
