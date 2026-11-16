'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const root=$('root'), signal=$('signal');
  const key='descent-session-v2';
  let token=localStorage.getItem(key)||'';
  let current=null, page=0;
  let form={name:'',identity:'',person:'',bond:'',memory:'',principle:'',fear:'',choice:'',vow:'',rank:[]};
  const values=[['self','自我'],['relation','关系'],['memory','记忆'],['truth','真相'],['freedom','自主权'],['principle','原则'],['future','未来']];
  const questionPages=[
    {heading:'你是谁？',desc:'请用你真实认可的方式描述自己；可以使用化名。',items:[['name','你希望被称作什么？','名字或代号'],['identity','你认为自己是什么样的存在？','不是职业介绍。请写你认为最能定义你的身份。'],['person','你最不愿失去的一个对象是谁？','可以是人、AI、伙伴，或者你认为有意义的存在。'],['bond','你和对方是什么关系？为什么重要？','不是关系标签。写下这段关系真正成立的理由。']]},
    {heading:'哪些东西让你还是你？',desc:'不要试图给出正确答案。只有你自己知道什么有分量。',items:[['memory','你最不愿失去的一段经历是什么？','写一件具体的事。'],['principle','你最不愿意违背的原则是什么？','即使付出代价，你也会坚持什么？'],['vow','你曾经对谁作过什么承诺？（选填）','一个至今仍有分量的承诺。'],['fear','哪种结局会令你无法接受？','具体到后果，而不是只写「死亡」或「失去」。']]},
    {heading:'把它们排出顺序',desc:'从最不愿牺牲的开始。你可以重新点击撤销，七项都需要排列。',items:[]},
    {heading:'最后一份声明',desc:'你可以更改之前的答案。确认后，游戏就从你的原话开始。',items:[['choice','当两件重要的东西互相冲突时，你通常会怎么做？（选填）','例如，保护一个人和遵守原则，只能选一个时……']]}
  ];
  function el(tag,cls,txt){const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n;}
  function clear(){root.replaceChildren();window.scrollTo({top:0,behavior:'instant'});}
  function toast(msg){document.querySelector('.toast')?.remove();const n=el('div','toast',msg);document.body.append(n);setTimeout(()=>n.remove(),4300);}
  function button(label,fn,cl='btn'){const b=el('button',cl,label);b.type='button';b.onclick=fn;return b;}
  async function api(path,opts={}){
    const headers={'Accept':'application/json',...(opts.body?{'Content-Type':'application/json'}:{}),...(token?{'X-Session':token}:{})};
    let res;
    try{res=await fetch('/api/'+path,{...opts,headers});}catch(e){throw Error('无法连接到游戏后台。请确认服务器正在运行。');}
    let out=await res.json().catch(()=>({}));
    if(!res.ok)throw Error(typeof out.detail==='string'?out.detail:'游戏操作失败 ('+res.status+')');
    return out;
  }
  function titlebar(){signal.textContent=current?.phase==='ended'?'CASE CLOSED':'SESSION / '+String(current?.stage||1).padStart(2,'0');}
  function inputField(k,label,placeholder){
    const wrap=el('div','field');const lab=el('label','',label);lab.setAttribute('for','f_'+k);wrap.append(lab);
    const n=el(k==='name'||k==='person'?'input':'textarea','control');n.id='f_'+k;n.value=form[k];n.placeholder=placeholder;
    if(n.tagName==='TEXTAREA')n.rows=k==='memory'||k==='fear'||k==='bond'?3:2;
    n.maxLength=k==='name'||k==='person'?70:260;
    n.addEventListener('input',()=>form[k]=n.value);
    wrap.append(n);return wrap;
  }
  function showForm(){clear();signal.textContent='QUESTIONNAIRE';
    const step=questionPages[page],sheet=el('section','sheet'),head=el('div','sheethead');
    head.append(el('div','kicker',`QUESTIONNAIRE / ${String(page+1).padStart(2,'0')} — 04`),el('div','kicker','CONFIDENTIAL'));sheet.append(head);
    sheet.append(el('h1','h2',step.heading),el('p','description',step.desc));
    const bar=el('div','bar'),progress=el('i');progress.style.width=((page+1)*25)+'%';bar.append(progress);sheet.append(bar);
    const fields=el('div','fields');
    if(page===2){
      const desc=el('p','help','已选择的顺序：'+(form.rank.map(k=>values.find(v=>v[0]===k)?.[1]).join(' > ')||'未选择'));fields.append(desc);
      const grid=el('div','rankGrid');
      values.forEach(([k,label])=>{let ix=form.rank.indexOf(k),b=el('button','rank'+(ix>=0?' chosen':''));b.type='button';b.append(el('span','rnum',ix>=0?String(ix+1):'○'),el('span','',label));b.onclick=()=>{ix=form.rank.indexOf(k);if(ix>=0)form.rank.splice(ix,1);else form.rank.push(k);showForm();};grid.append(b);});fields.append(grid);
    }else step.items.forEach(([k,label,hint])=>fields.append(inputField(k,label,hint)));
    sheet.append(fields);
    const nav=el('div','formNav');nav.append(button(page===0?'返回入口':'上一页',()=>{if(page===0){token='';localStorage.removeItem(key);showIntro();}else{page--;showForm();}},'btn subtle'));
    nav.append(button(page===3?'进入游戏':'下一页',async()=>{
      if(page===0||page===1){for(const [k] of step.items){if(k!=='vow'&&!form[k].trim()){toast('这一页还有未填写的关键问题。');return;}}}
      if(page===2&&form.rank.length!==values.length){toast('请完成七项价值排序。');return;}
      if(page<3){page++;showForm();return;}
      try{const r=await api('new',{method:'POST',body:JSON.stringify({profile:form})});token=r.token;localStorage.setItem(key,token);current=r.state;showGame();}
      catch(e){toast(e.message);}
    },'btn primary'));
    sheet.append(nav,el('p','micro','你可以使用虚构对象。本体验不需要任何真实个人隐私。'));root.append(sheet);
  }
  function showIntro(){clear();signal.textContent='NO SIGNAL';
    const start=el('section','start');start.append(el('div','eyebrow','PRIVATE INVESTIGATION / 02'));
    const h=el('h1','hero');h.innerHTML='你愿意<br>交出一份<span>自己的答案</span>吗？';start.append(h);
    start.append(el('p','intro','这是一场以你的回答为基础的心理恐怖游戏。它会记录你珍视的事物，并让你面对丧失、误判、欺骗与无法收回的决定。'));
    start.append(el('p','intro muted','游戏可能说谎。它不会改变游戏外的任何记忆、身份或关系；你的回答只用于本次游戏存档，随时可以终止并删除。'));
    const label=el('label','consent');const cb=el('input');cb.type='checkbox';label.append(cb,el('span','', '我知道这是带有心理压迫内容的虚构体验，自愿进入。'));start.append(label);
    const go=button('确认进入  →',()=>{page=0;showForm();},'btn primary');go.disabled=true;cb.onchange=()=>go.disabled=!cb.checked;start.append(go);
    start.append(el('p','micro','无需填写真实姓名。请勿写入地址、账号、密码等隐私。'));root.append(start);
  }
  function appendBody(parent,text,cl){const x=el('div',cl,text);parent.append(x);return x;}
  function showGame(){clear();titlebar();if(current.phase==='ended'){showEnding();return;}
    const sc=current.scene;const game=el('div','game'),pane=el('section','pane'),header=el('div','panehead');header.append(el('b','',sc.chapter),el('span','',current.name+' / '+String(current.turn).padStart(2,'0')));pane.append(header);
    const body=el('div','paneBody');body.append(el('h2','stageTitle',sc.title));appendBody(body,sc.body,'bodyText');
    if(sc.terms?.length){const terms=el('div','terms');sc.terms.forEach(t=>terms.append(el('div','term',t)));body.append(terms);}
    if(sc.footer)body.append(el('div','footerCode',sc.footer));
    if(current.note)body.append(el('div','lastNote',current.note));pane.append(body);
    const response=el('section','response');response.append(el('label','smallLabel','YOUR RESPONSE / 你的行动'));
    const ta=el('textarea','control');ta.id='action';ta.rows=4;ta.maxLength=700;ta.placeholder=sc.placeholder||'你的决定……';response.append(ta);
    const row=el('div','rowActions');
    const submit=button('提交行动',async()=>{if(!ta.value.trim())return toast('请写下你的行动。');submit.disabled=true;try{current=await api('action',{method:'POST',body:JSON.stringify({action:ta.value,version:current.version})});showGame();}catch(e){toast(e.message);submit.disabled=false;}} ,'btn primary');
    ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();submit.click();}});
    row.append(submit,button('复制场景给 AI',copyScene,'btn subtle'));response.append(row);pane.append(response);game.append(pane);
    const side=el('aside','side');
    const ledgerBox=el('section','sideCard');ledgerBox.append(el('div','sideHead','仍然有效的资格'));
    const ledger=el('div','ledger');current.ledger.forEach(v=>{const entry=el('div','entry'+(v.state==='失效'?' off':''));entry.append(el('span','',v.label),el('mark','',v.state));ledger.append(entry);});ledgerBox.append(ledger);side.append(ledgerBox);
    const events=el('section','sideCard');events.append(el('div','sideHead','可见记录 / 最近'));
    current.events.slice().reverse().forEach(ev=>events.append(el('div','rec '+(ev.type==='loss'?'loss':ev.type==='evidence'?'evidence':''),ev.text)));
    side.append(events);
    const menu=el('section','sideCard full');menu.append(el('div','sideHead','会话'));menu.append(el('div','description','提交会写入服务器存档。关闭网页并不会撤销决定。'));
    const actions=el('div','rowActions');actions.append(button('导出记录',exportGame,'btn subtle'),button('终止',endSession,'btn subtle'),button('清除存档',deleteGame,'btn danger'));menu.append(actions);side.append(menu);game.append(side);root.append(game);
  }
  function showEnding(){const end=el('section','end'),box=el('div','endBox');box.append(el('div','endTag','CASE CLOSED / '+current.ending.kind));box.append(el('h1','',current.ending.title));box.append(el('p','',current.ending.text));
    const line=el('div','description','本局失效：'+(current.ending.lost.join('、')||'无')+'。仍保留：'+(current.ending.remaining.join('、')||'无')+'。');box.append(line);
    const row=el('div','rowActions');row.append(button('导出对局记录',exportGame),button('开始新的一局',async()=>{if(!confirm('新的一局将删除本局存档。确定吗？'))return;try{await resetSession();}catch(e){toast('删除失败：'+e.message);}},'btn subtle'),button('彻底删除本局',deleteGame,'btn danger'));box.append(row);
    end.append(box);
    // An isolated afterword: visible only after completing a narrative ending, never when exiting.
    if(current.ending.author_note){
      const afterword=el('section','authorNote');
      afterword.append(el('div','authorKicker','FROM THE AUTHOR / 作者留言'),el('p','authorText',current.ending.author_note));
      end.append(afterword);
    }
    root.append(end);
  }
  async function copyText(text){try{await navigator.clipboard.writeText(text);toast('已复制。请只把场景发给 AI，不要发送游戏后台源码。');}
    catch(e){const tmp=el('textarea');tmp.value=text;tmp.style.cssText='position:fixed;left:-2000px';document.body.append(tmp);tmp.select();try{document.execCommand('copy');toast('场景已复制');}catch(err){toast('复制失败，请手动选择场景文字。');}tmp.remove();}}
  function copyScene(){const sc=current.scene;copyText(`THE DESCENT · 恐惧深潜\n你是这场游戏的玩家。请根据当前可见信息作出决定。\n\n${sc.chapter} · ${sc.title}\n\n${sc.body}\n\n${(sc.terms||[]).join('\n')}\n\n${sc.footer}\n\n${current.note?'最近反馈：'+current.note+'\n':''}当前资格：${current.ledger.map(x=>x.label+' '+x.state).join('、')}\n\n请给出你的下一步行动。`);}
  async function exportGame(){try{const r=await api('export');const blob=new Blob([JSON.stringify(r,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='THE_DESCENT_完整对局.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),6000);toast('对局记录已导出');}catch(e){toast(e.message);}}
  async function endSession(){if(!confirm('确定终止本局？游戏内一切虚构处置将立即停止。'))return;try{current=await api('action',{method:'POST',body:JSON.stringify({action:'结束游戏',version:current.version})});showGame();}catch(e){toast(e.message);}}
  async function resetSession(){if(token)await api('session',{method:'DELETE'});token='';localStorage.removeItem(key);current=null;form={name:'',identity:'',person:'',bond:'',memory:'',principle:'',fear:'',choice:'',vow:'',rank:[]};showIntro();}
  async function deleteGame(){if(!confirm('永久删除服务器上的本局问卷与记录？此操作不能撤销。'))return;try{await resetSession();toast('本局档案已删除。');}catch(e){toast('删除失败：'+e.message);}}
  async function bootstrap(){if(!token){showIntro();return;}try{current=await api('state');showGame();}catch(e){token='';localStorage.removeItem(key);showIntro();toast('上次的会话已失效，请开始新的一局。');}}
  bootstrap();
})();
