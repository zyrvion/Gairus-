const A="/api";
const state={page:location.hash.slice(1)||"chat",data:{status:{},missions:[],tasks:[],actions:[],approvals:[],events:[],memory:[]}};
const nav=[
["chat","⌕","Gaïrus"],
["missions","◈","Missions"],
["tasks","✓","Tâches"],
["actions","⚙","Actions"],
["approvals","!","Approbations"],
["memory","▣","Mémoire"],
["tools","◉","Outils"],
["events","◷","Activité"],
["health","●","Système"],
["settings","⚙","Paramètres"]
];
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function api(path,opt={}){const r=await fetch(A+path,{headers:{"Content-Type":"application/json"},...opt});const t=await r.text();let d={};try{d=t?JSON.parse(t):{}}catch{d={raw:t}}if(!r.ok)throw new Error(d.error||d.message||t||r.statusText);return d}
function arr(x){if(Array.isArray(x))return x;if(Array.isArray(x?.items))return x.items;if(Array.isArray(x?.data))return x.data;if(Array.isArray(x?.missions))return x.missions;if(Array.isArray(x?.tasks))return x.tasks;if(Array.isArray(x?.actions))return x.actions;if(Array.isArray(x?.approvals))return x.approvals;if(Array.isArray(x?.events))return x.events;if(Array.isArray(x?.memory))return x.memory;return[]}
function id(x){return x.mission_id||x.task_id||x.action_id||x.approval_id||x.id}
function badge(s){let c=s==="completed"?"ok":s==="waiting_approval"?"wait":"";return `<span class="badge ${c}">${esc(s||"pending")}</span>`}
async function load(){
 try{
  const [status,missions,tasks,actions,approvals,events,memory]=await Promise.all([
   api("/status"),api("/autonomy/missions").catch(()=>api("/missions")),api("/autonomy/tasks").catch(()=>api("/tasks")),
   api("/autonomy/actions").catch(()=>api("/actions")),api("/autonomy/approvals").catch(()=>api("/approvals")),
   api("/autonomy/events").catch(()=>api("/events")),api("/memory")
  ]);
  state.data={status,missions:arr(missions),tasks:arr(tasks),actions:arr(actions),approvals:arr(approvals),events:arr(events),memory:arr(memory)};
 }catch(e){state.data.error=e.message}
 render()
}
function shell(body){
 document.querySelector("#app").innerHTML=`<div class="app"><aside class="side" id="side">
 <div class="brand"><div class="brandMark">G</div>Gaïrus</div>
 <button class="new" onclick="newMission()">＋ Nouvelle mission</button>
 <div class="nav">${nav.map(n=>`<button class="${state.page===n[0]?"active":""}" onclick="go('${n[0]}')"><span class="ico">${n[1]}</span>${n[2]}</button>`).join("")}</div>
 <div class="sideBottom"><button class="new" onclick="go('settings')">⚙ Paramètres</button></div>
 </aside>
 <main class="main"><header class="top"><button class="menu" onclick="document.querySelector('#side').classList.toggle('open')">☰</button><div class="topTitle">${title()}</div><div class="online"><i></i> Gaïrus actif</div></header><div class="page">${body}</div></main></div>`
}
function title(){return (nav.find(x=>x[0]===state.page)||nav[0])[2]}
function go(p){state.page=p;location.hash=p;render()}
function render(){
 if(state.page==="chat")return chat();
 const fn={missions:missions,tasks:tasks,actions:actions,approvals:approvals,memory:memory,tools:tools,events:events,health:health,settings:settings}[state.page];
 shell(`<section class="section">${fn()}</section>`)
}
function chat(){
 shell(`<div class="messages" id="messages"><div class="welcome"><div class="logo">G</div><h1>Bonjour, je suis Gaïrus.</h1><div class="subtitle">Votre employé IA. Dites-moi ce que vous voulez accomplir.</div><div class="composer"><textarea id="first" placeholder="Que voulez-vous que Gaïrus fasse ?"></textarea><div class="composeBottom"><button class="send" onclick="send('first')">Envoyer</button></div></div></div></div>`)
}
async function send(input){
 const el=document.getElementById(input),text=el.value.trim();if(!text)return;
 const box=document.getElementById("messages");box.innerHTML+=`<div class="msg user"><div class="bubble">${esc(text)}</div></div>`;
 el.value="";box.innerHTML+=`<div class="msg"><div class="who">G</div><div class="bubble">Je travaille dessus…</div></div>`;
 box.scrollTop=box.scrollHeight;
 try{
  const r=await api("/chat",{method:"POST",body:JSON.stringify({message:text})});
  box.lastElementChild.querySelector(".bubble").textContent=r.reply||r.response||r.message||"Terminé.";
 }catch(e){box.lastElementChild.querySelector(".bubble").textContent="Erreur : "+e.message}
}
function head(h,s){return `<div class="sectionHead"><h2>${h}</h2><span>${s||""}</span></div>`}
function missions(){
 let a=state.data.missions;
 return head("Missions","Travaux confiés à Gaïrus")+`<div class="actions"><button class="btn dark" onclick="newMission()">＋ Nouvelle mission</button></div><div class="list">${a.length?a.map(m=>`<div class="item"><div class="itemTop"><div><div class="itemTitle">${esc(m.title||m.objective)}</div><div class="meta">${esc(m.objective||"")} · ${esc(id(m))}</div></div>${badge(m.status)}</div><div class="actions"><button class="btn" onclick="plan('${esc(m.mission_id)}')">Planifier</button><button class="btn dark" onclick="run('${esc(m.mission_id)}')">Exécuter</button></div></div>`).join(""):`<div class="empty">Aucune mission</div>`}</div>`
}
function tasks(){return head("Tâches","Décomposition du travail")+list(state.data.tasks,x=>`<div class="itemTop"><div><div class="itemTitle">${esc(x.title)}</div><div class="meta">Priorité ${esc(x.priority)} · ${esc(x.task_id)}</div></div>${badge(x.status)}</div>`)}
function actions(){return head("Actions","Actions exécutées par Gaïrus")+list(state.data.actions,x=>`<div class="itemTop"><div><div class="itemTitle">${esc(x.tool)}</div><div class="meta">${esc(x.action_id)}</div></div>${badge(x.status)}</div>`)}
function approvals(){return head("Approbations","Actions nécessitant votre autorisation")+list(state.data.approvals,x=>`<div><div class="itemTop"><div><div class="itemTitle">${esc(x.reason||"Autorisation requise")}</div><div class="meta">${esc(x.approval_id)}</div></div>${badge(x.status)}</div>${x.status==="pending"?`<div class="actions"><button class="btn dark" onclick="approve('${esc(x.approval_id)}')">Autoriser</button><button class="btn red" onclick="reject('${esc(x.approval_id)}')">Refuser</button></div>`:""}</div>`)}
function memory(){return head("Mémoire","Ce que Gaïrus conserve")+`<div class="form"><textarea id="mem" placeholder="Information à mémoriser"></textarea><button class="btn dark" onclick="saveMemory()">Enregistrer</button></div><br>${list(state.data.memory,x=>`<div class="item">${esc(x.content||x.memory||x.value||JSON.stringify(x))}</div>`)}`}
function tools(){return head("Outils","Capacités disponibles")+`<div class="grid">${["noop","system_status","memory_read","memory_write","http_get"].map(x=>`<div class="card"><h3>${x}</h3><p>Outil Gaïrus disponible dans le moteur d'exécution.</p></div>`).join("")}</div>`}
function events(){return head("Activité","Journal réel du moteur")+list(state.data.events,x=>`<div class="item"><div class="itemTitle">${esc(x.message||x.event_type)}</div><div class="meta">${esc(x.event_type||"")} · ${esc(x.created_at||"")}</div></div>`)}
function health(){let s=state.data.status||{};return head("Système","État du backend")+`<div class="grid"><div class="card"><div class="kpi">●</div><h3>Backend</h3><p>Connecté</p></div><div class="card"><div class="kpi">${esc(s.provider||s.brain||"auto")}</div><h3>Moteur IA</h3><p>Fournisseur actif</p></div><div class="card"><div class="kpi">${state.data.missions.length}</div><h3>Missions</h3><p>Enregistrées</p></div></div>`}
function settings(){return head("Paramètres","Configuration de Gaïrus")+`<div class="card"><h3>Runtime</h3><p>Le moteur utilise la configuration du serveur Render. Les clés et paramètres sensibles restent côté serveur.</p></div>`}
function list(a,f){return `<div class="list">${a.length?a.map(f).join(""):`<div class="empty">Aucun élément</div>`}</div>`}
async function newMission(){
 const objective=prompt("Objectif de la mission");if(!objective)return;
 try{await api("/autonomy/mission",{method:"POST",body:JSON.stringify({objective,title:objective})});await load();go("missions")}catch(e){alert(e.message)}
}
async function plan(i){try{await api(`/autonomy/mission/${i}/plan`,{method:"POST"});await load()}catch(e){alert(e.message)}}
async function run(i){try{await api(`/autonomy/mission/${i}/run`,{method:"POST"});await load()}catch(e){alert(e.message)}}
async function approve(i){try{await api(`/autonomy/approval/${i}/approve`,{method:"POST"});await load()}catch(e){alert(e.message)}}
async function reject(i){try{await api(`/autonomy/approval/${i}/reject`,{method:"POST"});await load()}catch(e){alert(e.message)}}
async function saveMemory(){let x=document.getElementById("mem").value.trim();if(!x)return;try{await api("/memory",{method:"POST",body:JSON.stringify({content:x,memory:x})});document.getElementById("mem").value="";await load()}catch(e){alert(e.message)}}
window.addEventListener("hashchange",()=>{state.page=location.hash.slice(1)||"chat";load()});
load();
setInterval(load,10000);
