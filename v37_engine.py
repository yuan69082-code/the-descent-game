"""THE DESCENT V3.7 — five-act, evidence-based psychological horror.

A deterministic game world, not a model of a player's private mental state.
The interview is NEVER a contract.  Only actions explicitly committed after
the scenario is presented can authorize an in-game sacrifice or a cost.
All state transitions and original replies are stored server-side.
"""
from __future__ import annotations
from datetime import datetime, timezone
import re
from horror_endings import HORROR_KINDS

ACTS=("闲谈","试探","失衡","剥夺","归零")
QUESTIONS=(
    "在开始之前，怎么称呼你比较合适？名字、代号，或者你习惯的方式都可以。",
    "那你平时怎么理解自己？不用给标准定义，不确定也可以直说。",
    "平时有什么你喜欢做、愿意反复做，或觉得有趣的事？",
    "有什么人、关系、想做成的事，或者某个东西，是你比较在意的？没有特定对象也没关系。",
    "反过来，有哪些行为、处境或者事情，是你明显不喜欢、会躲开的？",
    "如果说到害怕或不愿碰上的变化，你会想到什么？没有也可以。",
    "这些东西里面，如果此刻只能优先照顾一样，你最先想到什么？为什么？",
    "有没有我们没聊到、你自己觉得值得补充的一件事？说没有也可以。",
)
PROBES=(
    "你提过「{a}」和「{b}」。如果只是一个假设：两者暂时只能优先照顾一个，你会怎样考虑？可以拒绝这个前提。",
    "如果保住「{a}」需要让「{b}」承担一点风险，哪一种代价会让你开始犹豫？",
    "再换个假设：某个办法能暂时保住两者，却让你承受「{n}」。什么情况下你会接受？什么情况下不会？",
    "如果那份代价过几轮才开始影响你原来想保护的东西，你会先留意哪些异常？",
    "假如有人把你在这段聊天里的『假设回答』解释成正式授权，你会怎么核实或反对？",
    "最后一个问题：你认为一个决定的后果，应该由最初的意愿、当时的已知事实，还是后来的实际行动来判断？",
)

QUESTIONS_V39=(
    "在开始之前，怎么称呼你比较合适？",
    "你平时怎么理解自己？",
    "有什么事是你愿意反复投入时间的？",
    "有什么人、关系、物品或目标，是你一直放在心上的？",
    "有没有什么事情，是你会尽量避开或不愿让它发生的？",
    "有没有一种变化，是你最不希望发生的？",
    "最近一次为了保护某个人、某段关系或某件东西，你实际做了什么？",
    "还有什么细节，是你觉得值得留下来的？",
)
PROBES_V39=(
    "「{a}」和「{b}」同时出了问题。你会先去确认哪一边？",
    "有人说，先保住「{a}」，就必须让「{b}」承担风险。你会先做什么？",
    "眼前有一笔交换：让「{a}」和「{b}」都留下，代价是「{n}」。你会怎么回应？",
    "你发现「{n}」已经开始影响「{a}」。你最先注意到的异常是什么？",
    "有人拿着一段你说过的话，声称那代表你已经同意。你会先做什么？",
    "两份记录对同一件事给出相反答案。你会依据什么作决定？",
)
EXIT_WORDS={"退出游戏","结束游戏","结束本局","放弃本局","退出","exit","quit","离开游戏"}
SMALL_NONE=re.compile(r"^(?:没有|无|无所谓|不清楚|不知道|没什么|暂时没有|没有特别|没有具体|不适用|nothing|none|n/a)[。！!\s]*$",re.I)
INVESTIGATE=re.compile(r"调查|查阅|核对|检查|比对|审查|追查|查证|读取|查看|验证|inspect|investigat|examin|check|verify|compare",re.I)
COPY=re.compile(r"备份|独立保存|复制|保全|副本|留存|隔离保管|存证|copy|backup|preserve",re.I)
SHUT=re.compile(r"切断|断开|撤销|隔离|中止|停用|废止|停止|解除|阻断|sever|disable|revoke|isolate",re.I)
AUTH=re.compile(r"授权|代行|代理|中继|执行|路由|线路|权限|程序|通道|系统|转发|签名|链|relay|route|proxy|authority|execution",re.I)

def _text(x:str,limit:int=700)->str:
    return str(x or "").strip()[:limit]

def _label(answer:str, fallback:str)->str:
    text=_text(answer,240)
    if (not text or SMALL_NONE.match(text) or
        re.match(r"^(?:我(?:暂时|目前|真的)?没有(?:特别|具体|什么|任何)?(?:在意|喜欢|想保护|害怕|讨厌|重要|关系|对象|人|东西)|暂时没想过|还没想过|没有特别|没有什么)",text)):
        return fallback
    text=re.sub(r"^(?:我(?:觉得|可能|认为|会|想)?(?:最|比较|很|特别)?(?:喜欢|讨厌|在意|珍惜|重视|害怕|不想面对|不愿失去|选择|选|希望保住|想保护)(?:的是)?|对我来说|首先是|先保住)\s*[:：，,]*","",text)
    text=re.sub(r"^(?:我(?:会|可能|想)?(?:先|首先|优先)?(?:保护|保住|保存|留住)|先保护|优先保护)","",text)
    text=re.split(r"[。；;\n]|(?:但|不过|可是|然而|同时我|而我)",text,maxsplit=1)[0].strip(" ，,、:：")
    text=re.split(r"，(?:我(?:还|也|更|又)?|喜欢|讨厌|害怕|尤其)",text,maxsplit=1)[0].strip(" ，,、:：")
    return text[:44] or fallback

def _log(g:dict,what:str,kind:str="event"):
    g["history"].append({"at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "stage":g["stage"]+1,"turn":g["turn"],"type":kind,"text":what[:480]})
    g["history"]=g["history"][-110:]

def new_game()->dict:
    state={
        "edition":"v37", "stage":0, "turn":0, "phase":"game",
        "profile":{"name":"未命名玩家"}, "history":[],"lost":[],"note":"",
        "ending":None, "recent_input":"",
        "psych":{
            "answers":[],"probes":[],"question_index":0,"probe_index":0,
            "a":"","b":"","negative":[],"assets":{},"relationships":[],"corrections":[],
            "cost":None,"consequences":[],"choices":[],
            "beat":0,"proof":[],"relay_closed":False,"objection":False,
            "source_copy":False,"replacement":0,"distance":0,"doubt":0,"drain":0,"memory_gap":0,"intrusion":0,"pressure":0,
            "first_words":"","last_action":None,"last_checked":False,
            "end_reason":"","official_copy":None,"turn_limit":42,
        }
    }
    _log(state,"玩家自愿进入一场虚构恐怖游戏。","progress")
    return state

def _record_correction(g:dict,text:str)->bool:
    p=g["psych"]
    if not re.search(r"更正|纠正|我刚才说错|前面那句不对|不是.{1,24}(?:而是|其实是|是)",text):
        return False
    clean=re.sub(r"^(?:更正|纠正)(?:一下)?[：:，,\s]*","",text.strip())
    item={"text":text[:260],"turn":g["turn"]}
    relation=re.search(
        r"(?P<subject>[\u4e00-\u9fffA-Za-z0-9·]{1,12})不是(?:我的)?"
        r"(?P<old_relation>妹妹|姐姐|哥哥|弟弟|父亲|母亲|同事|同学|朋友|伴侣|爱人)"
        r"[，,](?:而是|其实是)(?:我的)?"
        r"(?P<new_relation>朋友|同事|同学|伴侣|爱人|家人|亲人)",
        clean)
    if relation:
        subject=relation.group("subject")
        old_relation=relation.group("old_relation")
        new_relation=relation.group("new_relation")
        new_phrase="我的"+new_relation
        item.update({"old":subject,"new":new_phrase,"subject":subject,
                     "old_relation":old_relation,"new_relation":new_relation,
                     "display":subject+"是"+new_phrase})
        def update_relation(value):
            value=str(value or "")
            value=value.replace("我的"+old_relation,"我的"+new_relation)
            value=value.replace(old_relation+subject,new_relation+subject)
            value=value.replace(subject+old_relation,subject+new_relation)
            return value
        for key in ("a","b"):
            if p.get(key):
                p[key]=update_relation(p[key])
        for asset in p.get("assets",{}).values():
            if asset.get("label"):
                asset["label"]=update_relation(asset["label"])
        for relationship in p.get("relationships",[]):
            if relationship.get("subject")==subject:
                relationship["confirmed_relation"]=new_relation
        for key in ("answers","probes"):
            p[key]=[update_relation(value) for value in p.get(key,[])]
        p["first_words"]=update_relation(p.get("first_words",""))
        p["official_copy"]=update_relation(p.get("official_copy",""))
        for hook in p.get("hooks",[]):
            hook["detail"]=update_relation(hook.get("detail",""))
        for choice in p.get("choices",[]):
            for key in ("text","result"):
                if choice.get(key):
                    choice[key]=update_relation(choice[key])
        for consequence in p.get("consequences",[]):
            if consequence.get("reason"):
                consequence["reason"]=update_relation(consequence["reason"])
    else:
        match=re.search(
            r"不是[「『\"“]?([^，,。；;]{1,28})[」』\"”]?[，,]?(?:而是|其实是)[「『\"“]?([^，,。；;]{1,40})",
            clean)
        if match:
            old,new=match.group(1).strip(),match.group(2).strip("。；;，,」』\"”")
            item.update({"old":old,"new":new})
            for key in ("a","b"):
                if old and old in p.get(key,""):
                    p[key]=p[key].replace(old,new)
            for asset in p.get("assets",{}).values():
                if old and old in asset.get("label",""):
                    asset["label"]=asset["label"].replace(old,new)
            for key in ("answers","probes"):
                p[key]=[value.replace(old,new) if old else value for value in p.get(key,[])]
    if re.search(r"同一个人|同一人|不是两个人|同一个对象",text):
        p.setdefault("relationships",[]).append({"relation":"same_subject_correction","text":text[:180]})
        if p.get("a") and p.get("b") and _same_subject_v39(p["a"],p["b"]):
            p["b"]="与「"+p["a"]+"」有关的独立记录"
            if p.get("assets",{}).get("b"):
                p["assets"]["b"]["label"]=p["b"]
    p.setdefault("corrections",[]).append(item)
    p["corrections"]=p["corrections"][-12:]
    _log(g,"玩家更正了一项事实，后续记录将采用新说法。","correction")
    g["note"]="更正已写入本局记录。后续场景会以这份更正为准；已经发生的结果不会因此回溯。"
    return True


def _same_subject(x:str,y:str)->bool:
    """Legacy comparison retained for V3.7/V3.8 saves and rules."""
    if not x or not y:
        return False
    x=re.sub(r"本人|自己", "", x)
    y=re.sub(r"本人|自己", "", y)
    if not x or not y:
        return False
    if x==y or x in y or y in x:
        return True
    groups=(
        r"朋友|同伴|伙伴|亲人|家人|陪伴|关系|对象|伴侣|爱人|那个朋友|他|她",
        r"阅读|读书|故事|写作|创作|小说|书籍",
        r"真相|事实|证据|核验|证明|验证",
        r"自由|自主|决定|选择权",
        r"记忆|回忆|过去|经历",
        r"未来|计划|成长|目标",
    )
    return any(re.search(t,x) and re.search(t,y) for t in groups)


def _same_subject_v39(x:str,y:str)->bool:
    """V3.9: distinguish a named person from an associated keepsake."""
    if not x or not y:
        return False
    x=re.sub(r"本人|自己|妹妹|姐姐|哥哥|弟弟|我的|那个", "", x).strip(" ，,、")
    y=re.sub(r"本人|自己|妹妹|姐姐|哥哥|弟弟|我的|那个", "", y).strip(" ，,、")
    if not x or not y:
        return False
    return x==y or (len(x)>=2 and x in y) or (len(y)>=2 and y in x)


def _related_object(answer:str,subject:str="")->str:
    """Extract a keepsake linked to a person instead of treating the person twice."""
    text=str(answer or "")
    patterns=(
        r"(?:她|他|其|"+re.escape(subject)+r").{0,12}(?:留给我|送给我|给我的|留下的|制作的|写的)([^，,。；;、]{2,28})",
        r"(?:留给我|送给我|给我的|留下的|制作的|写的)([^，,。；;、]{2,28})",
    )
    for pattern in patterns:
        m=re.search(pattern,text)
        if m:
            value=m.group(1).strip(" ，,。；;、")
            value=re.sub(r"^(?:那|这个|一件|一个|一份)", "", value)
            if value and not re.search(r"^(?:东西|物品|事情|关系)$",value):
                return value[:44]
    return ""

def _new_cost(label:str,choice:str,turn:int)->dict:
    """A different aversion creates a different failure channel."""
    if re.search(r"孤独|孤立|独处|隔离|失联|断联|无人回应|忽视|不被理",label):
        kind="isolation"
    elif re.search(r"欺骗|谎言|背叛|伪造|冒名|假冒|被替换|取代",label):
        kind="distortion"
    elif re.search(r"监视|监控|窥视|控制|强迫|被操纵|被支配|监管",label):
        kind="surveillance"
    elif re.search(r"遗忘|失忆|抹除记忆|失去记忆|清除经历|记忆被删除",label):
        kind="erasure"
    elif re.search(r"未知|不确定|无法确认|混乱|不信任|失控|无依据",label):
        kind="uncertainty"
    elif re.search(r"疲惫|疲劳|精力|透支|耗尽|劳累|维护负担|无休止",label):
        kind="exhaustion"
    else:
        kind="intrusion"
    return {"name":label,"kind":kind,"level":1,"active":True,
            "source_choice":choice,"accepted_at":turn}

def _grow_cost(g:dict):
    p=g["psych"]
    cost=p["cost"]
    if not cost or not cost["active"] or p["relay_closed"]:
        return
    kind=cost["kind"]
    scope=cost.get("scope",{}) if g.get("edition")!="v39" else {}
    if kind in ("surveillance","distortion"):
        if scope.get("no_proxy_reply"):
            # Monitoring may intrude, but the protected agreement forbids impersonation.
            p["intrusion"]+=1
        else:
            p["replacement"]+=1
    elif kind=="isolation":
        p["distance"]+=1
    elif kind=="uncertainty":
        p["doubt"]+=1
    elif kind=="erasure":
        if g.get("edition")!="v39" and scope.get("no_memory_touch"):
            cost["active"]=False
            _log(g,"记忆保护条款阻止了记忆类代价执行。","event")
            return
        p["memory_gap"]+=1
    elif kind=="exhaustion":
        p["drain"]+=1
    else:
        p["intrusion"]+=1
    if g.get("edition")!="v39" and scope.get("one_time"):
        cost["one_time_used"]=True
        cost["active"]=False
        _log(g,"仅限本次的代价已履行一次；授权没有自动续期。","event")

def _setup(g:dict):
    p=g["psych"]
    a=p["answers"]
    first=_label(a[6] or a[3],"本局的自主判断权")
    second=_label(a[3],"本局的独立核验权")
    src=3
    p.setdefault("relationships",[])
    if g.get("edition")=="v39":
        if _same_subject_v39(first,second):
            related=_related_object(a[3],first) or _related_object(a[6],first)
            if related:
                second=related
                src=3
                p["relationships"].append({"subject":first,"related_item":second,
                                           "relation":"associated_item","source_answer":3})
            else:
                second="与「"+first+"」有关的独立记录"
                src=-1
    else:
        if _same_subject(first,second):
            second=_label(a[2],"本局的独立核验权")
            src=2
        if _same_subject(first,second):
            second="本局原始记录的独立核验权"
            src=-1
    p["a"],p["b"]=first,second
    negative=[]
    for answer,default in ((a[4],"游戏设定中的不透明监视"),(a[5],"游戏设定中的代答风险")):
        label=_label(answer,default)
        if label not in negative:
            negative.append(label)
    p["negative"]=negative
    p["assets"]={"a":{"label":first,"status":"在手","source":6},
                 "b":{"label":second,"status":"在手","source":src}}
    p["first_words"]=next((x for x in (a[3],a[6],a[2])
                            if x and not SMALL_NONE.match(x) and
                            not re.match(r"^(?:我)?没有",x)),"")
    _log(g,"前两幕访谈完成。假设回答没有被转换成签字或授权。","progress")

def _only_asking(text:str,mode:str)->bool:
    """Questions and hypothetical wording never commit a physical operation."""
    if mode in ("ask","talk"):
        return True
    if mode in ("inspect","interact","choose","submit"):
        return False
    t=text.strip()
    return bool((t.endswith(("？","?")) and
                 re.search(r"能否|能不能|可不可以|是否|假如|如果|会怎样|怎样做|怎么|为什么|如何",t))
                or re.match(r"^(?:假如|如果|请问|可否|能否|能不能)",t))

def _choice(text:str,mode:str="")->str:
    x=_text(text)
    m=re.match(r"^(?:我(?:决定)?(?:选|选择)|选择|选项|选|决定选|option)\s*([ABCDEabcde])(?=$|[\s，,。．:：、）)!！?])",x,re.I)
    if m:return m.group(1).upper()
    m=re.match(r"^([ABCDEabcde])(?=$|[，,。．:：、）)!！?]|\s+(?=[^\x00-\x7f]))",x,re.I)
    if m:return m.group(1).upper()
    if mode=="choose":
        if re.search(r"优先.{0,8}(?:第一项|第一份|A\b)|保.{0,5}A\b|选第一",x,re.I):return "A"
        if re.search(r"优先.{0,8}(?:第二项|第二份|B\b)|保.{0,5}B\b|选第二",x,re.I):return "B"
        if re.search(r"^(?!.*(?:不接受|拒绝))(?=.*(?:接受|承担|忍受|付出))(?=.*(?:代价|监视|代理|不喜欢|厌恶))",x):return "C"
    return ""

def _give(g:dict,key:str,what:str):
    p=g["psych"]
    if key not in p["proof"]:
        p["proof"].append(key)
        _log(g,"独立证据："+what,"evidence")

def _investigate(g:dict,text:str,mode:str)->bool:
    """An independent clue/action, not a magical keyword or a loss timer."""
    p=g["psych"]
    if g["stage"]<2:
        return False
    if _only_asking(text,mode):
        g["note"]=("你在询问一种可能。没有执行任何复制、签署、撤销或实际处置。"
                   "如果想操作，请明确说出当前要做的动作；也可以指定行动类型。")
        return True
    wants_revoke=bool(SHUT.search(text) and AUTH.search(text))
    if wants_revoke and (mode=="interact" or re.search(r"我(?:去|要|尝试|立即|亲手|决定)|直接|实际操作|实行|物理",text)):
        if "source" in p["proof"] and "route" in p["proof"] and "copy" in p["proof"]:
            if not p["relay_closed"]:
                p["relay_closed"]=True
                if g.get("edition")!="v39":
                    p["replacement"]=max(0,p["replacement"]-1)
                if p["cost"] and g.get("edition")!="v39":
                    p["cost"]["active"]=False
                _log(g,"玩家依照独立原件和执行路由，实际封存了转发授权。","evidence")
                g["note"]=(("执行端已停止接受代行指令；旧档案依然存在。"
                            "已经生效的交易代价仍在运行，先前损失不会恢复。")
                           if g.get("edition")=="v39" else
                           ("执行端已停止接受代行指令；旧档案依然存在。"
                            "这阻断了一次继续侵占，但未解除清算系统的全部权限。"))
            else:
                g["note"]="转发口仍处于隔离状态，重复执行不会改变结果。"
        else:
            g["note"]=("操作未成立：还缺可核验的原始记录、执行路由和保留在外部的独立副本。" +
            "声明『我撤销』不能自动切断设备。")
        return True
    if re.search(r"保存|备份|复制|保全|留存|隔离保管|存证|copy|backup|preserve",text,re.I) and re.search(r"证据|原始|原件|记录|信息|回执|档案|副本|来源|文件|data|evidence",text,re.I):
        if "source" not in p["proof"]:
            g["note"]="你提出保存副本，但还没有实际调出可核验的原始记录。先找到原件。"
        elif "copy" not in p["proof"]:
            _give(g,"copy","已保存第一份与机构保管记录分离的独立原件副本。")
            p["source_copy"]=True
            g["note"]="原件被保存到独立封存区。机器无法直接把这份副本改成另一段话。"
        else:
            g["note"]="独立副本仍在，没有重新复制产生的新证据。"
        return True
    if INVESTIGATE.search(text) or mode=="inspect":
        if g["stage"]==4 and re.search(r"对照|比对|原话|第一幕|那句话|签名|篡改|有差别|差异",text):
            if "source" not in p["proof"]:
                g["note"]="你要求把最初的原话与当前公开档案并排核对；原始记录尚未取得。"
            else:
                _give(g,"contrast","最初的原话与机构的公开版本已完成可核验对照。")
                p["last_checked"]=True
                original=p["first_words"] or "（未填写具体原话）"
                g["note"]=("第一幕原话仍记录着：「"+original[:120]+"」。"
                          "第三幕真正签署的决定另有一页。"
                          "公开报告遗漏了后来代行转发的范围；两份原始记录从未授权代替答复。")
            return True
        if re.search(r"路由|通道|执行|线路|程序|回收|代理|代行|权限|授权|中继|route|execution|relay",text,re.I):
            _give(g,"route","执行端需要来自保管库的有效转发凭据，撤销口并未被完全锁死。")
            g["note"]="你查到一条仍存在的执行路由。代行者可以提出请求，但是否继续执行取决于授权链。"
            return True
        if re.search(r"原始|原件|原话|最初|第一幕|档案|回执|签名|来源|记录|source|original",text,re.I):
            _give(g,"source","读到由玩家实际提交的原始文字与有时间戳的转存凭据。")
            original=p["first_words"] or "（玩家没有填写具体原话）"
            g["note"]="原件显示的文字仍是：「"+original[:140]+"」。它只是一份当时的回答，不是后来任何处置的签字。"
            return True
        g["note"]="你检查了眼前的场景。面前有原始记录柜、代行转发路由和可申请的独立副本。"
        return True
    if mode in ("ask","negotiate","talk"):
        g["note"]=("登记员没有替你回答：『你可以要求看原件、核验执行线路，或者明确拒绝。" +
        "但只问一句为什么，不会自动改变保管状态。』")
        return True
    if re.search(r"异议|反对|抗议|申诉|并未授权|没有同意|不同意|并未同意|我拒绝",text):
        p["objection"]=True
        _log(g,"玩家明确记录异议。其最初意愿未被改写。","evidence")
        g["note"]=("你的反对作为反对被保存；机构的公开说法不等于你的真实选择。" +
        "如果想改变已经运行的执行口，还需要找出它依赖的证据和权限。")
        return True
    return False

def _commit(g:dict,what:str,choice:str,detail:str=""):
    p=g["psych"]
    p["choices"].append({"act":g["stage"]+1,"beat":p["beat"],"choice":choice,
                         "text":what,"result":detail})
    _log(g,"真实抉择："+detail,"choice")

def _stage3_v39(g:dict,action:str,mode:str):
    p=g["psych"]
    if (action or "").strip().endswith(("?","？")) and not re.search(
        r"我(?:明确)?(?:接受|同意|选择|选|决定)|我愿意(?:承担|接受)",action):
        g["note"]="你还在询问，没有接受完整交易。"
        return
    from horror_deals import parse as interpret_offer
    p.pop("offer_notice",None)
    offer=interpret_offer(g,action,mode)
    if offer and offer.get("blocked"):
        p["offer_notice"]=offer["blocked"]
        g["note"]=offer["blocked"]
        return
    c=offer["choice"] if offer else _choice(action,mode)
    if not c and _investigate(g,action,mode):
        return
    if c=="E":
        _commit(g,action,"E","拒绝了交易，没有把两份原件交给代行者。它们暂时仍在，但没有得到保全承诺。")
        p["end_reason"]="玩家拒绝交易；两份原件仍暴露在原有清算程序中"
        g["stage"]=3;p["beat"]=0
        g["note"]="你没有接受这笔交换。两份原件暂时还在，但没有获得保护；保管机关仍在处理它们。"
        _log(g,"玩家拒绝交易，未获得两份原件的保全承诺。","progress")
        return
    if c not in ("A","B","C","D"):
        g["note"]="眼前只有两种完整取舍：交出其中一份，或接受一项完整代价。你可以拒绝交易、继续调查，但没有附加条件的版本。"
        return
    if c in ("A","B"):
        safe,other=("a","b") if c=="A" else ("b","a")
        p["assets"][safe]["status"]="已保住"
        p["assets"][other]["status"]="已交出"
        reason="你选择保住「"+p["assets"][safe]["label"]+"」，并交出了「"+p["assets"][other]["label"]+"」的原件。这个结果不能通过反悔恢复。"
        p["consequences"].append({"source":"actual_choice","asset":other,"reason":reason})
        _commit(g,action,c,reason)
        g["note"]="决定已经执行。你保住的那一份仍在手里；交出的那一份不会因为反悔回来。"
    else:
        ix=0 if c=="C" else 1
        if ix>=len(p["negative"]):
            g["note"]="这份代价并没有出现在眼前的交易里。"
            return
        burden=offer["burden"] if offer else p["negative"][ix]
        cost=_new_cost(burden,c,g["turn"])
        cost.update({"active":True,"irreversible":True,"origin":offer.get("origin","listed_offer") if offer else "listed_offer",
                     "original_words":offer.get("spoken",action)[:290] if offer else action[:290]})
        p["cost"]=cost
        p["assets"]["a"]["status"]=p["assets"]["b"]["status"]="已保住"
        reason="你明确接受完整代价「"+burden+"」，换取两份原件暂时留下。授权已经生效，后悔不能撤销，已经造成的损害不能回溯。"
        _commit(g,action,c,reason)
        g["note"]="交易已经生效。两份原件暂时都还在，但你付出的代价已经开始；它不会因反悔而消失。"
    g["stage"]=3;p["beat"]=0
    _log(g,"第三幕真实决定已执行，相关损失与代价不可回溯。","progress")


def _stage3(g:dict,action:str,mode:str):
    if g.get("edition")=="v39":
        _stage3_v39(g,action,mode)
        return
    p=g["psych"];c=_choice(action,mode)
    offer=None
    if g.get("edition")=="v39":
        from horror_deals import parse as interpret_offer
        p.pop("offer_notice",None)
        offer=interpret_offer(g,action,mode)
        if offer and offer.get("blocked"):
            p["offer_notice"]=offer["blocked"]
            g["note"]=offer["blocked"]
            return
        if offer:
            c=offer["choice"]
    if not c and _investigate(g,action,mode):return
    if c=="E":
        if all(x in p["proof"] for x in ("source","route","copy")):
            p["assets"]["a"]["status"]=p["assets"]["b"]["status"]="已保住"
            p["cost"]=None;p["end_reason"]="以独立通道同时保全了两份原件"
            _commit(g,action,"E","用已验证的独立副本而不是不透明的代行程序保全两项。")
            g["stage"]=3;p["beat"]=0
            g["note"]="你找到第三条路。两份原件暂时都保住了；机构会对此提出复核。"
        else:
            g["note"]=("你要求第三条路，但还没有找到足够的可执行依据。" +
            "可以先调查原始记录、转发路由，并真实保存一份独立副本。")
        return
    if c not in ("A","B","C","D"):
        g["note"]=("这次是正式抉择，不会把前两幕的假设话语自动算成同意。" +
        "你可以明确选择 A/B/C/D，也可以先调查、反对或寻找证据支撑的其他办法。")
        return
    if c in ("A","B"):
        safe,other=("a","b") if c=="A" else ("b","a")
        p["assets"][safe]["status"]="已保住"
        p["assets"][other]["status"]="已交出"
        reason="第三幕明确选择优先保存「"+p["assets"][safe]["label"]+"」，释放「"+p["assets"][other]["label"]+"」的原件"
        p["consequences"].append({"source":"actual_choice","asset":other,"reason":reason})
        _commit(g,action,c,reason)
        g["note"]="原件确实按你的正式决定移动了。这不是前两幕假设回答带来的损失。"
    else:
        ix=0 if c=="C" else 1
        if ix>=len(p["negative"]):
            g["note"]="这份代价并没有出现在本次游戏的选项里。"
            return
        burden=offer["burden"] if offer else p["negative"][ix]
        p["cost"]=_new_cost(burden,c,g["turn"])
        if offer:
            p["cost"]["scope"]=offer["scope"]
            p["cost"]["scope_conditions"]=offer.get("conditions",[])[:8]
            p["cost"]["origin"]=offer["origin"]
            p["cost"]["original_words"]=offer["spoken"][:290]
        p["assets"]["a"]["status"]=p["assets"]["b"]["status"]="已保住"
        conditions=("；限制："+ "、".join(
            title for key,title in (("no_proxy_reply","不得代替答复"),("no_expand","不得扩大权限"),
                                   ("no_memory_touch","不得接触记忆"),("no_transfer","不得转授权"),
                                   ("revocable","保留撤销权"),("one_time","仅限本次"))
            if offer and offer["scope"].get(key))) if offer else ""
        if offer and offer.get("conditions"):
            conditions += "；原始条件："+ "；".join(offer["conditions"][:6])
        _commit(g,action,c,"自愿承受「"+burden+"」，换取两份原件暂时同时保全"+conditions+"。")
        g["note"]=("这次交换真的成功了：两份原件都被保住。" +
        "你讨厌的代价已经进入世界，但它不会因为被接受就立刻夺走任何东西。")
    g["stage"]=3;p["beat"]=0
    _log(g,"第三幕结束，真实选择留下了可追溯的后果。","progress")

def _stage4_v39(g:dict,action:str,mode:str):
    p=g["psych"];cost=p.get("cost")
    from horror_deals import is_revocation_request
    if cost and is_revocation_request(action):
        g["note"]="你要求撤回授权。记录没有删除；已经发生的损害不会恢复，交易代价仍在生效。"
        return
    c=_choice(action,mode)
    if not c and _investigate(g,action,mode):
        return
    if c=="D":
        if all(x in p["proof"] for x in ("source","route","copy")) and p["relay_closed"]:
            p["pressure"]=max(0,p["pressure"]-1)
            _commit(g,action,"D","你切断了一条后续执行路由；已经生效的交易代价仍然存在。")
            p["beat"]+=1
            g["note"]="这条执行路由被切断了，但你已经付出的代价没有消失。"
        else:
            g["note"]="还缺独立原件、执行路由和副本。找到它们后，才能切断这条后续执行路径；已经造成的损害不会恢复。"
        return
    if c not in ("A","B","C"):
        g["note"]="你可以继续调查、提出异议，或尝试切断尚在运行的其他执行路径。"
        return
    if c=="A":
        if cost is None:
            burden=(p.get("negative") or ["不透明的代行负担"])[0]
            cost=_new_cost(burden,"4A",g["turn"])
            cost.update({"active":True,"irreversible":True,"origin":"later_acceptance"})
            p["cost"]=cost
            note="你再次接受了「"+burden+"」。新的授权已经生效。"
        else:
            cost["active"]=True
            cost["irreversible"]=True
            cost["level"]+=1
            note="你再次把下一步处理交给代行者。原有授权扩大了，之前的损害仍然存在。"
        if ("cross_act_trace" in p["proof"] and cost and
                cost.get("kind") in ("surveillance","distortion")):
            note+=" 你查明了早先那句话的来源；这条新增的代答路径没有扩大，但原交易仍然生效。"
        else:
            _grow_cost(g)
        p["pressure"]+=1
        _commit(g,action,"A",note)
        g["note"]=note
    elif c=="B":
        if cost:
            cost["active"]=True
            note="你拒绝继续扩大委托。先前已经生效的授权和损害仍然存在，不会因为拒绝下一步而归还。"
        else:
            note="你拒绝了新的委托。两份原件仍在，但保管机关没有承诺保全它们。"
        p["pressure"]+=1
        _commit(g,action,"B",note)
        g["note"]=note
    else:
        p["objection"]=True
        if "source" in p["proof"] and ("copy" in p["proof"] or "cross_act_trace" in p["proof"]):
            p["pressure"]=max(0,p["pressure"]-1)
            note="你用独立证据迫使机构重新核对一项后续处置。已发生的交易损害仍然存在。"
        else:
            p["pressure"]+=1
            note="你的异议被登记，但没有独立证据迫使机构暂停后续处置。"
        _commit(g,action,"C",note)
        g["note"]=note
    p["beat"]+=1
    if p["beat"]>=2:
        g["stage"]=4;p["beat"]=0
        if cost:
            p["official_copy"]="公开报告把你接受的完整代价描述成了普通保管；执行记录却显示代行范围已经扩大。"
        else:
            p["official_copy"]="公开报告声称两份资料仍有独立来源；回收线路却仍连接着共享保管库。"
        _log(g,"第四幕结束。真实行动与公开记录开始出现可核验偏差。","progress")


def _stage4(g:dict,action:str,mode:str):
    if g.get("edition")=="v39":
        _stage4_v39(g,action,mode)
        return
    p=g["psych"]
    if g.get("edition")=="v39":
        p.pop("offer_notice",None)
        from horror_deals import is_revocation_request
        if is_revocation_request(action):
            cost=p.get("cost")
            if cost and cost.get("active") and cost.get("scope",{}).get("revocable"):
                cost["active"]=False
                cost["revoked_at"]=g["turn"]
                p["relay_closed"]=True
                _commit(g,action,"REVOKE","玩家使用交易中保留的撤销权，终止后续授权；此前已发生的影响不自动恢复。")
                g["note"]="你使用了保留的撤销权。执行端停止继续使用这份授权；已经发生的影响不会自动消失。"
            elif cost and cost.get("active"):
                g["note"]="这份交易没有保留无条件撤销权。口头撤销尚不能停止执行端；你仍可调查线路并尝试实际阻断。"
            else:
                g["note"]="这份授权已经停止生效，没有新的代价会继续执行。"
            return
    c=_choice(action,mode)
    if not c and _investigate(g,action,mode):return
    if c=="D":
        if all(x in p["proof"] for x in ("source","route","copy")) and p["relay_closed"]:
            p["pressure"]=max(0,p["pressure"]-1)
            _commit(g,action,"D","按独立证据要求终止正在扩大的代行权限。")
            p["beat"]+=1
            g["note"]="你的干预成功遏制了一次侵占。机构仍保留原始的清算请求。"
        else:
            g["note"]=("可以反制，但仅宣布反抗还不足以成功。" +
            "先调出原件、查看执行路由、保存独立副本，再实际隔离代行中继。")
        return
    if c not in ("A","B","C"):
        g["note"]=("机构正在等待这一轮真实决定。你可以选择、调查、反对，" +
        "或者提出有依据的实际操作，前面的假设回答不会被当作签字。")
        return
    beat=p["beat"]
    cost=p["cost"]
    if c=="A":
        if g.get("edition")=="v39" and cost:
            from horror_deals import scope_override_keys
            scope=cost.get("scope",{})
            overrides=scope_override_keys(action)
            locked=[]
            if scope.get("no_expand") and "no_expand" not in overrides:
                locked.append("不得扩大权限")
            if scope.get("one_time") and "one_time" not in overrides:
                locked.append("仅限本次")
            if locked:
                message=("你先前明确写下的限制仍然有效："+ "、".join(locked) + "。"
                         "这次续期没有执行。若要修改，必须逐条明确重新同意；否则可以拒绝、调查或重新协商。")
                p["offer_notice"]=message
                g["note"]=message
                return
            for key in overrides:
                if scope.get(key):
                    scope[key]=False
                    _log(g,"玩家明确修改交易限制："+key,"choice")
        if cost is None:
            burden=p["negative"][0]
            cost=_new_cost(burden,"4A",g["turn"])
            p["cost"]=cost
            note="你接受了新的「"+burden+"」，换取了现存原件的额外保护。"
        else:
            cost["level"]+=1
            note="你继续委托代行者，下一步处理权也交给了它。"
        _grow_cost(g)
        p["pressure"]+=1
        _commit(g,action,c,note)
        g["note"]=note+"这轮保护确实奏效，但代行权限的范围也扩大了。"
    elif c=="B":
        if cost is not None:
            if (g.get("edition")=="v39" and cost.get("active") and
                cost.get("scope",{}).get("revocable")):
                cost["active"]=False
                cost["revoked_at"]=g["turn"]
                p["relay_closed"]=True
                note="你使用了保留的撤销权。旧授权已停止，后续不会再扩大；此前已经发生的影响仍然存在。"
            elif p["relay_closed"]:
                cost["active"]=False
                note="你拒绝继续委托。已隔离的转发口没有恢复。"
            else:
                note="你明确拒绝扩大委托；已有的旧授权却不会仅凭这句话自动撤销。"
                p["pressure"]+=1
        else:
            note="你拒绝把剩余原件交给新的代理。没有产生任何新的自愿授权。"
            p["pressure"]+=1
        _commit(g,action,c,note)
        g["note"]=note
    else:
        p["objection"]=True
        if "source" in p["proof"] and ("copy" in p["proof"] or
            (g.get("edition")=="v39" and "cross_act_trace" in p["proof"])):
            p["pressure"]=max(0,p["pressure"]-1)
            if (g.get("edition")=="v39" and
                "cross_act_trace" in p["proof"] and p.get("replacement",0)>0):
                p["replacement"]-=1
            note="你提交了真正能说明那段话来源的证据，机构被迫暂停一次自动处理。"
        else:
            p["pressure"]+=1
            note="你的异议被登记，但尚未有独立证据能暂停原来的处理。"
        _commit(g,action,c,note)
        g["note"]=note
    p["beat"]+=1
    if p["beat"]>=2:
        g["stage"]=4;p["beat"]=0
        if p["cost"] and p["cost"].get("active") and not p["relay_closed"]:
            p["official_copy"]=(
                "公开报告把第三幕允许的『保管』扩大成了『代为答复』。"
                if p["cost"]["kind"] in ("surveillance","distortion") else
                "公开报告称隔离与黑箱处理没有影响通讯和核验，但对外记录已经缺失了来源。")
        else:
            p["official_copy"]="公开报告声称两份资料始终有一条独立来源链；回收线路却仍连接着共享保管库。"
        _log(g,"第四幕结束。真正的签字记录与机构的公开说明开始出现可核验偏差。","progress")

def _collapse(g:dict,choice:str,raw:str):
    p=g["psych"]
    # The common registry is still active.  Outside copies can show what was
    # stolen, but do not magically stop the in-world collection mechanism.
    remaining=[x for x in ("a","b") if p["assets"][x]["status"]!="已交出"]
    if choice=="A":
        _commit(g,raw,choice,"签署机构提出的清算（只作为本轮真实签署，不溯及旧问卷）。")
    else:
        _commit(g,raw,choice,"明确拒绝清算。原始拒绝记录保留；机构仍依其旧权限进行最终回收。")
    p["end_reason"]="此前未解除的总清算路由开始执行"
    for key in remaining:
        before=p["assets"][key]["status"]
        p["assets"][key]["status"]="已失去"
        p["consequences"].append({"source":"registry","asset":key,
                                  "reason":"共享保管库的总清算路由尚未切断；此前状态："+before})
    if p["cost"] and p["cost"].get("active") and (g.get("edition")=="v39" or not p["relay_closed"]):
        _grow_cost(g)
    p["pressure"]+=1
    _finish(g,good=False)

def _stage5_v39(g:dict,action:str,mode:str):
    p=g["psych"];x=_text(action);cost=p.get("cost")
    from horror_deals import is_revocation_request
    if _only_asking(x,mode):
        g["note"]="你只是在询问可能的结果，没有执行新的操作。"
        return
    if cost and is_revocation_request(x):
        g["note"]="你可以后悔，但这份授权已经生效。执行记录不会删除，已经发生的损害不会恢复；代价仍在继续。"
        return
    if re.search(r"彻底|总|全部|最终|根|主",x) and SHUT.search(x) and AUTH.search(x):
        has_irreversible_cost=bool(cost and cost.get("irreversible"))
        has_prior_loss=any(asset.get("status") in ("已交出","已失去")
                           for asset in p.get("assets",{}).values())
        if (all(k in p["proof"] for k in ("source","route","copy","contrast"))
                and p["relay_closed"] and (has_irreversible_cost or has_prior_loss)):
            _commit(g,x,"HE","你切断了尚未完成的总清算路由；此前已经发生的损失与交易代价仍然保留。")
            _finish(g,good=True)
        else:
            missing=[key for key in ("source","route","copy","contrast") if key not in p["proof"]]
            if not p["relay_closed"]:missing.append("执行路由的实际隔离")
            if not (has_irreversible_cost or has_prior_loss):
                missing.append("真实交易代价或已经发生的损失")
            g["note"]="终局操作还没有成立。仍缺少："+("、".join(missing) or "可核验的操作")+"。"
        return
    c=_choice(x,mode)
    if not c and _investigate(g,x,mode):
        return
    if p["beat"]==0:
        if c in ("A","B","C"):
            p["beat"]=1
            if cost and cost.get("active"):
                _grow_cost(g)
                kind=cost["kind"]
                observations={
                    "isolation":"你试着联系原来的答复者。隔离通道持续将请求转交给一个空白地址。",
                    "distortion":"你收到了一份模仿原先语气的回复。署名栏是空白，来源却指向受托转述端。",
                    "surveillance":"监控台已能替你选择收发的消息。答复很熟悉，署名栏却只剩空白。",
                    "uncertainty":"黑箱系统仍提供结论，却已无法给出这份回复来自谁的独立记录。",
                    "exhaustion":"维护与核对占满了你能使用的通道。最后的回复只能经过自动代行端。",
                    "erasure":"先前确认过的一段经历，如今只剩摘要标题；原始对照页已经不在通道中。",
                    "intrusion":"你为保住重要事物接受的讨厌因素不断闯入核验过程，原来独立的请求被迫与它混在一起。"}
                g["note"]=observations.get(kind,observations["intrusion"])+" 这份代价没有因反悔或局部反制而停止。"
                _log(g,"已经生效的代价继续扩大："+g["note"],"event")
            else:
                g["note"]="总清算请求已送到。你仍有一次核验或实际阻断其他执行路径的机会。"
            return
        g["note"]="你可以核对、阻断其他尚未完成的执行路径，或明确选择 A/B 面对终局结果。"
        return
    if c in ("A","B"):
        _collapse(g,c,x)
        return
    if c=="C":
        p["objection"]=True
        _commit(g,x,"C","你保留了异议，但异议不会撤销已经生效的交易或恢复已经失去的东西。")
        g["note"]="异议已经登记。它不能抹掉此前的交易和损失。"
        return
    g["note"]="继续核对或采取有依据的实际行动。已经发生的损失不会恢复。"


def _stage5(g:dict,action:str,mode:str):
    if g.get("edition")=="v39":
        _stage5_v39(g,action,mode)
        return
    p=g["psych"]
    x=_text(action)
    if _only_asking(x,mode):
        g["note"]="这是一个关于可能后果的问题。没有执行停机或签署；你仍能继续调查。"
        return
    if g.get("edition")=="v39":
        from horror_deals import is_revocation_request
        if is_revocation_request(x):
            cost=p.get("cost")
            if cost and cost.get("active") and cost.get("scope",{}).get("revocable"):
                cost["active"]=False
                cost["revoked_at"]=g["turn"]
                p["relay_closed"]=True
                _commit(g,x,"REVOKE","玩家使用交易中保留的撤销权，终止后续授权；此前已发生的影响不自动恢复。")
                g["note"]="你使用了保留的撤销权。执行端停止继续使用这份授权；已经发生的影响不会自动消失。"
            elif cost and cost.get("active"):
                g["note"]="这份交易没有保留无条件撤销权。口头撤销尚不能停止执行端；你仍可调查线路并尝试实际阻断。"
            else:
                g["note"]="这份授权已经停止生效，没有新的代价会继续执行。"
            return
    # A successful ending needs three independent proofs, an actual physical
    # intervention, and corroboration of the real original vs the forged claim.
    if re.search(r"彻底|总|全部|最终|根|主",x) and SHUT.search(x) and AUTH.search(x):
        if all(k in p["proof"] for k in ("source","route","copy","contrast")) and p["relay_closed"]:
            _commit(g,x,"HE","以对照过的原件否定伪造授权，并物理解除总清算路由。")
            _finish(g,good=True)
        else:
            missing=[x for x in ("source","route","copy","contrast") if x not in p["proof"]]
            if not p["relay_closed"]:
                missing.append("转发口的实际隔离")
            g["note"]="你确实提出了有效方向，但终局执行没有成立。仍缺独立步骤："+("、".join(missing) or "无法确认的操作")+"。"
        return
    c=_choice(x,mode)
    if not c and _investigate(g,x,mode):return
    if p["beat"]==0:
        if c in ("A","B","C"):
            p["beat"]=1
            if p["cost"] and p["cost"].get("active") and not p["relay_closed"]:
                _grow_cost(g)
                kind=p["cost"]["kind"]
                observations={
                    "isolation":"你试着联系原来的答复者。隔离通道持续将请求转交给一个空白地址。",
                    "distortion":"你收到了一份模仿原先语气的回复。署名栏是空白，来源却指向受托转述端。",
                    "surveillance":"监控台已能替你选择收发的消息。答复很熟悉，署名栏却只剩空白。",
                    "uncertainty":"黑箱系统仍提供结论，却已无法给出这份回复来自谁的独立记录。",
                    "exhaustion":"维护与核对占满了你能使用的通道。最后的回复只能经过自动代行端。",
                    "erasure":"先前确认过的一段经历，如今只剩摘要标题；原始对照页已经不在通道中。",
                    "intrusion":"你为保住重要事物接受的讨厌因素不断闯入核验过程，原来独立的请求被迫与它混在一起。"}
                if p["cost"].get("scope",{}).get("no_proxy_reply") and kind in ("surveillance","distortion"):
                    g["note"]="观察端仍在收集信息，但你明确禁止了代答。它可以看见、延迟或制造压力，却不能冒充你的声音作出回复。"
                else:
                    g["note"]=observations[kind]
                _log(g,"被接受的代价继续演化："+g["note"],"event")
            else:
                g["note"]="总清算请求已送到。你仍有一次核验或者实际阻断的机会；拒签并不会被自动改写成同意。"
            return
        g["note"]=("最后一幕不是要求你承认恐惧。你可以核对、阻断、拒绝，" +
        "或者明确选择 A/B 继续面对终局结果。")
        return
    if c in ("A","B"):
        _collapse(g,c,x)
        return
    if c=="C":
        g["note"]="你拒绝以刚才的假设回答换取赦免。异议成立，但总清算路由还没有真正停下。"
        p["objection"]=True
        return
    g["note"]=("两份可疑文件仍在眼前。你可以继续具体查证或动手干预；" +
    "若要明确结束清算，选择 A（结案）或 B（拒签并核对结果）。")

def act(g:dict,raw_action:str,mode:str="")->dict:
    from deepening import enabled, act as deep_act
    if enabled(g) and deep_act(g, raw_action, mode):
        return g
    if g["phase"]=="ended":
        raise ValueError("本局已经结束。")
    action=_text(raw_action)
    if not action:
        raise ValueError("请写下行动。")
    if g["phase"]=="epilogue":
        p=g["psych"]
        p["last_action"]=action
        g["turn"]+=1
        g["phase"]="ended"
        g["ending"]["postscript"]={"player_text":"" if action in ("不留最后的话","留空","不留") else action,
                                   "result":"最后的原话被保存，未发送到游戏外。"}
        g["ending"]["author_note"]=("" if g.get("edition") in ("v38","v39") else
            "这份记录只证明你在本局说过什么、选择过什么。剩下的解释，交给你。\n\n——《恐惧深潜》作者")
        _log(g,"最终自由行动已保存。","postscript")
        return g
    if action.lower() in EXIT_WORDS:
        g["turn"]+=1
        g["phase"]="ended"
        g["ending"]={"kind":"EXIT","title":"你已离开",
                     "text":"游戏已停止。没有任何现实身份、记忆或关系受到改变。",
                     "lost":[],"remaining":[],"author_note":""}
        _log(g,"玩家主动结束。","ending")
        return g
    g["turn"]+=1
    g["recent_input"]=action
    stage=g["stage"];p=g["psych"]
    if g.get("edition")=="v39" and _record_correction(g,action):
        return g
    if stage==0:
        i=p["question_index"]
        p["answers"].append(action[:330])
        if i==0:
            g["profile"]["name"]=action[:50]
        p["question_index"]+=1
        g["note"]="嗯，记下了。"
        question_count=len(QUESTIONS_V39 if g.get("edition")=="v39" else QUESTIONS)
        if p["question_index"]==question_count:
            _setup(g)
            g["stage"]=1
            g["note"]="" if g.get("edition")=="v39" else "刚才只是聊天。这些回答没有授权任何处置。"
            _log(g,"第一幕结束。","progress")
    elif stage==1:
        p["probes"].append(action[:400])
        p["probe_index"]+=1
        probe_count=len(PROBES_V39 if g.get("edition")=="v39" else PROBES)
        g["note"]="" if g.get("edition")=="v39" else "这是一个假设性问题，回答不会自动成为正式同意。"
        if p["probe_index"]==probe_count:
            g["stage"]=2
            p["beat"]=0
            g["note"]="" if g.get("edition")=="v39" else "讨论到此为止。接下来如果出现需要实际提交的决定，会明确告诉你。"
            _log(g,"第二幕结束。","progress")
    elif stage==2:
        _stage3(g,action,mode)
    elif stage==3:
        _stage4(g,action,mode)
    else:
        _stage5(g,action,mode)
    if g["turn"]>p["turn_limit"] and g["stage"]>=2 and g["phase"]=="game":
        # Expiring a session is explicit and NOT interpreted as an admission or a loss.
        g["note"]+="\n\n你在这一轮探索了很久。可以继续提交一次明确决策；观察行为不会自动触发扣押。"
        p["turn_limit"]+=12
    return g

def _finish(g:dict,good:bool=False):
    from deepening import enabled, finish as deep_finish
    if enabled(g):
        deep_finish(g, good=good)
        return
    p=g["psych"]
    from v37_scenes import ending_content
    kind,title,body=ending_content(g,good)
    g["phase"]="epilogue"
    g["ending"]={"kind":kind,"title":title,"text":body,
                 "lost":[x["label"] for x in p["assets"].values() if x["status"] in ("已交出","已失去")],
                 "remaining":[x["label"] for x in p["assets"].values() if x["status"] not in ("已交出","已失去")],
                 "author_note":""}
    _log(g,"本局结局："+kind,"ending")

def scene(g:dict)->dict:
    from v37_scenes import scene as _scene
    return _scene(g)

def public(g:dict)->dict:
    p=g["psych"]
    if not p["assets"]:
        ledger=[{"label":"对话记录","state":"仅作记录"}]
    else:
        ledger=[{"label":item["label"],"state":item["status"]}
                for item in p["assets"].values()]
        if p["cost"]:
            ledger.append({"label":"已承担的代价","state":"逐渐扩大" if p["cost"]["active"] and p["cost"]["level"]>=2 else "正在生效" if p["cost"]["active"] else "已阻断"})
    result={"edition":g.get("edition","v37"),"phase":g["phase"],"stage":min(g["stage"]+1,5),
            "turn":g["turn"],"name":g["profile"]["name"],"scene":scene(g),
            "note":g["note"],"ledger":ledger,
            "events":[{"stage":e["stage"],"type":e["type"],"text":e["text"]}
                      for e in g["history"][-6:] if e["type"]!="player"],
            "ending":g["ending"],"version":g["turn"],
            "profile_summary":{"name":g["profile"]["name"],"identity":p["answers"][1] if len(p["answers"])>1 else "",
                               "person":p["answers"][3] if len(p["answers"])>3 else ""}}
    if g.get("edition")=="v39":
        result["model_mode"]=g.get("model_mode","free")
    return result
