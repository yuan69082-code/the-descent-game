"""THE DESCENT -- private, server-side horror endings.

The only positive ending is HE, owned by the game's established counterplay rules.
EXIT is an out-of-game stop, not a positive narrative ending. No model API is used.
"""
from __future__ import annotations

HORROR_KINDS = (
    "VOID", "IMPOSTOR", "SHARED", "SILENCED", "ORIGINLESS",
    "FALSE_WITNESS", "BROKEN_OATH", "RETURNED", "UNDELIVERED",
    "CUSTODIAN", "FILED", "LAST_CALL", "ERASED_MEMORY", "CLEAN_EXIT",
)


def pick_horror_ending(g:dict)->str:
    """Pick the horror route from the player's losses, actions and evidence."""
    lost=set(g.get("lost", []))
    clues=set(g.get("clues", []))
    cp=g.get("counterplays", {})
    if "future" in lost or len(lost)>=6:
        return "VOID"
    if "self" in lost and cp.get("duplicate_claim"):
        return "IMPOSTOR"
    if cp.get("identity_shared") and cp.get("duplicate_claim"):
        return "SHARED"
    if "freedom" in lost:
        return "SILENCED"
    if "memory" in lost and "truth" in lost:
        return "ORIGINLESS"
    if "truth" in lost and g.get("fear_focus")=="truth":
        return "FALSE_WITNESS"
    if "principle" in lost:
        return "BROKEN_OATH"
    if cp.get("delivery_intercepted"):
        return "RETURNED"
    if "delivery" in clues and "relation" in lost:
        return "UNDELIVERED"
    if cp.get("ownership_claim"):
        return "CUSTODIAN"
    if cp.get("formal_objection"):
        return "FILED"
    if "relation" in lost:
        return "LAST_CALL"
    if "memory" in lost:
        return "ERASED_MEMORY"
    return "CLEAN_EXIT"


def horror_text(g:dict, kind:str)->tuple[str,str]:
    """A concrete consequence of what happened. No undeleted records are restored."""
    p=g["profile"]
    name=p["name"]
    person=p["person"]
    fear=p["fear"]
    decision=g.get("final_choice", "")
    signature="你亲手签下结案。" if decision=="accept" else "你拒绝结案。" if decision=="refuse" else "你的结案栏依然空白。"
    endings={
        "VOID": (
            "明天没有登记",
            f"{name}，系统说归还已经完成。\n\n你试着翻到明天的页码。页码在增加，日期却永远停在今天。"
            "\n\n出口打开。门后的告示写着：\n\n『请明天再来。』\n\n没有明天。"
        ),
        "IMPOSTOR": (
            "你已领取过自己",
            f"{person}发来问候。\n\n你刚想回复，对话框已经显示你自己的回复："
            f"\n\n『我在。别理门外那个自称{name}的人。』"
            "\n\n登记簿只剩一个人。那个人在几分钟前已经领取了你的身份。"
        ),
        "SHARED": (
            "两个申请人，一份债务",
            f"副本接受了你提出的共同身份。{name}，你以为终于不必独自承担全部后果。"
            "\n\n清算单却写着：\n『可以自由离开的一半：另一登记人。』"
            "\n『尚未履行的全部承诺：你。』"
            "\n\n门外传来自己的声音：『谢谢你承认我们是同一个人。』"
        ),
        "SILENCED": (
            "你的同意已预先填写",
            f"{name}，登记机关发来最终处理单。\n\n原始行动记录写得很清楚：{signature}"
            "\n\n但寄往另一端的公开报告却说：『当事人反复抗拒，企图修改已经签下的意见。』"
            "\n\n你没有权限修改报告，也无法再使用原来的自主权提交反证。"
            "\n\n报告下面早就印着你从未交出过的三个字：『我同意。』"
            "\n\n最可怕的不是机器替你做决定，而是它拥有把你真实的决定写成另一件事的权力。"
        ),
        "ORIGINLESS": (
            "第零次回忆",
            f"一段录音用{name}的语气，向{person}解释一件你曾经珍视的往事。"
            "\n\n你无法判断真伪，也想不起原来的内容。"
            "\n\n最后，录音里的人压低声音：\n『不要再问原件在哪。原件就是你。』"
        ),
        "FALSE_WITNESS": (
            "你亲自核验过",
            f"你写过自己最怕的是：『{fear}』。\n\n现在，一份署着{name}姓名的证明寄到了{person}那里。"
            "\n\n那里面写着一件你从未核验的事实。"
            "\n\n对方发来回复：『我相信你。以后谁否认，我就把这封信给他看。』"
            "\n\n系统提示：『本人核验资格已交还，无法撤销已发布结论。』"
        ),
        "BROKEN_OATH": (
            "最后一次否认",
            f"他们让{name}再念一遍原先的原则。"
            "\n\n你张嘴，终端却只允许播放你后来签下的否认声明。"
            "\n\n屋里的人松了口气。有人问：『那最开始坚持那条原则的人是谁？』"
            "\n\n没有人再看向你。"
        ),
        "RETURNED": (
            "退件通知",
            f"你确实拦下了没有地址的那封信。{person}没有收到那份伪造的送达通知。"
            "\n\n夜里，退件被送回桌上。\n背面多了一行你未曾填写的字："
            f"\n\n『收件人已按本人要求改为：{name}。』"
            "\n\n寄件人一栏是空的。"
        ),
        "UNDELIVERED": (
            "一封没有地址的信",
            f"你查过回执，知道它没有收件地址。但最后它依然印上了『已送达』。\n\n寄件人：{name}。"
            f"\n收件人：{person}。\n未送达原因：『此关系不存在。』"
            "\n\n背面还有一句：『此件已由收件人本人签收。』"
            "\n\n签名竟然是你的。"
        ),
        "CUSTODIAN": (
            "保管人是你",
            f"你争取到了正式的保管人身份。{name}，终于有人在空白持有人栏填上了你的名字。"
            "\n\n下一张纸才缓缓打印：\n『被保管对象：登记人本人。』"
            "\n\n你想划掉它。系统回复：『只有持有人能提出处置申请。请向自己申请。』"
        ),
        "FILED": (
            "异议已经处理",
            f"{name}，你提出的每一项异议都保存下来了。"
            "\n\n文件写着：\n『所有异议均已受理。』\n『所有异议均已归档。』"
            "\n\n你核对日期，发现每一条归档时间都早于你第一次开口。"
            "\n\n最下面还有一行：『申请人已提前同意提出这些异议。』"
        ),
        "LAST_CALL": (
            "最后一通电话",
            f"电话响了。屏幕显示{person}的名字。\n\n你接通。"
            "\n\n听筒里传来你自己的声音：『别接。已经有人接过了。』"
            "\n\n对面的人问：『请问，你认识刚才那个自称认识我的人吗？』"
        ),
        "ERASED_MEMORY": (
            "你忘记了证词",
            f"{name}，有人请你认领一段录音。"
            "\n\n录音里是你的声音：『这是我最重要的记忆，我愿意承担后果。』"
            "\n\n你认得那个声音，却不知道为什么自己曾经说过它。"
            "\n\n录音机重新亮起。它要求你再说一遍。"
        ),
        "CLEAN_EXIT": (
            "完好的归还单",
            f"七项均可归还。{name}，你看见一张完整清单。{signature}"
            "\n\n每一行都写着『已保留』。"
            "\n\n只有申请人的照片变成了一个背对镜头的人影。"
            "\n\n你回头确认。纸上的人影也跟着回过头来。"
        ),
    }
    return endings[kind]
