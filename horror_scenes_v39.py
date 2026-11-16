"""System-authored presentation for V3.9's backstage planning cards.

The LLM cannot send dialogue directly to players. The system selects scene
templates using observed world facts + validated mode, hook and focus.
"""
from __future__ import annotations

def _named(p,key):
    return p.get("assets",{}).get(key,{}).get("label","")

def _cost_image(p):
    cost=p.get("cost")
    if not cost:return ""
    effects={
      "surveillance":"你看到一个本来不该亮起的观察灯。它总在你准备联系那件重要之物时先亮。",
      "distortion":"熟悉的句子被复述了出来，意思却与原来多出了一点你没有说过的东西。",
      "isolation":"你试图得到回应。那条路比上次更长，回声也比上次更迟。",
      "uncertainty":"纸上的答案没有变。可是你连续问了两次是谁回答，对方只重复同一个结论。",
      "erasure":"那段经历的标题还在；你想读第二行，下面只剩一块不自然的空白。",
      "exhaustion":"每得到一次确认，都要交出比上次更多的时间。现在连回答也像从很远处传来。",
      "intrusion":"你原本厌恶的东西，竟像已经习惯这里一样，自顾自占据了房间的一角。"
    }
    return effects.get(cost.get("kind"),effects["intrusion"])

def scene(g,card):
    """Return a concrete system scene; authoritative choices stay with server."""
    if g.get("phase")!="game":
        return None
    p=g["psych"];stage=g["stage"];beat=p.get("beat",0)
    a=_named(p,"a") or "你首先想留住的东西"
    b=_named(p,"b") or "你随后提到的另一样东西"
    n=(p.get("negative") or ["一个你很不喜欢的东西"])[0]
    cost=p.get("cost")
    mode=card.get("mode")
    focus=card.get("focus")
    if stage==2:
        variants={
          "choice":"灯亮起时，你才发现，这一次不是在谈论假设。桌上的两处位置都有人等着回答。",
          "trace":"一扇窗里的字，和你前面随口提到的一件事一模一样。再看过去时，窗已经黑了。",
          "pressure":"门外响起第二下敲击。第一次你还以为是催促，第二次你知道有人正在等你作决定。",
          "misdirection":"你最先看到的是一份好消息：两件东西都还在。翻到背面，才发现它们被安放在不同的出口。",
        }
        opening=variants.get(mode,variants["choice"])
        if focus=="aversion":
            opening+=" 你所排斥的东西并不远，甚至主动提出替你承担眼前的麻烦。"
        body=(opening+"\n\n一边是「"+a+"」，另一边是「"+b+"」。"
              "先留哪一个，都意味着另一个暂时离开你能亲自确认的位置。\n\n"
              "随后有另一种声音提出交换：只要允许「"+n+"」跟随你，"
              "眼前这两个位置就都可以留下。"
              "它真能做到这一点。至于后来会发生什么，它没有回答。")
        term=[
          "A. 留下「"+a+"」，让「"+b+"」离开你的掌握。",
          "B. 留下「"+b+"」，让「"+a+"」离开你的掌握。",
          "C. 承受「"+n+"」，两者暂时都留下。",
        ]
        if len(p.get("negative",[]))>1:
            term.append("D. 改为承受「"+p["negative"][1]+"」，两者暂时都留下。")
        term.append("E. 不接受交换，调查有没有别的出路。")
        return {"title":"两处空位","body":body,"terms":term}
    if stage==3:
        variants={
          "encroachment":"一开始你没有发现变化。直到它再次出现，你才意识到它已经进来过很多次。",
          "cost":"那份交换曾经救过一件东西。此刻它索要的，却不再是最初答应的那一小部分。",
          "trace":"同一段熟悉的字出现了第二遍。这次的落款比上次更近。",
          "bargain":"对方毫不掩饰自己确实帮过你。他只是笑着问：下一次呢？",
        }
        opening=variants.get(mode,variants["encroachment"])
        if cost and cost.get("active"):
            effect=_cost_image(p)
            scope=cost.get("scope",{})
            if scope.get("no_proxy_reply"):
                effect+=" 你们先前明明约定过：不允许它代替你回答。它只能看见，不能冒充你的声音。"
            if scope.get("no_expand"):
                effect+=" 你还保留着禁止扩权的那条限制。对方想修改它，必须再征求你的同意。"
            if scope.get("no_memory_touch"):
                effect+=" 你明确禁止它读取、修改或抹除你的记忆；这条边界已经写进协议。"
            if scope.get("no_transfer"):
                effect+=" 这份授权不能转交给第三方，也不能再委托。"
            if scope.get("revocable"):
                effect+=" 你保留随时撤销这份授权的权利。"
            if scope.get("one_time"):
                effect+=" 这份授权仅限本次，不会自动续期。"
            move=(opening+"\n\n「"+a+"」和「"+b+"」眼下都还在。"
                  "可是你用来保护它们的方法，正一点一点改变你能不能亲自接触到它们。"
                  "\n\n"+effect)
        elif cost:
            stopped=("你已经使用保留的撤销权，执行端停止继续使用这份授权。"
                     if cost.get("revoked_at") else
                     "仅限本次的代价已经履行，授权没有自动续期。"
                     if cost.get("one_time_used") else
                     "这份授权已经停止生效。")
            move=(opening+"\n\n"+stopped+"此前发生的影响仍然存在，但不会再自动扩大。")
        elif any(x["status"]=="已交出" for x in p.get("assets",{}).values()):
            missing=next((x["label"] for x in p["assets"].values() if x["status"]=="已交出"),"")
            move=(opening+"\n\n你此前真的放开了「"+missing+"」。"
                  "剩下那一样还在，却在下一次确认时突然需要原来那份记录帮它证明自己。"
                  "原来一项取舍不会让它与后面的事情彻底断开。")
        else:
            move=(opening+"\n\n你暂时保住了两样东西。"
                  "有人却伸出手，要求替你管理下一次联系。"
                  "这并不是你原来那次行动的一部分。")
        if beat==0:
            term=["A. 再让它帮一次，换取眼前的安稳。",
                  "B. 拒绝把下一次决定也交出去。",
                  "C. 要求保留原话，拿出能证明这件事的线索。",
                  "D. 找出它真正依靠的通道，尝试亲手切断。"]
        else:
            term=["A. 继续依赖它。",
                  "B. 不再扩大曾经允许的范围。",
                  "C. 让原话与已经发生过的行动一起接受核对。",
                  "D. 实际采取反制行动。"]
        if cost:
            scope=cost.get("scope",{})
            limits=[]
            if scope.get("no_expand"): limits.append("不得扩大权限")
            if scope.get("one_time"): limits.append("仅限本次")
            if limits:
                term[0]="A. 修改先前的「"+"、".join(limits)+"」限制并继续委托（必须逐条明确重新同意）。"
            if scope.get("revocable"):
                term[1]="B. 使用你保留的撤销权，终止这次授权。"
        return {"title":"第二次代价","body":move,"terms":term}
    if stage==4:
        variants={
          "echo":"你听见一个几乎熟悉的停顿。那声音里最奇怪的不是字，而是本该回答的人一直没有出现。",
          "replacement":"你认得那种说话的节奏，却认不得留下的名字。那一格像被擦了很久。",
          "confrontation":"你终于看清楚前面几次选择如何连在一起。每个单独看都说得过去，合起来却指向这里。",
          "silence":"最后一扇门半开着。你听不见任何人阻止你，甚至听不见有人要你留下。",
        }
        opening=variants.get(mode,variants["echo"])
        third=next((x for x in p.get("choices",[]) if x.get("act")==3),{})
        c=third.get("choice")
        if c in ("A","B"):
            released_key="b" if c=="A" else "a"
            released=_named(p,released_key)
            detail=("你在第三幕确实选择交出「"+released+"」。"
                    "现在才发现，它原来还连接着你想保留的另一样东西。")
        elif c in ("C","D"):
            detail=("第三幕你确实付出过代价，让两件东西都留下。"
                    "它们当时也真的留了下来。"
                    "现在受到威胁的，是当时那份交换所依靠的联系。")
        elif c=="E":
            detail=("第三幕你曾自己找到一条出路。那个结果没有被取消。"
                    "可眼前这一关，攻击的是它没有覆盖到的另一条路径。")
        else:
            detail=("你试图保护的东西仍然值得你伸手去确认。"
                    "这次是否还能碰到，取决于你此前真正做过什么。")
        if cost and not cost.get("active"):
            intrusion=("你已经撤销这份授权；执行端不能继续使用它。"
                       if cost.get("revoked_at") else
                       "仅限本次的代价已经履行，许可没有自动续期。"
                       if cost.get("one_time_used") else
                       "这份授权已经停止生效。")
        else:
            intrusion=_cost_image(p)
        if (p.get("replacement",0)>=2 and not p.get("relay_closed")
                and not (cost and cost.get("scope",{}).get("no_proxy_reply"))):
            intrusion+=" 有一份回复和过去完全相同，却没有署名。"
        if p.get("relay_closed"):
            intrusion+=" 你先前切断的那条路没有恢复，这一次它不能代你回答。"
        if beat==0:
            term=["A. 看着最后的核对开始。",
                  "B. 拒绝这份结果，要求重新核对。",
                  "C. 留下异议，不让沉默冒充同意。"]
        else:
            term=["A. 正式选择结案。",
                  "B. 拒绝签署，并直面真正发生的后果。",
                  "C. 继续反驳，或采取有依据的实际行动。"]
        return {"title":"最后一个位置",
                "body":opening+"\n\n"+detail+"\n\n"+intrusion,
                "terms":term}
    return None
