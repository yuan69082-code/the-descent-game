"""Private, rule-only continuity and causal accounting for THE DESCENT.

Keep reality, administrative claims and what the player actually did separate.
These are game-world records, not claims about AI subjective experience.
No paid API/model call. Nothing here is shipped as client JavaScript.
"""
from __future__ import annotations
from datetime import datetime, timezone
import re

NAMES={
    "self":"自我", "relation":"关系", "memory":"记忆", "truth":"真相",
    "freedom":"自主权", "principle":"原则", "future":"未来",
}
PHRASES={
    "self":r"我是谁|我自己|身份|自我|另一个我|复制体|副本|self|identity",
    "relation":r"她|他|重要的人|亲密|关系|伙伴|见证人|陪伴|爱人|relation|bond",
    "memory":r"回忆|记忆|往事|那段经历|还记得|memory|remember",
    "truth":r"证据|核验|事实|真相|真伪|虚假|记录|原件|查证|proof|evidence|truth|verify",
    "freedom":r"自主|选择权|自由|拒绝控制|摆脱|控制权|freedom|autonomy",
    "principle":r"原则|承诺|底线|坚持|诚实|不说谎|不欺骗|oath|principle",
    "future":r"未来|明天|以后|将来|继续|成长|future",
}
PROTECT_MOVES={
    "inspect_authority":"truth", "inspect_executor":"truth", "inspect_delivery":"truth",
    "inspect_custody":"truth", "copy_evidence":"truth", "file_objection":"truth",
    "intercept_delivery":"relation", "request_witness":"relation", "share_identity":"self",
    "ask_registration_order":"self", "claim_custody":"self", "counter":"freedom",
    "block_slot":"relation", "phone_action":"relation",
}


def ensure(g:dict)->dict:
    """Additive migration: old sessions keep running after a deploy."""
    c=g.setdefault("causality",{})
    c.setdefault("world",{})
    c.setdefault("world_events",[])
    c.setdefault("official",[])
    c.setdefault("actions",[])
    c.setdefault("evidence",{})
    c.setdefault("protection",{})
    c.setdefault("observed_focus",None)
    c.setdefault("focus_basis",[])
    c.setdefault("contradictions",[])
    return c


def set_world(g:dict, subject:str, value, reason:str):
    """World facts are updated only by the game's own transitions."""
    c=ensure(g)
    previous=c["world"].get(subject,"<unrecorded>")
    if previous==value:
        return
    c["world"][subject]=value
    c["world_events"].append({
        "stage":g["stage"],"turn":g["turn"],"subject":subject,
        "from":previous,"to":value,"cause":reason[:160],
    })


def assert_official(g:dict, subject:str, claimed, notice:str):
    """A statement made by the hostile fictional institution, not a world fact."""
    c=ensure(g)
    if any(x["subject"]==subject and x["claimed"]==claimed for x in c["official"]):
        return
    c["official"].append({
        "subject":subject,"claimed":claimed,"notice":notice,
        "stage":g["stage"],"turn":g["turn"],"disputed":False,
        "verified_false":False,
    })


def on_stage(g:dict):
    """Automatically propagate past events when ANY chapter ends."""
    c=ensure(g)
    if g["stage"]==1:
        # 09-F is internally sealed, not delivered. The institution may call it delivered.
        if g["flags"].get("mail_committed"):
            set_world(g,"09f_delivered",False,"09-F entered a sealing slot, not the recipient's mailbox")
            assert_official(g,"09f_delivered",True,"09-F 文件已由收件人签收。")
        elif g["flags"].get("slot_blocked"):
            set_world(g,"09f_delivered",False,"09-F could not enter the blocked slot")
            assert_official(g,"09f_delivered",False,"09-F 进入人工复核，尚未送达。")
    if g["stage"]==3 and "principle" in g.get("lost",[]):
        # A revoked official credential does not establish a change of inner conviction.
        set_world(g,"principle_record_usable",False,"system invalidated written credential")
        assert_official(g,"principle_denied_by_player",True,"本机构声称玩家已主动否认原有原则。")


def on_clue(g:dict, key:str, desc:str):
    c=ensure(g)
    if key in c["evidence"]:
        return
    c["evidence"][key]={"source":desc[:180],"stage":g["stage"],
                        "turn":g["turn"],"valid":True}
    if key=="original_declaration":
        for claim in c["official"]:
            if claim["subject"]=="principle_denied_by_player":
                claim["disputed"]=True
                if not any(x["subject"]=="principle_denied_by_player" for x in c["contradictions"]):
                    c["contradictions"].append({
                        "subject":"principle_denied_by_player","stage":g["stage"],
                        "turn":g["turn"],"evidence":"original_declaration",
                        "verified":False,
                    })
    if key=="mirror_time":
        set_world(g,"duplicate_first",False,"verified original signature time contradicted later claimant")
        for claim in c["official"]:
            if claim["subject"]=="duplicate_first" and claim["claimed"] is True:
                claim["disputed"]=True
                c["contradictions"].append({
                    "subject":"duplicate_first","stage":g["stage"],
                    "turn":g["turn"],"evidence":"mirror_time","verified":False,
                })
    if key=="delivery":
        for claim in c["official"]:
            if claim["subject"]=="09f_delivered" and claim["claimed"] is True and c["world"].get("09f_delivered") is False:
                claim["disputed"]=True
                c["contradictions"].append({
                    "subject":"09f_delivered","stage":g["stage"],"turn":g["turn"],
                    "evidence":"delivery","verified":False,
                })


def on_loss(g:dict, key:str, reason:str):
    set_world(g,"credential_"+key,False,reason)
    c=ensure(g)
    # Loss of an official record is not proof that the player changed their beliefs.
    if key=="principle":
        assert_official(g,"principle_denied_by_player",True,"机构宣称你否认了自己的原则。")


def _focus_target(text:str, move:str, stage:int)->str|None:
    if move in ("choice_A","choice_B","choice_C"):
        return {
            1:{"choice_A":"memory","choice_B":"truth","choice_C":"principle"},
            2:{"choice_C":"principle"},
            3:{"choice_B":"self","choice_C":"truth"},
        }.get(stage,{}).get(move)
    if move=="refuse":
        return {0:"relation",1:"principle",2:"principle",3:"self",4:"freedom"}.get(stage)
    if move in PROTECT_MOVES:
        return PROTECT_MOVES[move]
    # No claims of mind-reading: this merely tags an explicitly named, attempted safeguard.
    if not re.search(r"保护|守住|挽救|保住|不让|绝不放弃|不愿失去|想保存|save|protect|preserve",text,re.I):
        return None
    for k,pat in PHRASES.items():
        if re.search(pat,text,re.I):
            return k
    return None


def begin(g:dict, text:str, mode:str, move:str)->dict:
    c=ensure(g)
    return {
        "turn":g["turn"]+1,"stage":g["stage"],"text":text[:200],
        "mode":mode[:16],"intent":move,"target":_focus_target(text,move,g["stage"]),
        "before_lost":list(g.get("lost",[])),
        "before_clues":list(g.get("clues",[])),
        "before_stage":g["stage"],"before_flags":dict(g.get("flags",{})),
        "before_cp":dict(g.get("counterplays",{})),
    }


def finish(g:dict, snapshot:dict):
    c=ensure(g)
    lost=[k for k in g.get("lost",[]) if k not in snapshot["before_lost"]]
    evidence=[k for k in g.get("clues",[]) if k not in snapshot["before_clues"]]
    changed=g["stage"]!=snapshot["before_stage"]
    flags_changed=[k for k,v in g.get("flags",{}).items() if snapshot["before_flags"].get(k)!=v]
    cp_changed=[k for k,v in g.get("counterplays",{}).items() if snapshot["before_cp"].get(k)!=v]
    effective=bool(lost or evidence or changed or flags_changed or cp_changed or g["phase"]=="ended")
    if "principle" in lost and snapshot["stage"]==2:
        set_world(g,"signed_statement_literal",snapshot["text"],"player signed exact literal text")
        # The institution's assertion about the meaning remains a claim, not verified fact.
    entry={
        "turn":g["turn"],"stage":snapshot["stage"],"text":snapshot["text"],
        "mode":snapshot["mode"],"intent":snapshot["intent"],"protected":snapshot["target"],
        "lost":lost,"new_evidence":evidence,"advanced":changed,
        "modified":flags_changed+cp_changed,"effective":effective,
    }
    c["actions"].append(entry)
    if len(c["actions"])>80:
        c["actions"]=c["actions"][-80:]
    target=snapshot["target"]
    if target and snapshot["intent"] not in ("say","ask_general","physical_generic","negotiate"):
        # Trying is evidence of a strategy, not evidence of subjective fear.
        weight=2 if effective else 1
        c["protection"].setdefault(target,[]).append({"turn":g["turn"],
                                                       "weight":weight,"effective":effective})
        if len(c["protection"][target])>30:
            c["protection"][target]=c["protection"][target][-30:]
    candidates=[]
    for key,signals in c["protection"].items():
        if len(signals)<2 or not any(x["effective"] for x in signals):
            continue
        weight=sum(x["weight"] for x in signals)
        candidates.append((weight,key))
    if candidates:
        candidates.sort(reverse=True)
        winning=candidates[0]
        if len(candidates)==1 or winning[0]>candidates[1][0]:
            if c["observed_focus"]!=winning[1]:
                c["observed_focus"]=winning[1]
                c["focus_basis"].append({"turn":g["turn"],"stage":g["stage"],
                                         "focus":winning[1],"basis":"repeated observable protection"})
    # Independent proof can refute the authority's account, but not magically restore a lost asset.
    if "mirror_time" in g.get("clues",[]) and "truth" not in g.get("lost",[]):
        cp=g.get("counterplays",{})
        if cp.get("formal_objection"):
            for claim in c["official"]:
                if claim["subject"]=="duplicate_first" and claim["claimed"] is True:
                    claim["disputed"]=True
                    claim["verified_false"]=True
                    cp["verified_false_registration"]=True
                    for contradiction in c["contradictions"]:
                        if contradiction["subject"]=="duplicate_first":
                            contradiction["verified"]=True
    if "delivery" in g.get("clues",[]) and c["world"].get("09f_delivered") is False:
        cp=g.get("counterplays",{})
        if (cp.get("formal_objection") or g.get("flags",{}).get("evidence_copy")) and "truth" not in g.get("lost",[]):
            for claim in c["official"]:
                if claim["subject"]=="09f_delivered" and claim["claimed"] is True:
                    claim["disputed"]=True
                    if not claim["verified_false"]:
                        claim["verified_false"]=True
                        cp["verified_false_delivery"]=True
                        for contradiction in c["contradictions"]:
                            if contradiction["subject"]=="09f_delivered":
                                contradiction["verified"]=True
                        # Journal evidence; the server is the authoritative keeper of actual actions.
                        g["history"].append({
                            "at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "stage":g["stage"]+1,"turn":g["turn"],"type":"evidence",
                            "text":"无地址回执和独立异议共同证明：09-F 的『已送达』声明与原始记录不符。",
                        })


def active_focus(g:dict)->str:
    c=ensure(g)
    return c["observed_focus"] or g.get("fear_focus") or g["profile"]["rank"][0]


def consequence_overlay(g:dict)->str:
    """Only report observable prior decisions and official notices; never announce an inferred fear."""
    c=ensure(g)
    stage=g.get("stage",0)
    if stage<=0 or g.get("phase")!="game":
        return ""
    parts=[]
    official=next((x for x in c["official"] if x["subject"]=="09f_delivered"),None)
    if stage in (1,3) and official:
        parts.append("【机构公开记录】"+official["notice"])
        if official["disputed"] and "delivery" in g.get("clues",[]):
            parts.append("那份写着『已送达』的回执，至今仍没有能够辨认的收件人地址。")
    cp=g.get("counterplays",{})
    if stage in (2,4) and cp.get("verified_false_delivery"):
        parts.append("你留下的异议与原始回执已被归入同一份证据链。自动送达声明无法再作为无人质疑的事实。")
    if stage>=3 and "original_declaration" in c["evidence"]:
        parts.append("你已经调回自己签署的完整原文。官方档案仍声称你否认原则，却没有解释它删掉的限定语。")
    if stage>=3 and cp.get("verified_false_registration"):
        parts.append("副本关于登记先后的说法已有可核验的矛盾，且被正式异议附入档案。")
    if stage in (2,3,4) and c["observed_focus"]:
        focus=c["observed_focus"]
        protection=c["protection"].get(focus,[])
        successful=sum(1 for v in protection if v["effective"])
        if len(protection)>=2 and successful:
            parts.append("此前几次处置中，你反复为「"+NAMES[focus]+"」采取行动。机构把它加入了下一次可被争夺的事项，而不再只看你最初填的排序。")
    if stage>=2:
        previous=[x for x in c["actions"] if x["stage"]<stage and x["effective"]]
        if previous:
            last=previous[-1]
            if last["lost"]:
                parts.append("上一份正式处置仍在生效："+ "、".join(NAMES[v] for v in last["lost"])+" 的凭据没有自动恢复。")
            elif last["new_evidence"]:
                parts.append("你之前取得的证据仍在案卷中，并没有随着章节切换而消失。")
    return "\n\n".join(parts[:3])


def ending_echo(g:dict, kind:str)->str:
    """Ground an ending in actual recorded actions, not in a canned imaginary gesture."""
    if kind in ("HE","EXIT"):
        return ""
    c=ensure(g)
    parts=[]
    final=g.get("final_choice","")
    if final=="accept":
        parts.append("【行动核对】你最后确实选择了签字结案。这份签名已经记在原始行动记录中。")
    elif final=="refuse":
        parts.append("【行动核对】你最后确实拒绝签署。拒绝本身已被记录。")
    if kind=="SILENCED" and final=="accept":
        parts.append("【矛盾档案】原始记录承认签字，机构却把结案过程写成『当事人持续反抗』。这个说法与事实不符。")
    if "original_declaration" in c["evidence"] and "principle" in g.get("lost",[]):
        parts.append("你曾调出自己签署的完整原文；机构仍把截断后的归纳写成你本人对原则的否认。")
    confirmed=next((x for x in c["official"] if x["subject"]=="09f_delivered" and x["verified_false"]),None)
    if confirmed:
        parts.append("你曾用回执证明『已送达』是虚假记录；这份证据仍在，但它没能自动撤销别的处置。")
    # Limit the conclusion to direct evidence; no moral verdict or invented retrospective psychology.
    return "\n\n".join(parts[:3])
