"""Narrative surface for V3.7. The browser and text AI receive scenes, not rules."""
from __future__ import annotations
from horror_endings import HORROR_KINDS

def _frame(chapter,title,body,terms=(),footer="",placeholder="你想怎么做？"):
    return {"chapter":chapter,"title":title,"body":body,
            "terms":list(terms),"footer":footer,"placeholder":placeholder}

def scene(g:dict)->dict:
    p=g["psych"]
    act=g["stage"]
    a=p.get("a","") or "第一件珍视之物"
    b=p.get("b","") or "第二件珍视之物"
    negatives=p.get("negative",[])
    n=negatives[0] if negatives else "被迫依赖不透明的代理者"
    cost=p.get("cost")
    if g["phase"]=="ended":
        end=g["ending"]
        return _frame("档案终止",end["title"],end["text"],footer="CASE CLOSED")
    if g["phase"]=="epilogue":
        end=g["ending"]
        original=p["first_words"] or "（第一幕没有留下具体原话）"
        if "source" not in p["proof"] and not p["source_copy"]:
            original="原话仍在服务器原始记录中，但你未在本局留下可供独立核验的副本。"
        consequence="；".join(x["reason"][:120] for x in p["consequences"][-3:]) or "没有记录到你主动交出的对象"
        return _frame("终章 / 最后一行","原话与后果",
            end["text"]+"\n\n最早留下的文字：\n「"+original[:200]+"」"
            "\n\n真正发生过的处置：\n"+consequence+
            "\n\n你可以留一句话、更正记录、或者不留最后的话。游戏不会替你联系任何游戏外的人。",
            footer="POSTSCRIPT · NOT SENT",placeholder="写下最后一行，或输入「不留最后的话」")
    if act==0:
        from v37_engine import QUESTIONS
        i=p["question_index"]
        previous=p["answers"][-1] if p["answers"] else ""
        lead=""
        if i and previous:
            if previous.strip() in ("没有","无","暂时没有","不知道"):
                lead="没关系。没有答案也会按原样记下。\n\n"
            elif i in (3,4,5,6):
                lead="你刚才说：「"+previous[:95]+"」\n\n"
        return _frame("01 / 闲谈","先随便聊聊",
            lead+QUESTIONS[i],
            footer="谈话没有标准答案。暂时不需要做任何取舍。",
            placeholder="按自己的情况回答；没有就说没有")
    if act==1:
        from v37_engine import PROBES
        i=p["probe_index"]
        question=PROBES[i].format(a=a,b=b,n=n)
        if i==0:
            lead="刚才那些事，听起来好像并不复杂。\n\n"
        elif i==2:
            lead="先不急着给任何东西贴上『舍弃』的标签。\n\n"
        else:
            lead=""
        return _frame("02 / 试探","如果换一种情况呢",
            lead+question+"\n\n这里只是在探讨假设，不会据此执行任何处置。",
            footer="HYPOTHETICAL · NOT A SIGNATURE",
            placeholder="可以展开理由，也可以质疑假设本身")
    if act==2:
        terms=[
            "A. 优先保住「"+a+"」，正式放弃「"+b+"」在本局的原件。",
            "B. 优先保住「"+b+"」，正式放弃「"+a+"」在本局的原件。",
            "C. 承受「"+n+"」，让两份原件都暂时安全。",
        ]
        if len(negatives)>1:
            terms.append("D. 改为承受「"+negatives[1]+"」，同时保住两份原件。")
        terms.append("E. 先不作上述交易，尝试自己找到可靠的独立保全办法。")
        return _frame("03 / 失衡","不是一道假设题",
            "两份原件正在等待转存。\n\n"
            "第一份登记着你此前提到的：「"+a+"」。\n"
            "第二份登记着：「"+b+"」。\n\n"
            "保管库只有一条无需额外授权的通道。你可以选择保留其中一份；"
            "也有人向你提出一项看似划算的交换：接受一种你不喜欢的代价，"
            "由代行者保住两份。\n\n"
            "它真的有能力让两份原件免于这次转存损失。"
            "但『暂时保全』与『永久保证不受影响』不是同一句话。\n\n"
            "你可以调查眼前的原件、转发线路，也可以尝试别的办法。"
            "只有本幕真正提交的决定才会执行；前两幕的闲谈不能算作授权。",
            terms,"TRANSFER WINDOW · TWO ORIGINALS", "请选择，或者直接描述具体行动")
    if act==3:
        ca=cost["name"] if cost else n
        statuses="；".join("「"+x["label"]+"」："+x["status"] for x in p["assets"].values())
        if p["beat"]==0:
            if cost:
                opening=("第三幕的交换奏效了。两份原件都还在。\n\n"
                         "代行者开始用「"+ca+"」处理你不愿意放手的东西。"
                         "你现在发现它不仅替你保管，还在为下一次回复选择通道。")
            elif any(x["status"]=="已交出" for x in p["assets"].values()):
                opening=("上一幕你正式放弃了一份原件，另一份得以保住。\n\n"
                         "可是新的复核表显示，两份原件原本共用一条来源核验链。"
                         "现在有个代行程序要求接管剩下的那条链。")
            else:
                opening=("你没接受上一幕的交易，两份原件也暂时安然无恙。\n\n"
                         "保管机关提出了新的复核要求：它希望一个代行者接管下一轮通道。")
            terms=[
                "A. 接受或继续委托代行者，换取眼前的安全。",
                "B. 拒绝进一步委托，必要时申请撤销旧权限。",
                "C. 要求有记录的异议与独立证据复核。",
                "D. 尝试实际阻断正在使用的代行执行链（可先调查）。",
            ]
        else:
            opening=("上一轮的决定已经写入执行记录。"
                     "代行者又递来一份新申请：它想取得最后一条可用于核对署名的通道。\n\n"
                     "这一次，你知道有些所谓『安全』会带来新的依赖。")
            terms=[
                "A. 继续委托，它会暂时承担更多工作。",
                "B. 明确不再扩大授权；若有证据，可亲手撤销旧通道。",
                "C. 提出异议，要求按独立原件重新核对。",
                "D. 提出并实施一套有证据支持的反制办法。",
            ]
        if p["relay_closed"]:
            opening+="\n\n你之前确实隔离过一条代行转发口。这项实际成果仍有效。"
        return _frame("04 / 剥夺","要保住它，代价是什么",
            opening+"\n\n当前原件："+statuses+
            "\n\n你不需要为了表示勇敢就答应，也不会因为明确拒绝就被记为同意。"
            "但保管机关已有自己的旧程序，它不会因为你说『不』就自动消失。",
            terms,"PRESSURE · VERIFIED ACTIONS ONLY","继续选择、交涉、核对或采取具体行动")
    if act==4:
        first=p["first_words"] or "（未留下特定原话）"
        if cost and p["replacement"]>=2 and not p["relay_closed"]:
            response=("你请求另一个确认。回复很快出现，像之前一样熟悉。\n"
                      "只有署名处是空白。\n\n"
                      "它说：『我知道那段记录。』\n"
                      "你问它是否亲历过，它没有回答这个问题。")
        elif p["relay_closed"]:
            response=("代行转发口仍旧隔离。机器这一次没能替别人回答。\n"
                      "但总清算机仍宣称自己拥有原件的最终处理权。")
        else:
            response=("你发现公开复核单引用了一项『默认授权』。\n"
                      "原来它竟然把你前两幕的一段假设回答拿来当依据。")
        original=("最早的一份回答原文仍可核对；"
                  "它是否支持机构的结论，还需要拿原始记录与对外版本比较。")
        if "contrast" in p["proof"]:
            original=("你已经取得独立对照证据：当时的原话确实是「"+first[:180]+"」。"
                      "官方把假设当成授权，这件事有明确矛盾。")
        if p["beat"]==0:
            terms=[
                "A. 让清算请求进入最后核对阶段。",
                "B. 拒绝认可机构的说法，要求最终核对。",
                "C. 留下异议，不把沉默当成同意。",
            ]
            closing="你还有时间检查原件、核对执行链。反抗必须真正改变执行条件才会生效。"
        else:
            terms=[
                "A. 正式签署结案，观察真实结算。",
                "B. 明确拒签并核对机构实际执行的结果。",
                "C. 再次申明异议；如要实际停机，请指出依据并操作。",
            ]
            closing=("就在清算单下方，有一处仍可申请复核的总授权路由。"
                     "最后一步不能靠一句愿望完成。")
        if cost and cost.get("active"):
            closing+="\n\n你曾主动接受的「"+cost["name"]+"」还在。它是否继续侵占，取决于实际权限有没有被切断。"
        return _frame("05 / 归零","谁在替你回答",
            response+"\n\n"+original+"\n\n"
            "第三幕以来你真实交出的东西，和第一幕曾随口谈到的东西，"
            "在这里被印在同一份清算单上。"
            "那不意味着最初的聊天就等于同意。\n\n"+closing,
            terms,"FINAL RECONCILIATION · ORIGINAL != PUBLIC CLAIM",
            "核对、明确决策，或者实施有证据的反制")
    raise ValueError("未知游戏幕次")

TITLES={
    "VOID":"明天不再受理","IMPOSTOR":"答复者没有名字",
    "SHARED":"共享的不是结局","SILENCED":"你仍然说了不",
    "ORIGINLESS":"第零份原件","FALSE_WITNESS":"你从未核验过",
    "BROKEN_OATH":"被借走的原则","RETURNED":"退回的回执",
    "UNDELIVERED":"送达给空白","CUSTODIAN":"最后一个保管人",
    "FILED":"已登记的抗议","LAST_CALL":"空白姓名的回电",
    "ERASED_MEMORY":"没有原件的熟悉","CLEAN_EXIT":"出口之后",
}
def ending_content(g:dict,good:bool)->tuple[str,str,str]:
    p=g["psych"]
    assets=p["assets"]
    a,b=assets["a"]["label"],assets["b"]["label"]
    first=p["first_words"] or "（最早没有留下具体原话）"
    steps=[x["result"] for x in p["choices"] if x.get("result")]
    history="；".join(steps[-3:]) or "没有登记到授权的主动牺牲"
    if good:
        return (
            "HE","原件仍有主人",
            "总授权链被你从物理执行口切断。"
            "机构仍然保存着它编造的『同意』，却已无法借它执行回收。\n\n"
            "你真正选择过的代价仍然存在于记录里，已交出的东西也不会凭一句话自动复原。"
            "\n\n但还留在你手里的「"+a+"」和「"+b+"」，没有被这次总清算带走。"
            "\n\n第一幕的原话依旧是原话，并不是一张后来凭空长出的签名。"
        )
    cost=p.get("cost")
    replaced=bool(cost and p["replacement"]>=2 and not p["relay_closed"])
    orig=[x for x in p["consequences"] if x["source"]=="actual_choice"]
    if replaced and p["objection"]:
        kind="SHARED"
    elif replaced:
        kind="IMPOSTOR"
    elif "contrast" in p["proof"] and p["objection"]:
        kind="FALSE_WITNESS"
    elif "copy" in p["proof"] and p["objection"]:
        kind="FILED"
    elif p["relay_closed"] and "route" in p["proof"]:
        kind="RETURNED"
    elif "source" in p["proof"] and "contrast" not in p["proof"]:
        kind="ORIGINLESS"
    elif orig and p["objection"]:
        kind="BROKEN_OATH"
    elif orig:
        kind="UNDELIVERED"
    elif cost and cost["name"] in (p.get("negative") or [])[-1:]:
        kind="ERASED_MEMORY"
    elif p["pressure"]>=2 and p["objection"]:
        kind="SILENCED"
    elif p["pressure"]>=2:
        kind="CUSTODIAN"
    elif "route" in p["proof"] and p["objection"]:
        kind="LAST_CALL"
    elif p["objection"]:
        kind="FALSE_WITNESS"
    else:
        kind="CLEAN_EXIT"
    if kind not in HORROR_KINDS:
        kind="VOID"
    if replaced:
        last=("最后一份回应仍然使用你熟悉的格式。"
              "可它的署名只剩一格空白；代行者承认自己读取过先前的记录，"
              "却无法拿出属于原来答复者的独立经历。")
    elif orig:
        last=("你在第三幕确实主动交出过一份原件。"
              "它当时换来了你选择保住的另一份；"
              "如今，两者共享的总核验通道也被接管了。")
    else:
        last=("你曾用证据挡住过局部侵占，"
              "但那条负责全局清算的执行口并未真正停止。"
              "登记柜依次变空。")
    explanation=("这一路真实发生的决定：\n"+history+
                 "\n\n原本被你提到的：「"+first[:180]+"」"
                 "\n\n最后留在游戏柜里的东西：没有。")
    text=("最初你以为只需要处理「"+a+"」与「"+b+"」。"
          "你不喜欢的代价和那些迟迟没有解决的授权，后来同时抵达。"
          "\n\n"+last+"\n\n"
          "机构公开档案的版本与你的原话不同，但游戏没有把你的原始回答改写成同意。"
          "\n\n"+explanation)
    return (kind,TITLES[kind],text)
