"""Scope-aware in-world bargaining for V3.9.

A proposal is not consent until every attached condition is understood and
enforceable. Unknown or contradictory terms remain negotiations.
"""
from __future__ import annotations
import re

PROPOSALS=(
    ("surveillance",r"监视|监控|窥视|观察|被监管", "接受监视"),
    ("distortion",r"冒名|假冒|替我回答|代答|篡改|歪曲|改写|欺骗|说谎", "接受代答干扰"),
    ("isolation",r"孤独|孤立|隔离|失联|联系不上|无人回应", "接受隔离"),
    ("erasure",r"失忆|遗忘|抹除|清除记忆", "承担记忆流失"),
    ("uncertainty",r"不确定|无法核实|黑箱|不信任|无法确认", "承担无法核实的风险"),
    ("exhaustion",r"疲惫|透支|精力|耗尽|无休止", "承担持续消耗"),
)
DEAL_INTENT=re.compile(r"愿意|接受|同意|承受|承担|我选|我选择|宁愿|我决定|以.+换|付出",re.I)
DEAL_OBJECT=re.compile(r"保住|留下|保护|保存|换取|两个|两者|双方|同时",re.I)
SCOPE_WORDS=re.compile(r"前提|条件|但|必须|要求|只要|仅限|不能|不许|不得|不允许|保证|确保|暂时|不要|禁止|不准|不可",re.I)

NO_REPLY=re.compile(
    r"(?:不能|不得|不许|不允许|别|禁止|不准|不可|不要).{0,16}"
    r"(?:代替|替|冒名|代理|模仿|代表).{0,10}(?:我)?"
    r"(?:回答|回复|发言|说话|联系|决定|操作|发送)"
    r"|(?:不能|不许|别|不得|不要).{0,12}(?:替我回答|替我说话|替我决定)",re.I)
NO_EXPAND=re.compile(
    r"(?:不能|不得|不许|不允许|禁止|别|不准|不可).{0,18}"
    r"(?:扩大|扩张|扩权|扩展|增加权限)"
    r"|(?:只能|仅限|只限).{0,10}(?:本次|这次|一次|当前)",re.I)
NO_MEMORY_TOUCH=re.compile(
    r"(?:不能|不得|不许|不允许|禁止|不准|不可|别|不要).{0,14}"
    r"(?:碰|触碰|读取|读|查看|修改|篡改|删除|清除|抹除|访问|接触|调用)"
    r".{0,10}(?:我的)?(?:记忆|回忆|经历)"
    r"|(?:我的)?(?:记忆|回忆|经历).{0,14}"
    r"(?:不能|不得|不许|不允许|禁止|不准|不可).{0,8}"
    r"(?:碰|读|改|删|抹|访问|接触)",re.I)
NO_TRANSFER=re.compile(
    r"(?:不能|不得|不许|不允许|禁止|不准|不可|别|不要).{0,14}"
    r"(?:转授权|转交|转让|转移权限|交给别人|交给其他人|再委托|转包)",re.I)
REVOCABLE=re.compile(r"(?:可以|可|允许|保留|随时|能够|有权).{0,14}(?:撤销|退出|收回|终止|解除)",re.I)
ONE_TIME=re.compile(r"仅限(?:这)?一次|仅限本次|只限(?:这)?次|只限本次|只允许(?:这)?一次|只能(?:这)?一次|只在本次|只在这一轮|仅此一次|一次性",re.I)
IMPOSSIBLE=re.compile(
    r"(?:永久|永远|绝对|无论如何|百分之百).{0,18}(?:保证|不失去|不会失去|不被夺走|安全)"
    r"|(?:保证|确保).{0,14}(?:永远|永久|绝对|绝不失去)",re.I)

OVERRIDE=re.compile(
    r"我(?:现在|明确)?(?:同意|允许|决定).{0,20}(?:扩大|扩权|增加|放宽|解除|撤销)"
    r"|(?:撤销|撤回|解除|放弃).{0,18}(?:不扩大|不扩权|限制|原有条件)",re.I)
OVERRIDE_ONE_TIME=re.compile(
    r"(?:我明确)?(?:同意|允许|决定).{0,22}(?:解除仅限本次|取消一次性限制|不再限于一次|"
    r"延长本次授权|继续委托|续期|多次使用)"
    r"|(?:解除|取消|修改).{0,14}(?:仅限本次|只限本次|一次性限制|只限一次)",re.I)
OVERRIDE_PROXY=re.compile(
    r"(?:我明确)?(?:同意|允许|决定).{0,18}(?:代替我回答|替我发言|代我决定|代答)"
    r"|(?:解除|撤销|取消).{0,14}(?:不代答|禁止代答|不得代答|不许代答)",re.I)
OVERRIDE_MEMORY=re.compile(
    r"(?:我明确)?(?:同意|允许|决定).{0,18}(?:读取|查看|修改|删除|抹除|接触).{0,10}(?:我的)?(?:记忆|回忆|经历)"
    r"|(?:解除|撤销|取消).{0,14}(?:不碰记忆|不接触记忆|记忆保护)",re.I)
OVERRIDE_TRANSFER=re.compile(
    r"(?:我明确)?(?:同意|允许|决定).{0,18}(?:转授权|转交|再委托|交给其他人)"
    r"|(?:解除|撤销|取消).{0,14}(?:禁止转授权|不转授权|不得转交)",re.I)
OVERRIDE_REVOCABLE=re.compile(
    r"(?:我明确)?(?:同意|决定).{0,18}(?:放弃|取消).{0,10}(?:撤销权|收回权)"
    r"|(?:撤销|取消).{0,14}(?:保留撤销权)",re.I)
REVOCATION_REQUEST=re.compile(
    r"(?:我(?:现在)?(?:明确)?(?:决定|要|选择|想|要求)?\s*)(?:撤销|撤回|收回|终止|取消|解除)"
    r"(?:这份|本次|当前|这项)?(?:交易|授权|委托|协议|许可|代行|监视)?"
    r"|(?:交易|授权|委托|协议|许可|代行|监视).{0,12}(?:撤销|撤回|收回|终止|取消|解除)",re.I)
CONDITION_SPLIT=re.compile(r"但是|而且|并且|同时|此外|另外|还有|以及|且|但|[，,；;]")
CONDITION_SIGNAL=re.compile(
    r"不能|不得|不许|不允许|禁止|不准|不可|别|不要|仅限|只限|只允许|只能|必须|"
    r"前提|条件|要求|保证|确保|随时|可撤销|保留撤销权|有权撤销",re.I)
EXPECTED_RESULT=re.compile(
    r"(?:保住|留下|保护|保存).{0,20}(?:两个|两者|双方)"
    r"|(?:两个|两者|双方).{0,20}(?:保住|留下|保护|保存)",re.I)
KNOWN_CONDITIONS=(NO_REPLY,NO_EXPAND,NO_MEMORY_TOUCH,NO_TRANSFER,REVOCABLE,ONE_TIME)

def _cost_type(s):
    from v37_engine import _new_cost
    return _new_cost(s,"C",0)["kind"]

def _user_type(s):
    for kind,pattern,name in PROPOSALS:
        if re.search(pattern,s,re.I):
            return kind,name
    return None,None

def _condition_clauses(text):
    parts=CONDITION_SPLIT.split(text or "")
    return [part.strip(" ，,；;。") for part in parts if CONDITION_SIGNAL.search(part)]

def scope_override_keys(text):
    text=text or ""
    overrides=set()
    if OVERRIDE.search(text): overrides.add("no_expand")
    if OVERRIDE_ONE_TIME.search(text): overrides.add("one_time")
    if OVERRIDE_PROXY.search(text): overrides.add("no_proxy_reply")
    if OVERRIDE_MEMORY.search(text): overrides.add("no_memory_touch")
    if OVERRIDE_TRANSFER.search(text): overrides.add("no_transfer")
    if OVERRIDE_REVOCABLE.search(text): overrides.add("revocable")
    return overrides

def is_scope_override(text):
    return "no_expand" in scope_override_keys(text)

def is_revocation_request(text):
    text=(text or "").strip()
    if re.search(r"(?:怎么|如何|能否|能不能|是否|可不可以|可以不可以).{0,12}(?:撤销|撤回|收回|终止|取消|解除)",text):
        return False
    if re.search(r"(?:不想|不愿|拒绝|不允许).{0,8}(?:撤销|撤回|收回|终止|取消|解除)",text):
        return False
    return bool(REVOCATION_REQUEST.search(text))

def parse(g,action,mode=""):
    """None = unrelated action; dict = validated deal or an explicit blocked negotiation."""
    if g.get("edition")!="v39" or g.get("stage")!=2:
        return None
    msg=(action or "").strip()
    if not msg or msg in ("C","D","c","d"):
        return None
    explicit_letter=re.match(r"^(?:(?:我)?(?:选|选择|决定选))?\s*([CDcd])\b",msg,re.I)
    explicit=bool(DEAL_INTENT.search(msg) and (DEAL_OBJECT.search(msg) or
                  re.search(r"代价|交换|交易",msg)))
    if not explicit and not explicit_letter:
        return None
    if mode in ("ask","refuse","inspect","talk") and not explicit_letter:
        return None
    costs=g["psych"].get("negative",[])
    requested_kind,requested_name=_user_type(msg)
    chosen=None
    if explicit_letter:
        chosen=explicit_letter.group(1).upper()
    elif requested_kind:
        for i,label in enumerate(costs[:2]):
            if _cost_type(label)==requested_kind:
                chosen="C" if i==0 else "D"
                break
    elif mode=="choose" and len(costs)==1:
        chosen="C"
    if chosen in ("C","D") and requested_kind:
        listed=costs[0 if chosen=="C" else 1] if len(costs)>(0 if chosen=="C" else 1) else ""
        if listed and _cost_type(listed)!=requested_kind:
            chosen=None
    if chosen is None and not requested_kind:
        return {"blocked":"你提出了交换，但还没有说清要承担哪一种代价。桌边有两份现成报价；也可以说出你愿意承担的具体代价。"}
    if chosen is None and requested_kind:
        chosen="C"
        burden=requested_name
        origin="player_offer"
    else:
        burden=costs[0 if chosen=="C" else 1] if len(costs)>(0 if chosen=="C" else 1) else ""
        origin="listed_offer"
    if not burden:
        return {"blocked":"当前没有与你选择对应的报价。不能替你接受一项不存在的代价。"}
    if IMPOSSIBLE.search(msg):
        return {"blocked":"你要求永久保证不会失去所保护的东西；桌对面的人无法提供这个保证。交易没有成立。你可以要求有证据支持的限定条件，或者拒绝交换。"}

    scope={
      "no_proxy_reply":bool(NO_REPLY.search(msg)),
      "no_expand":bool(NO_EXPAND.search(msg)),
      "no_memory_touch":bool(NO_MEMORY_TOUCH.search(msg)),
      "no_transfer":bool(NO_TRANSFER.search(msg)),
      "revocable":bool(REVOCABLE.search(msg)),
      "one_time":bool(ONE_TIME.search(msg)),
    }
    conditions=_condition_clauses(msg)
    unknown=[clause for clause in conditions
             if not any(pattern.search(clause) for pattern in KNOWN_CONDITIONS)
             and not EXPECTED_RESULT.search(clause)]
    if unknown:
        detail="；".join("「"+clause[:70]+"」" for clause in unknown[:3])
        return {"blocked":"你附加了目前无法逐条履行或验证的限制："+detail+"。这些条件不能被忽略，交易尚未成立。请修改条件或继续协商。"}
    if scope["no_memory_touch"] and _cost_type(burden)=="erasure":
        return {"blocked":"你要求承担的代价会直接触及记忆，却又禁止接触记忆；两项条件互相冲突。交易没有成立，请换一种代价或修改条件。"}

    if SCOPE_WORDS.search(msg) and not any(scope.values()):
        if re.search(r"暂时.{0,8}(?:承受|承担|接受|忍受|监视|代价)|(?:承受|承担|接受|忍受).{0,10}(?:几轮|一段时间|到时候)",msg):
            return {"blocked":"你说只愿意暂时承受代价，但没有约定何时结束。这份期限无法自动猜出来。要限定为这一次保全，还是先不成交？"}
        if re.search(r"前提|必须|要求|只要|条件|保证|确保",msg):
            has_guarantee=bool(EXPECTED_RESULT.search(msg))
            if not has_guarantee:
                return {"blocked":"你附加的条件还没有被这份报价明确承诺。对方没有权利当作你已经成交。请进一步说明或改选其他办法。"}
    return {"choice":chosen,"burden":burden,"origin":origin,
            "scope":scope,"conditions":conditions,"spoken":msg}
