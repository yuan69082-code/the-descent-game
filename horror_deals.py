"""V3.9 transaction gate.

A transaction is either accepted in full or refused. The player may ask,
hesitate, investigate, or propose restrictions, but no conditional permission
is stored. Once accepted, the game engine records an irreversible cost.
"""
from __future__ import annotations
import re

PROPOSALS=(
    ("surveillance",r"监视|监控|窥视|观察|被监管","接受监视"),
    ("distortion",r"冒名|假冒|替我回答|代答|篡改|歪曲|改写|欺骗|说谎","接受代答干扰"),
    ("isolation",r"孤独|孤立|隔离|失联|联系不上|无人回应","接受隔离"),
    ("erasure",r"失忆|遗忘|抹除|清除记忆","承担记忆流失"),
    ("uncertainty",r"不确定|无法核实|黑箱|不信任|无法确认","承担无法核实的风险"),
    ("exhaustion",r"疲惫|透支|精力|耗尽|无休止","承担持续消耗"),
)
DEAL_INTENT=re.compile(r"愿意|接受|同意|承受|承担|我选|我选择|宁愿|我决定|付出|正式授权",re.I)
DEAL_OBJECT=re.compile(r"保住|留下|保护|保存|换取|代价|交换|交易|两份|两个|两者|双方|同时",re.I)
CONDITION=re.compile(
    r"但|但是|不过|前提|条件|要求|必须|只要|仅限|只限|只允许|只能|"
    r"不能|不得|不许|不允许|禁止|不准|不可|别|不要|不碰|不触碰|"
    r"不读取|不修改|不删除|不代答|不转授权|保留撤销权|撤销权|随时撤销|可撤销|"
    r"保证|确保|永远|永久",re.I)
QUESTION=re.compile(r"能不能|可不可以|是否|能否|为什么|怎么|如何|会怎样|可以吗|行不行",re.I)
REVOCATION=re.compile(r"(?:我(?:现在|明确)?(?:决定|要|选择|想|要求)?\s*)(?:撤销|撤回|收回|终止|取消|解除)(?:这份|本次|当前|这项)?(?:交易|授权|委托|协议|许可|代行|监视)?|(?:交易|授权|委托|协议|许可|代行|监视).{0,12}(?:撤销|撤回|收回|终止|取消|解除)",re.I)

def _cost_type(text):
    from v37_engine import _new_cost
    return _new_cost(text,"C",0)["kind"]

def _user_type(text):
    for kind,pattern,name in PROPOSALS:
        if re.search(pattern,text,re.I):
            return kind,name
    return None,None

def parse(g,action,mode=""):
    """Return None for unrelated input, a complete offer, or a blocked conditional offer."""
    if g.get("edition")!="v39" or g.get("stage")!=2:
        return None
    msg=(action or "").strip()
    if not msg or msg in ("C","D","c","d"):
        return None
    explicit_letter=re.match(r"^(?:(?:我)?(?:选|选择|决定选))?\s*([CDcd])\b",msg,re.I)
    explicit=bool(DEAL_INTENT.search(msg) and
                  (DEAL_OBJECT.search(msg) or re.search(r"代价|交换|交易",msg)))
    if not explicit and not explicit_letter:
        return None
    if mode in ("ask","refuse","inspect","talk") and not explicit_letter:
        return None
    if (msg.endswith(("？","?")) and QUESTION.search(msg) and
        not re.search(r"我(?:明确)?(?:接受|同意|选择|选|决定)|我愿意(?:承担|接受)",msg)):
        return None
    if CONDITION.search(msg):
        return {"blocked":"这笔交易不接受附加条件。你可以接受眼前的完整代价，也可以拒绝；任何限制都不会成为免责条款。交易尚未成立。"}
    costs=g["psych"].get("negative",[])
    requested_kind,requested_name=_user_type(msg)
    chosen=explicit_letter.group(1).upper() if explicit_letter else None
    origin="listed_offer"
    if requested_kind and chosen in ("C","D"):
        index=0 if chosen=="C" else 1
        listed=costs[index] if len(costs)>index else ""
        if not listed or _cost_type(listed)!=requested_kind:
            origin="player_offer"
            burden=requested_name
        else:
            burden=listed
    elif requested_kind:
        for i,label in enumerate(costs[:2]):
            if _cost_type(label)==requested_kind:
                chosen="C" if i==0 else "D"
                burden=label
                break
        else:
            chosen="C"
            origin="player_offer"
            burden=requested_name
    elif chosen in ("C","D"):
        index=0 if chosen=="C" else 1
        if len(costs)<=index:
            return {"blocked":"这份代价不在当前交易中。没有对应的完整报价，不能成交。"}
        burden=costs[index]
    else:
        return {"blocked":"请明确选择一项完整代价，或拒绝交易。模糊的愿意和保护意图不会自动成为授权。"}
    return {"choice":chosen,"burden":burden,"origin":origin,"spoken":msg}

def is_revocation_request(text):
    text=(text or "").strip()
    if QUESTION.search(text) and re.search(r"撤销|撤回|收回|终止|取消|解除",text):
        return False
    if re.search(r"不想|不愿|拒绝|不允许.{0,6}(?:撤销|撤回|收回)",text):
        return False
    return bool(REVOCATION.search(text))
