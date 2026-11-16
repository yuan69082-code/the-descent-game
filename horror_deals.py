"""Scope-aware in-world bargaining for V3.9.

We do not turn a request ("I would agree if...") into unconditional consent.
Only a concrete, valid exchange can become a real cost. An impossible promise
stays a negotiation, not a silent sacrifice.
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
SCOPE_WORDS=re.compile(r"前提|条件|但|必须|要求|只要|仅限|不能|不许|不得|不允许|保证|确保|暂时",re.I)
NO_REPLY=re.compile(r"(?:不能|不得|不许|不允许|别|禁止).{0,14}(?:代替|替|冒名|代理|模仿).{0,8}(?:我)?(?:回答|回复|发言|说话|联系)|(?:不能|不许|别|不得).{0,12}(?:替我回答|替我说话)",re.I)
NO_EXPAND=re.compile(r"(?:不能|不得|不许|不允许|禁止|别).{0,18}(?:扩大|扩张|扩权|扩展|转授权|转交|增加权限)|(?:只能|仅限).{0,10}(?:本次|这次|一次|当前)",re.I)
REVOCABLE=re.compile(r"(?:可以|允许|保留|随时|能够).{0,12}(?:撤销|退出|收回|终止|解除)",re.I)
IMPOSSIBLE=re.compile(r"(?:永久|永远|绝对|无论如何|百分之百).{0,18}(?:保证|不失去|不会失去|不被夺走|安全)|(?:保证|确保).{0,14}(?:永远|永久|绝对|绝不失去)",re.I)
OVERRIDE=re.compile(r"我(?:现在|明确)?(?:同意|允许|决定).{0,20}(?:扩大|扩权|增加|放宽|解除|撤销)|(?:撤销|撤回|解除|放弃).{0,18}(?:不扩大|不扩权|限制|原有条件)",re.I)

def _cost_type(s):
    from v37_engine import _new_cost
    return _new_cost(s,"C",0)["kind"]

def _user_type(s):
    for kind,pattern,name in PROPOSALS:
        if re.search(pattern,s,re.I):
            return kind,name
    return None,None

def parse(g,action,mode=""):
    """None = unrelated action; dict = validated scope-aware deal or negotiation."""
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
            # The letter and the spoken cost disagree; the *spoken* cost is not
            # discarded. Treat it as an explicit player counter-offer.
            chosen=None
    if chosen is None and not requested_kind:
        return {"blocked":"你提出了交换，但还没有说清要承担哪一种代价。"
                          "桌边有两份现成报价；也可以说出你愿意承担的具体代价。"}
    if chosen is None and requested_kind:
        # The player has proposed a new, concrete cost. This must be tracked
        # as *their* offer, rather than silently mapping it to one of the
        # game's previously offered, semantically different prices.
        chosen="C"
        burden=requested_name
        origin="player_offer"
    else:
        burden=costs[0 if chosen=="C" else 1] if len(costs)>(0 if chosen=="C" else 1) else ""
        origin="listed_offer"
    if not burden:
        return {"blocked":"当前没有与你选择对应的报价。不能替你接受一项不存在的代价。"}
    if IMPOSSIBLE.search(msg):
        return {"blocked":"你要求永久保证不会失去所保护的东西；桌对面的人无法提供这个保证。"
                          "交易没有成立。你可以要求有证据支持的限定条件，或者拒绝交换。"}
    scope={
      "no_proxy_reply":bool(NO_REPLY.search(msg)),
      "no_expand":bool(NO_EXPAND.search(msg)),
      "revocable":bool(REVOCABLE.search(msg)),
      "one_time":bool(re.search(r"仅限这一次|只限本次|只在这一轮",msg)),
    }
    if SCOPE_WORDS.search(msg) and not any(scope.values()):
        # "Temporary" without an end point is not a blank cheque.
        if re.search(r"暂时.{0,8}(?:承受|承担|接受|忍受|监视|代价)|(?:承受|承担|接受|忍受).{0,10}(?:几轮|一段时间|到时候)",msg):
            return {"blocked":"你说只愿意暂时承受代价，但没有约定何时结束。"
                              "这份期限无法自动猜出来。要限定为这一次保全，还是先不成交？"}
        # Conditions that cannot be tested must stay undecided.
        if re.search(r"前提|必须|要求|只要|条件|保证|确保",msg):
            has_guarantee=bool(re.search(r"(?:保住|留下|保护|保存).{0,15}(?:两个|两者|双方)|(?:两个|两者).{0,15}(?:保住|留下|保护)",msg))
            if not has_guarantee:
                return {"blocked":"你附加的条件还没有被这份报价明确承诺。"
                                  "对方没有权利当作你已经成交。请进一步说明或改选其他办法。"}
    return {"choice":chosen,"burden":burden,"origin":origin,
            "scope":scope,"spoken":msg}

def is_scope_override(text):
    return bool(OVERRIDE.search(text or ""))
