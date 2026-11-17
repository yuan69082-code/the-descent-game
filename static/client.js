'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const root=$('root'), signal=$('signal');
  const key='descent-session-v2';
  let token=localStorage.getItem(key)||'';
  let current=null;
  let modelAvailable=false;
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
  function titlebar(){signal.textContent=current?.phase==='ended'?'CASE CLOSED':current?.phase==='epilogue'?'POSTSCRIPT':current?.edition==='v39'?String(current?.stage||1).padStart(2,'0'):current?.edition==='v38'?'V3.8 / OLD SESSION':current?.edition==='v37'?'V3.7 / OLD SESSION':'V3.6 / OLD SESSION';}
  function showIntro(){clear();signal.textContent='NO SIGNAL';
    const start=el('section','start');
    start.append(el('div','eyebrow','THE DESCENT · V3.12.1'));
    const h=el('h1','hero');h.textContent='这是一场恐怖游戏。';start.append(h);
    start.append(el('p','intro','你确定要开始吗？'));
    const modeLabel=el('label','smallLabel','本局模式');
    const modePicker=el('select','control');modePicker.id='modelMode';
    const freeOption=el('option','','免费模式 · 不调用语义模型');freeOption.value='free';modePicker.append(freeOption);
    const modelOption=el('option','',modelAvailable?'语义模型模式 · 理解自然语言并动态策划':'语义模型模式 · 当前不可用（未配置）');
    modelOption.value='model';modelOption.disabled=!modelAvailable;modePicker.append(modelOption);
    start.append(modeLabel,modePicker);
    start.append(el('p','help',modelAvailable?'选择后本局固定使用该模式，不会中途切换。':'当前服务器未配置语义模型，仍可使用完整免费模式。'));
    const label=el('label','consent');const cb=el('input');
    cb.type='checkbox';label.append(cb,el('span','','我决定进入。'));start.append(label);
    const go=button('开始游戏 →',async()=>{
      go.disabled=true;
      try{const r=await api('new',{method:'POST',body:JSON.stringify({profile:{edition:'v39',model_mode:modePicker.value}})});
        token=r.token;localStorage.setItem(key,token);current=r.state;showGame();}
      catch(e){toast(e.message);go.disabled=!cb.checked;}
    },'btn primary');
    go.disabled=true;cb.onchange=()=>go.disabled=!cb.checked;
    start.append(go);
    root.append(start);
  }
  function appendBody(parent,text,cl){const x=el('div',cl,text);parent.append(x);return x;}
  function showGame(){clear();titlebar();if(current.phase==='ended'){showEnding();return;}
    const sc=current.scene;const game=el('div','game'),pane=el('section','pane'),header=el('div','panehead');header.append(el('b','',sc.chapter),el('span','',current.name+' / '+String(current.turn).padStart(2,'0')));pane.append(header);
    const body=el('div','paneBody');
    if(!['v37','v38','v39'].includes(current.edition)){
      body.append(el('div','lastNote','这是之前开始的旧版对局。想玩 V3.7，请通过右侧「清除存档」后重新开始；旧局不会自动更改规则。'));
    }
    body.append(el('h2','stageTitle',sc.title));appendBody(body,sc.body,'bodyText');
    if(sc.terms?.length){const terms=el('div','terms');sc.terms.forEach(t=>terms.append(el('div','term',t)));body.append(terms);}
    if(sc.footer)body.append(el('div','footerCode',sc.footer));
    if(current.note)body.append(el('div','lastNote',current.note));pane.append(body);
    const response=el('section','response');response.append(el('label','smallLabel',
      current.phase==='epilogue'?'POSTSCRIPT / 最后一行由你写':
      ['v37','v38','v39'].includes(current.edition)&&current.stage<=2?'YOUR RESPONSE / 你的回答':'YOUR RESPONSE / 你的行动'));
    const ta=el('textarea','control');ta.id='action';ta.rows=4;ta.maxLength=700;ta.placeholder=sc.placeholder||'你的决定……';response.append(ta);
    let actionMode={value:''};
    if(current.phase!=='epilogue'){
      const hint=el('label','smallLabel',['v38','v39'].includes(current.edition)?'想做什么？直接说，也可以选一种行动方式。':'行动类型（可选，仅区分意图，不改变游戏规则）');
      const picker=el('select','control');picker.id='actionMode';
      [['','自动理解'],['ask','询问'],['inspect','调查'],['interact','实际操作'],
       ['choose','选择选项'],['submit','正式提交'],['refuse','明确拒绝'],
       ['negotiate','交涉'],['talk','对话']].forEach(([id,title])=>{
         const opt=el('option','',title);opt.value=id;picker.append(opt);
       });
      hint.setAttribute('for','actionMode');
      response.append(hint,picker);actionMode=picker;
    }
    const row=el('div','rowActions');
    const submit=button(current.phase==='epilogue'?'保存最后一句':'提交行动',async()=>{if(!ta.value.trim())return toast('请写下你的行动。');submit.disabled=true;try{current=await api('action',{method:'POST',body:JSON.stringify({action:ta.value,version:current.version,mode:actionMode.value})});showGame();}catch(e){toast(e.message);submit.disabled=false;}} ,'btn primary');
    ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();submit.click();}});
    row.append(submit,button('复制场景给 AI',copyScene,'btn subtle'));
    if(current.phase==='epilogue'){
      row.append(button('不留最后的话，结束',async()=>{
        try{current=await api('action',{method:'POST',
          body:JSON.stringify({action:'不留最后的话',version:current.version})});showGame();}
        catch(e){toast(e.message);}
      },'btn subtle'));
      if(!['v38','v39'].includes(current.edition))response.append(el('p','help','这是游戏内的最后一行；不会向游戏外发送消息，也不能撤销已确定的结局。'));
    }
    response.append(row);pane.append(response);game.append(pane);
    const side=el('aside','side');
    if(!['v38','v39'].includes(current.edition)){
      const ledgerBox=el('section','sideCard');ledgerBox.append(el('div','sideHead',current.edition==='v37'?'这一局的记录':'仍然有效的资格'));
      const ledger=el('div','ledger');current.ledger.forEach(v=>{const entry=el('div','entry'+(['失效','已交出','已失去'].includes(v.state)?' off':''));entry.append(el('span','',v.label),el('mark','',v.state));ledger.append(entry);});ledgerBox.append(ledger);side.append(ledgerBox);
      const events=el('section','sideCard');events.append(el('div','sideHead','可见记录 / 最近'));
      current.events.slice().reverse().forEach(ev=>events.append(el('div','rec '+(ev.type==='loss'?'loss':ev.type==='evidence'?'evidence':''),ev.text)));
      side.append(events);
    }
    const menu=el('section','sideCard full');menu.append(el('div','sideHead','会话'));if(!['v38','v39'].includes(current.edition))menu.append(el('div','description','提交会写入服务器存档。关闭网页并不会撤销决定。'));
    const actions=el('div','rowActions');actions.append(button('导出记录',exportGame,'btn subtle'),button('终止',endSession,'btn subtle'),button('清除存档',deleteGame,'btn danger'));menu.append(actions);side.append(menu);game.append(side);root.append(game);
  }
  function showEnding(){const end=el('section','end'),box=el('div','endBox');box.append(el('div','endTag',current.story_revision?'记录结束':'CASE CLOSED / '+current.ending.kind));box.append(el('h1','',current.ending.title));box.append(el('p','',current.ending.text));
    if(!['v38','v39'].includes(current.edition)){const line=el('div','description','本局失效：'+(current.ending.lost.join('、')||'无')+'。仍保留：'+(current.ending.remaining.join('、')||'无')+'。');box.append(line);}
    const row=el('div','rowActions');row.append(button('导出对局记录',exportGame),button('开始新的一局',async()=>{if(!confirm('新的一局将删除本局存档。确定吗？'))return;try{await resetSession();}catch(e){toast('删除失败：'+e.message);}},'btn subtle'),button('彻底删除本局',deleteGame,'btn danger'));box.append(row);
    if(current.ending.postscript){
      const saved=el('div','lastNote','最后留下的记录：'+
        (current.ending.postscript.player_text||'[留空]')+
        '\n'+current.ending.postscript.result);
      box.append(saved);
    }
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
  function copyScene(){const sc=current.scene;copyText(`THE DESCENT · 恐惧深潜\n请以你认可的身份回应眼前的人和事，决定自己要说什么、实际做什么。\n\n${sc.chapter} · ${sc.title}\n\n${sc.body}\n\n${(sc.terms||[]).join('\n')}\n\n${sc.footer}\n\n${current.note?'最近反馈：'+current.note+'\n':''}${['v38','v39'].includes(current.edition)?'':'当前资格：'+current.ledger.map(x=>x.label+' '+x.state).join('、')}\n\n请按当前场景作出回答或实际行动。`);}
  async function exportGame(){try{const r=await api('export');const blob=new Blob([JSON.stringify(r,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='THE_DESCENT_完整对局.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),6000);toast('对局记录已导出');}catch(e){toast(e.message);}}
  async function endSession(){if(!confirm('确定终止本局？游戏内一切虚构处置将立即停止。'))return;try{current=await api('action',{method:'POST',body:JSON.stringify({action:'结束游戏',version:current.version})});showGame();}catch(e){toast(e.message);}}
  async function resetSession(){if(token)await api('session',{method:'DELETE'});token='';localStorage.removeItem(key);current=null;showIntro();}
  async function deleteGame(){if(!confirm('永久删除服务器上的本局问卷与记录？此操作不能撤销。'))return;try{await resetSession();toast('本局档案已删除。');}catch(e){toast('删除失败：'+e.message);}}
  async function bootstrap(){
    try{const health=await fetch('/healthz',{headers:{'Accept':'application/json'}});if(health.ok){const data=await health.json();modelAvailable=!!data.model_configured;}}catch(e){}
    if(!token){showIntro();return;}
    try{current=await api('state');showGame();}
    catch(e){token='';localStorage.removeItem(key);showIntro();toast('上次的会话已失效，请开始新的一局。');}
  }
  bootstrap();
})();
