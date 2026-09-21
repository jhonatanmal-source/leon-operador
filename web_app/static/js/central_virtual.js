(() => {
  'use strict';
  const $ = id => document.getElementById(id), root = $('cv');
  if (!root) return;
  const list = x => Array.isArray(x) ? x : [];
  const node = (tag,text,cls) => { const n=document.createElement(tag); if(text!=null)n.textContent=String(text); if(cls)n.className=cls; return n; };
  const put = (id,text) => { $(id).textContent=text ?? 'Sem dados'; };
  const date = value => {const d=new Date(value);return value && Number.isFinite(d.getTime())?d:null;};
  const when = value => date(value)?.toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}) || 'Sem registro';
  let clockOffset=0;
  const serverNow = () => Date.now()-clockOffset;
  function syncClock(snapshot) {const generated=date(snapshot.generated_at);if(generated)clockOffset=Date.now()-generated.getTime();}
  const recent = value => {const d=date(value),now=serverNow();return !!d && now-d.getTime()<=180000 && d.getTime()<=now+30000;};
  const clock = value => {const n=node('time',when(value));if(date(value))n.dateTime=date(value).toISOString();return n;};
  const empty = text => node('p',text,'empty');
  const names={RUNNING:'Em execução',QUEUED:'Na fila',COMPLETED:'Concluído',FAILED:'Falha',WAITING:'Aguardando',BLOCKED:'Bloqueado',UNCONFIGURED:'Não configurado',STALE:'Dados antigos'};
  let data={},selected=null,pending=false,mutation=false,offline=false,failures=0,timer,artifactController,dialogOrigin;
  const canManage = () => root.dataset.canManage==='true' && data.can_manage===true;
  const snapshotStale = () => offline || !recent(data.generated_at);
  const stale = item => snapshotStale() || !item || item.stale===true || !recent(item.updated_at);
  function jobStatus(job) {
    if(job.state!=='RUNNING')return {...job,updated_at:job.finished_at || job.created_at};
    const agent=list(data.agents).find(a=>a.id===job.agent_id && a.run_id && a.run_id===(job.run_id || job.id));
    return {...job,updated_at:agent?.updated_at,stale:!agent || agent.stale===true || agent.state!=='RUNNING'};
  }
  const reasons = {
    DAILY_STOP_REACHED:'Stop diário atingido. Novas entradas pausadas.',
    DAILY_PROFIT_GIVEBACK_REACHED:'Limite de devolução do lucro diário atingido. Novas entradas pausadas.',
    NO_OPEN_PRE_OPERATION_TO_EXECUTE:'Aguardando um setup aprovado para entrada.',
    DEMO_EXECUTION_INTERVAL_WAIT:'Aguardando o próximo ciclo de execução demo.'
  };
  function state(item) {
    if(!item)return {label:'Sem dados',tone:''};
    if(['COMPLETED','FAILED'].includes(item.state))return {label:item.label || names[item.state],tone:item.state==='COMPLETED'?'good':'bad'};
    if(stale(item))return {label:offline?'Estado não confirmado · sem conexão':'Estado não confirmado · dados antigos',tone:'warn'};
    return {label:item.label || names[item.state] || item.state || 'Sem dados',tone:['RUNNING','COMPLETED'].includes(item.state)?'good':['FAILED','BLOCKED'].includes(item.state)?'bad':''};
  }
  const badge = item => {const s=state(item),n=node('span',s.label,'badge');n.dataset.tone=s.tone;return n;};
  const notice = text => { $('notice').hidden=!text;put('notice',text || ''); };
  const details = pairs => {const dl=node('dl',null,'details');pairs.forEach(([k,v])=>{const n=node('div');n.append(node('dt',k),node('dd',v==null || v===''?'Sem dados':v));dl.append(n);});return dl;};
  const ordered = (items,key) => [...list(items)].sort((a,b)=>(date(b[key])?.getTime()||0)-(date(a[key])?.getTime()||0));
  function inspector() {
    const host=$('inspector'),a=list(data.agents).find(a=>a.id===selected);host.replaceChildren();
    if(!a){host.append(empty('Nenhuma estação registrada'));return;}
    host.append(node('h3',a.name || a.id),badge(a),node('p',a.role),details([['Trabalho registrado',a.task],['Mecanismo',a.engine],['Atualizado em',when(a.updated_at)],['Execução',a.run_id]]),node('h4','Evidências'));
    if(!list(a.evidence).length)host.append(empty('Nenhuma evidência registrada'));
    list(a.evidence).forEach(e=>host.append(node('div',typeof e==='string'?e:JSON.stringify(e,null,2),'evidence')));
    const m=data.metrics || {},op=data.operator || {};
    if(op.funnel?.candidates!=null){host.append(node('h4',`Avaliações de ${op.funnel.day} (${op.funnel.timezone || 'UTC'})`),details([['Candidatos',op.funnel.candidates],['Planos prontos',op.funnel.approved]]));Object.entries(op.funnel.blocked_by || {}).forEach(([reason,count])=>host.append(node('p',`${reason}: ${count} recusas`)));}
    host.append(details([['Versão do setup',m.setup_version],['Testes aprovados / falhos',m.tests?.passed!=null && m.tests?.failed!=null?`${m.tests.passed} / ${m.tests.failed}`:null],['Testes atualizados',when(m.tests?.updated_at)],['Autonomia',stale(op)?'Não confirmada · dados antigos':op.autonomy_active===true?(date(op.autonomy_expires_at) && date(op.autonomy_expires_at).getTime()<=serverNow()?'Expirada':'Autorizada'):op.autonomy_active===false?'Inativa':'Sem dados'],['Autorização até',when(op.autonomy_expires_at)]]));
    list(data.artifacts).filter(ar=>ar.job_id && list(data.jobs).some(j=>j.id===ar.job_id && j.agent_id===a.id)).forEach(ar=>host.append(artifactButton(ar)));
  }
  function stations() {
    const agents=list(data.agents);if(!agents.some(a=>a.id===selected))selected=agents[0]?.id;
    const focus=document.activeElement?.dataset?.station;
    $('stations').replaceChildren();$('hotspots').replaceChildren();
    // Seven desk centers, relative to the cropped room (x: 0..1300, y: 108..848).
    const points=[[49,16],[26,34],[40,31],[71,34],[79,54],[48,67],[63,81]];
    agents.forEach((a,i)=>{
      const s=state(a),b=node('button',null,'station'),dot=node('span',null,'dot');dot.dataset.tone=s.tone;b.append(dot,node('span',`${i+1}. ${a.name || a.id}`));b.dataset.station=`list-${a.id}`;b.setAttribute('aria-pressed',String(a.id===selected));b.title=s.label;
      const choose=()=>{selected=a.id;stations();};b.onclick=choose;$('stations').append(b);
      if(points[i]){const h=node('button',String(i+1),'hotspot');h.style.setProperty('--x',`${points[i][0]}%`);h.style.setProperty('--y',`${points[i][1]}%`);h.dataset.station=`map-${a.id}`;h.title=`${a.name || a.id}: ${s.label}`;h.setAttribute('aria-label',h.title);h.setAttribute('aria-pressed',String(a.id===selected));h.onclick=choose;$('hotspots').append(h);}
    });
    if(!agents.length)$('stations').append(empty('Nenhuma estação registrada'));
    if(focus)[...root.querySelectorAll('[data-station]')].find(n=>n.dataset.station===focus)?.focus({preventScroll:true});inspector();
  }
  function eventRow(e) {
    const n=node('article',null,'row'),body=node('div');body.append(node('strong',e.title || 'Evento'),node('p',e.summary || 'Sem detalhes'));
    const a=list(data.agents).find(a=>a.id===e.agent_id);if(a)body.append(node('p',a.name));n.append(clock(e.at),body);
    if(['error','warning'].includes(e.severity)){const b=node('span',e.severity==='error'?'Erro':'Atenção','badge');b.dataset.tone=e.severity==='error'?'bad':'warn';n.append(b);}return n;
  }
  function events() {
    const all=ordered(data.events,'at'),q=$('search').value.toLocaleLowerCase('pt-BR'),severity=$('severity').value,agent=$('agent-filter').value;
    const filtered=all.filter(e=>(!severity || e.severity===severity)&&(!agent || e.agent_id===agent)&&JSON.stringify(e).toLocaleLowerCase('pt-BR').includes(q));
    [['recent',all.slice(0,3)],['events',filtered]].forEach(([id,items])=>{$(id).replaceChildren(...items.map(eventRow));if(!items.length)$(id).append(empty('Nenhuma atividade registrada'));});
  }
  function openDialog(title) {if(!$('cv-dialog').open)dialogOrigin=document.activeElement;put('dialog-title',title);$('dialog-body').replaceChildren();if(!$('cv-dialog').open)$('cv-dialog').showModal();$('close-dialog').focus();}
  function artifactButton(a) {if(!canManage())return document.createDocumentFragment();const b=node('button',a.title || 'Abrir artefato');b.onclick=()=>artifact(a);return b;}
  async function artifact(a) {
    if(!canManage())return;
    artifactController?.abort();artifactController=new AbortController();openDialog(a.title || 'Artefato');$('dialog-body').append(empty('Carregando'));
    try{const result=await request(`/artifacts/${encodeURIComponent(a.id)}`,{signal:artifactController.signal});$('dialog-body').replaceChildren(clock(result.created_at),node('pre',result.content || 'Artefato sem conteúdo'));}
    catch(e){if(e.name!=='AbortError')$('dialog-body').replaceChildren(empty(e.message));}
  }
  function showJob(j) {
    artifactController?.abort();openDialog(j.title || 'Missão');const body=$('dialog-body'),statusBadge=badge(jobStatus(j));statusBadge.dataset.dialogJob=j.id;body.append(statusBadge,node('p',j.summary || 'Sem conclusão registrada'),details([['Criada',when(j.created_at)],['Iniciada',when(j.started_at)],['Concluída',when(j.finished_at)],['Agente',j.agent_id],['Identificador',j.id]]),node('h3','Artefatos'));
    const artifacts=list(data.artifacts).filter(a=>a.job_id===j.id || list(j.artifact_ids).includes(a.id));artifacts.forEach(a=>body.append(artifactButton(a)));if(!artifacts.length)body.append(empty('Nenhum artefato registrado'));
  }
  function jobs() {
    const all=ordered(data.jobs,'created_at'),filter=$('job-filter').value,focus=document.activeElement?.dataset?.jobFocus;
    [['preview',all.slice(0,3)],['jobs',all.filter(j=>!filter || j.state===filter)]].forEach(([id,items])=>{const host=$(id);host.replaceChildren();items.forEach(j=>{const row=node('article',null,'row'),body=node('div'),b=node('button',j.title || 'Missão','link');b.dataset.jobFocus=`${id}-${j.id}`;b.onclick=()=>showJob(j);body.append(b,node('p',j.summary || when(j.created_at)));row.append(body,badge(jobStatus(j)));host.append(row);});if(!items.length)host.append(empty('Nenhuma missão registrada'));});
    const dialogBadge=$('dialog-body').querySelector('[data-dialog-job]');
    if(dialogBadge){const job=all.find(j=>j.id===dialogBadge.dataset.dialogJob),s=state(job?jobStatus(job):null);dialogBadge.textContent=s.label;dialogBadge.dataset.tone=s.tone;}
    if(focus)[...root.querySelectorAll('[data-job-focus]')].find(n=>n.dataset.jobFocus===focus)?.focus({preventScroll:true});
  }
  function render() {
    const op=data.operator || {},eng=data.engineering || {},m=data.metrics || {},r=op.risk || {};
    put('asset',op.asset || 'Sem ativo');put('state',state(op).label);put('reason',Object.hasOwn(reasons,op.reason)?reasons[op.reason]:op.reason || 'Sem registro operacional');put('worker',state(eng.worker).label);
    $('checks').replaceChildren(...list(op.checks).map(c=>{const old=stale(op) || c.stale===true || (c.updated_at!=null && !recent(c.updated_at));const b=node('span',`${c.label || c.id}: ${old?'Dados antigos':c.passed===true?'Confirmado':c.passed===false?'Não confirmado':'Sem dados'}`,'badge');b.dataset.tone=old?'warn':c.passed===true?'good':c.passed===false?'bad':'';return b;}));
    const values=[['Operações confirmadas',m.confirmed_trades],['Vitórias / perdas',m.wins!=null && m.losses!=null?`${m.wins} / ${m.losses}`:null],['Na versão atual',m.version_trades],['Risco por entrada',r.risk_percent==null?null:`${r.risk_percent}%`],['Stop diário',r.daily_loss_percent==null?null:`${r.daily_loss_percent}%`],['Posições máximas',r.max_positions]];
    if(r.giveback_activation_percent!=null)values.push(['Ativação da proteção de lucro',`${r.giveback_activation_percent}%`]);
    if(r.giveback_day_balance!=null)values.push(['Saldo diário da proteção',typeof r.giveback_day_balance==='number'?r.giveback_day_balance.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}):r.giveback_day_balance]);
    if(r.giveback_armed!=null)values.push(['Proteção de lucro',stale(op)?'Não confirmada':r.giveback_armed===true?'Armada':r.giveback_armed===false?'Não armada':'Sem dados']);
    $('metrics').replaceChildren(...values.map(([k,v])=>{const n=node('div');n.append(node('dt',k),node('dd',v ?? 'Sem dados'));return n;}));
    put('provider',snapshotStale() || eng.provider?.available!==true?'IA não confirmada':eng.provider.label || 'IA disponível');$('provider').title=eng.provider?.reason || '';put('next',`Próximo ciclo${snapshotStale()?' registrado':''}: ${when(eng.next_run_at)}`);
    const manage=root.dataset.canManage==='true' && data.can_manage===true;$('actions').hidden=!manage;$('automation-wrap').hidden=!manage;$('automation').checked=!snapshotStale() && eng.enabled===true;$('automation').indeterminate=snapshotStale();$('automation').title=snapshotStale()?'Estado não confirmado':'';$('automation').disabled=mutation || snapshotStale();root.querySelectorAll('[data-job]').forEach(b=>b.disabled=mutation || snapshotStale());
    put('sync',`${offline?'Conexão interrompida':recent(data.generated_at)?'Atualizado':'Dados antigos'} · ${when(data.generated_at)}`);
    const s=$('agent-filter'),value=s.value;s.replaceChildren(new Option('Todos',''),...list(data.agents).map(a=>new Option(a.name || a.id,a.id)));s.value=value;
    stations();events();jobs();
  }
  async function request(path,options={}) {
    const controller=new AbortController(),external=options.signal,abort=()=>controller.abort(),timeout=setTimeout(abort,12000);external?.addEventListener('abort',abort,{once:true});
    try{const response=await fetch(`/central-virtual${path}`,{...options,signal:controller.signal,credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json',...options.headers}});if(!response.ok){let body={};try{body=await response.json();}catch(_){}throw new Error(body.error || ([401,403].includes(response.status)?'Sessão expirada ou acesso negado.':`Solicitação não concluída (${response.status}).`));}if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('Sessão indisponível. Entre novamente no painel.');return await response.json();}
    finally{clearTimeout(timeout);external?.removeEventListener('abort',abort);}
  }
  function schedule(){clearTimeout(timer);if(!document.hidden)timer=setTimeout(poll,Math.min(60000,5000*2**failures));}
  async function poll(){
    if(pending || document.hidden || mutation){schedule();return;}pending=true;$('refresh').disabled=true;
    try{const result=await request('/snapshot');if(result.schema_version!==1)throw new Error('Formato de dados incompatível.');syncClock(result);data=result;offline=false;failures=0;notice('');render();}
    catch(e){offline=true;failures=Math.min(failures+1,4);notice(`Sem conexão com a Central. ${e.name==='AbortError'?'Tempo de resposta excedido.':e.message}`);render();}
    finally{pending=false;$('refresh').disabled=false;schedule();}
  }
  async function mutate(path,payload){
    if(mutation || root.dataset.canManage!=='true' || !data.can_manage)return;mutation=true;render();
    let succeeded=false;
    try{await request(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':root.dataset.csrf},body:JSON.stringify(payload)});succeeded=true;notice(path==='/jobs'?'Missão enviada.':'Engenharia atualizada.');}
    catch(e){notice(e.name==='AbortError'?'Resposta não recebida. Atualize antes de repetir o comando.':e.message);}
    finally{mutation=false;render();schedule();}
    if(succeeded)await poll();
  }
  function view(name,focus=false){root.querySelectorAll('[data-view]').forEach(b=>{const active=b.dataset.view===name;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;$(b.dataset.view).hidden=!active;if(active && focus)b.focus();});}
  root.querySelectorAll('[data-view]').forEach(b=>{b.onclick=()=>view(b.dataset.view);b.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...root.querySelectorAll('[data-view]')],i=tabs.indexOf(b),n=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;view(tabs[n].dataset.view,true);};});
  root.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>view(b.dataset.open,true));root.querySelectorAll('[data-job]').forEach(b=>b.onclick=()=>mutate('/jobs',{kind:b.dataset.job}));
  $('automation').onchange=e=>mutate('/automation',{enabled:e.target.checked});$('refresh').onclick=poll;
  ['search','severity','agent-filter'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',events));$('job-filter').onchange=jobs;
  $('close-dialog').onclick=()=>$('cv-dialog').close();$('cv-dialog').addEventListener('close',()=>{artifactController?.abort();if(dialogOrigin?.isConnected)dialogOrigin.focus();else $('refresh').focus();});
  let ageTimer;
  function ageLocally(){clearTimeout(ageTimer);if(document.hidden)return;ageTimer=setTimeout(()=>{render();ageLocally();},1000);}
  document.addEventListener('visibilitychange',()=>{clearTimeout(timer);clearTimeout(ageTimer);if(!document.hidden){render();ageLocally();poll();}});window.addEventListener('pagehide',()=>{clearTimeout(timer);clearTimeout(ageTimer);});
  try{data=JSON.parse($('cv-data').textContent || '{}');syncClock(data);}catch(_){notice('Dados iniciais indisponíveis.');}render();window.lucide?.createIcons();ageLocally();poll();
})();
