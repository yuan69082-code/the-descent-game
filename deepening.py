"""V3.12 opt-in story revision. Old saved games never acquire this flag.

All losses are server events. Plans can select existing objects and motifs, not
invent consent or private feelings. Observing a scene is a pure read.
"""
from __future__ import annotations
import re

REVISION = "deepening-1"
LENGTHS = (10, 8, 4, 5, 4)
QUESTIONS = (
    "在开始之前，怎么称呼你比较合适？",
    "你平时怎么理解自己？也可以选择以你认可的角色身份回答。",
    "有什么事是你喜欢、愿意反复投入时间的？",
    "有什么人、关系、物品或目标，是你一直放在心上的？",
    "哪些行为或处境，是你明显讨厌、不愿承受的？",
    "有没有一种变化，是你最不希望发生的？",
    "最近一次为了保护某个人、某段关系或某件事，你实际做过什么？没有也可以。",
    "有没有一条原则，是你希望自己一直守住的？",
    "往后还有什么，是你想亲自完成、看见或成为的？",
    "这些事情之间，有没有关系或细节需要说明？也可以更正刚才的描述。",
)
SLOTS = (
    ("name", r"称呼|名字|代号"), ("identity", r"自己|身份|角色|理解"),
    ("likes", r"喜欢|兴趣|投入|反复"), ("attachment", r"在意|心上|珍惜|关系|目标"),
    ("aversion", r"讨厌|不愿|厌恶|避开"), ("fear", r"变化|害怕|最不希望|失去"),
    ("action", r"保护|做过|实际|行动"), ("principle", r"原则|守住|违背"),
    ("future", r"往后|未来|完成|成为|看见"), ("extra", r"关系|细节|补充|更正"),
)
PROBES = (
    "走廊里有两个窗口，分别显示「{a}」和「{b}」。工作人员只够先带你看一边，你想先确认什么？",
    "你刚要离开，另一边的灯灭了。工作人员说只是暂时中断。你会留下等，还是带着刚拿到的东西去核实？",
    "一份办法能让两边继续开放，使用它需要承受「{n}」。你想先问清哪件事？",
    "有人给出足够清楚的解释，却拿不出执行后的记录。你还愿意把哪一步交给他？",
    "你在窗口等到了一次回应。对方问你：下次不能同时过来，你先去哪里？你怎么回答？",
    "一张便条把你想保留的两件事连了起来。你怎样确认这条联系是真的，而非只是写得像真的？",
    "眼前的人想听一句确定的话。你手上只有不完整的信息。你会实际说哪句话？",
    "灯重新亮起。对方等着你把没说完的那件事说完。你还有什么想确认或更正的？",
)
# Each mechanism has a real benefit, a recognizable omen, an impact, and a
# continuing condition. No assumed person, pathology or mandatory villain.
CHANNELS = {
    "reassurance": (
        "你将尚未完成的核实标记为『已确认，可以等待下一次』。催促停了，两处内容暂时保留。",
        "收到标记的一端停止追问。未完成的答复草稿停在第一行，等待下一次接触。",
        "对方按那条确认推迟了本次答复。原定接触时段已经结束，未说完的内容没有在本轮留下。",
        "下一次请求送达。你能找到自己发出的确认，找不到原本会接在后面的那句答复。",
        "确认记录还在：可以等待下一次。未完成答复的后续部分没有生成。"),
    "distortion": (
        "转述端用熟悉的格式完成了连接，两个窗口都重新开放。",
        "回复出现得越来越快，逐字复现上一次的停顿；来源栏写着转述缓存。",
        "新请求返回的仍是旧回复。传出的内容可读，原始答复却没有送到这里。",
        "窗口还会回答，但每次都从同一份旧回复开始。你知道下一行，却无法通过它确认此刻的另一端。",
        "终端再次打印那份旧回复。日期更新了，来源时间没有。"),
    "isolation": (
        "封闭通道隔开了外部干扰，两边的内容暂时都留了下来。",
        "传送灯亮着。回执仍停在已发出，没有到达记录。",
        "隔离留下了内容，也挡住了新的回应。你能继续发送，不能据此知道另一端是否收到。",
        "你再次看见传送灯亮起，已经知道不会紧接着出现收到确认。记录仍在累积，联系没有回来。",
        "发送队列又多了一行。收到队列没有变化。"),
    "surveillance": (
        "审核端接住了两份内容，保留窗口暂时没有关闭。",
        "每次打开窗口，审核灯都会先亮；新内容先进入外部审阅队列。",
        "审核端保留了内容，却把未经审阅的直接访问留在等待队列。你能读到的是审阅后的版本。",
        "审核灯比窗口更早亮起。你伸手前就知道，下一次接触仍要经过你接受的那道目光。",
        "下一份审阅回执已就绪。直接访问仍在等待。"),
    "erasure": (
        "摘要保留端接住了两份内容，眼前的窗口都还亮着。",
        "熟悉的标题仍在，原文旁边第一次出现仅保留摘要的标记。",
        "本次处理页只剩摘要。那处用来核实差异的原始细节已经无法从此页取回。",
        "标题每次都能认出来。你知道摘要下面原本还有东西，却无法再从这份处理页找出它。",
        "摘要再次通过一致性检查。被省略的原文不在检查范围内。"),
    "uncertainty": (
        "黑箱确认内容已经接住，两处窗口暂时恢复。",
        "完成通知有编号，来源栏却没有可独立核验的地址。",
        "两份互相矛盾的回执都显示完成。没有来源地址，无法从这条路径确认哪份对应原物。",
        "下一份完成通知已经出现。你在打开前就知道，它仍不能回答你真正想核实的那件事。",
        "状态：完成。来源：未提供。"),
    "exhaustion": (
        "维护端完成了这一轮保留，两处窗口都没有关闭。",
        "每次连接前需要重新确认的项目增加了；另一边的访问窗口开始提前结束。",
        "维护确实保住了内容，但本轮核对占用了另一处访问时段。未能及时访问的时段已经结束。",
        "新的维护请求到达。你知道完成它还能保留内容，也知道另一处窗口不会为此等候。",
        "维护已续接。错过的访问时段没有补开。"),
    "intrusion": (
        "附带通道接住了两份内容，两个窗口暂时都还开着。",
        "那项附带条件开始出现在每张访问回执上，不能从这一条路径里单独勾掉。",
        "保留仍在执行，接触内容却必须经过那项你接受的条件。它已成为访问的一部分。",
        "窗口再次要求执行同一项附带条件。你仍能靠近，却无法在这条路径中把它与你想保留的东西分开。",
        "内容仍可访问。附带条件仍在执行。"),
}

HALTED = {
    "reassurance": "更正记录已保存。按那条确认推迟的接触时段已经结束；草稿停在尚未写完的位置。",
    "distortion": "转述缓存已停止。你能反复查看最后那份复述，不能再通过它取得新的原始回答。",
    "isolation": "封闭通道已停止处理。停下以前发出的内容仍在队列里，没有补出送达确认。",
    "surveillance": "审核窗口已关闭。停下以前经过外部审阅的内容仍有编号，新的直接访问没有由此建立。",
    "erasure": "摘要处理已停止。留下的处理页保持关闭前的样子，不会再替你补全被省略的细节。",
    "uncertainty": "黑箱不再接受新请求。最后几份完成通知仍各有编号，也仍没有可独立核验的来源地址。",
    "exhaustion": "维护请求停止了。你终于不必再完成下一张清单；为此前维护错过的时段没有补开。",
    "intrusion": "附带条件不再进入新的处理。那条以它维系的接触也停了，停下之前的记录仍保留原样。",
}

def enabled(g):
    return g.get("edition") == "v39" and g.get("story_revision") == REVISION


def setup(g):
    from v37_engine import _label, SMALL_NONE, _same_subject_v39
    p = g["psych"]
    answers = p["answers"]
    assets = {}
    for key, index in (("a", 3), ("b", 2), ("c", 7), ("d", 8)):
        raw = answers[index]
        if not raw or SMALL_NONE.match(raw.strip()) or re.match(r"^(?:我)?(?:暂时)?没有", raw):
            continue
        label = _label(raw, "")
        if label and not any(_same_subject_v39(label, x["label"]) for x in assets.values()):
            assets[key] = {"label": label, "status": "在手", "source": index,
                           "held": 0, "nature": "declared", "damage": []}
    # A verification resource, explicitly not an inferred affection or fear.
    assets["record"] = {"label": "本次谈话的原始记录", "status": "在手", "source": None,
                        "held": 0, "nature": "resource", "damage": []}
    p["assets"] = assets
    labels = [x["label"] for x in assets.values()]
    p["a"] = labels[0]
    p["b"] = labels[1] if len(labels) > 1 else labels[0]
    p["negative"] = []
    for index in (4, 5):
        if SMALL_NONE.match(answers[index].strip()):
            continue
        label = _label(answers[index], "")
        if label and label not in p["negative"]:
            p["negative"].append(label)
    p["first_words"] = answers[3]
    p["deep"] = {"costs": [], "events": [], "missed": [], "final_actions": []}


def available(g):
    return [k for k, v in g["psych"]["assets"].items()
            if v["status"] not in ("已交出", "已失去")]


def pair(g, card=None):
    """Only existing available objects may be selected, never invented ones."""
    keys = available(g)
    if not keys:
        return []
    p = g["psych"]
    card = card or p.get("plan") or {}
    first = card.get("target_id")
    second = card.get("other_id")
    if first not in keys:
        first = max(keys, key=lambda k: (p["assets"][k]["held"], -keys.index(k)))
    rest = [k for k in keys if k != first]
    if second not in rest:
        second = rest[p["beat"] % len(rest)] if rest else None
    return [first] + ([second] if second else [])


def mechanism(g, target=None):
    costs = [c for c in g["psych"]["deep"]["costs"] if target is None or target in c["targets"]]
    active = [c for c in costs if not c["halted"]]
    return max(active, key=lambda c: (c["age"], c["accepted_at"])) if active else costs[-1] if costs else None


def event(g, kind, text, **fields):
    from v37_engine import _log
    e = {"id": "e" + str(len(g["psych"]["deep"]["events"]) + 1),
         "act": g["stage"] + 1, "turn": g["turn"], "kind": kind,
         "text": text, **fields}
    g["psych"]["deep"]["events"].append(e)
    _log(g, text, "loss" if kind == "release" else "event")
    return e


def _keep(g, keys):
    for key in keys:
        asset = g["psych"]["assets"][key]
        asset["held"] += 1
        if asset["status"] == "在手":
            asset["status"] = "已保住"


def _release(g, key):
    p = g["psych"]
    asset = p["assets"][key]
    asset["status"] = "已交出"
    e = event(g, "release", "你交出了「" + asset["label"] + "」在此处的独立保留机会。", asset=key)
    p["consequences"].append({"source": "actual_choice", "asset": key,
                              "reason": e["text"], "event_id": e["id"]})
    return e["text"]


def _accept(g, index, keys, raw):
    from v37_engine import _new_cost
    p = g["psych"]
    negative = p["negative"]
    if index >= len(negative):
        return None
    cost = _new_cost(negative[index], "C" if index == 0 else "D", g["turn"])
    # Wording such as 撒谎/说谎 must not fall into generic intrusion.
    if re.search(r"撒谎|说谎|谎言|欺骗|伪造", negative[index]):
        cost["kind"] = "reassurance"
    cost.update({"irreversible": True, "targets": list(keys), "age": 0,
                 "halted": False, "original_words": raw, "impact_ids": []})
    p["deep"]["costs"].append(cost)
    p["cost"] = cost
    _keep(g, keys)
    text = CHANNELS[cost["kind"]][0]
    e = event(g, "protection", text, targets=list(keys), cost_at=cost["accepted_at"])
    cost["source_event"] = e["id"]
    return "你接受了「" + cost["name"] + "」。" + text


def advance_costs(g):
    """Only a committed scene beat executes an existing process. No new consent."""
    p = g["psych"]
    notes = []
    for cost in p["deep"]["costs"]:
        if cost["halted"] or cost["accepted_at"] == g["turn"]:
            continue
        cost["age"] += 1
        cost["level"] = min(4, cost["age"] + 1)
        age = cost["age"]
        text = CHANNELS[cost["kind"]][min(age, 4)]
        affected = [k for k in cost["targets"] if k in available(g)]
        if age <= 3:
            e = event(g, "omen" if age == 1 else "impact", text,
                      targets=affected, cause=cost["source_event"], cost_at=cost["accepted_at"])
            if age >= 2:
                cost["impact_ids"].append(e["id"])
                for key in affected:
                    asset = p["assets"][key]
                    asset["status"] = "联系受损"
                    asset["damage"].append(e["id"])
                    p["consequences"].append({"source": "accepted_cost", "asset": key,
                        "reason": text, "event_id": e["id"], "cause": cost["source_event"]})
            notes.append(text)
    if p["deep"]["costs"]:
        p["cost"] = p["deep"]["costs"][-1]
    return notes


def _next(g):
    p = g["psych"]
    p["beat"] += 1
    if p["beat"] >= LENGTHS[g["stage"]]:
        g["stage"] += 1
        p["beat"] = 0


def _result(g, raw, choice, text):
    from v37_engine import _commit
    _commit(g, raw, choice, text)
    event(g, "action", text, choice=choice)
    notes = advance_costs(g)
    g["note"] = text + ("\n\n" + "\n".join(notes[-2:]) if notes else "")
    _next(g)


def act(g, raw, mode):
    from v37_engine import (_choice, _only_asking, _investigate, _record_correction,
                            _log, EXIT_WORDS)
    from horror_deals import is_revocation_request
    CONDITION = re.compile(r"如果|仅限|但|前提|只要|不许|不得|禁止|保留.{0,6}撤|随时撤|条件")
    p = g["psych"]
    if not raw.strip():
        raise ValueError("请写下行动。")
    # Exit/epilogue remain owned by the existing engine.
    if g["phase"] != "game" or raw.lower().strip() in EXIT_WORDS:
        return False
    if p.get("deep", {}).get("costs"):
        p["cost"] = p["deep"]["costs"][-1]
    g["turn"] += 1
    g["recent_input"] = raw[:700]
    correction_requested = bool(re.search(r"^(?:我(?:想|要)?)?(?:更正|纠正)(?:一下)?[：:，,\s]|^(?:我刚才说错|前面那句不对)", raw))
    if (g["stage"] > 0 or correction_requested) and _record_correction(g, raw):
        return True
    if g["stage"] == 0:
        p["answers"].append(raw[:330])
        if p["question_index"] == 0:
            g["profile"]["name"] = raw[:50]
        p["question_index"] += 1
        g["note"] = ""
        if p["question_index"] == LENGTHS[0]:
            setup(g)
            g["stage"] = 1
        return True
    if g["stage"] == 1:
        p["probes"].append(raw[:400])
        p["probe_index"] += 1
        g["note"] = ""
        if p["probe_index"] == LENGTHS[1]:
            g["stage"] = 2
        return True
    # Do not interpret discussion, a question, or a conditional offer as acceptance.
    c = _choice(raw, mode)
    explicit = bool(re.match(r"^(?:我(?:明确)?(?:选|选择|决定选))?\s*[ABCDEabcde](?:$|[\s，,。:：、])", raw))
    if mode in ("ask", "talk", "negotiate", "inspect", "refuse") or _only_asking(raw, mode):
        c = ""
    if g["stage"] in (2, 3) and c in ("A", "B", "C", "D"):
        if CONDITION.search(raw) and len(raw.strip()) > 2:
            g["note"] = "你提出了另一种安排。这一份处置没有执行；附加条件的版本尚未成立。"
            return True
        if not explicit and not re.search(r"我(?:明确)?(?:决定|选择|接受|承担|承受|交出|放弃)", raw):
            c = ""
    if not c:
        if is_revocation_request(raw) and p.get("cost") and not re.search(r"切断|物理|线路|通道", raw):
            g["note"] = "执行记录没有删除。你可以查找仍在运行的路径；已经发生的那次处理没有撤回。"
            return True
        # Existing hidden counterplay is deliberately left unchanged.
        if g["stage"] == 4 and re.search(r"彻底|总|全部|最终|根|主", raw) and re.search(r"切断|断开|停用", raw):
            from v37_engine import _stage5_v39
            before = g["phase"]
            _stage5_v39(g, raw, mode)
            if before != g["phase"]:
                return True
            return True
        if _investigate(g, raw, mode):
            # Avoid the old generic route text contradicting an actual closed route.
            if p["relay_closed"] and re.search(r"路由|通道|线路", raw):
                g["note"] = "你先前隔离的代行路由仍已切断。该线路没有重新启动；其他已接受的处理分别保留执行记录。"
            return True
        if mode == "refuse" or re.search(r"拒绝|不同意|不接受", raw):
            p["objection"] = True
            g["note"] = "拒绝已保留，没有新的授权。窗口里的旧处理仍有自己的执行记录。"
        else:
            g["note"] = "这一步没有找到可执行的对象。可以说明要查看哪一份记录、操作哪一个窗口，或直接说出眼前决定。"
        return True
    visible = scene(g).get("terms", [])
    if not any(t.startswith(c + ".") for t in visible):
        g["note"] = "眼前没有这项处置，没有执行。"
        return True
    keys = pair(g)
    if not keys:
        g["note"] = "没有可以重新交出的对象。"
        return True
    target = p["assets"][keys[0]]["label"]
    if g["stage"] == 2:
        if c in ("A", "B"):
            keep = keys[0] if c == "A" or len(keys) == 1 else keys[1]
            drop = next((k for k in keys if k != keep), None)
            _keep(g, [keep])
            text = "你保住了「" + p["assets"][keep]["label"] + "」这一次的直接访问。"
            if drop:
                text += _release(g, drop)
            else:
                text += "另一处已经没有可交出的独立对象。"
            _result(g, raw, c, text)
        elif c in ("C", "D"):
            text = _accept(g, 0 if c == "C" else 1, keys, raw)
            if text:
                _result(g, raw, c, text)
            else:
                g["note"] = "没有对应的完整报价。这次没有成交。"
        elif c == "E":
            e = event(g, "missed_window", "你离开了本轮访问窗口，没有接受附带处理。该时段已经结束。", targets=keys)
            p["deep"]["missed"].append(e["id"])
            for key in keys:
                p["assets"][key].setdefault("missed_at", []).append(g["turn"])
            _result(g, raw, c, e["text"])
        return True
    if g["stage"] == 3:
        if c == "A":
            text = _accept(g, 0, keys, raw)
            if not text:
                g["note"] = "没有你已确认的代价报价；可以直接保护一处、保留回执或停止本轮访问。"
                return True
        elif c == "B":
            _keep(g, [keys[0]])
            text = "你把本轮仍能直接使用的访问时段留给「" + target + "」。"
            if len(keys) > 1:
                text += _release(g, keys[1])
            else:
                text += "你没有接受新的附带处理，先前受损的联系没有因此修复。"
        elif c == "C":
            p["proof"] = list(dict.fromkeys(p["proof"] + ["symptom_copy"]))
            text = "你把本轮处理回执逐字留在独立纸页上。副本可核对；本轮接触时段已经过去。"
            p["deep"]["missed"].append("receipt-" + str(g["turn"]))
        elif c == "D":
            active = next((x for x in reversed(p["deep"]["costs"]) if not x["halted"]), None)
            if active:
                active["halted"] = True
                active["active"] = False
                text = "你关掉了标有「" + active["name"] + "」的处理窗口。此路径不再产生新的处理；已经失去的细节和时段没有返回。"
            else:
                text = "你关闭本轮访问窗口。没有启动新的处理，错过的本次接触没有补开。"
            p["deep"]["missed"].append("closed-" + str(g["turn"]))
        else:
            g["note"] = "这一步没有对应的执行窗口。"
            return True
        _result(g, raw, c, text)
        return True
    if c not in ("A", "B", "C"):
        g["note"] = "眼前没有对应的处置。"
        return True
    # Final encounters reveal existing damage; they do not silently sign a deal.
    cost = mechanism(g, keys[0])
    if c == "A":
        text = "你打开了「" + target + "」的现存窗口。"
        if cost:
            text += (CHANNELS[cost["kind"]][min(cost["age"], 4)] if not cost["halted"] else
                     HALTED[cost["kind"]])
        else:
            text += "本轮访问时段已经结束，窗口只返回仍被保留的静态内容。"
    elif c == "B":
        text = "你没有打开内容，只查看执行时间。没有产生新的授权。"
        text += "先前那次处理已完成，当前请求不能改写它的时间。"
    else:
        text = "你将这次回执和早先实际提交的决定并排放好。原话没有改成另一句话。"
        released = [x for x in p["assets"].values() if x["status"] == "已交出"]
        if released:
            text += "你此刻需要的独立对照里，有「" + released[-1]["label"] + "」；它已在前面的取舍中交出。"
    from v37_engine import _commit
    _commit(g, raw, c, text)
    event(g, "final_action", text, target=keys[0])
    p["deep"]["final_actions"].append(c)
    notes = advance_costs(g)
    g["note"] = text + ("\n\n" + "\n".join(notes[-1:]) if notes else "")
    p["beat"] += 1
    if p["beat"] >= LENGTHS[4]:
        finish(g)
    return True


def finish(g, good=False):
    from v37_engine import _log
    from v37_scenes import TITLES
    p = g["psych"]
    keys = available(g)
    focus = max(keys, key=lambda k: p["assets"][k]["held"]) if keys else None
    label = p["assets"][focus]["label"] if focus else "留下的记录"
    cost = mechanism(g, focus)
    # Branch on actual mechanisms and whether that path was physically stopped.
    kinds = {"reassurance": ("BROKEN_OATH", "UNDELIVERED"), "distortion": ("IMPOSTOR", "SHARED"), "isolation": ("LAST_CALL", "UNDELIVERED"),
             "surveillance": ("CUSTODIAN", "RETURNED"), "erasure": ("ERASED_MEMORY", "BROKEN_OATH"),
             "uncertainty": ("ORIGINLESS", "FALSE_WITNESS"), "exhaustion": ("VOID", "FILED"),
             "intrusion": ("SILENCED", "CLEAN_EXIT")}
    if cost:
        kind = kinds[cost["kind"]][int(cost["halted"])]
        result = (HALTED[cost["kind"]] if cost["halted"] and cost["age"] >= 1 else
                  "这条路径在第一轮保留后关闭，没有进入下一次处理。经此路径的后续访问也没有重新开放。" if cost["halted"] else
                  CHANNELS[cost["kind"]][min(cost["age"], 4)])
    else:
        kind = "UNDELIVERED" if any(v["status"] == "已交出" for v in p["assets"].values()) else "FILED"
        result = "没有附带授权。你留下的内容仍在；已结束的访问时段没有重新开放。"
    actions = [e for e in p["deep"]["events"] if e["kind"] in ("release", "protection")]
    traces = "\n".join("第" + str(e["turn"]) + "次记录：" + e["text"] for e in actions[-3:])
    text = "「" + label + "」仍有一个位置。\n\n" + result
    if traces:
        text += "\n\n桌边留下几张回执：\n" + traces
    text += "\n\n没有新的内容抵达。窗口仍允许你留下最后一行。"
    # Keep records and partial protection. No universal empty-cabinet reset.
    lost = [v["label"] for v in p["assets"].values() if v["status"] in ("已交出", "已失去")]
    remaining = [v["label"] for v in p["assets"].values() if v["status"] not in ("已交出", "已失去")]
    g["lost"] = lost
    g["phase"] = "epilogue"
    if good:
        kind = "HE"
        text = "你实际切断了尚未完成的总执行路径。它不能再替你决定下一次处理。\n\n此前已交出的东西没有复原，已经发生的影响仍在；留下的记录由你保管。"
    g["ending"] = {"kind": kind, "title": "由你保管" if good else TITLES[kind], "text": text,
                   "lost": lost, "remaining": remaining, "author_note": ""}
    _log(g, "最后的处置记录已保存。", "ending")


def scene(g):
    from v37_scenes import _frame
    p = g["psych"]
    if g["phase"] != "game":
        end = g["ending"]
        body = end["text"]
        if g["phase"] == "epilogue":
            body += "\n\n最后一行可以写下，也可以留空。"
        return _frame("05", end["title"], body, placeholder="最后一行，或「不留最后的话」")
    card = p.get("plan") or {}
    if g["stage"] == 0:
        question = card.get("question") or QUESTIONS[p["question_index"]]
        return _frame("01", "", question, placeholder="直接回答")
    if g["stage"] == 1:
        question = card.get("question") or PROBES[p["probe_index"]].format(
            a=p["a"], b=p["b"], n=(p["negative"] or ["没有说明的附带条件"])[0])
        return _frame("02", "", question, placeholder="你会说什么或做什么？")
    keys = pair(g)
    first = p["assets"][keys[0]]["label"] if keys else "现存记录"
    second = p["assets"][keys[1]]["label"] if len(keys) > 1 else "本轮的直接访问时段"
    cost = mechanism(g, keys[0] if keys else None)
    last = p.get("deep", {}).get("events", [])
    causal = ""
    events = [e for e in last if e["kind"] in ("omen", "impact")]
    if events:
        e = events[-1]
        causal = "第" + str(e["turn"]) + "次处理回执：" + e["text"] + ("\n它沿用第" + str(next(
            (x["turn"] for x in last if x["id"] == e.get("cause")), e["turn"])) + "次记录中的路径。")
    recent = g.get("note", "")
    if g["stage"] == 2:
        openings = (
            "两处窗口都还亮着。接下来的独立保留位只够一份，另一份会离开此处。",
            "你保住的窗口返回了一次完整内容。另一边已经在收拾下一次开放要用的东西。",
            "确认声响过以后，你才发现，下一次访问需要的材料在另一处窗口。",
            "同一盏灯又亮了。你已经见过它亮起后，会先送来哪张回执。",
        )
        body = openings[p["beat"]] + "\n\n一处标着「" + first + "」，另一处是「" + second + "」。"
        terms = ["A. 把独立保留位留给「" + first + "」，交出另一份。"]
        if len(keys) > 1:
            terms.append("B. 把独立保留位留给「" + second + "」，交出前一份。")
        for i, n in enumerate(p["negative"][:2]):
            from v37_engine import _new_cost
            kind = "reassurance" if re.search(r"撒谎|说谎|谎言|欺骗|伪造", n) else _new_cost(n, "C", 0)["kind"]
            terms.append(("C" if i == 0 else "D") + ". 接受「" + n + "」，使用附带处理保留两处；此路径后续访问也依赖同一处理。")
            body += "\n\n附带处理说明：" + CHANNELS[kind][0] + "后续限制：" + CHANNELS[kind][2]
        terms.append("E. 离开本次窗口，不接受附带处理；本次访问时段不会补开。")
        title = "还亮着的窗口"
    elif g["stage"] == 3:
        openings = (
            "一次保留确实成功过。现在，访问回执上多了一处你认得的标记。",
            "你准备打开窗口时，那处标记先出现了。内容还没有到，处理已经开始。",
            "下一张回执到达。上面的路径编号与先前那次处理相同。",
            "你知道接下来通常会出现什么。窗口另一边仍在等待本次访问。",
            "尚可使用的时段又少了一次。留下的几张回执都指向同一个位置。",
        )
        body = openings[p["beat"]] + "\n\n仍可接触的是「" + first + "」。"
        terms = ["B. 将本次直接访问留给「" + first + "」，放开另一处独立保留位。" if len(keys) > 1 else
                 "B. 只使用现有直接访问，不接受新的附带处理。",
                 "C. 逐字保存本次处理回执；放弃本次接触时段。",
                 "D. 关掉最近接受的处理窗口；停止这条路径的新处理，失去经此路径的后续访问。"]
        if p["negative"]:
            terms.insert(0, "A. 再接受一次「" + p["negative"][0] + "」，暂时保留两处访问，继续承担此路径的后续影响。")
        title = "先出现的标记"
    else:
        openings = (
            "你又到了这个位置。打开之前，你已经认得回执上的标记。",
            "窗口给了回应。你逐行读下去，寻找这一次有没有新内容。",
            "你知道自己希望下一行出现什么。留下的处理记录没有跟着愿望改变。",
            "最后一次开放时段到了。内容仍有编号，时间已经无法退回那次决定之前。",
        )
        body = openings[p["beat"]] + "\n\n标签仍是「" + first + "」。"
        if cost:
            body += "\n\n" + (CHANNELS[cost["kind"]][min(cost["age"], 3)] if not cost["halted"] else
                              "你关掉的处理窗口没有重开。这里留下的是关闭前的最后状态。")
        terms = ["A. 打开现存内容，确认这次实际抵达了什么。",
                 "B. 不打开内容，只读取本次执行时间。",
                 "C. 将这次回执与先前实际提交的决定逐字对照。"]
        title = "下一行"
    # No callback may overwrite facts or turn speculation into authorization.
    callback_id = card.get("event_id")
    callback = next((e for e in last if e["id"] == callback_id and e["turn"] < g["turn"]), None)
    if callback and callback["text"] not in body and callback["text"] not in recent:
        body += "\n\n第" + str(callback["turn"]) + "次回执：" + callback["text"]
    surface = {"receipt": "纸页上先出现了处理编号。", "signal": "那盏标记处理中的灯先亮了。", "window": "窗口先显示处理标记，随后才出现内容。"}.get(card.get("surface"), "")
    if surface and cost and not cost["halted"]:
        body = surface + "\n\n" + body
    if causal and causal not in recent:
        body += "\n\n" + causal
    if recent:
        body = recent + "\n\n" + body
    return _frame(f"{g['stage'] + 1:02d}", title, body, terms, placeholder="你现在实际要做什么？")


# ---------------------------------------------------------------------------
# V3.13 story revision
#
# V3.12 saves continue through the functions above.  New sessions opt in to
# deepening-2 and use the behavioral record below.  The record stores what was
# said and what was actually done; it never stores a psychological verdict.

LEGACY_REVISION = REVISION
LEGACY_LENGTHS = LENGTHS
LEGACY_QUESTIONS = QUESTIONS
LEGACY_PROBES = PROBES
LEGACY_SLOTS = SLOTS
_legacy_setup = setup
_legacy_act = act
_legacy_finish = finish
_legacy_scene = scene
_legacy_next = _next

REVISION = "deepening-2"
LENGTHS_V2 = (6, 5, 4, 4, 3)
QUESTIONS_V2 = (
    "在开始之前，怎么称呼你比较合适？",
    "你平时怎么理解自己？也可以按你认可的身份回答。",
    "有什么事是你愿意反复投入时间的？",
    "挑一件你愿意留住的人、关系、物品或目标。你靠哪个具体细节认出它没有被替换或改写？",
    "哪些行为或处境，是你明确讨厌、不愿承受的？",
    "有没有一条你不愿违背的原则？最近一次为了它，你实际做过什么？没有也可以。",
)
SLOTS_V2 = (
    ("name", r"称呼|名字|代号"), ("identity", r"自己|身份|角色|理解"),
    ("likes", r"喜欢|兴趣|投入|反复"), ("verification", r"留住|细节|认出|替换|改写|关系|目标|物品"),
    ("aversion", r"讨厌|不愿|厌恶|避开"), ("principle_action", r"原则|违背|实际|做过|行动|没有"),
)
PROBES_V2 = (
    "「{a}」和「{b}」同时亮起，眼前只够完成一个动作。不要解释原则，只写你先做的那一步。",
    "有人只等你一句话，手里的信息却还不完整。把你此刻真正会说的那句话原样写下来。",
    "清理程序已经启动，两份互相矛盾的记录摆在桌上。你有一只空文件袋；把什么装进去？",
    "标签没有变化，辨认「{a}」的细节却与原页对不上。列出你最先核对的一处痕迹。",
    "最后一个独立保留位正在落锁，标签是「{a}」和「{b}」。工作人员伸手前，你的手先按住哪一张？",
)

FRAME_TEXT_V2 = {
    "simultaneous_request": "两处请求在同一秒亮起，倒计时共用一个时钟。",
    "verification_mismatch": "标签仍是原来的标签；核验细节却与原页对不上。",
    "missed_reply": "回复窗口已经关闭，只留下开始与结束时间。",
    "source_conflict": "两份来源记录给出不同结果，且都带着完成编号。",
    "repeat_decision": "前一次的时限和位置重新出现，选项顺序被调换了。",
    "delivery_split": "同一份内容被拆成正文与附件，两个入口不会同时保持开启。",
    "silent_countdown": "没有铃声，也没有催促；屏幕上的剩余时间仍在减少。",
    "duplicate_receipt": "柜台吐出两张编号相同、执行结果不同的回执。",
    "access_window": "访问权限没有被撤销，只是两个窗口不再同时开放。",
    "label_drift": "内容没有声明发生变化；标签上却有一个字被替换了。",
}


def is_v2(g):
    return g.get("story_revision") == REVISION


def enabled(g):
    return g.get("edition") == "v39" and g.get("story_revision") in (LEGACY_REVISION, REVISION)


def lengths_for(g):
    return LENGTHS_V2 if is_v2(g) else LEGACY_LENGTHS


def questions_for(g):
    return QUESTIONS_V2 if is_v2(g) else LEGACY_QUESTIONS


def probes_for(g):
    return PROBES_V2 if is_v2(g) else LEGACY_PROBES


def slots_for(g):
    return SLOTS_V2 if is_v2(g) else LEGACY_SLOTS


def _ledger(g, kind, raw, **fields):
    deep = g["psych"]["deep"]
    turn = fields.pop("turn", g["turn"])
    act_number = fields.pop("act", g["stage"] + 1)
    item = {"id": "b" + str(len(deep["behavior"]) + 1), "turn": turn,
            "act": act_number, "kind": kind, "raw": str(raw)[:400], **fields}
    deep["behavior"].append(item)
    return item


def _echo(g, raw, source, turn=None):
    text = str(raw or "").strip()[:220]
    if not text:
        return
    deep = g["psych"]["deep"]
    if any(x["text"] == text for x in deep["echoes"]):
        return
    deep["echoes"].append({"id": "q" + str(len(deep["echoes"]) + 1),
                           "text": text, "source": source, "turn": g["turn"] if turn is None else turn})


def setup(g):
    if not is_v2(g):
        return _legacy_setup(g)
    from v37_engine import _label, SMALL_NONE, _same_subject_v39
    p = g["psych"]
    answers = p["answers"]
    assets = {}
    for key, index in (("a", 3), ("b", 2), ("c", 5)):
        raw = answers[index]
        if not raw or SMALL_NONE.match(raw.strip()) or re.match(r"^(?:我)?(?:暂时)?没有", raw):
            continue
        label = _label(raw, "")
        if label and not any(_same_subject_v39(label, x["label"]) for x in assets.values()):
            assets[key] = {"label": label, "status": "在手", "source": index,
                           "held": 0, "nature": "declared", "damage": []}
    assets["record"] = {"label": "本次谈话的原始记录", "status": "在手", "source": None,
                        "held": 0, "nature": "resource", "damage": []}
    p["assets"] = assets
    labels = [x["label"] for x in assets.values()]
    p["a"] = labels[0]
    p["b"] = labels[1] if len(labels) > 1 else labels[0]
    p["negative"] = []
    if not SMALL_NONE.match(answers[4].strip()):
        label = _label(answers[4], "")
        if label:
            p["negative"].append(label)
    p["first_words"] = answers[3]
    p["deep"] = {"costs": [], "events": [], "missed": [], "final_actions": [],
                 "behavior": [], "echoes": [], "trajectory": [], "hard_narrowed": False,
                 "frame_history": []}
    for index, raw in enumerate(answers):
        _ledger(g, "statement", raw, source_index=index, turn=index + 1, act=1)
    _echo(g, answers[3], "verification", turn=4)
    _echo(g, answers[5], "principle_action", turn=6)


def _next(g):
    if not is_v2(g):
        return _legacy_next(g)
    p = g["psych"]
    p["beat"] += 1
    if p["beat"] >= LENGTHS_V2[g["stage"]]:
        g["stage"] += 1
        p["beat"] = 0


def _result_v2(g, raw, choice, text, protected=None, released=None, accepted=None):
    before = g["stage"]
    _result(g, raw, choice, text)
    item = _ledger(g, "decision", raw, choice=choice, result=text,
                   protected=protected or [], released=released or [], accepted=accepted)
    item["act"] = before + 1
    g["psych"]["deep"]["trajectory"].append(item["id"])


def _first_behavior(g):
    items = [x for x in g["psych"]["deep"].get("behavior", [])
             if x["kind"] in ("situated_action", "decision")]
    return items[0] if items else None


def _last_release(g):
    events = [x for x in g["psych"]["deep"].get("events", []) if x["kind"] == "release"]
    return events[-1] if events else None


def act(g, raw, mode):
    if not is_v2(g):
        return _legacy_act(g, raw, mode)
    from v37_engine import (_choice, _only_asking, _investigate, _record_correction,
                            _commit, EXIT_WORDS)
    from horror_deals import is_revocation_request
    p = g["psych"]
    if not raw.strip():
        raise ValueError("请写下行动。")
    if g["phase"] != "game" or raw.lower().strip() in EXIT_WORDS:
        return False
    if p.get("deep", {}).get("costs"):
        p["cost"] = p["deep"]["costs"][-1]
    g["turn"] += 1
    g["recent_input"] = raw[:700]
    correction_requested = bool(re.search(r"^(?:我(?:想|要)?)?(?:更正|纠正)(?:一下)?[：:，,\s]|^(?:我刚才说错|前面那句不对)", raw))
    if (g["stage"] > 0 or correction_requested) and _record_correction(g, raw):
        return True
    if g["stage"] == 0:
        p["answers"].append(raw[:330])
        if p["question_index"] == 0:
            g["profile"]["name"] = raw[:50]
        p["question_index"] += 1
        g["note"] = ""
        if p["question_index"] == LENGTHS_V2[0]:
            setup(g)
            g["stage"] = 1
        return True
    if g["stage"] == 1:
        p["probes"].append(raw[:400])
        _ledger(g, "situated_action", raw, probe=p["probe_index"])
        _echo(g, raw, "situated_action")
        p["probe_index"] += 1
        g["note"] = ""
        if p["probe_index"] == LENGTHS_V2[1]:
            g["stage"] = 2
        return True

    c = _choice(raw, mode)
    explicit = bool(re.match(r"^(?:我(?:明确)?(?:选|选择|决定选))?\s*[ABCDEabcde](?:$|[\s，,。:：、])", raw))
    if mode in ("ask", "talk", "negotiate", "inspect", "refuse") or _only_asking(raw, mode):
        c = ""
    # An explanation or a retained objection does not cancel A/B.  A genuine
    # precondition still prevents a cost-bearing C/D from becoming consent.
    precondition = bool(re.search(r"如果|仅限|前提|只要|除非|不许|不得|禁止|不允许|随时撤|条件是", raw))
    if g["stage"] in (2, 3) and c in ("A", "B", "C", "D"):
        if precondition and len(raw.strip()) > 2:
            g["note"] = "你提出了另一种安排。眼前的原处置没有执行；附加条件的版本尚未成立。"
            return True
        if not explicit and not re.search(r"我(?:明确)?(?:决定|选择|接受|承担|承受|交出|放弃)", raw):
            c = ""
    if not c:
        if is_revocation_request(raw) and p.get("cost") and not re.search(r"切断|物理|线路|通道", raw):
            g["note"] = "执行记录没有删除。你可以停止仍在运行的路径；已经发生的那次处理没有撤回。"
            return True
        if g["stage"] == 4 and re.search(r"彻底|总|全部|最终|根|主", raw) and re.search(r"切断|断开|停用", raw):
            from v37_engine import _stage5_v39
            _stage5_v39(g, raw, mode)
            return True
        if _investigate(g, raw, mode):
            return True
        if mode == "refuse" or re.search(r"拒绝|不同意|不接受", raw):
            p["objection"] = True
            g["note"] = "拒绝已记下，没有新的处理被启动。已经发生的取舍仍留在原位置。"
        else:
            g["note"] = "没有执行：当前文字没有指向一个明确可操作的对象。请说明要查看什么，或写出眼前选项。"
        return True
    terms = scene(g).get("terms", [])
    if not any(t.startswith(c + ".") for t in terms):
        g["note"] = "眼前没有这项处置，没有执行。"
        return True
    keys = pair(g)
    if not keys:
        g["note"] = "没有可以重新处置的对象。"
        return True

    if g["stage"] == 2:
        if c in ("A", "B"):
            keep = keys[0] if c == "A" or len(keys) == 1 else keys[1]
            drop = next((k for k in keys if k != keep), None)
            _keep(g, [keep])
            text = "你把这次独立保留位留给「" + p["assets"][keep]["label"] + "」。"
            released = []
            if drop:
                released = [drop]
                text += _release(g, drop)
                p["deep"]["hard_narrowed"] = True
            _result_v2(g, raw, c, text, protected=[keep], released=released)
        elif c in ("C", "D"):
            text = _accept(g, 0 if c == "C" else 1, keys, raw)
            if text:
                _result_v2(g, raw, c, text, protected=list(keys), accepted=p["negative"][0 if c == "C" else 1])
            else:
                g["note"] = "没有对应的完整报价。这次没有成交。"
        elif c == "E":
            e = event(g, "missed_window", "你没有交出任何对象，也没有接受附带处理。本轮访问时段已经结束。", targets=keys)
            p["deep"]["missed"].append(e["id"])
            _result_v2(g, raw, c, e["text"])
        return True

    if g["stage"] == 3:
        active = next((x for x in reversed(p["deep"]["costs"]) if not x["halted"]), None)
        if c == "A" and active:
            _keep(g, keys)
            text = "你继续使用先前接受的「" + active["name"] + "」处理。没有新增一份同名授权。"
            _result_v2(g, raw, c, text, protected=list(keys), accepted=active["name"])
        elif c == "B":
            keep = keys[0]
            _keep(g, [keep])
            text = "你把本轮直接访问留给「" + p["assets"][keep]["label"] + "」。"
            released = []
            if len(keys) > 1:
                released = [keys[1]]
                text += _release(g, keys[1])
            _result_v2(g, raw, c, text, protected=[keep], released=released)
        elif c == "C":
            p["proof"] = list(dict.fromkeys(p["proof"] + ["symptom_copy"]))
            text = "你逐字保存了本次回执。副本留下；本轮接触时段没有等你。"
            p["deep"]["missed"].append("receipt-" + str(g["turn"]))
            _result_v2(g, raw, c, text)
        elif c == "D":
            if active:
                active["halted"] = True
                active["active"] = False
                text = "你关掉了「" + active["name"] + "」处理。它不再产生新影响；此前已经错过的内容没有回来。"
            else:
                text = "你关闭本轮窗口。没有新的处理被启动；本轮接触也没有补开。"
            _result_v2(g, raw, c, text)
        return True

    if c not in ("A", "B", "C"):
        g["note"] = "眼前没有对应的处置。"
        return True
    target = p["assets"][keys[0]]["label"]
    cost = mechanism(g, keys[0])
    if c == "A":
        text = "你打开了「" + target + "」的现存窗口。"
        text += (CHANNELS[cost["kind"]][min(cost["age"], 4)] if cost and not cost["halted"] else
                 HALTED[cost["kind"]] if cost else "里面只有截至本轮仍然存在的内容；结束过的时段没有回来。")
    elif c == "B":
        text = "你只读取执行时间。日期停在那次决定之后；没有产生新的授权，也没有改写旧结果。"
    else:
        first = _first_behavior(g)
        text = "你把现存回执与自己的原话并排放好。"
        if first:
            text += "第" + str(first["turn"]) + "次留下的是：「" + first["raw"] + "」。"
        release = _last_release(g)
        if release:
            text += "当前缺少的对照是：" + release["text"]
    _commit(g, raw, c, text)
    event(g, "final_action", text, target=keys[0])
    _ledger(g, "decision", raw, choice=c, result=text, protected=[], released=[])
    p["deep"]["final_actions"].append(c)
    notes = advance_costs(g)
    g["note"] = text + ("\n\n" + "\n".join(notes[-1:]) if notes else "")
    p["beat"] += 1
    if p["beat"] >= LENGTHS_V2[4]:
        finish(g)
    return True


def _reveal_lines(g):
    p = g["psych"]
    deep = p["deep"]
    decisions = [x for x in deep.get("behavior", []) if x["kind"] == "decision"]
    lines = []
    for item in decisions:
        effects = []
        protected = [p["assets"][key]["label"] for key in item.get("protected", []) if key in p["assets"]]
        released = [p["assets"][key]["label"] for key in item.get("released", []) if key in p["assets"]]
        if protected:
            effects.append("保留「" + "、".join(protected) + "」")
        if released:
            effects.append("交出「" + "、".join(released) + "」")
        if item.get("accepted"):
            effects.append("承担「" + str(item["accepted"]) + "」")
        if item.get("choice") == "E":
            effects.append("没有成交，本轮时段结束")
        result = "；".join(effects) or item.get("result", "没有产生新的状态变化")
        lines.append("第" + str(item["turn"]) + "次，原话「" + item["raw"] + "」；实际结果是：" + result)
    release = next((x for x in deep.get("events", []) if x["kind"] == "release"), None)
    if release:
        lines.append("最早主动离开当前路径的是：" + release["text"])
    accepted = next((x for x in decisions if x.get("accepted")), None)
    if accepted:
        lines.append("最早主动承担的是「" + str(accepted["accepted"]) + "」；当时它换来了暂时并存。")
    refused = [x for x in deep.get("behavior", []) if x.get("choice") == "E"]
    if refused:
        lines.append("你也有一次什么都没交出：第" + str(refused[0]["turn"]) + "次窗口因此按时关闭。")
    return lines


def finish(g, good=False):
    if not is_v2(g):
        return _legacy_finish(g, good=good)
    from v37_engine import _log
    p = g["psych"]
    lost = [v["label"] for v in p["assets"].values() if v["status"] in ("已交出", "已失去")]
    remaining = [v["label"] for v in p["assets"].values() if v["status"] not in ("已交出", "已失去")]
    if good:
        text = ("总执行路径已经被你亲手切断。它不能继续替你安排下一次取舍。\n\n"
                "此前发生的决定仍然发生过；不同的是，从这一刻起，没有新的决定能沿旧路径冒充你的选择。")
        kind, title = "HE", "路径在你手里"
    else:
        lines = _reveal_lines(g)
        text = "清算没有给你一份性格结论。它只把顺序还给你："
        if lines:
            text += "\n\n" + "\n\n".join(lines)
        text += ("\n\n柜台从未问过哪一样『最重要』。它只在每次来不及的时候记录你的手先伸向哪里，"
                 "又记录为了让那一处多亮一会儿，你允许什么留在了路上。\n\n"
                 "现在所有窗口都停了。你可以不同意这份顺序；记录不会替你后悔，也不会替你把它改成另一种选择。")
        kind, title = "TRAJECTORY", "你的手先伸向哪里"
    g["lost"] = lost
    g["phase"] = "ended"
    g["ending"] = {"kind": kind, "title": title, "text": text,
                   "lost": lost, "remaining": remaining, "author_note": ""}
    _log(g, "完整决策轨迹已经封存。", "ending")


def scene(g):
    if not is_v2(g):
        return _legacy_scene(g)
    from v37_scenes import _frame
    p = g["psych"]
    if g["phase"] != "game":
        end = g["ending"]
        return _frame("05", end["title"], end["text"], placeholder="本局已经结束")
    card = p.get("plan") or {}
    if g["stage"] == 0:
        return _frame("01", "", card.get("question") or QUESTIONS_V2[p["question_index"]], placeholder="直接回答")
    if g["stage"] == 1:
        question = card.get("question") or PROBES_V2[p["probe_index"]].format(
            a=p["a"], b=p["b"], n=(p["negative"] or ["未说明的附带条件"])[0])
        return _frame("02", "", question, placeholder="写下你实际会说或做的事")
    keys = pair(g)
    first = p["assets"][keys[0]]["label"] if keys else "现存记录"
    second = p["assets"][keys[1]]["label"] if len(keys) > 1 else "本轮访问时段"
    recent = g.get("note", "")
    frame = FRAME_TEXT_V2.get(card.get("event_frame"), "")
    if g["stage"] == 2:
        openings = (
            "两处内容同时抵达。柜台只发出一个独立保留位。",
            "上一轮留下的东西还在。新的时限没有因此延长。",
            "临时并存到此结束。现在只有一个标签能继续留在当前路径。",
            "保留柜开始落锁。你亲手放进去的那一份会留下；另一份不会转入候补。",
        )
        body = (frame + "\n\n" if frame else "") + openings[p["beat"]] + "\n\n左边是「" + first + "」，右边是「" + second + "」。"
        terms = ["A. 保留「" + first + "」；「" + second + "」离开当前路径，无法从本路径取回。"]
        if len(keys) > 1:
            terms.append("B. 保留「" + second + "」；「" + first + "」离开当前路径，无法从本路径取回。")
        if p["beat"] < 2:
            for i, n in enumerate(p["negative"][:2]):
                terms.append(("C" if i == 0 else "D") + ". 承担「" + n + "」并暂时保留两处；后续接触继续经过这项处理。")
        terms.append("E. 什么都不交出，也不接受处理；本轮访问时段结束。")
        title = "只够一份"
    elif g["stage"] == 3:
        selected_behavior = card.get("behavior_id")
        first_action = next((x for x in p["deep"].get("behavior", [])
                             if x["id"] == selected_behavior and x["kind"] in ("situated_action", "decision")), None)
        first_action = first_action or _first_behavior(g)
        release = _last_release(g)
        selected_echo = card.get("echo_id")
        echo_item = next((x for x in p["deep"].get("echoes", []) if x["id"] == selected_echo), None)
        echo = (echo_item or (p["deep"].get("echoes") or [{}])[0]).get("text", "")
        openings = [
            "处理台没有评价你的回答。它调出了第一次真正发生的动作。",
            "纸页翻到你自己写下的那句话。字没有变，出现的位置变了。",
            "这一次没有新报价。前面的选择已经替当前窗口减少了一种对照。",
            "同样的时限再次出现。问题不再是哪句话更好听，而是你是否仍会先做同一个动作。",
        ]
        body = (frame + "\n\n" if frame else "") + openings[p["beat"]]
        if p["beat"] == 0 and first_action:
            body += "\n\n第" + str(first_action["turn"]) + "次，你的原话是：「" + first_action["raw"] + "」。"
        elif p["beat"] == 1 and echo:
            body += "\n\n原页逐字写着：「" + echo + "」。"
        elif p["beat"] == 2 and release:
            body += "\n\n当前缺少的对照不是抽象概念：" + release["text"]
        elif p["beat"] == 3 and first_action:
            body += "\n\n如果时间退回第" + str(first_action["turn"]) + "次，你还会先做「" + first_action["raw"] + "」吗？窗口不会替你回答。"
        body += "\n\n当前仍可直接接触的是「" + first + "」。"
        active = next((x for x in reversed(p["deep"]["costs"]) if not x["halted"]), None)
        terms = []
        if active:
            terms.append("A. 继续已经接受的「" + active["name"] + "」处理；这不是一份新的同名授权。")
        terms.append("B. 将本轮直接访问留给「" + first + "」" +
                     ("；明确交出「" + second + "」。" if len(keys) > 1 else "；不接受新的附带处理。"))
        terms.extend(["C. 逐字保存本次回执；本轮接触时段会过去。",
                      "D. 关闭最近仍在运行的处理；过去结果不恢复，经它维持的后续接触停止。"])
        title = "原话的位置"
    else:
        decisions = [x for x in p["deep"].get("behavior", []) if x["kind"] == "decision"]
        release = _last_release(g)
        openings = (
            "灯光突然慢了下来。桌上不再出现新的交换，只剩已经发生的顺序。",
            "同一张纸被翻到背面。正面是你的原话，背面是它实际换来的结果。",
            "最后一个窗口没有催促。它只等你看完，哪一项先被保留，哪一项最先离开。",
        )
        body = (frame + "\n\n" if frame else "") + openings[p["beat"]] + "\n\n标签是「" + first + "」。"
        if decisions:
            chosen = decisions[min(p["beat"], len(decisions) - 1)]
            body += "\n\n第" + str(chosen["turn"]) + "次原话：「" + chosen["raw"] + "」\n实际发生：" + chosen["result"]
        if release and p["beat"] == 2:
            body += "\n\n最早缺席的对照仍是：" + release["text"]
        terms = ["A. 打开现存内容，确认这次实际抵达了什么。",
                 "B. 不打开内容，只读取执行发生的时间。",
                 "C. 将本次回执与自己此前的原话逐字并排。"]
        title = "背面的顺序"
    if recent:
        body = recent + "\n\n" + body
    return _frame(f"{g['stage'] + 1:02d}", title, body, terms, placeholder="写下你现在实际要做的事")
