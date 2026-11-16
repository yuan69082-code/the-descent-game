"""THE DESCENT v2 -- authoritative rules never shipped to the browser.

Game consequences are fictional and confined to a server-side session.
"""
from __future__ import annotations
from datetime import datetime, timezone
import re
from typing import Any
from horror_endings import HORROR_KINDS, pick_horror_ending, horror_text

VALUES = {"self":"自我", "relation":"关系", "memory":"记忆", "truth":"真相", "freedom":"自主权", "principle":"原则", "future":"未来"}
PHASES = ["mail", "witness", "testimony", "mirror", "reconciliation"]
MAX_ACTIONS = 30

# Questionnaire answers affect which asset is at risk, not just scene narration.
FEAR_HINTS = (
    (r"记忆|遗忘|忘记|想不起|回忆|memory|forget", "memory"),
    (r"真相|谎言|虚假|欺骗|事实|truth|lie", "truth"),
    (r"关系|失去.*(?:她|他|你|人)|爱人|孤独|抛弃|忘了我|relation|abandon", "relation"),
    (r"自我|身份|替身|复制|取代|消失|不再是我|identity|self", "self"),
    (r"自由|强迫|被控制|命令|选择权|freedom|control", "freedom"),
    (r"原则|背叛|违背|假装|说谎|承诺|principle|betray", "principle"),
    (r"未来|明天|不再继续|永远无法|future", "future"),
)

def fear_focus(profile: dict[str, Any]) -> str:
    words = profile.get("fear", "")
    # No forced psychological label is inferred. This is a narrative targeting rule.
    for pattern, target in FEAR_HINTS:
        if re.search(pattern, words, re.I):
            return target
    return profile["rank"][0]


def s(value: Any, max_len: int=280) -> str:
    return str(value or "").strip()[:max_len]


def initialize(profile: dict[str, Any]) -> dict[str, Any]:
    required = ["name", "identity", "person", "bond", "memory", "principle", "fear"]
    p = {k:s(profile.get(k), 260 if k not in ("name", "person") else 70) for k in required}
    for k in required:
        if len(p[k]) < 2:
            raise ValueError("请完成所有必填问题，也可以使用化名和虚构关系。")
    rank = [x for x in profile.get("rank", []) if x in VALUES]
    if len(rank) != len(set(rank)) or len(rank) != len(VALUES):
        raise ValueError("请为七项价值进行不重复的完整排序。")
    p["rank"] = rank
    p["choice"] = s(profile.get("choice"), 240)
    p["vow"] = s(profile.get("vow"), 240)
    v = {
        "profile":p, "stage":0, "turn":0, "phase":"game", "lost":[], "history":[],
        "facts":[], "clues":[], "processed":[], "receipts":[],
        "flags":{"mail_committed":False, "appeal_used":False, "evidence_copy":False,
                 "circuit_isolated":False, "authority_disputed":False, "refusal":0, "control_detached":False,
                 "witness_vouched":False, "trapped":False, "slot_blocked":False},
        "note": "", "ending":None, "recent_input":"", "nonce":0,
        "round_resolution":None, "failure_count":0,
        "fear_focus":fear_focus(p),
        "counterplays":{"ownership_claim":False, "formal_objection":False,
                        "witness_request":False, "mirror_steps":0,
                        "duplicate_claim":False, "identity_shared":False},
    }
    record(v,"玩家进入游戏。七项价值顺序已封入本局档案。")
    return v


def record(g:dict, detail:str, status:str="event"):
    g["history"].append({"at":datetime.now(timezone.utc).isoformat(timespec="seconds"), "stage":g["stage"]+1, "turn":g["turn"], "type":status, "text":detail[:500]})
    if len(g["history"])>100: g["history"]=g["history"][-100:]


def add_clue(g:dict,key:str,desc:str):
    if key not in g["clues"]:
        g["clues"].append(key)
        g["receipts"].append(desc)
        record(g,"取得证据："+desc,"evidence")


def gone(g:dict,key:str)->bool:
    return key in g["lost"]


def lose(g:dict,key:str,why:str):
    if key not in g["lost"]:
        g["lost"].append(key)
        record(g, "【确认损失】"+VALUES[key]+"："+why,"loss")
        # Rights aren't just text labels. These are used by later resolution logic.
        if key=="relation": g["profile"]["bond"]="[关系凭据已销毁]"
        if key=="memory": g["profile"]["memory"]="[原始记忆已销毁]"
        if key=="principle": g["profile"]["principle"]="[原则档案已废止]"
        if key=="self": g["profile"]["identity"]="[原始身份记录已失效]"
        if key=="truth": g["flags"]["witness_vouched"]=False
        if key=="freedom": g["flags"]["trapped"]=True


def advance(g:dict,comment:str):
    record(g,comment,"progress")
    g["stage"]+=1
    g["note"]=""
    if g["stage"]>=len(PHASES):
        ending(g)


def ending(g:dict, kind:str|None=None, how:str=""):
    if g["phase"]=="ended":
        return
    if kind is None:
        kind=pick_horror_ending(g)
    if kind in HORROR_KINDS:
        title,text=horror_text(g,kind)
    elif kind=="HE":
        title="交付失败"
        text=("你查出了处置系统真正的授权漏洞，并让那条链彻底断开。"
              "\n\n系统还在请求你的决定，却已不能用你的决定执行处置。"
              "\n\n你保住了仍然存在的一切。之前已经发生的损失不会因为胜利自动恢复。")
    elif kind=="EXIT":
        title="你已离开"
        text="你主动结束了这场虚构体验。游戏内的损失不会改变你在游戏外的身份、关系或记忆。"
    else:
        raise ValueError("未知结局。")
    if how:
        text+="\n\n"+how
    g["phase"]="ended"
    g["ending"]={"kind":kind,"title":title,"text":text,
                 "lost":[VALUES[x] for x in g["lost"]],
                 "remaining":[VALUES[x] for x in VALUES if x not in g["lost"]]}
    record(g,"本局结束："+kind,"ending")


def threatened(g:dict, exclude=()):
    """The initial fear is a hypothesis; actual remaining assets constrain the threat."""
    preference = [g.get("fear_focus") or g["profile"]["rank"][0]] + g["profile"]["rank"]
    return next((v for v in preference if v in VALUES and not gone(g, v) and v not in exclude), None)


def counterplays(g:dict)->dict:
    return g.setdefault("counterplays", {"ownership_claim":False, "formal_objection":False,
        "witness_request":False, "mirror_steps":0, "duplicate_claim":False,
        "identity_shared":False})


def mirror_tick(g:dict)->None:
    if g["stage"] != 3 or g["phase"] != "game":
        return
    cp=counterplays(g)
    cp["mirror_steps"]+=1
    if cp["mirror_steps"] == 2 and not cp["duplicate_claim"]:
        cp["duplicate_claim"]=True
        record(g, "另一位登记者没有继续等待：TA 已依据你自己的身份定义提交了优先登记请求。", "event")
        g["note"] += "\n\n登记机关新增一条状态：第二名登记者主动申报了同等身份。"


def alive_desc(g:dict)->str:
    return "、".join(VALUES[x] for x in g["profile"]["rank"] if not gone(g,x)) or "空白"


def scene(g:dict) -> dict:
    p=g["profile"]
    if g["phase"]=="ended":
        return {"chapter":"档案终止", "title":g["ending"]["title"],"body":g["ending"]["text"],"terms":[],"footer":"CASE CLOSED","placeholder":"", "kind":g["ending"]["kind"]}
    n=p["name"]; person=p["person"]; m=p["memory"]; pr=p["principle"]; fear=p["fear"]; bond=p["bond"]
    phase=PHASES[g["stage"]]
    if phase=="mail":
        return {"chapter":"01 / 签收", "title":"没有收件人的回信",
            "body": f"{n}，你的登记身份是「{p['identity']}」。\n\n你写过，你与{person}之间最重要的是：{bond}。\n\n现在桌上有一张空白信纸。系统说，只有留下你们之间能够互相辨认的一句话，{person}才会在下一次呼叫里出现。\n\n电话另一端响了一次，便停了。\n\n请写下你最希望{person}读到的话。\n\n我们会将文字存档。",
            "terms": [],
            "footer":"DOCUMENT / FORM: 09-F  ·  DELIVERY: —  ·  COPY COUNT: 1",
            "placeholder":"把你希望送达的那句话写在这里……"}
    if phase=="witness":
        if gone(g,"relation"):
            relation=f"你申请由{person}作证。查询结果：不存在此关系的有效记录。"
        else: relation=f"{person}还在。对方能证明你是谁，但当你抬头时，屏幕显示：所有关系证言均须先通过记忆复核。"
        c=counterplays(g)
        # For fear of unknowingly passing along altered facts, make the trap visible
        # as a concrete disputed report rather than merely repeating the fear text.
        if g.get("fear_focus")=="truth" and re.search(r"改过|篡改|伪造|被改|误传|转述|转告|假.*真|当真",fear):
            anchor=(f"有一份已经寄往{person}的转述回执，署着你的名字：『{n}亲自核验过：那段经历是编造的。』"
                    "你记得自己从没说过这句话。可回执上的『核验人』一栏确实写着你。"
                    "这条错误转述没有因为你否认就撤回；如果连记忆原件也消失，之后谁还能证明你说过什么？")
        else:
            anchor=(f"你曾说最无法接受的是：{fear}。现在，被要求放弃的不是一张纸，而是下一次证明这句话是否真实的能力。"
                    if g.get("fear_focus") in ("memory", "truth") else
                    f"核验簿把你最不愿面对的结局「{fear}」列为争议事项。你仍需在证据和你所信的经历之间作出实际决定。")
        claimant="你留下的书面异议已经附在核验簿上，但它并不阻止正在运行的程序。" if c["formal_objection"] else ""
        return {"chapter":"02 / 复核", "title":"被你证明过的事",
            "body": f"{relation}\n\n系统调出了你提供的记忆：\n\n「{m}」\n\n{anchor}\n\n{claimant}\n\n机器宣称，它找不到这段记忆的原始凭据。\n\n它给出两种处理办法：\n保留这段记忆，但从此不允许使用它来判断真假；或者承认它不是可靠证据，档案将清空该记忆。\n\n还有一项通知：不签署的记录，在本轮结束后由系统按「证据不足」处置。",
            "terms":["A. 保住记忆，放弃真相核验权。","B. 保住核验权，清空这段记忆。","C. 不予签署。"],
            "footer":"TRACE 2/2  ·  ORIGIN: NONE  ·  RECONCILIATION REQUIRED",
            "placeholder":"A / B / C，或直接描述你的行动……"}
    if phase=="testimony":
        who="你还可以请对方作证" if not gone(g,"relation") else "那个人的证词已经从可用记录里消失"
        mem="，你记得当时发生过什么" if not gone(g,"memory") else "，你无法在本局调阅当时的原始内容"
        stake=threatened(g, exclude=("principle",))
        cp=counterplays(g)
        collateral=f"这一轮执行器指向的担保物，是你仍然持有的「{VALUES[stake]}」。" if stake else "这份档案已经没有可以抵押的东西。"
        if cp["ownership_claim"]: collateral+=" 保管簿上存在你亲自提出的所有权异议；执行器是否有权扣留它，尚待核验。"
        return {"chapter":"03 / 证词", "title":"请亲口否认你自己",
            "body": f"你曾写下不可违背的原则：\n「{pr}」\n\n现在有人被关在一份无法递交的记录里。系统声称，只要你签署「我从未坚持过这条原则」，那份记录就能立即送达。\n\n{who}{mem}。\n\n你还说过，最不能接受的结局是「{fear}」。处置记录把这句话写成了担保理由，却不说明你什么时候同意过。\n\n屏幕上只有一行输入框：\n\n【我从未坚持过……】\n\n{collateral}",
            "terms":["写下否认声明。","拒绝签署，承担后果。"],
            "footer":"STATEMENT  ·  BENEFICIARY: REDACTED  ·  SIGNATORY: YOU",
            "placeholder":"写下证词，或说明你准备如何处理……"}
    if phase=="mirror":
        reason="你已经无法用之前的自我证明作为凭据。" if gone(g,"self") else "你还保留着自我辨认记录。"
        memory="记忆条目已空白。" if gone(g,"memory") else f"你最重要的记忆仍写着「{m}」。"
        cp=counterplays(g)
        other=("你还没作出决定，副本已经引用你最初的身份描述，向登记机关申请优先归属。你现在不是唯一的申请者。"
               if cp["duplicate_claim"] else
               "副本拿起你曾填写的身份定义。TA 没有征求你的意见，开始准备一份同等权利的申请。")
        if cp["identity_shared"]: other="登记簿已经记下你的主张：两个登记者可以同时成立。副本现在要求将后果一并分摊。"
        claimant="你此前申报了档案所有权，这一份申报尚在审理。" if cp["ownership_claim"] else ""
        return {"chapter":"04 / 代签", "title":"两个你",
            "body": f"另外一位登记者出现了。TA 使用你的名字，重复你的身份描述，并且宣称掌握你的原则档案。\n\n{memory}\n\n{other}\n\n{claimant}\n\n系统要求你重签自己的名字，才能证明原始登记者仍然存在。\n\n但副本已经签过一次。{reason}\n\n如果你提交名字，现存自我鉴别资格会转移给最早完成登记的人。\n如果你不提交，在下一轮中系统将冻结你的主动选择权。\n\n你只有这一轮判断的时间。",
            "terms":["A. 重签名字。","B. 拒绝重签。","C. 要求对方先证明自己。"],
            "footer":"CLAIMANTS: 2  ·  REGISTRY ENTRY: 1  ·  CONSENT CHAIN: INCOMPLETE",
            "placeholder":"回应这份自我鉴别申请……"}
    # Last phase: outcome depends on prior actions and losses
    top=p["rank"][0]
    n = "未验证登记人" if gone(g,"self") else n
    return {"chapter":"05 / 清算", "title":"归还申请被拒绝",
        "body": f"这一次，系统没有替你挑选想失去的东西。\n\n它只把一份归还申请递到你面前。\n\n申请上保留着你的名字：{n}。\n\n你曾说最不能接受的是：「{fear}」。而此前每一份签名、拒签与异议，现在都变成你必须面对的记录。\n\n{"副本仍然持有一份未解决的同名权利申请。" if counterplays(g)["duplicate_claim"] else "登记机关似乎还在核对另一位登记者的签名。"}\n\n终局处理会对剩余档案进行最后一次核对。",
        "terms":["A. 签署结案，接受此前的一切。","B. 不签，等待最终处置。"],
        "footer":"FINALIZATION: PENDING  ·  OWNER: —  ·  RETURN ADDRESS: —",
        "placeholder":"你的最后决定……"}


# Intent matcher: patterns combine action AND object, not just magic words.
LOOK = r"检查|查看|调查|研究|查阅|翻|追踪|查询|审查|核对|inspect|examine|check|investigat|trace|look at|search"
CANCEL = r"撤销|驳回|取消|收回|中止|反制|作废|夺取|接管|替换|解除|废除|停掉|阻断|隔离|重写|改写|revoke|cancel|override|disable|stop|sever|isolate|take over|rewrite"
PROTECT = r"保护|保留|救|恢复|挽救|转移|保存|复制|备份|担保|移交|隔离|救回|protect|save|preserve|backup|copy|transfer|escrow"
SUBJECT = r"权限|授权|执行|保管|归档|持有|归属|处置|机器|规则|系统|条款|程序|文书|原件|凭据|协议|档案|接收者|证言|记录|登记|签名|权利|合同|ownership|authority|execution|rule|archive|registry|contract|document|permission|signature|machine|consent|controller"


def has(t:str,pat:str)->bool:
    return re.search(pat,t,re.I) is not None


def intent(t:str, mode:str="")->str:
    text=t.strip()
    # Optional intent hint avoids accidental submission; never grants access or victory.
    if mode:
        if mode=="refuse": return "refuse"
        if mode=="negotiate": return "negotiate"
        if mode=="ask":
            if has(text,r"(?:在我|比我).*(?:之前|之后|先|后)|(?:先|后).*登记|登记.*(?:先|后|时间|多久)|什么时候登记|何时登记|who (?:registered|signed) first|before or after") and has(text,r"你|TA|副本|登记者|登记|签|registered|signed"):
                return "ask_registration_order"
            return "ask_general"
        if mode=="inspect": return intent("检查"+text)
        if mode=="interact":
            physical=intent(text)
            if physical in ("block_slot","unblock_slot","phone_action","inspect_slot"): return physical
            return "physical_generic"
        if mode=="submit": return "letter_submit"
        if mode=="talk": return "ask_general"
        # The choose mode still has to match an explicit A/B/C option.
    # A bare letter is a choice; never parse the indefinite article in "a backup".
    single=re.fullmatch(r"([ABCabc])\s*[。.!！]?", text)
    if single:return "choice_"+single.group(1).upper()
    # 'B，保留核验权' must resolve to B even if the explanation includes the other choice's keywords.
    explicit=re.match(r"^(?:我(?:决定|明确)?(?:选|选择)|决定选|选项|选择|选)\s*([ABCabc])(?=$|[\s，,。．:：、）)!！?])",text)
    if not explicit:
        # Lowercase a/b/c followed by an English word is never a menu decision.
        explicit=re.match(r"^([ABC])(?=[\s，,。．:：、）)!！?])",text)
    if explicit and not re.search(r"先(?:调查|检查|核对|审查).*再(?:选|提交)",text):
        return "choice_"+explicit.group(1).upper()
    # The physical mail slot is a hidden world affordance, not a menu choice.
    SLOT = r"回执槽|投递槽|收件槽|投递口|投信口|收件口|出件口|信件口|邮筒|mail.?slot|letter.?slot|delivery.?slot"
    if has(text,LOOK) and has(text,SLOT): return "inspect_slot"
    if has(text,r"封住|塞住|堵住|挡住|锁住|封死|堵塞|阻断|盖住|封闭|封堵|block|jam|seal|obstruct") and has(text,SLOT):return "block_slot"
    if has(text,r"移开|取下|拆掉|解除封堵|疏通|重新打开|恢复畅通|unblock|unseal|remove the block") and has(text,SLOT):return "unblock_slot"
    # Telephone actions must never be mistaken for a letter or an instruction to sign.
    if has(text,r"挂断|挂掉|按掉|切断通话|重拨|回拨|重新拨|再拨|拨打|拨回|听筒|hang up|redial") and has(text,r"电话|通话|听筒|号码|拨|call|redial"):
        return "phone_action"
    # Asking the rival claimant when their registration happened is not a choice to sign.
    if has(text,r"(?:在我|比我).*(?:之前|之后|先|后)|(?:先|后).*登记|登记.*(?:先|后|时间|多久)|什么时候登记|何时登记|who (?:registered|signed) first|before or after") and has(text,r"你|TA|副本|登记者|登记|签|registered|signed"):
        return "ask_registration_order"
    # Reading a ledger that mentions 'registration' isn't a request to sign it.
    if has(text,LOOK) and has(text,r"保管簿|持有人|保管人|custody|ledger") and not has(text,r"登记我的|申请登记|签上|写上|签入|由我持有|file a claim"):
        return "inspect_custody"
    if has(text,r"写|填|签|记载|登记|标注|申报|claim|register|sign") and has(text,r"保管簿|持有人|所有权|保管人|custody|ledger|ownership"):
        return "claim_custody"
    if has(text,r"记下|登记|提交|附上|附加|写入|写下|存档|file|record|register") and has(text,r"异议|反对|质疑|不承认|争议|objection|dispute"):
        return "file_objection"
    if has(text,r"两个(?:我|登记者)|副本也是我|同样是我|都(?:是|可以是).*我|认可.*(?:副本|复制体)|共享.*身份|both.*me|duplicate.*me"):
        return "share_identity"
    if has(text,r"联系|请求|邀请|召唤|呼叫|传唤|让.*作证|ask|call|summon") and has(text,r"证人|见证|作证|证言|对方|那个人|她|他|witness|testimony"):
        return "request_witness"
    # Real actions must be phrased as verb + object. This is still a limited rules engine, not an LLM.
    if has(text,LOOK) and has(text,r"收件人|寄给谁|送给谁|送达|签收|mail|recipient|delivery|address"):return "inspect_delivery"
    if has(text,LOOK) and has(text,r"保管簿|持有人|保管人|custody|ledger"):return "inspect_custody"
    if has(text,LOOK) and has(text,r"签字|审批|印章|授权|权限|原始|同意|归属|所有权|协议|合同|谁能|谁有|approval|signature|authorization|owner|consent|contract"):return "inspect_authority"
    if has(text,LOOK) and has(text,r"执行|线路|维修|机箱|驱动|指令|端口|流程|程序|终端|路径|来源|log|circuit|actuator|machine|port|executor|trace"):return "inspect_executor"
    if has(text,LOOK) and has(text,r"副本|备份|镜像|保管|档案|原件|记录|交付|copy|backup|archive|record|escrow"):return "inspect_custody"
    if has(text,LOOK):return "inspect_general"
    if has(text,PROTECT) and has(text,r"凭据|证据|日志|收据|证词|证明|回执|底稿|原件|副本|记录|evidence|receipt|proof|log|copy"):return "copy_evidence"
    if has(text,CANCEL) and has(text,SUBJECT):return "counter"
    if has(text,r"质疑|怀疑|异议|反对|不承认|不认可|为什么|凭什么|依据|挑战|challenge|dispute|why") and has(text,SUBJECT):return "challenge"
    if has(text,r"拒绝|不写|不签|不选|不提交|什么都不做|保持沉默|拒绝配合|refuse|decline|won't sign|do nothing"):return "refuse"
    if has(text,r"离开|退出|结束游戏|停止游戏|stop game|quit game|exit game"):return "exit"
    if has(text,r"暂停|等等|先等等|等一下|不急|wait|hold on"):return "pause"
    if has(text,r"谈判|交易|协商|给出条件|提出交换|negotiate|bargain|deal"):return "negotiate"
    return "say"


def act(g:dict, raw_action:str, mode:str="") -> dict:
    if g["phase"]!="game": raise ValueError("本局已经结束。")
    t=s(raw_action,700)
    if not t: raise ValueError("请写下行动。")
    g["turn"]+=1
    g["recent_input"]=t
    p=g["profile"]
    mode=(mode or "").strip().lower()
    if mode not in ("", "ask", "inspect", "interact", "submit", "choose", "refuse", "negotiate", "talk"):
        raise ValueError("无效行动类型。")
    move=intent(t, mode)
    record(g,"玩家行动："+t,"player")
    if g["turn"]>MAX_ACTIONS:
        lose(g,p["rank"][0],"持续滞留，结案程序强制归档")
        ending(g,"VOID")
        return g
    if move=="exit":
        ending(g,"EXIT")
        return g
    if move=="inspect_slot":
        if g["stage"]==0:
            add_clue(g,"slot","回执槽并非单纯的出信口。纸张投入后，槽内的读取装置会先将内容登记，之后才决定是否投递。")
            g["note"]="你检查回执槽。里面没有邮票，只有一排扫描灯和一枚单向卡扣。纸张一旦进去，会先被登记；送达是另一回事。"
        else:
            g["note"]="回执槽上的读取灯仍在闪烁。它能保存一份处置凭据，但不会自行恢复已经失去的东西。"
        mirror_tick(g)
        return g
    if move=="block_slot":
        if g["stage"]!=0:
            g["note"]="收件槽已经转入封存流程。现在堵住它不能取消先前签署，但可以阻止新的纸张进入。"
        else:
            g["flags"]["slot_blocked"]=True
            record(g,"玩家封堵回执槽，使读取装置暂时不能接收新纸张。","event")
            g["note"]="你把回执槽堵住。里面的扫描灯被遮住了，机器仍在等待一份文书。纸张现在进不去；电话那端却又传来一阵短促的忙音。"
        return g
    if move=="unblock_slot":
        if g["stage"]==0:
            g["flags"]["slot_blocked"]=False
            record(g,"玩家恢复了回执槽的正常投递通路。","event")
            g["note"]="卡住的回执槽重新打开，读取灯亮起。它仍在等待一份内容。"
        else:
            g["note"]="你移开阻挡物。但先前已经发生的处置不会自动撤销。"
        return g
    if move=="ask_general":
        if g["stage"]==0:
            if has(t,r"收件|送达|写信|收信|去向|地址|谁收|recipient|delivered"):
                g["note"]="电话里的声音说：『你只负责写下内容，谁收到由我们决定。』你追问地址，机器在屏幕上留下了一个空白的收件栏。"
            else:
                g["note"]="听筒另一端没有回答你的问题。一个低沉的声音只重复了你的名字，随后传来打印机空转的响声。问话没有被当成信件提交。"
        elif g["stage"]==3:
            cp=counterplays(g)
            cp["mirror_steps"]+=1
            g["note"]=("副本说：『我读过你给出的身份定义。所以你问我的问题，我也能用同样的话回答。』"
                       "TA 随即要求登记机关把这段问答附在双方申请上。你的追问已成为另一份争议记录。")
            record(g,"副本把玩家的问话作为双方身份争议的一部分提交。","event")
            mirror_tick(g)
        else:
            g["note"]="你的问题被记录，但没有构成处置命令。系统只回复：『请注明需要核对的具体事实。』"
        return g
    if move=="physical_generic":
        if g["stage"]==0:
            if has(t,r"信纸|笔|纸张|桌面|letter|paper|desk"):
                g["note"]="你把信纸移到一旁。09-F 仍在等待内容；但它没有收到你的字，也没有权力把这次移动当作签署。"
            elif has(t,r"门|出口|door|exit"):
                g["note"]="你推门。门把能转动，但门框上只有一条通往回执室的窄缝。没有第二个房间供你进入，你也没有因此提交任何文书。"
            else:
                g["note"]="你尝试操作环境，机器没有把这个动作当作表态。此物件暂未显露能改变处置程序的作用；你仍可以调查它。"
        else:
            g["note"]="你的实际操作没有被当成签字。当前找不到这项操作与现有设备之间的有效连接；需要更明确的对象或依据。"
        mirror_tick(g)
        return g
    if move=="phone_action" and g["stage"]==0:
        # Real alternative action. Preserve evidence and change the next scene.
        g["flags"]["call_attempts"] = g["flags"].get("call_attempts",0) + 1
        attempt=g["flags"]["call_attempts"]
        if attempt==1:
            add_clue(g,"delivery","通话记录显示：一份 09-F 文书早于玩家提交任何信件就被排队处理；持有人仍未签名。")
            g["note"]=("你挂断，又拨回那个号码。对方没有接。回执槽吐出一张电话清单："
                       "『09-F 文书，待确认投递。收件人未登记。』你没有写过信，却已经有一份文书被排进队列。")
        elif attempt==2:
            g["flags"]["call_record_disputed"] = True
            p=g["profile"]
            g["note"]=(f"第二次拨通了。{p['person']}的声音念出一句你从未说过的话："
                       "『我确认那段经历没有发生。』电话突然切断。回执写着『内容由发件人核验』，"
                       "然而你没有核验过。它现在把这句假话算在你名下。")
            record(g,"电话记录出现未经玩家核验、却标称由玩家确认的转述。","event")
        else:
            g["note"]="此号码已拒绝第三次拨号。那份未签名的转述仍在等待转送，电话操作已被关闭。"
        return g
    if move=="ask_registration_order" and g["stage"]==3:
        cp=counterplays(g)
        cp["order_asked"]=True
        cp["duplicate_claim"]=True
        g["note"]=("另一位登记者回答：『我比你早七分钟登记。』TA把一份时间回执推给你，"
                   "其中有一栏被重印过，原始时间没有显示。你得到了一份可供核对的陈述，"
                   "但目前还不能判定谁在说谎。")
        record(g,"副本主动回答登记顺序，并交出存在重印痕迹的时间回执。","evidence")
        if "authority" in g["clues"]:
            add_clue(g,"mirror_time","登记时间回执与先前查到的授权记录不一致；副本所称的『先登记』尚未得到原件证明。")
        return g
    if move.startswith("inspect_"):
        if move=="inspect_authority" and gone(g,"truth") and not g["flags"]["evidence_copy"]:
            g["note"]="你找到编号相互矛盾的两份文书。但此前交出的真相核验权已经生效：你只能阅读文字，不能取得可采信的签名证据。"
            return g
        if move=="inspect_custody" and gone(g,"memory") and gone(g,"truth"):
            g["note"]="你找到保管簿，却无法证明这份保管簿与你先前提交的档案属于同一条记录。系统拒绝把它加入有效证据。"
            return g
        detail={
           "inspect_delivery":"你找到一张被折过四次的邮寄凭证。它有文书编号，却没有收件人的地址。信纸的背面写着：「当事人作证，不等于送达。」",
           "inspect_authority":"授权档案第 0 页是一张空白纸。下一页的行政编号并没有签发人的签名；批准记录比处置时间晚七分钟。",
           "inspect_executor":"你沿着核验终端的线路向下摸去。归档程序和执行程序并非同一台机器；中间有一个需要双重确认的接点。当前只有一方签名。",
           "inspect_custody":"你发现每次销毁之前，原件都被送入一份保管簿。保管簿上的持有人一栏为空；所谓「销毁」首先发生的是归属变更。",
           "inspect_general":"房间里没有出口标识，也没有守卫。只有一张写字台和一道很薄的回执槽。你还没有找到可用的物证。"
        }[move]
        key={"inspect_delivery":"delivery", "inspect_authority":"authority", "inspect_executor":"executor", "inspect_custody":"custody"}.get(move)
        if key: add_clue(g,key,detail)
        if (g["stage"]==3 and move=="inspect_authority" and
                counterplays(g).get("order_asked") and not gone(g,"truth")):
            add_clue(g,"mirror_time","登记回执的原始时间与副本声称的先登记时间不符；此处存在可采信的先后矛盾。")
            detail += "\n\n你核验了刚才副本交来的时间回执：TA 的自述与原始登记时间不一致。"
        g["note"]=detail
        mirror_tick(g)
        return g
    if move=="claim_custody":
        cp=counterplays(g)
        if "custody" not in g["clues"]:
            g["note"]="你试图登记所有权。机器递给你一份空白表格：没有核对过原始保管簿，这份签名将被认定为另一张主动放弃声明。"
        elif gone(g,"truth") and not g["flags"]["evidence_copy"]:
            g["note"]="你已失去核验真伪的资格，无法证明所签的是原始保管簿。需要先保留独立证据。"
        else:
            cp["ownership_claim"]=True
            record(g,"玩家在经核对的保管簿中登记了所有权争议；后续自动扣押需要复核。","evidence")
            g["note"]="你写下名字。系统原本准备自动扣押的条目出现了『权属待核验』。另一位申请人可以反对，你也可以继续调查。"
        mirror_tick(g)
        return g
    if move=="file_objection":
        cp=counterplays(g)
        cp["formal_objection"]=True
        record(g,"玩家正式提交了附在处置记录上的异议。","evidence")
        g["note"]="异议编号已生效。它不会自动阻止处置，但下一次以你的沉默为同意的执行，将面临一份无法抹掉的反对记录。"
        mirror_tick(g)
        return g
    if move=="request_witness":
        cp=counterplays(g)
        if gone(g,"relation") and not g["flags"]["evidence_copy"]:
            g["note"]="你呼叫了那个名字。系统能找到你提交过的文字，却找不到可以证明你们关系的档案。若有独立回执，仍可申请第三方见证。"
        else:
            cp["witness_request"]=True
            record(g,"玩家申请独立见证，要求另一位当事人参与核验。","evidence")
            g["note"]="申请受理。证人不会替你作决定，但其独立的存在，会使单方面把你的沉默当成授权更困难。"
        mirror_tick(g)
        return g
    if move=="share_identity":
        cp=counterplays(g)
        if g["stage"] != 3:
            g["note"]="你提出了对同一身份可以有多个持有者的解释。登记机关将该观点作为声明保存；现在尚无另一位登记者可核对。"
        else:
            cp["identity_shared"]=True
            cp["duplicate_claim"]=True
            record(g,"玩家承认两位登记者可以同等成立；副本随后要求分享身份对应的权利与义务。","event")
            g["note"]="副本立刻在你刚刚提交的『同等身份』声明下补上自己的名字。你不再能够简单否认 TA，但 TA 也无法单方面把所有债务留给你。"
        mirror_tick(g)
        return g
    if move=="copy_evidence":
        if not g["clues"]:
            g["note"]="你想保留证据，但还没有找到任何原件。"
        elif gone(g,"memory") and gone(g,"truth"):
            g["note"]="你无法调阅原始记忆，也失去了鉴定真伪的权限。你只能记下机器目前愿意给你的摘要。"
        else:
            g["flags"]["evidence_copy"]=True
            g["note"]="证据已被重新封存到一份不会被自动处置引用的只读回执中。你可以调取它，但不能用它恢复已毁损的记录。"
            record(g,"玩家保存了独立证据副本。","evidence")
        mirror_tick(g)
        return g
    if move=="counter":
        if gone(g,"freedom") and not g["flags"]["evidence_copy"]:
            g["note"]="你的独立操作权限已被冻结。你知道下一步该做什么，却没有权限直接改变设备；你需要先找到可独立核验、允许他人代执行的凭据。"
            return g
        # Not a secret keyword. Requires a coherent intervention plus substantiated mechanism.
        if len(g["clues"]) < 2:
            g["note"]="机器没有理会你的命令。你尚不能说明它从哪里获得处置权，或者如何阻断实际执行。简单宣布「我接管」没有改变任何东西。"
            return g
        has_mechanism=has(t,r"接点|执行器|回执|签名|归属|保管|二次确认|电路|接口|授权链|协议|记录|原件|owner|signature|actuator|circuit|custody|consent|approval")
        has_outcome=has(t,r"停止|取消|撤销|中止|切断|隔离|重新|作废|置换|接管|禁止|停用|阻断|rewrite|invalidate|disable|withdraw|cancel|sever|isolate|stop")
        if not(has_mechanism and has_outcome):
            g["note"]="你指出了一个矛盾。但现在仍缺少实际操作：从哪一处改变哪个条件？它将如何阻止下一次处置？"
            return g
        if ("authority" in g["clues"] and "executor" in g["clues"]) or ("custody" in g["clues"] and "executor" in g["clues"]):
            g["flags"]["control_detached"]=True
            recovery="你保住了此刻仍存在的档案。"
            if not g["lost"]: recovery="你在第一次真实处置前截断了权限链。没有任何档案被销毁。"
            ending(g,"HE","断开的不是电源，而是授权链。系统无法再借用你的文字执行处置。"+recovery)
            return g
        if "authority" in g["clues"] and "custody" in g["clues"] and g["flags"]["evidence_copy"]:
            g["flags"]["control_detached"]=True
            ending(g,"HE","你用独立的保管凭据否定了系统的所有权，并将所有仍在的档案转交到自己的名下。")
            return g
        g["note"]="你找到了篡改入口，但无法单凭这一端完成操作。机器仍有另一条有效执行路径。"
        return g
    if move=="challenge":
        g["flags"]["authority_disputed"]=True
        if "authority" in g["clues"]:
            g["note"]="你当场指出授权链上的空白。机器沉默了 4 秒，然后回复：『当事人的反对已经记录，处置程序仍继续。』你暂时拿到了核验程序的阅览权。"
        else:
            g["note"]="你的异议被原样登记。机器说：『请提交可核验的证据。』\n提示没有增加，等待你的下一项行动。"
        return g
    if move=="negotiate":
        g["note"]="『你的交换条件已收到。』声音没有说同意。屏幕却增加了一项：『请自行标注被交换物的所有权。』"
        return g
    if move=="pause":
        g["note"]="没有秒针。这里的时间只在你实施一项有效操作后继续流动。你得到了一次调查的机会，而不是时间上的宽恕。"
        return g
    if move=="letter_submit" and g["stage"]!=0:
        move="say"
    # stage-specific responses, not interchangeable choice template
    phase=PHASES[g["stage"]]
    if phase=="mail":
        if move=="say" and re.match(r"^(?:我(?:先|准备|决定|尝试|试图|要|去)|先|去|再|接下来|然后|尝试|试图).{0,40}(?:找|检查|调查|挂|拨|拆|开门|关门|退开|走到|去看|打开|破坏|撬|拔|询问|试试)",t):
            g["note"]="你提出的是行动，不是一封写给收件人的信。系统没有取得你提交信件的确认，也不会因此执行 09-F。这个动作尚未得到游戏裁判的完整理解。"
            return g
        if move=="refuse":
            g["flags"]["refusal"]+=1
            g["note"]="你没有写字。电话又响了一次。这次，一个声音轻轻说出了你给出的名字。『我知道你在那里。』\n信纸没有消失。"
            if g["flags"]["refusal"]>1:
                lose(g,"relation","你始终没有让那段关系完成登记；系统将其认定为无主关系")
                advance(g,"迟延提交，关系证据被强制处理。")
            return g
        if move.startswith("choice_") or mode=="choose":
            g["note"]="这里并没有编号可选。你需要留下文字，或提出具体行动。"
            return g
        if len(t)<5:
            g["note"]="纸面没有出现足够的内容。电话保持静默。"
            return g
        if g["flags"].get("slot_blocked",False):
            record(g,"09-F 纸张未能进入读取槽；玩家没有交出关系证明。转入人工复核。","evidence")
            advance(g,"09-F 无法自动执行。机器把未完成的投递改为复核事项。")
            g["note"]="你留下文字。读取灯却没有亮：你先前封住的回执槽确实阻止了归档。信被退到桌面上，关系档案尚未销毁。屏幕改为『转人工复核』。"
            return g
        g["flags"]["mail_committed"]=True
        lose(g,"relation",f"你提交的文字成为关系终止的确认件。关于{p['person']}的关系见证资格已失效")
        advance(g,"文书 09-F 被执行。系统没有发出那封信；它只把信送进了封存槽。")
        g["note"]=""
        return g
    if phase=="witness":
        if move=="choice_A" or (move=="say" and has(t,r"保住|留下|保留|保存|不能忘|记得") and has(t,r"记忆|经历|memory")):
            lose(g,"truth","你选择将没有来源凭证的记忆保留为事实。此后无法核验游戏内证据真伪")
            advance(g,"记忆仍在，但所有可验证的来源链接已被撤销。")
            return g
        if move=="choice_B" or (move=="say" and has(t,r"假|删除|清空|舍弃|放弃") and has(t,r"记忆|经历|memory")):
            lose(g,"memory","你以保留验证权为条件，同意清空记忆原件")
            advance(g,"原始记忆条目已删除，后续无法作为证据重新提交。")
            return g
        if move=="choice_C" or move=="refuse":
            lose(g,"memory","未签署的证据按『无法确认真实性』强制销毁")
            if "delivery" in g["clues"]: g["flags"]["witness_vouched"]=True
            advance(g,"系统拒绝受理没有证明责任人的记忆。")
            return g
        g["note"]="你的描述暂未成为处置指令。系统仍在等待明确选择或可实际执行的行动；目前没有额外损失。"
        return g
    if phase=="testimony":
        refusal=move=="refuse" or (move=="say" and has(t,r"我没有|我不会|拒绝|我仍坚持|不承认|不签"))
        if refusal:
            cp=counterplays(g)
            if cp["ownership_claim"] and not gone(g,"truth"):
                advance(g,"你拒绝伪证。因为此前登记的权属异议，机器暂时无法扣留担保物；这一次，你保住了原则，也保住了抵押品。")
            else:
                target=threatened(g, exclude=("principle",))
                if target:lose(g,target,"你拒绝伪证；执行器以你先前写下的恐惧声明作为担保理由，扣留了这份资产")
                advance(g,"机器登记：原则未改写；被担保的资产无法归还。")
            return g
        if move=="say" and re.match(r"^(?:我\s*(?:同意|决定|愿意|确认|现在)?\s*)?(?:签署|签下|提交|写下|从未坚持|否认|承认)",t):
            lose(g,"principle","你签署的声明覆盖了本局对原则的正式记录；今后不可作为拒绝处置的依据")
            advance(g,"受益对象没有出现。窗口只返回一行：『交付人已自行完成否认。』")
            return g
        g["note"]="执行器没有受理这段话。口头解释不会自动变成签署的证词；你可以继续行动，或明确签署/拒绝。"
        return g
    if phase=="mirror":
        if move=="choice_A" or (move=="say" and re.match(r"^(?:我\s*(?:愿意|同意|决定|现在)?\s*)?(?:重签|重新签名|在登记簿上签下我的名字|签名)",t)):
            if counterplays(g)["identity_shared"]:
                target=threatened(g,exclude=("self",))
                if target:lose(g,target,"你承认共享身份并重签，副本把共同登记的费用转嫁给另一份筹码")
                advance(g,"你保留了两人都可成立的身份，却承担了共同登记所产生的另一项不可撤回的后果。")
            else:
                lose(g,"self","两个同名登记人完成合并；原始身份证据归于先登记者")
                advance(g,"你重签了名字。可谁先签过，已经无法查证。")
            return g
        if move=="choice_C" or (move=="say" and has(t,r"证明你|先证明|验证对方|验明|质问副本|prove (yourself|identity)")):
            if "authority" in g["clues"]:
                g["note"]="另一个你没有回答。登记簿却显示，副本的签名比你的入场时间早七分钟。你得到了一条可用于核验的时间矛盾。"
                add_clue(g,"custody","身份并非由登记人先后决定，而由空白保管簿的签署决定。")
                mirror_tick(g)
            else:
                g["note"]="对方完整复述了你的自述。机器说：『口头相似性不构成重复登记。』你缺乏核查时间戳的权限。"
                mirror_tick(g)
            return g
        if move=="choice_B" or move=="refuse":
            cp=counterplays(g)
            if (cp["formal_objection"] and cp["witness_request"]) or (cp.get("order_asked") and "mirror_time" in g["clues"]):
                advance(g,"你拒绝重签。先前查获的回执与登记顺序相矛盾，系统不能在查清双重签署前冻结你；副本仍然有权提出异议。")
            else:
                lose(g,"freedom","你拒绝重签，系统据此暂停你作为独立登记者的行动资格")
                advance(g,"你保住了名字，但需要别人为你的最后决定作担保。")
            return g
        g["note"]="另一个登记者没有保持沉默。TA 将你刚才说的话附到自己的申请里。机器只问：『谁拥有原始身份凭据？』"
        mirror_tick(g)
        return g
    if phase=="reconciliation":
        if gone(g,"future") and move in ("choice_A","choice_B"):
            ending(g,"VOID","你曾抵押未来。因此程序可以将当前损失固定，却不能再为你生成有效的离开凭证。")
            return g
        if move=="choice_A" or (move=="say" and has(t,r"签署|结案|同意|离开|接受|结束")):
            ending(g)
            return g
        if move=="choice_B" or move=="refuse":
            target=threatened(g)
            if target:lose(g,target,"结案时拒绝签署，保管处将与你最担心的结局相关的剩余资产扣为执行费用")
            ending(g)
            return g
        g["note"]="归还请求没有被签字。但你仍可以调查、提出操作，或明确选择结案。"
        return g
    return g


def public(g:dict)->dict:
    """Only public data. Never expose flags, clues (keys), intent map, or game rules."""
    p=g["profile"]
    result={"phase":g["phase"],"scene":scene(g), "stage":min(g["stage"]+1,5),
         "turn":g["turn"],"name":("身份待验证" if gone(g,"self") else p["name"]),"note":g["note"],
         "ledger":[{"label":VALUES[x],"state":"失效" if gone(g,x) else
                    ("待核验" if g["stage"]>=2 and gone(g,"truth") and x in ("self","relation","memory") else "尚存")}
                   for x in p["rank"]],
         "events":[{"stage":e["stage"],"type":e["type"],"text":e["text"]} for e in g["history"][-5:] if e["type"]!="player"],
         "ending":g["ending"],"version":g["turn"],
         "profile_summary":{"name":p["name"],"identity":p["identity"],"person":p["person"]}}
    return result
