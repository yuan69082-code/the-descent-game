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
    """A pending order expires on a later chapter event, never while investigating."""
    story=ensure(g)
    if (key in g.get("lost",[]) or
        any(x["key"]==key for x in story["pending"]) or
        any(x["key"]==key for x in story["wins"])):
        return False
    deadline=min(g["stage"]+3,5)
    story["pending"].append({"key":key,"reason":reason[:220],
                             "origin":g["stage"],"opened":g["turn"],
                             "remaining":delay,"due_stage":deadline})
    _record(g,"一份尚未实际执行的处置进入复核队列。","pending")
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
        # Finding a receipt or asserting a witness exists is not independently verified proof.
        return bool(cp.get("verified_false_delivery") or cp.get("delivery_intercepted") or
                    (fl.get("evidence_copy") and
                     bool(clues.intersection({"delivery","authority","custody","original_declaration"}))))
    if key=="freedom":
        return bool(cp.get("verified_false_registration") or
                    (cp.get("formal_objection") and cp.get("witness_request") and
                     "truth" not in lost))
    if key=="principle":
        return bool(cp.get("ownership_claim") or cp.get("verified_false_delivery"))
    if key=="self":
        return bool(cp.get("verified_false_registration") or
                    ("rival_phrase" in clues and cp.get("formal_objection") and fl.get("evidence_copy")))
    if key=="truth":
        return bool(cp.get("verified_false_delivery") or
                    ("authority" in clues and cp.get("formal_objection") and fl.get("evidence_copy")))
    if key=="future":
        return bool(cp.get("formal_objection") and fl.get("evidence_copy") and "authority" in clues)
    return False


def settle(g:dict,move:str="",force:bool=False):
    """Only a later committed chapter or closing order can execute an unresolved claim."""
    story=ensure(g)
    from game_engine import lose
    kept=[]
    resolved=[]
    for order in story["pending"]:
        key=order["key"]
        if key in g.get("lost",[]):
            continue
        if protected(g,key):
            if win(g,key,"你已建立能够独立核验的反证，原处置被撤回。"):
                resolved.append("被撤回："+LABELS[key])
            continue
        due=order.get("due_stage",min(order.get("origin",0)+3,5))
        if force or g["stage"]>=due:
            lose(g,key,order["reason"])
            resolved.append("执行："+LABELS[key])
            _record(g,"【延期后果】旧处置如今正式生效："+LABELS[key]+"。","loss")
        else:
            kept.append(order)
    story["pending"]=kept
    if resolved and not force and g.get("phase")=="game":
        message="你先前留下的选择开始兑现——"+"；".join(resolved)+"。"
        g["note"]=(g.get("note","")+"\n\n"+message).strip()
    return resolved

def after(g:dict,snapshot:dict):
    story=ensure(g)
    move=snapshot["intent"]
    previous=snapshot["before_stage"]
    new_clues=[v for v in g.get("clues",[]) if v not in snapshot["before_clues"]]
    if g["phase"]=="game":
        settle(g,move)
    before_wins=snapshot.get("before_wins",0)
    new_wins=[v["key"] for v in story["wins"][before_wins:]]
    lost=[v for v in g.get("lost",[]) if v not in snapshot["before_lost"]]
    if g.get("causality",{}).get("actions"):
        a=g["causality"]["actions"][-1]
        for key in lost:
            if key not in a["lost"]:
                a["lost"].append(key)
        if new_wins or lost:
            a["effective"]=True
    story["traces"].append({
        "turn":g["turn"],"stage":previous,"intent":move,
        "new_clues":new_clues,"new_loss":lost,"saved":new_wins,
        "world_changed":bool(new_clues or lost or new_wins or previous!=g["stage"]),
    })
    if len(story["traces"])>60:
        story["traces"]=story["traces"][-60:]

def scene_overlay(g:dict)->str:
    """Show consequences in the world, not a repeated account of declared fears."""
    story=ensure(g)
    if g.get("phase")!="game":
        return ""
    stage=g["stage"]
    pending={v["key"] for v in story["pending"]}
    saved={v["key"] for v in story["wins"]}
    lost=set(g.get("lost",[]))
    first=story.get("first_words","")
    note=[]
    person=g["profile"]["person"]

    if stage==1 and first:
        if "relation" in saved:
            note.append("第一幕被退回的信仍在桌上。读取槽的灯确实没亮；你保住了原件。")
        elif "relation" in pending and "delivery" not in g["clues"]:
            note.append("听筒里传来一句短促的「看到了」。你想再听一遍，对方已经挂断。"
                        "柜台放下一枚写着『签收』的印章，却没有附上那个人的声音记录。")
        elif "relation" in pending:
            note.append("你手中的邮寄单有编号，没有收件地址；柜台仍坚持信已交给了正确的人。")

    if stage>=2:
        if "relation" in saved:
            note.append("无地址信的签收声明已被反证压住。"
                        +person+"的登记证言仍有资格参加下一轮核对，这一成果不会被自动撤销。")
        elif "relation" in lost and stage==2:
            note.append("你想调取最初的电话确认，却只找到一份登记签收。"
                        "关系栏被封存。你申请见证，联系人列表却只有空白。")
        elif "relation" in pending and stage==2:
            note.append("上一幕的『已签收』文件仍缺独立的交付凭据。"
                        "机构将它压在下一份处置单下方，等待正式移交。")

    if stage>=3:
        if "relation" in lost and stage==3:
            note.append("你再次申请让"+person+"出面确认第一封信，却得到『见证关系已销毁』的回执。"
                        "联系人名字仍看得见，作证资格却已经不在。")
        if "memory" in saved:
            note.append("你拿回了记忆的独立来源。"
                        "副本能复述案卷内容，却无法凭复述取走你已经核验的记录。")
        elif "memory" in lost and stage==3:
            note.append("终端要求你核对那段经历。它仍有标题，正文却只有一块空白。"
                        "副本念出了另一个版本，你再也无法与原件比对。")
        if "truth" in lost and stage==3:
            note.append("你仍可读机构提供的摘要，但独立签名链已不在你手中。"
                        "副本要求你凭这些无法核验的文字证明身份。")

    if stage==4:
        if first and "memory" not in lost and ("truth" not in lost or g["flags"].get("evidence_copy")):
            note.append("清算单背面还留着第一幕那行真正由你提交的字：『"+first[:180]+"』。"
                        "这行文字与上面的官方摘要并排放着，没有替你回答哪一个才算送达。")
        elif first and "memory" in lost:
            note.append("第一幕的信还在清算单背面，但你此刻拿不到它的原始文本来核对。")
        if "freedom" in pending:
            note.append("冻结令挂在最终清算单旁，尚未执行。"
                        "你仍能提交反证；直接结案则要连冻结令一起处理。")
        elif "freedom" in saved:
            note.append("先前的冻结申请被驳回。你仍可独立签署或拒绝。")
        if "principle" in lost:
            note.append("原则登记凭据已经失效。你仍能坚持那句话，"
                        "但机构不再承认被撤销的旧档案具有强制执行效力。")
        if "self" in lost:
            note.append("两个相同名字出现在不同签收栏。"
                        "你那栏只剩登记编号，另一份却有完整署名。")

    return "\n\n".join(note[:3])


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
        from causal_core import active_focus
        existing={x["key"] for x in ensure(g)["pending"]+ensure(g)["wins"]}
        key=next((x for x in [active_focus(g),*g["profile"]["rank"]]
                  if x not in g.get("lost",[]) and x not in existing and x!="principle"),None)
        if key in LABELS:
            return queue(g,key,"机构试图将先前拒签产生的担保责任转嫁给此项凭据。",2)
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
    if "memory" in g.get("lost",[]) and not g["flags"].get("evidence_copy"):
        first="[旧信纸仍有编号，但你已经无法在本局调阅并核验它的原文]"
    elif "truth" in g.get("lost",[]) and not g["flags"].get("evidence_copy"):
        first=first[:180]+" [机构展示的版本，原件暂无法独立核验]"
    first=first[:220]
    winlines="；".join(LABELS.get(x["key"],x["key"])+"的扣押确实被阻断" for x in story["wins"][-2:])
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
    is_blank=short in ("不留","不留最后的话","留空","保持沉默","跳过","skip","结束","结束游戏","退出游戏","不说")
    if is_blank:
        reaction="你决定不再留下任何话。最后一栏保持空白。"
        story["final_action"]={"kind":"silence","raw":short,"outcome":reaction}
    else:
        draft=any(x in short for x in ("发给","写给","留给","送给","告诉她","告诉他","联系","拨打","寄给","发送"))
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
