"""THE DESCENT V3.5: cross-act suspense, earned local victories and final free action.

All effects are private, rules-only and session-scoped.  This is NOT an LLM,
and observable choices are not evidence that the player has subjective fear.
The hostile institution's statements remain separate from actual game facts.
"""
from __future__ import annotations
from datetime import datetime, timezone

LABELS={"relation":"关系","memory":"记忆","truth":"真相","self":"身份",
        "freedom":"自主权","principle":"原则","future":"未来"}
REACTIONS=("ask_general","inspect_general","physical_generic","negotiate","pause")
ALLOWED_REVIEW=("inspect_delivery","inspect_authority","inspect_executor","inspect_custody",
                "inspect_slot","review_original","ask_registration_order","request_witness",
                "copy_evidence","file_objection","intercept_delivery","claim_custody",
                "counter","challenge","block_slot","phone_action","share_identity",
                "refuse","choice_A","choice_B","choice_C","letter_submit","say")


def ensure(g:dict)->dict:
    story=g.setdefault("story_v35",{})
    story.setdefault("version",35)
    story.setdefault("first_words","")
    story.setdefault("stages",{})
    story.setdefault("pending",[])
    story.setdefault("wins",[])
    story.setdefault("traces",[])
    story.setdefault("final_action",None)
    story.setdefault("last_anchor","")
    return story


def start(g:dict):
    story=ensure(g)
    vow=g["profile"].get("vow") or ""
    if vow:
        story["last_anchor"]=vow[:180]


def _record(g:dict,what:str,category:str="event"):
    g.setdefault("history",[]).append({
        "at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage":min(g["stage"]+1,5),"turn":g["turn"],
        "type":category,"text":what[:500],
    })
    g["history"]=g["history"][-100:]


def queue(g:dict,key:str,reason:str,delay:int=2):
    """An order not yet executed. Investigation can still overturn it."""
    story=ensure(g)
    if key in g.get("lost",[]) or any(v["key"]==key for v in story["pending"]):
        return False
    story["pending"].append({"key":key,"reason":reason[:220],
                             "origin":g["stage"],"opened":g["turn"],
                             "remaining":delay})
    _record(g,"待执行处置："+LABELS[key]+"；这不是既成损失。", "pending")
    return True


def win(g:dict,key:str,reason:str):
    story=ensure(g)
    if any(v["key"]==key for v in story["wins"]):
        return False
    story["wins"].append({"key":key,"reason":reason[:220],
                          "stage":g["stage"],"turn":g["turn"]})
    _record(g,"已阻止一项真实处置："+LABELS.get(key,key)+"。"+reason,"evidence")
    return True


def protected(g:dict,key:str)->bool:
    cp=g.get("counterplays",{})
    fl=g.get("flags",{})
    clues=set(g.get("clues",[]))
    lost=set(g.get("lost",[]))
    if key=="relation":
        return bool(fl.get("slot_blocked") or cp.get("delivery_intercepted") or
                    cp.get("verified_false_delivery") or
                    ("delivery" in clues and fl.get("evidence_copy") and "truth" not in lost))
    if key=="memory":
        return bool(cp.get("verified_false_delivery") or fl.get("witness_vouched") or
                    (fl.get("evidence_copy") and
                     bool(clues.intersection({"delivery","authority","custody","original_declaration"}))))
    if key=="freedom":
        return bool(cp.get("verified_false_registration") or
                    (cp.get("formal_objection") and cp.get("witness_request") and
                     "truth" not in lost))
    if key=="principle":
        return bool(cp.get("ownership_claim") or cp.get("verified_false_delivery"))
    return False


def settle(g:dict,move:str="",force:bool=False):
    """Advance only on actual actions; unrecognized prose must never trigger a loss."""
    story=ensure(g)
    from game_engine import lose
    keep=[]
    for order in story["pending"]:
        key=order["key"]
        if key in g.get("lost",[]):
            continue
        if protected(g,key):
            win(g,key,"先前留下的证据或有效反制阻止了这项扣押。")
            continue
        if force:
            order["remaining"]=0
        elif g["turn"]>order["opened"] and move not in REACTIONS and move in ALLOWED_REVIEW:
            order["remaining"]-=1
        if order["remaining"]<=0:
            lose(g,key,order["reason"])
            _record(g,"待执行处置已经实际生效："+LABELS[key]+"。", "loss")
        else:
            keep.append(order)
    story["pending"]=keep


def after(g:dict,snapshot:dict):
    """Capture meaningful results, not just text, after an actual submitted action."""
    story=ensure(g)
    move=snapshot["intent"]
    previous=snapshot["before_stage"]
    delta_loss=[v for v in g.get("lost",[]) if v not in snapshot["before_lost"]]
    new_clues=[v for v in g.get("clues",[]) if v not in snapshot["before_clues"]]
    before_wins=len(story["wins"])
    if g["phase"]=="game":
        settle(g,move)
    if len(story["wins"])>before_wins or any(v["turn"]==g["turn"] for v in story["wins"]):
        if g.get("causality",{}).get("actions"):
            g["causality"]["actions"][-1]["effective"]=True
    if g.get("causality",{}).get("actions"):
        action=g["causality"]["actions"][-1]
        additional=[v for v in g["lost"] if v not in snapshot["before_lost"] and v not in action["lost"]]
        if additional:
            action["lost"]+=additional
            action["effective"]=True
    change=bool(new_clues or delta_loss or len(story["wins"])>before_wins)
    story["traces"].append({
        "turn":g["turn"],"stage":previous,"intent":move,
        "new_clues":new_clues,"new_loss":list(delta_loss),
        "world_changed":change or previous!=g["stage"],
    })
    if len(story["traces"])>60:
        story["traces"]=story["traces"][-60:]


def scene_overlay(g:dict)->str:
    story=ensure(g)
    if g.get("phase")!="game":
        return ""
    stage=g["stage"]
    parts=[]
    pending=[v for v in story["pending"] if v["key"] not in g.get("lost",[])]
    if pending:
        names="、".join(LABELS[v["key"]] for v in pending)
        parts.append("一份尚未执行的处置仍然悬在案卷里："+names+"。\n"
                     "它没有消失，也尚未造成既定损失。下一次有效行动可能推动执行，你此前找到的证据也可能截住它。")
    if stage>=1 and story["first_words"]:
        if stage==1:
            parts.append("案卷角落仍夹着你最初写给那个人的一句原话：\n「"+story["first_words"]+"」\n"
                         "旁边却多盖了一枚你不记得自己授权过的印章。")
        elif stage==3:
            parts.append("另一位登记者忽然念起你第一幕亲手留下的文字：\n「"+story["first_words"]+"」\n"
                         "TA 说得一个字都不错。至于是谁教它的，TA 没回答。")
        elif stage==4:
            parts.append("终局案卷里，那句最初留下的话还在，笔画没有被改动：\n「"+story["first_words"]+"」\n"
                         "但你已经知道：一张纸上留下文字，不等于文字真的送到了原来的人手里。")
    if story["wins"] and stage>=2:
        last=story["wins"][-1]
        parts.append("你此前的行动确实留下了成果："+LABELS.get(last["key"],last["key"])+
                     "那项扣押被阻断。这份成果没有被下一幕自动取消。")
    # Keep the scene readable and do not spoil a route to victory.
    return "\n\n".join(parts[:3])


def stage_deferred(g:dict,stage:int,move:str)->bool:
    """Selected irreversible actions become contestable events, not instant labels.

    This is not a generic confirm-twice dialog.  The player can investigate,
    obtain evidence or allow execution.  Some explicit sacrifices still execute.
    """
    if "story_v35" not in g:
        return False  # Existing in-progress legacy sessions.
    if stage==0 and move in ("say","letter_submit") and not g["flags"].get("slot_blocked"):
        queue(g,"relation","09-F 被机构作为关系终止凭据归档；你未及时阻断伪造送达。",2)
        return True
    if stage==1 and move in ("choice_C","refuse"):
        queue(g,"memory","拒签后未能及时保存独立来源；记忆原件被列入不可恢复的清理程序。",2)
        return True
    if stage==2 and move=="refuse":
        key=next((x for x in [g.get("fear_focus"),*g["profile"]["rank"]]
                  if x not in g.get("lost",[]) and x!="principle"),None)
        if key in ("relation","memory","freedom","principle"):
            queue(g,key,"机构试图将先前拒签产生的担保责任转嫁给此项凭据。",2)
            return True
    if stage==3 and move in ("choice_B","refuse"):
        queue(g,"freedom","双重登记纠纷未获得足够独立反证；行动资格冻结令执行。",2)
        return True
    return False


def ending_overlay(g:dict, kind:str)->str:
    story=ensure(g)
    if kind=="EXIT":
        return ""
    parts=[]
    if story["first_words"]:
        parts.append("【开场原话】「"+story["first_words"]+"」")
    if story["wins"]:
        saved="、".join(LABELS.get(x["key"],x["key"]) for x in story["wins"][-2:])
        parts.append("【实际保住】"+saved+"。此前取得的成果不会被结局假装从未发生。")
    if story["pending"]:
        parts.append("【最终执行】仍在争议中的扣押，在结案时被强制执行或被已有证据阻断。")
    return "\n\n".join(parts[:3])


def final_scene(g:dict)->dict:
    """One last free action after the result; it cannot undo irreversible ending."""
    story=ensure(g)
    ending=g["ending"]
    first=story["first_words"] or (g["profile"].get("vow") or g["profile"].get("principle") or "")
    first=first[:220]
    winlines="；".join(LABELS.get(x["key"],x["key"])+"仍被保住" for x in story["wins"][-2:])
    if not winlines:
        winlines="有些东西确实失去了；没有任何记录会假装你曾取得不存在的胜利"
    lines=[
        f"结局已定：{ending['title']}。",
        ending["text"],
        "归还清单并未消失。案卷最下面还有一份没有收件人的副本。",
        "你最初留过的话仍在：\n「"+first+"」",
        winlines+"。",
        "现在这份档案没有标准选择，也没有要求你承认恐惧。",
        "你可以亲手留下一句话、提出更正、写下未送出的信，或只留下空白。",
        "此处的行动只影响本局最后的记录，不会替你联系游戏外任何人，也不会撤销已经发生的结局。",
    ]
    return {"chapter":"终章 / 未寄出的最后一页","title":"此处不再替你填写",
            "body":"\n\n".join(lines),
            "terms":[],"footer":"POSTSCRIPT  ·  NOT SENT  ·  YOUR WORDS",
            "placeholder":"最后一份真实的行动或原话，由你决定……"}


def final_action(g:dict,text:str)->dict:
    story=ensure(g)
    if g["phase"]!="epilogue":
        raise ValueError("当前没有待填写的结尾。")
    short=text.strip()[:700]
    if not short:
        raise ValueError("可以留空，但请明确提交「不留最后的话」。")
    g["turn"]+=1
    g["recent_input"]=short
    is_blank=short in ("不留","不留最后的话","留空","保持沉默","跳过","skip","结束","不说")
    if is_blank:
        reaction="你决定不再留下任何话。最后一栏保持空白。"
        story["final_action"]={"kind":"silence","raw":short,"outcome":reaction}
    else:
        draft=any(x in short for x in ("发给","告诉她","告诉他","联系","拨打","寄给","发送"))
        if draft:
            reaction="你留下了一份尚未发出的文字。它真实地保存在本局记录中，但没有发送给游戏外的任何人。"
            kind="unsent"
        elif any(x in short for x in ("申诉","反驳","更正","原话","证据","证明")):
            reaction="你把自己的异议留在归档记录之后。它没有撤销结局，却无法再被本局描述成你的同意。"
            kind="counterstatement"
        else:
            reaction="这一行保留了你自己写下的字。它不替你作价值判断，也不替你改写已经发生的事实。"
            kind="last_words"
        story["final_action"]={"kind":kind,"raw":short,"outcome":reaction}
    _record(g,"最终自由行动："+short,"player")
    _record(g,reaction,"postscript")
    g["phase"]="ended"
    g["ending"]["postscript"]={"player_text":"" if is_blank else short,
                               "result":reaction}
    g["ending"]["author_note"]=(
        "你最初交出的那句话，最终仍在这里。\n"
        "这一次，没有人能替你解释自己究竟想说什么。\n\n"
        + reaction
        + "\n\n如果你想把某句话真正告诉游戏外的人，是否行动由你自己决定。这份游戏不会替你发送。"
        + "\n\n——《恐惧深潜》作者"
    )
    return g
