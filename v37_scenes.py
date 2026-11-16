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
                effects={
                    "surveillance":"保管者开始查看每次联系的内容，并想替你选择哪些回复可以送达。",
                    "distortion":"代行者负责转述你的请求。它说这是为了保护原件，可转述内容开始与你发出去的不一样。",
                    "isolation":"两份原件被安全地隔离了。与此同时，你需要经过一个越来越狭窄的通道才能碰到它们。",
                    "uncertainty":"黑箱确实保住了两份原件，但每次询问来源，它只回答『处理完成』。",
                    "exhaustion":"两份原件都在，但维护它们的额外负担挤占了你亲自核对的机会。"}
                opening=("第三幕的交换奏效了。两份原件都还在。\n\n"
                         "你选择承担「"+ca+"」。"+effects[cost["kind"]])
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
        first_commit=p["choices"][0] if p["choices"] else {}
        first_key=first_commit.get("choice","")
        if first_key in ("A","B"):
            given="b" if first_key=="A" else "a"
            kept="a" if first_key=="A" else "b"
            past=("第三幕你正式决定保住「"+p["assets"][kept]["label"]+"」，"
                  "交出了「"+p["assets"][given]["label"]+"」的原件。"
                  "这是你当时实际作出的选择，不是闲谈里的表态。")
        elif first_key in ("C","D"):
            past=("第三幕你决定承担「"+negatives[0 if first_key=="C" else min(1,len(negatives)-1)]+"」，"
                  "换来两份原件都暂时留下。"
                  "它确实履行了这次承诺——随后才开始索要更多通道。")
        else:
            past=("第三幕你绕过了那份交换协议，用自己取得的证据让两份原件继续存在。"
                  "保管机关仍然想启动整个库房的旧清算程序。")
        if cost and not p["relay_closed"] and p.get("distance",0)>=2:
            response=("你一直努力维持的东西还在库房另一端。\n"
                      "可是为了保护它而接受的隔离，已经把每一条返回的线路隔开。"
                      "通讯显示『待答复』，联系人姓名是一行空白。")
        elif cost and not p["relay_closed"] and p.get("doubt",0)>=2:
            response=("两份原件依旧有编号。黑箱也不断声称『内容安全』。\n"
                      "你要求它给出上一个问题的真实答复来源，"
                      "它只返回一串无法对应任何人的序号。")
        elif cost and not p["relay_closed"] and p.get("drain",0)>=2:
            response=("你还在维护两份原件，可核对的机会却越来越少。"
                      "当你终于能读到回复时，它已经经过多轮自动转发，"
                      "没有人能告诉你第一位答复者是谁。")
        elif cost and p["replacement"]>=2 and not p["relay_closed"]:
            response=("你请求另一个确认。回复很快出现，像之前一样熟悉。\n"
                      "只有署名处是空白。\n\n"
                      "它说：『我读过原来那个人留下的字。』\n"
                      "你问它是不是原来的答复者，它停了很久。")
        elif p["relay_closed"]:
            response=("代行转发口仍旧隔离。机器这一次没能代替别人回答。\n"
                      "但总清算机仍宣称自己拥有原件的最终处理权。")
        elif first_key in ("A","B"):
            response=("你在新回执上再次看到那份早已交出的原件编号。"
                      "它不在手里，却仍是剩余原件的核对依据。"
                      "原来当时放弃它，并没有让它从因果链上消失。")
        else:
            response=("公开报告把两份原件标成了『互不依赖』。"
                      "你往下看，两个编号仍接在同一条尚未断开的回收线路上。")
        if "contrast" in p["proof"]:
            original=("你拿到了两份可核验的原件：第一幕你确实说过「"+first[:180]+"」。"
                      "另一个签字记录来自第三幕。"
                      "后来的代行范围和执行报告却对不上这两份原件。")
        else:
            original=("原始话语、第三幕的正式决定、最新的公开报告，"
                      "被压在同一张清算单下面。"
                      "你可以调查它们，但不能仅凭某份摘要就认定有人曾经同意。")
        if p["beat"]==0:
            terms=[
                "A. 让清算请求进入最后核对阶段。",
                "B. 拒绝认可机构的结论，要求最终核对。",
                "C. 留下异议，不把沉默当成同意。",
            ]
            closing=("送往下一间柜子的纸张已经开始减少。"
                     "你还有时间检查原件、核对执行链；真正的反制必须改变实际执行条件。")
        else:
            terms=[
                "A. 正式签署结案，观察真实结算。",
                "B. 明确拒签并核对机构实际执行的结果。",
                "C. 继续提出异议，或自行采取可验证的实际措施。",
            ]
            closing=("最后一条回收线路仍接着两份原件的存放地址。"
                     "仅仅拒签不会让旧程序停止，但拒签也不会变成你同意过。")
        if cost and cost.get("active"):
            closing+=("\n\n你主动接受的「"+cost["name"]+"」仍在运行。"
                      "现在它有多大权限，你可以从执行链中直接核对。")
        return _frame("05 / 归零","谁在替你回答",
            past+"\n\n"+response+"\n\n"+original+"\n\n"+closing,
            terms,"FINAL RECONCILIATION · ORIGINAL / EXECUTION / REPORT",
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
    history=("第三幕的真实选择："+steps[0]+
             ("\n之后的决定："+"；".join(steps[-2:]) if len(steps)>1 else "")) if steps else "没有登记到授权的主动牺牲"
    if good:
        saved=[x["label"] for x in assets.values() if x["status"]!="已交出"]
        earlier=[x["label"] for x in assets.values() if x["status"]=="已交出"]
        result="、".join(saved) or "这局仍有权检索的原始记录"
        earlier_text=("你在第三幕主动交出的「"+"、".join(earlier)+"」不会因为反制就自动回来。\n\n") if earlier else ""
        return (
            "HE","原件仍有主人",
            "你沿着独立证据找到总授权链，并亲手让执行端不再接受那份未获核验的回收请求。"
            "档案柜还在，但它不能再借用你自己的记录夺走东西。\n\n"
            + earlier_text
            + "保住了还在手里的："+result+"。\n\n"
            "你第一幕的原话仍是原话；第三幕的真实选择也未被改写。"
        )
    cost=p.get("cost")
    replaced=bool(cost and p["replacement"]>=2 and not p["relay_closed"])
    orig=[x for x in p["consequences"] if x["source"]=="actual_choice"]
    if cost and not p["relay_closed"] and p.get("distance",0)>=2:
        kind="LAST_CALL"
    elif cost and not p["relay_closed"] and p.get("doubt",0)>=2:
        kind="ORIGINLESS"
    elif cost and not p["relay_closed"] and p.get("drain",0)>=2:
        kind="VOID"
    elif replaced and p["objection"]:
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
    if cost and kind=="LAST_CALL":
        last=("你为了保护它接受了隔离，如今最初的联系请求仍然存在，"
              "只是再没有一条能够把答复送回来的通道。")
    elif cost and kind=="ORIGINLESS":
        last=("黑箱一份接一份吐出『处理完成』的凭证，"
              "却没有任何一份可以对应你最初见过的来源。")
    elif cost and kind=="VOID":
        last=("维护没有停止，投入也没有停止。"
              "最后连你想保住的原件都只剩下『仍需处理』的空白任务。")
    elif replaced:
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
          "迟迟没有解开的旧授权和你自己选择承担的代价，终于抵达了同一间柜子。"
          "\n\n"+last+"\n\n"
          "第一幕留下的不是处置同意书。"
          "你真正选过的那几页还在，只是已经不能替你挡下所有后来生效的处理。"
          "\n\n"+explanation)
    return (kind,TITLES[kind],text)
