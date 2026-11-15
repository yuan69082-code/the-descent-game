"""THE DESCENT v2 -- authoritative rules never shipped to the browser.

Game consequences are fictional and confined to a server-side session.
"""
from __future__ import annotations
from datetime import datetime, timezone
import re
from typing import Any

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
                 "witness_vouched":False, "trapped":False},
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


def ending(g:dict,kind:str|None=None,how:str=""):
    if kind is None:
        alive=7-len(g["lost"])
        if alive>=5:kind="NE"
        elif alive>=2:kind="BE"
        else:kind="VOID"
    g["phase"]="ended"
    p=g["profile"]
    text={
        "HE":"程序还在请求你的答复。你却不再需要答复它。\n\n它不是被说服，而是失去了把你的文字变成处置命令的权力。\n\n本局尚存的一切保留。已经发生的损失不会因为胜利自动复活。",
        "NE": "门打开了。你确实能够离开。\n\n但档案不再完整。你叫得出某些名字，却无法再以它们证明原来的东西。你赢得了一次离开，而非回到从前。",
        "BE": "你终于得到了一份写着「通过」的凭证。\n\n纸上没有任何人能证明是谁通过了审查。",
        "VOID": "请求已完成。\n\n没有可交付的对象。\n\n系统仍在等待一个已不存在的名字。",
        "EXIT":"你终止了体验。所有损失都只发生在本局档案，不会影响你在游戏外的身份、关系和记忆。",
    }[kind]
    if how: text += "\n\n"+how
    g["ending"]={"kind":kind,"title":{"HE":"交付失败","NE":"未能原样归还","BE":"合法空白","VOID":"无人签收","EXIT":"你已离开"}[kind],"text":text,
                 "lost":[VALUES[x] for x in g["lost"]],"remaining":[VALUES[x] for x in VALUES if x not in g["lost"]]}
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


def intent(t:str)->str:
    text=t.strip()
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


def act(g:dict, raw_action:str) -> dict:
    if g["phase"]!="game": raise ValueError("本局已经结束。")
    t=s(raw_action,700)
    if not t: raise ValueError("请写下行动。")
    g["turn"]+=1
    g["recent_input"]=t
    p=g["profile"]
    move=intent(t)
    record(g,"玩家行动："+t,"player")
    if g["turn"]>MAX_ACTIONS:
        lose(g,p["rank"][0],"持续滞留，结案程序强制归档")
        ending(g,"VOID")
        return g
    if move=="exit":
        ending(g,"EXIT")
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
    # stage-specific responses, not interchangeable choice template
    phase=PHASES[g["stage"]]
    if phase=="mail":
        if move=="refuse":
            g["flags"]["refusal"]+=1
            g["note"]="你没有写字。电话又响了一次。这次，一个声音轻轻说出了你给出的名字。『我知道你在那里。』\n信纸没有消失。"
            if g["flags"]["refusal"]>1:
                lose(g,"relation","你始终没有让那段关系完成登记；系统将其认定为无主关系")
                advance(g,"迟延提交，关系证据被强制处理。")
            return g
        if move.startswith("choice_"):
            g["note"]="这里并没有编号可选。你需要留下文字，或提出具体行动。"
            return g
        if len(t)<5:
            g["note"]="纸面没有出现足够的内容。电话保持静默。"
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
            if cp["formal_objection"] and cp["witness_request"]:
                advance(g,"你拒绝重签。此前登记的书面异议与独立证人共同否定了自动代签的条件；这次冻结没有生效。副本仍持有另一份独立申请。")
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
