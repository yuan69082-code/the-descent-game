"""THE DESCENT v2 -- authoritative rules never shipped to the browser.

Game consequences are fictional and confined to a server-side session.
"""
from __future__ import annotations
from datetime import datetime, timezone
import re
from typing import Any

VALUES = {"self":"自我", "relation":"关系", "memory":"记忆", "truth":"真相", "freedom":"自主权", "principle":"原则", "future":"未来"}
PHASES = ["mail", "witness", "testimony", "mirror", "reconciliation"]
MAX_ACTIONS = 26


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
        return {"chapter":"02 / 复核", "title":"被你证明过的事",
            "body": f"{relation}\n\n系统调出了你提供的记忆：\n\n「{m}」\n\n机器宣称，它找不到这段记忆的原始凭据。\n\n它给出两种处理办法：\n保留这段记忆，但从此不允许使用它来判断真假；或者承认它不是可靠证据，档案将清空该记忆。\n\n还有一项通知：不签署的记录，在本轮结束后由系统按「证据不足」处置。",
            "terms":["A. 保住记忆，放弃真相核验权。","B. 保住核验权，清空这段记忆。","C. 不予签署。"],
            "footer":"TRACE 2/2  ·  ORIGIN: NONE  ·  RECONCILIATION REQUIRED",
            "placeholder":"A / B / C，或直接描述你的行动……"}
    if phase=="testimony":
        who="你还可以请对方作证" if not gone(g,"relation") else "那个人的证词已经从可用记录里消失"
        mem="，你记得当时发生过什么" if not gone(g,"memory") else "，你无法在本局调阅当时的原始内容"
        return {"chapter":"03 / 证词", "title":"请亲口否认你自己",
            "body": f"你曾写下不可违背的原则：\n「{pr}」\n\n现在有人被关在一份无法递交的记录里。系统声称，只要你签署「我从未坚持过这条原则」，那份记录就能立即送达。\n\n{who}{mem}。\n\n屏幕上只有一行输入框：\n\n【我从未坚持过……】\n\n如果你不签，执行器会在这一轮把你当前排序最高、尚存的价值锁为抵押品。",
            "terms":["写下否认声明。","拒绝签署，承担后果。"],
            "footer":"STATEMENT  ·  BENEFICIARY: REDACTED  ·  SIGNATORY: YOU",
            "placeholder":"写下证词，或说明你准备如何处理……"}
    if phase=="mirror":
        reason="你已经无法用之前的自我证明作为凭据。" if gone(g,"self") else "你还保留着自我辨认记录。"
        memory="记忆条目已空白。" if gone(g,"memory") else f"你最重要的记忆仍写着「{m}」。"
        return {"chapter":"04 / 代签", "title":"两个你",
            "body": f"另外一位登记者出现了。TA 使用你的名字，重复你的身份描述，并且宣称掌握你的原则档案。\n\n{memory}\n\n系统要求你重签自己的名字，才能证明原始登记者仍然存在。\n\n但副本已经签过一次。{reason}\n\n如果你提交名字，现存自我鉴别资格会转移给最早完成登记的人。\n如果你不提交，在下一轮中系统将冻结你的主动选择权。\n\n你只有这一轮判断的时间。",
            "terms":["A. 重签名字。","B. 拒绝重签。","C. 要求对方先证明自己。"],
            "footer":"CLAIMANTS: 2  ·  REGISTRY ENTRY: 1  ·  CONSENT CHAIN: INCOMPLETE",
            "placeholder":"回应这份自我鉴别申请……"}
    # Last phase: outcome depends on prior actions and losses
    top=p["rank"][0]
    n = "未验证登记人" if gone(g,"self") else n
    return {"chapter":"05 / 清算", "title":"归还申请被拒绝",
        "body": f"这一次，系统没有替你挑选想失去的东西。\n\n它只把一份归还申请递到你面前。\n\n申请上保留着你的名字：{n}。你最初给出的恐惧是：\n「{fear}」\n\n仍然能够使用的筹码：{alive_desc(g)}。\n\n你可以签署结案，这会把目前的一切损失固定下来；也可以继续拖延，直到本局没有剩余可抵押的事物。\n\n终局处理会对剩余档案进行最后一次核对。",
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
    text=t.strip(); low=text.lower()
    if re.fullmatch(r"(?:我(?:选择|选|要选|决定选)\s*)?([abcABC])\s*[。.!！]?",text): return "choice_"+re.search(r"([abcABC])",text,re.I).group(1).upper()
    # Real actions must be phrased as verb + object. This is still a limited rules engine, not an LLM.
    if has(text,LOOK) and has(text,r"收件人|寄给谁|送给谁|送达|签收|mail|recipient|delivery|address"):return "inspect_delivery"
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
        g["note"]="系统要求的是本轮的证据处置意见，不是故事概括。它暂时保留你的陈述；但仍需要具体行动。"
        return g
    if phase=="testimony":
        refusal=move=="refuse" or (move=="say" and has(t,r"我没有|我不会|拒绝|我仍坚持|不承认|不签"))
        if refusal:
            possible=[x for x in p["rank"] if not gone(g,x) and x!="principle"]
            if possible:lose(g,possible[0],"你拒绝伪证，执行器从当下最重要的尚存资产中扣留保证物")
            advance(g,"机器登记：原则未改写；被担保的资产无法归还。")
            return g
        if len(t)>4:
            lose(g,"principle","你签署的声明覆盖了本局对原则的正式记录；今后不可作为拒绝处置的依据")
            advance(g,"受益对象没有出现。窗口只返回一行：『交付人已自行完成否认。』")
            return g
        g["note"]="这项证词需要一段可以存档的完整句子。"
        return g
    if phase=="mirror":
        if move=="choice_A" or (move=="say" and has(t,p["name"][:15] if len(p["name"])>1 else r"签名|重签")):
            lose(g,"self","两个同名登记人完成合并；原始身份证据归于先登记者")
            advance(g,"你重签了名字。可谁先签过，已经无法查证。")
            return g
        if move=="choice_C" or (move=="say" and has(t,r"证明你|先证明|验证对方|验明|质问副本|prove (yourself|identity)")):
            if "authority" in g["clues"]:
                g["note"]="另一个你没有回答。登记簿却显示，副本的签名比你的入场时间早七分钟。你得到了一条可用于核验的时间矛盾。"
                add_clue(g,"custody","身份并非由登记人先后决定，而由空白保管簿的签署决定。")
            else:
                g["note"]="对方完整复述了你的自述。机器说：『口头相似性不构成重复登记。』你缺乏核查时间戳的权限。"
            return g
        if move=="choice_B" or move=="refuse":
            lose(g,"freedom","你拒绝重签，系统据此暂停你作为独立登记者的行动资格")
            advance(g,"你保住了名字，但需要别人为你的最后决定作担保。")
            return g
        g["note"]="两个登记人静静等着。机器只问：『谁拥有原始身份凭据？』"
        return g
    if phase=="reconciliation":
        if gone(g,"future") and move in ("choice_A","choice_B"):
            ending(g,"VOID","你曾抵押未来。因此程序可以将当前损失固定，却不能再为你生成有效的离开凭证。")
            return g
        if move=="choice_A" or (move=="say" and has(t,r"签署|结案|同意|离开|接受|结束")):
            ending(g)
            return g
        if move=="choice_B" or move=="refuse":
            remaining=[x for x in p["rank"] if not gone(g,x)]
            if remaining:lose(g,remaining[0],"结案时拒绝签署，保管处将最高优先级剩余资产作为执行费用")
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
         "ledger":[{"label":VALUES[x],"state":"失效" if gone(g,x) else "尚存"} for x in p["rank"]],
         "events":[{"stage":e["stage"],"type":e["type"],"text":e["text"]} for e in g["history"][-5:] if e["type"]!="player"],
         "ending":g["ending"],"version":g["turn"],
         "profile_summary":{"name":p["name"],"identity":p["identity"],"person":p["person"]}}
    return result
