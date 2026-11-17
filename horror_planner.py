"""THE DESCENT: model is an invisible backstage planner, never the narrator.

It chooses a limited question/mode/focus/earlier hook. The game server alone
displays scenes, adjudicates actions and decides whether a hook pays off.
A conversation answer is an exposed detail, never implied consent.
"""
from __future__ import annotations
import hashlib
import json
import re
from horror_director import _completion, configured, failure_hint

MODES = {
  0:("smalltalk","interest","contrast","memory"),
  1:("comparison","condition","reversal","boundary"),
  2:("choice","trace","pressure","misdirection"),
  3:("encroachment","cost","trace","bargain"),
  4:("echo","replacement","confrontation","silence"),
}
FOCI=("a","b","aversion","choice")
SLOTS=(
 ("name",r"叫|称呼|名字|代号|名号"),
 ("identity",r"自己|身份|存在|理解|定义|认识"),
 ("likes",r"喜欢|兴趣|享受|愿意|常做|有趣|爱好|好奇"),
 ("attachment",r"在意|珍惜|重要|关系|舍不得|保护|陪伴|谁|值得"),
 ("aversion",r"讨厌|不喜欢|厌恶|排斥|避开|不愿|拒绝"),
 ("fear",r"害怕|恐惧|担心|最怕|不愿面对|失去"),
 ("priority",r"优先|更重要|最重要|先|选择|取舍|保留|愿意"),
 ("extra",r"补充|其他|遗漏|还有|没提|想说|补上"),
)
SLOTS_V39=(
 ("name",r"叫|称呼|名字|代号|名号"),
 ("identity",r"自己|身份|存在|理解|定义|认识"),
 ("likes",r"喜欢|兴趣|享受|愿意|常做|有趣|爱好|好奇"),
 ("attachment",r"在意|珍惜|重要|关系|舍不得|保护|陪伴|谁|值得"),
 ("aversion",r"讨厌|不喜欢|厌恶|排斥|避开|不愿|拒绝"),
 ("fear",r"害怕|恐惧|担心|最怕|不愿面对|失去"),
 ("action",r"保护|为了|做过|行动|采取|核对|留下|帮助|付出"),
 ("extra",r"补充|其他|遗漏|还有|没提|想说|补上"),
)
BANNED=re.compile(r"你(?:已经|明明|亲自)(?:同意|签|放弃)|你必须(?:承认|答应)|"
                  r"你现在(?:已经)?(?:失去|被夺走)|我知道你(?:真的)?(?:害怕|恐惧)|"
                  r"这只是游戏|你很安全|放心|别害怕|免责声明",re.I)
INTERNAL_PROMPT="""你是《恐惧深潜》游戏的幕后策划，不是角色，也不是主持人。
你永远不能对玩家直接说话。你的 JSON 仅交给程序；程序自己显示问答与世界事件。
请理解玩家真正说了什么、珍视什么、厌恶什么、正在试图保护什么，
以及某句话是提问、假设、拒绝还是完整接受。
附加条件不是有效的授权：玩家提出限制时，交易尚未成立，只能让其接受完整代价或拒绝。
一旦玩家明确接受完整交易，授权和损害不可逆；不能因为反悔、局部反制或后续异议而恢复。
不要把拒绝改成同意，不要把闲聊等同签字，不得自作主张剥夺、恢复、签名或决定结局。
不要在玩家可见文字中使用幕名、阶段名或“你之前提过/再换个假设”等策划提示。

【灵活埋伏笔】
第一幕留下的称呼、习惯、关系、喜欢和讨厌可以成为以后 NPC 获得的线索；
第二幕的假设回答可以让敌人看懂玩家的取舍倾向，但不是执行授权；
第三、四幕真正发生的交易、拒绝、保护、调查和代价，可以改变第四或第五幕。
任意早期线索都可能在后续任何一幕出现，不要强制拖到第五幕，也别每个伏笔都兑现。
没有真正发生的行动，就不能伪造对应后果；提前采取有效反制就要改变后续局面。
让玩家自己发现早期言语或行为与后来异常存在可追溯联系，而不是宣告他一定害怕。

任务：从允许的 mode 中选当前游戏节奏，从已有的 hook_id 中选一个要回收的旧线索；
选择 focus 指向当前值得观察的对象。仅在第一、二幕写一个自然、切题的下一问题。
第一幕只可询问后台本轮指定 slot 的主题，不提前透露布局和恐怖机制；
从第二个问题开始必须注意上一轮玩家真正的回答，问他提过的具体细节；
第二幕每一轮都要抓住已有回答中一个具体的、实际出现过的人/习惯/犹豫/拒绝条件，
由此提出下一层假设，不能每一轮换句话重复「你会怎么选」，不能凭空新增他没提过的往事。
如果玩家回答没有，就围绕「没有」本身或另一条真实回答继续，不要编造关系。
第三至第五幕 question 必须为空，
程序会按 mode/focus/hook_id 构建场景，显示正式可用选择并核实因果。
严禁输出展示给玩家的故事正文、直接 NPC 对话、伦理说教、免责协议。
只输出 JSON {"mode":"当前幕允许的枚举值","focus":"a|b|aversion|choice",
"hook_id":"已有线索 ID 或空串","question":"仅第一、二幕的问题，最多110字；其他为空"}。"""

DEEP_PROMPT = """
【V3.12：逐步收窄的经历】
目标是玩家通过本局实际取舍逐渐发现自己在意什么、开始担心下一次接触；不要围绕输赢、通关、最优解策划。
幕内节奏为10/8/4/5/4个主要段落。前两幕建立具体联系，第二幕通过连续处境理解取舍，仍不构成执行授权。
第三幕让实际保护先成功，尾部出现被接受代价的征兆；第四幕让同一征兆可辨认地重现、影响保护手段；第五幕让玩家面对仍想接近却不敢再次确认的对象与未完成后果。
喜欢和厌恶都要理解：厌恶是玩家可能为保留两项而接受的代价，不是可以随意施加的惩罚。
看实际交出、重复保护、主动停止的记录，不仅看自我介绍。target_id可选玩家反复保留的现存对象，other_id选另一现存对象；不能把同一人物和其信物武断当成两个独立牺牲者。
保护记录多也可能来自沉没成本，不能据此断言玩家真正的爱、恐惧、人格或必然崩溃。
没有固定反派。时间、不可兼得的需要、正常运作但有代价的保存方式都可形成困境。
回收event_id必须来自真实事件；区分事实、访谈、角色说法、尚未执行的提议。询问、假设、拒绝和带条件接受不能变成已付代价。
已经停止的路径不可重新写成仍在执行；停止未来影响不能恢复过去损失。调查可获得证据，不自动成为两全的救援。
不临时制造新权限或新代价，不写假签名成真实历史，不在结局突然编造可避免一切的隐藏事实。
question仅前两幕使用；第二幕提问围绕具体处境，避免连串哲学判断题、心理诊断和反复问“你怎么选”。
可额外输出target_id、other_id（来自available_objects的id）、event_id（来自actual_encounters的id）、surface（receipt|signal|window）。
这些字段只建议系统挑选合法对象、回执和呈现方式。不得输出新的事实、直接剧情、NPC台词或结局。
"""

def _deep_facts(g):
    from deepening import SLOTS, available, CHANNELS
    p = g["psych"]
    stage = g["stage"]
    slot = SLOTS[p["question_index"]][0] if stage == 0 else "situated_comparison" if stage == 1 else "consequence"
    deep = p.get("deep", {})
    return {"current_act": stage+1, "beat": p.get("beat", 0), "slot": slot,
        "allowed_modes": MODES[stage], "allowed_focus": FOCI,
        "self_description": [x[:170] for x in p["answers"][:10]],
        "recent_responses": [x[:190] for x in p["probes"][-3:]],
        "prior_questions": [{"question": x.get("asked", "")[:110],
                              "answer": x.get("answered", "")[:140]} for x in p.get("question_log", [])[-3:]],
        "available_objects": [{"id": k, "label": p["assets"][k]["label"],
            "status": p["assets"][k]["status"], "times_protected": p["assets"][k]["held"],
            "source_answer": p["assets"][k]["source"]} for k in available(g)],
        "released_objects": [{"id": k, "label": v["label"]} for k,v in p["assets"].items() if v["status"] == "已交出"],
        "disliked": p["negative"],
        "actual_encounters": [{k: e[k] for k in ("id", "turn", "kind", "text", "cause", "targets") if k in e}
                              for e in deep.get("events", [])[-6:]],
        "accepted_paths": [{"kind": c["kind"], "name": c["name"], "targets": c["targets"],
            "halted": c["halted"], "age": c["age"], "accepted_at": c["accepted_at"],
            "source_event": c["source_event"]} for c in deep.get("costs", [])[-4:]],
        "corrections": p.get("corrections", [])[-2:],
        "last_actual_action": g.get("recent_input", "")[:280]}


def _seed(g):
    p=g["psych"]
    data="|".join([g.get("recent_input",""),p.get("a",""),p.get("b",""),
      ",".join(p.get("negative",[])),str(g.get("stage",0)),
      str(p.get("question_index",0)),str(p.get("probe_index",0)),
      str(p.get("beat",0))])
    return int(hashlib.sha256(data.encode()).hexdigest()[:12],16)

def _eligible(g):
    """Old observations are usable at varied later moments; no fixed countdown."""
    p=g["psych"]
    stage=g["stage"]
    return [x for x in p.get("hooks",[]) if
            x["origin"] <= stage and x["origin"] >=0 and
            x.get("kind")!="imagined_consent" and
            x.get("id") and len(x.get("seen_at",[]))<3]

def fallback(g):
    from v37_engine import QUESTIONS, PROBES, QUESTIONS_V39, PROBES_V39
    p=g["psych"];stage=g["stage"];seed=_seed(g)
    modes=MODES.get(stage,("echo",))
    questions=QUESTIONS_V39 if g.get("edition")=="v39" else QUESTIONS
    probes=PROBES_V39 if g.get("edition")=="v39" else PROBES
    from deepening import enabled, QUESTIONS as DQ, PROBES as DP
    if enabled(g): questions, probes = DQ, DP
    if stage==0:
        question=questions[p["question_index"]]
    elif stage==1:
        question=probes[p["probe_index"]].format(
          a=p.get("a",""),b=p.get("b",""),
          n=(p.get("negative") or ["一个讨厌的代价"])[0])
    else:question=""
    candidates=_eligible(g)
    recent=[x for x in candidates if stage>x["origin"] and stage not in x.get("seen_at",[])]
    hook=(recent[seed%len(recent)]["id"] if recent and (seed//7)%3!=0 else "")
    return {"mode":modes[seed%len(modes)],
            "focus":FOCI[(seed//11)%len(FOCI)],
            "hook_id":hook,"question":question}

def _facts(g):
    from deepening import enabled
    if enabled(g): return _deep_facts(g)
    p=g["psych"];stage=g["stage"]
    active=_eligible(g)
    slots=SLOTS_V39 if g.get("edition")=="v39" else SLOTS
    return {
      "current_act":stage+1,
      "allowed_modes":MODES.get(stage,("echo",)),
      "allowed_focus":FOCI,
      "slot":slots[p["question_index"]][0] if stage==0 else
               "hypothetical" if stage==1 else "story",
      "prior_questions":p.get("question_log",[])[-7:],
      "last_actual_answer":((p.get("probes",[])[-1] if stage==1 and p.get("probes")
                            else p.get("answers",[])[-1] if p.get("answers") else "")[:250]),
      "current_required_topic":slots[p["question_index"]][0] if stage==0 else "probe_real_priority_and_hesitation",
      "interview_answers":p.get("answers",[])[-8:],
      "hypothetical_answers":p.get("probes",[])[-6:],
      "actual_decisions":p.get("choices",[])[-5:],
      "known_values":(p.get("a",""),p.get("b","")),
      "relationships":p.get("relationships",[]),
      "corrections":p.get("corrections",[])[-8:],
      "disliked":p.get("negative",[]),
      "paid_cost":p.get("cost"),
      "model_mode":g.get("model_mode","legacy-auto"),
      "protected_status":p.get("assets"),
      "old_hooks":[{"id":x["id"],"from_act":x["origin"]+1,
                    "kind":x["kind"],"detail":x["detail"][:170],
                    "already_appeared":x.get("seen_at",[])}
                   for x in active[-10:]],
      "actual_executed_changes":p.get("consequences",[])[-5:],
      "can_respond":g["phase"]=="game",
    }

def _question_ok(g,text):
    if not isinstance(text,str) or len(text.strip())<9 or len(text)>110 or BANNED.search(text):
        return False
    stage=g["stage"]
    p=g["psych"]
    if stage==0:
        slot=p["question_index"]
        slots=SLOTS_V39 if g.get("edition")=="v39" else SLOTS
        from deepening import enabled, SLOTS as DS
        if enabled(g): slots = DS
        if not re.search(slots[slot][1],text,re.I):
            return False
    elif stage==1:
        # A model must at least refer to some real prior detail. An entirely
        # generic hypothetical is not a personalized second-act question.
        import re as regex
        from v37_engine import SMALL_NONE
        material=[p.get("a",""),p.get("b",""),*(p.get("negative") or [])]
        material.extend(p.get("answers",[])[2:7])
        material.extend(p.get("probes",[])[-3:])
        stop={"我会","你的","什么","时候","如果","这样","就是","或者",
              "可以","一个","他们","我们","自己","现在","那样","对方",
              "觉得","愿意","选择","重要","你会","是否","问题","可能",
              "一个","事情","一种","这些","的话","没有","还是"}
        fragments=set()
        for source in material:
            if not isinstance(source,str) or SMALL_NONE.match(source.strip()):
                continue
            for chunk in regex.findall(r"[一-龥]{2,}",source):
                for size in (2,3):
                    for i in range(max(0,len(chunk)-size+1)):
                        fragment=chunk[i:i+size]
                        if (fragment not in stop and
                            not fragment.startswith(("我","你","他","她","会","是","不"))):
                            fragments.add(fragment)
        if fragments and not any(fragment in text for fragment in fragments):
            return False
    return True

def create(g):
    """Store a structured plan per turn, never a player-facing model completion."""
    if g.get("edition")!="v39":return
    p=g["psych"]
    if g["phase"]=="ended":return
    default=fallback(g)
    proposal=None
    mode=g.get("model_mode")
    use_model=configured() if mode is None else mode=="model" and configured()
    if mode=="model" and not configured():
        raise RuntimeError("本局选择了语义模型模式，但模型服务当前不可用；没有切换到免费模式。")
    if use_model and g["phase"]=="game":
        from deepening import enabled
        deep = enabled(g)
        request=json.dumps(_facts(g),ensure_ascii=False,default=str)
        if not deep: request = request[:7900]
        proposal=_completion([{"role":"system","content":INTERNAL_PROMPT + (DEEP_PROMPT if deep else "")},
          {"role":"user","content":"请给程序一张下一幕计划卡，不要自己叙述场景。当前事实：\n"+request}],
          420,fast=True)
        if not isinstance(proposal,dict):
            raise RuntimeError(failure_hint()+"语义模型连续调用未完成。本轮行动没有提交，存档版本没有推进，也没有切换到免费模式。建议10秒后重试同一行动。")
    stage=g["stage"]
    current=default.copy()
    applied=False
    if isinstance(proposal,dict):
        if proposal.get("mode") in MODES.get(stage,()):
            current["mode"]=proposal["mode"];applied=True
        if proposal.get("focus") in FOCI:
            current["focus"]=proposal["focus"];applied=True
        valid={x["id"] for x in _eligible(g) if x["origin"]<stage}
        candidate=proposal.get("hook_id")
        if candidate=="":
            current["hook_id"]="";applied=True
        elif isinstance(candidate,str) and candidate in valid:
            current["hook_id"]=candidate;applied=True
        if stage<2 and _question_ok(g,proposal.get("question")):
            current["question"]=proposal["question"].strip();applied=True
    from deepening import enabled, available
    if enabled(g) and isinstance(proposal, dict):
        keys = available(g)
        for field in ("target_id", "other_id"):
            if proposal.get(field) in keys:
                current[field] = proposal[field]
                applied = True
        if current.get("other_id") == current.get("target_id"):
            current.pop("other_id", None)
        events = {e["id"] for e in p.get("deep", {}).get("events", [])}
        if isinstance(proposal.get("event_id"), str) and proposal["event_id"] in events:
            current["event_id"] = proposal["event_id"]
            applied = True
        if proposal.get("surface") in ("receipt", "signal", "window"):
            current["surface"] = proposal["surface"]
            applied = True
    if enabled(g) and use_model and g["phase"] == "game" and not applied:
        raise RuntimeError("语义模型没有返回可使用的计划字段。本轮未提交，存档未推进，没有切换到免费模式。")
    if stage>=2:current["question"]=""
    p["plan"]=dict(current,turn=g["turn"],stage=stage,from_model=applied)
    return p["plan"]

def remember(g,raw:str,previous_stage:int,literal:str|None=None,mode:str=""):
    """Only actual submissions, not mere model plans, have effects."""
    if g.get("edition")!="v39":return
    p=g["psych"]
    p.setdefault("question_log",[])
    p.setdefault("hooks",[])
    value=(raw or "").strip()[:290]
    original=(literal or value).strip()[:290]
    if g["turn"]==0 or not value or value.lower() in ("退出","结束游戏","退出游戏"):
        return
    p.setdefault("literal_actions",[]).append({"act":previous_stage+1,
           "literal":original,"accepted_action":value,"turn":g["turn"]})
    p["literal_actions"]=p["literal_actions"][-55:]
    from deepening import enabled
    if enabled(g) and p.get("corrections") and p["corrections"][-1].get("turn") == g["turn"]:
        return
    current=p.get("plan") or {}
    earlier=next((h for h in p.get("hooks",[]) if h["id"]==current.get("hook_id")
                  and h["origin"]<previous_stage),None)
    investigating=bool(re.search(r"核对|检查|调查|查证|追查|溯源|记录|原话|来源|谁告诉|怎么知道|比对|verify|trace|inspect|check",original,re.I))
    if earlier and previous_stage>=2 and (mode=="inspect" or investigating):
        p.setdefault("traced_hooks",[])
        if earlier["id"] not in p["traced_hooks"]:
            p["traced_hooks"].append(earlier["id"])
            earlier["traced"]=True
            from v37_engine import _log
            _log(g,"玩家追查了此前某段原话为什么会出现在新的场景。","evidence")
            if "cross_act_trace" not in p["proof"]:
                p["proof"].append("cross_act_trace")
    if previous_stage in (0,1):
        from v37_engine import QUESTIONS,PROBES,QUESTIONS_V39,PROBES_V39
        questions=QUESTIONS_V39 if g.get("edition")=="v39" else QUESTIONS
        probes=PROBES_V39 if g.get("edition")=="v39" else PROBES
        from deepening import enabled, QUESTIONS as DQ, PROBES as DP
        if enabled(g): questions, probes = DQ, DP
        i=len(p["answers"])-1 if previous_stage==0 else len(p["probes"])-1
        if i<0:return
        plan=p.get("plan") or {}
        planned=plan.get("question","") if plan.get("stage")==previous_stage else ""
        if previous_stage==0:
            prompt=planned or questions[i]
        else:
            prompt=planned or probes[i].format(
              a=p.get("a",""),b=p.get("b",""),
              n=(p.get("negative") or [""])[0])
        p["question_log"].append({"act":previous_stage+1,"asked":prompt[:160],
                                  "answered":value,"turn":g["turn"]})
        if previous_stage==0 and i not in (0,7):
            kind=("exposed_attachment" if i in (3,6) else "exposed_aversion"
                  if i in (4,5) else "exposed_detail")
        elif previous_stage==1:
            kind="hypothetical_boundary"
        else:kind=None
    elif previous_stage in (2,3,4) and p.get("choices"):
        last=p["choices"][-1]
        kind=("actual_choice" if last.get("act")==previous_stage+1 and
              last.get("text")==value else None)
    else:kind=None
    if not kind:return
    marker=f"{previous_stage}/{g['turn']}/{kind}"
    hid="h"+hashlib.sha256(marker.encode()).hexdigest()[:10]
    if any(x["id"]==hid for x in p["hooks"]):return
    p["hooks"].append({"id":hid,"origin":previous_stage,"kind":kind,
                       "detail":original,"seen_at":[],"at_turn":g["turn"]})
    p["hooks"]=p["hooks"][-42:]

def _callback(g,card):
    p=g["psych"];hid=card.get("hook_id")
    hook=next((x for x in p.get("hooks",[]) if x["id"]==hid),None)
    if not hook or hook["origin"]>=g["stage"]:return ""
    detail=hook["detail"].strip()[:100]
    if not detail:return ""
    if hook.get("traced"):
        return ("你已经追查过这句话出现的来路：「"+detail+"」。"
                "你说过这句话是真的；别人从那份访谈里读到它也是真的。"
                "但这不是允许别人代替你回答的授权。")
    # These are in-world signs, not a claim that an interview was consent.
    focus=card.get("focus","a");stage=g["stage"];kind=hook["kind"]
    if stage==1:
        return ("「"+detail+"」出现在一份新的登记里。"
                "登记人写下了你的称呼，却没有写明这句话是谁告诉他的。")
    if kind=="actual_choice":
        if stage==3:
            return ("你刚刚亲自决定过：「"+detail+"」。"
                    "这次它确实帮你度过了眼前的危险。"
                    "现在另一份要求正沿着那条相同的路径到来。")
        return ("你在前面的真实决定还在起作用：「"+detail+"」。"
                "当时形成的结果没有消失；另一件事现在也受到了它的影响。")
    if kind=="hypothetical_boundary":
        return ("「"+detail+"」被抄进一份正式记录。"
                "落款处写着你的名字，签署时间却比这段谈话早了一天。")
    if kind=="exposed_aversion":
        return ("「"+detail+"」出现在一条新的联系路径里。"
                "你没有发出请求，屏幕却显示有人已经替你提交。")
    if kind=="exposed_attachment":
        return ("有人在另一份登记里写下「"+detail+"」。"
                "他知道这件事，却不肯说明信息来源。")
    return ("一份记录里出现了「"+detail+"」。"
            "它原本只是普通信息，现在却成了某项处置的依据。")

def paint(g,result):
    from deepening import enabled, scene as deep_scene
    if enabled(g):
        result["scene"] = deep_scene(g)
        result["note"] = ""
        result["story_revision"] = g["story_revision"]
        return result
    if g.get("edition")!="v39" or g["phase"]!="game":return result
    p=g["psych"]
    card=p.get("plan") or {}
    if card.get("stage")!=g["stage"] or card.get("turn")!=g["turn"]:
        card=fallback(g)
    scene=result["scene"].copy()
    stage=g["stage"]
    question=card.get("question","")
    if stage<2 and question:
        scene["chapter"]=f"{stage+1:02d}"
        scene["body"]=question
        scene["title"]=""
        scene["footer"]=""
        result["note"]=""
    elif stage>=2:
        from horror_scenes_v39 import scene as authored_scene
        written=authored_scene(g,card)
        if written:
            scene.update(written)
        mode=card.get("mode","")
        pivot=_callback(g,card)
        assets=p.get("assets") or {}
        focus=card.get("focus","a")
        if focus in ("a","b"):
            target=assets.get(focus,{}).get("label","")
        elif focus=="aversion":
            target=(p.get("negative") or [""])[0]
        else:
            target=p.get("cost",{}).get("name","") if p.get("cost") else ""
        effects={
          "choice":"有人把两个你想保住的东西放在了不同方向。",
          "trace":"纸面记录很整齐，唯独缺少最早答应保管的人。",
          "pressure":"敲门声变快了。对方甚至不等你说完一句话。",
          "misdirection":"你以为刚才那次决定解决了问题；另一个位置却空了。",
          "encroachment":"你为了留下的东西还在。交换来的代价却已经走得更近。",
          "cost":"你刚刚接受的代价，开始要求你付第二次。",
          "bargain":"对方确实帮过你一次。正是那一次让你难以立即拒绝。",
          "echo":"原话还在；下一次有人读出它时，尾音却不太一样。",
          "replacement":"原本属于熟悉之物的位置，还亮着，只是名字模糊了。",
          "confrontation":"对方不再解释理由。之前的选择都被摆在了眼前。",
          "silence":"门没有锁，仍然没有回应。你还记得这里曾经有人回答过。"
        }
        grounding=("桌面上的标签写着「"+target[:60]+"」。"
                   if target and stage in (2,3,4) else "")
        correction=p.get("corrections",[])
        correction_line=""
        if correction and correction[-1].get("turn")==g.get("turn"):
            item=correction[-1]
            correction_line=("档案上的关系更正为：「"+item["display"]+"」。"
                             if item.get("display") else
                             "档案上的一行字被划掉，改成：「"+item.get("new",item.get("text",""))[:120]+"」。"
                             if item.get("new") else
                             "你刚刚更正的内容已经写入档案：「"+item.get("text","")[:120]+"」。")
        if pivot:
            scene["body"]=correction_line+"\n\n"+pivot+"\n\n"+grounding+effects.get(mode,"")+"\n\n"+scene["body"]
            for hook in p.get("hooks",[]):
                if hook["id"]==card.get("hook_id") and stage not in hook.get("seen_at",[]):
                    hook.setdefault("seen_at",[]).append(stage)
        elif mode in effects or correction_line:
            scene["body"]=correction_line+"\n\n"+grounding+effects.get(mode,"")+"\n\n"+scene["body"]
        # The server's authoritative options stay exactly as the engine provided.
        scene["footer"]=""
        result["note"]=""
    notice=p.get("offer_notice")
    if notice and stage in (2,3) and g["phase"]=="game":
        scene["body"]=notice+"\n\n"+scene["body"]
    result["scene"]=scene
    return result
