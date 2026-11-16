"""THE DESCENT: model is an invisible backstage planner, never the narrator.

It chooses a limited question/mode/focus/earlier hook. The game server alone
displays scenes, adjudicates actions and decides whether a hook pays off.
A conversation answer is an exposed detail, never implied consent.
"""
from __future__ import annotations
import hashlib
import json
import re
from horror_director import _completion, configured

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
BANNED=re.compile(r"你(?:已经|明明|亲自)(?:同意|签|放弃)|你必须(?:承认|答应)|"
                  r"你现在(?:已经)?(?:失去|被夺走)|我知道你(?:真的)?(?:害怕|恐惧)|"
                  r"这只是游戏|你很安全|放心|别害怕|免责声明",re.I)
INTERNAL_PROMPT="""你是《恐惧深潜》游戏的幕后策划，不是角色，也不是主持人。
你永远不能对玩家直接说话。你的 JSON 仅交给程序；程序自己显示问答与世界事件。
请理解玩家真正说了什么、珍视什么、厌恶什么、正在试图保护什么，
以及某句话是提问、假设、拒绝、有条件同意还是正式决定。
不要把拒绝改成同意，不要把闲聊等同签字，不得自作主张剥夺、恢复、签名或决定结局。

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
    from v37_engine import QUESTIONS, PROBES
    p=g["psych"];stage=g["stage"];seed=_seed(g)
    modes=MODES.get(stage,("echo",))
    if stage==0:
        question=QUESTIONS[p["question_index"]]
    elif stage==1:
        question=PROBES[p["probe_index"]].format(
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
    from v37_engine import QUESTIONS
    p=g["psych"];stage=g["stage"]
    active=_eligible(g)
    return {
      "current_act":stage+1,
      "allowed_modes":MODES.get(stage,("echo",)),
      "allowed_focus":FOCI,
      "slot":SLOTS[p["question_index"]][0] if stage==0 else
               "hypothetical" if stage==1 else "story",
      "prior_questions":p.get("question_log",[])[-7:],
      "last_actual_answer":((p.get("probes",[])[-1] if stage==1 and p.get("probes")
                            else p.get("answers",[])[-1] if p.get("answers") else "")[:250]),
      "current_required_topic":SLOTS[p["question_index"]][0] if stage==0 else "probe_real_priority_and_hesitation",
      "interview_answers":p.get("answers",[])[-8:],
      "hypothetical_answers":p.get("probes",[])[-6:],
      "actual_decisions":p.get("choices",[])[-5:],
      "known_values":(p.get("a",""),p.get("b","")),
      "disliked":p.get("negative",[]),
      "paid_cost":p.get("cost"),
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
        if not re.search(SLOTS[slot][1],text,re.I):
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
    if configured() and g["phase"]=="game":
        request=json.dumps(_facts(g),ensure_ascii=False,default=str)[:7900]
        proposal=_completion([{"role":"system","content":INTERNAL_PROMPT},
          {"role":"user","content":"请给程序一张下一幕计划卡，不要自己叙述场景。当前事实：\n"+request}],420)
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
    if stage>=2:current["question"]=""
    p["plan"]=dict(current,turn=g["turn"],stage=stage,from_model=applied)
    if current["hook_id"]:
        for h in p.get("hooks",[]):
            if h["id"]==current["hook_id"] and stage not in h.get("seen_at",[]):
                h.setdefault("seen_at",[]).append(stage)
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
        from v37_engine import QUESTIONS,PROBES
        i=len(p["answers"])-1 if previous_stage==0 else len(p["probes"])-1
        if i<0:return
        plan=p.get("plan") or {}
        planned=plan.get("question","") if plan.get("stage")==previous_stage else ""
        if previous_stage==0:
            prompt=planned or QUESTIONS[i]
        else:
            prompt=planned or PROBES[i].format(
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
        return ("你还记得刚才提过「"+detail+"」吗？"
                "一个很小的变化：假如别人也知道了这句话，你希望他怎样使用它？")
    if kind=="actual_choice":
        if stage==3:
            return ("你刚刚亲自决定过：「"+detail+"」。"
                    "这次它确实帮你度过了眼前的危险。"
                    "现在另一份要求正沿着那条相同的路径到来。")
        return ("你在前面的真实决定还在起作用：「"+detail+"」。"
                "当时形成的结果没有消失；另一件事现在也受到了它的影响。")
    if kind=="hypothetical_boundary":
        return ("有人翻出了你曾经讨论过的一种可能：「"+detail+"」。"
                "它不是签名，却暴露了你习惯先防守哪一边。"
                "对方开始利用这个判断安排下一次局面。")
    if kind=="exposed_aversion":
        return ("你曾提到不愿面对：「"+detail+"」。"
                "现在它没有以惩罚通知的形式出现；"
                "它从你刚刚借用的一条联系途径里，悄悄挤进来了。")
    if kind=="exposed_attachment":
        return ("之前你提到过「"+detail+"」。"
                "另一个人竟也知道这句话，但他并没有说自己从哪听来。"
                "被知道，并不代表你曾允许他代替你。")
    return ("你前面随口提过：「"+detail+"」。"
            "原本不起眼的一句话，在这次局面里忽然有了另一个用处。")

def paint(g,result):
    if g.get("edition")!="v39" or g["phase"]!="game":return result
    p=g["psych"]
    card=p.get("plan") or {}
    if card.get("stage")!=g["stage"] or card.get("turn")!=g["turn"]:
        card=fallback(g)
    scene=result["scene"].copy()
    stage=g["stage"]
    question=card.get("question","")
    if stage<2 and question:
        lead=("")
        if stage==1 and p.get("answers"):
            lead="你前面提过的那些事还在这里。\n\n"
        scene["body"]=lead+question
        scene["title"]=("先聊聊" if stage==0 else
                        {"comparison":"交换顺序","conditions":"界限在哪",
                         "reversal":"如果反过来","boundary":"你会答应吗"}.get(card.get("mode"),"假如如此"))
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
        grounding=("这一次，对方把目光停在「"+target[:60]+"」上。"
                   if target and stage in (2,3,4) else "")
        if pivot:
            scene["body"]=pivot+"\n\n"+grounding+effects.get(mode,"")+"\n\n"+scene["body"]
        elif mode in effects:
            scene["body"]=grounding+effects[mode]+"\n\n"+scene["body"]
        # The server's authoritative options stay exactly as the engine provided.
        scene["footer"]=""
        result["note"]=""
    notice=p.get("offer_notice")
    if notice and stage in (2,3) and g["phase"]=="game":
        scene["body"]=notice+"\n\n"+scene["body"]
    result["scene"]=scene
    return result
