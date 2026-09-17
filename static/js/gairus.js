const API="/api";

const state={
 page:location.hash.slice(1)||"chat",
 data:{status:{},missions:[],tasks:[],actions:[],approvals:[],events:[],memory:[]},
 messages:JSON.parse(localStorage.getItem("gairus_chat")||"[]")
};

const nav=[
 ["chat","⌕","Chat"],
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

function esc(x){
 return String(x??"").replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
 }[c]));
}

function arr(x){
 if(Array.isArray(x))return x;
 if(Array.isArray(x?.items))return x.items;
 if(Array.isArray(x?.data))return x.data;
 if(Array.isArray(x?.missions))return x.missions;
 if(Array.isArray(x?.tasks))return x.tasks;
 if(Array.isArray(x?.actions))return x.actions;
 if(Array.isArray(x?.approvals))return x.approvals;
 if(Array.isArray(x?.events))return x.events;
 if(Array.isArray(x?.memory))return x.memory;
 return [];
}

function ident(x){
 return x.mission_id||x.task_id||x.action_id||x.approval_id||x.id||"";
}

async function api(path,options={}){
 const opts={...options,headers:{"Content-Type":"application/json",...(options.headers||{})}};
 const r=await fetch(API+path,opts);
 const text=await r.text();
 let data={};
 try{data=text?JSON.parse(text):{}}catch{data={raw:text}};
 if(!r.ok)throw new Error(data.error||data.message||text||"Erreur serveur");
 return data;
}

async function loadData(){
 const jobs=await Promise.allSettled([
  api("/status"),
  api("/autonomy/missions").catch(()=>api("/missions")),
  api("/autonomy/tasks").catch(()=>api("/tasks")),
  api("/autonomy/actions").catch(()=>api("/actions")),
  api("/autonomy/approvals").catch(()=>api("/approvals")),
  api("/autonomy/events").catch(()=>api("/events")),
  api("/memory")
 ]);

 state.data.status=jobs[0].status==="fulfilled"?jobs[0].value:{};
 state.data.missions=jobs[1].status==="fulfilled"?arr(jobs[1].value):[];
 state.data.tasks=jobs[2].status==="fulfilled"?arr(jobs[2].value):[];
 state.data.actions=jobs[3].status==="fulfilled"?arr(jobs[3].value):[];
 state.data.approvals=jobs[4].status==="fulfilled"?arr(jobs[4].value):[];
 state.data.events=jobs[5].status==="fulfilled"?arr(jobs[5].value):[];
 state.data.memory=jobs[6].status==="fulfilled"?arr(jobs[6].value):[];

 if(state.page==="chat"){
  updateChatStatus();
 }else{
  render();
 }
}

function shell(content){
 document.querySelector("#app").innerHTML=
 `<div class="app">
   <aside class="side" id="side">
    <div class="brand"><div class="brandMark">G</div><span>Gaïrus</span></div>
    <button class="new" data-action="new-mission">＋ Nouvelle mission</button>
    <div class="nav">
      ${nav.map(n=>`<button class="${state.page===n[0]?"active":""}" data-page="${n[0]}"><span class="ico">${n[1]}</span>${n[2]}</button>`).join("")}
    </div>
    <div class="sideBottom">
      <button class="new" data-page="settings">⚙ Paramètres</button>
    </div>
   </aside>
   <main class="main">
    <header class="top">
      <button class="menu" data-action="menu">☰</button>
      <div class="topTitle">${title()}</div>
      <div class="online"><i></i> Gaïrus actif</div>
    </header>
    <div class="page">${content}</div>
   </main>
 </div>`;
}

function title(){
 return (nav.find(x=>x[0]===state.page)||nav[0])[2];
}

function render(){
 const pages={missions, tasks, actions, approvals, memory, tools, events, health, settings};
 if(state.page==="chat"){renderChat();return}
 shell(`<section class="section">${pages[state.page]?pages[state.page]():missions()}</section>`);
}

function renderChat(){
 shell(`
  <div class="chat">
   <div class="messages" id="messages">
    ${state.messages.length?state.messages.map(messageHTML).join(""):`
      <div class="welcome">
       <div class="logo">G</div>
       <h1>Bonjour, je suis Gaïrus.</h1>
       <div class="subtitle">Votre employé IA. Donnez-moi une question, une tâche ou un objectif.</div>
      </div>`}
   </div>
   <form class="composer" id="chatForm">
    <textarea id="chatInput" placeholder="Écrivez votre demande à Gaïrus..." autocomplete="off"></textarea>
    <button class="send" id="sendBtn" type="submit">Envoyer</button>
   </form>
   <div class="hints">
    <button class="hint" data-fill="Planifie une nouvelle mission">Planifier une mission</button>
    <button class="hint" data-fill="Montre-moi mes missions">Mes missions</button>
    <button class="hint" data-fill="Que peux-tu faire ?">Tes capacités</button>
   </div>
  </div>`);
 attachChat();
}

function messageHTML(m){
 return `<div class="msg ${m.role==="user"?"user":""}">
   ${m.role==="user"?"":`<div class="avatar">G</div>`}
   <div class="bubble">${esc(m.text)}</div>
 </div>`;
}

function attachChat(){
 const form=document.querySelector("#chatForm");
 const input=document.querySelector("#chatInput");
 if(!form||!input)return;

 form.addEventListener("submit",e=>{
  e.preventDefault();
  sendChat();
 });

 input.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){
   e.preventDefault();
   sendChat();
  }
 });

 document.querySelectorAll("[data-fill]").forEach(b=>{
  b.addEventListener("click",()=>{
   input.value=b.dataset.fill;
   input.focus();
  });
 });

 input.focus();
 const box=document.querySelector("#messages");
 if(box)box.scrollTop=box.scrollHeight;
}

async function sendChat(){
 const input=document.querySelector("#chatInput");
 const btn=document.querySelector("#sendBtn");
 const box=document.querySelector("#messages");
 if(!input||!btn||!box)return;

 const text=input.value.trim();
 if(!text)return;

 const welcome=box.querySelector(".welcome");
 if(welcome)welcome.remove();

 state.messages.push({role:"user",text});
 localStorage.setItem("gairus_chat",JSON.stringify(state.messages));

 box.insertAdjacentHTML("beforeend",messageHTML({role:"user",text}));
 box.insertAdjacentHTML("beforeend",`<div class="msg" id="working"><div class="avatar">G</div><div class="bubble">Gaïrus travaille…</div></div>`);
 box.scrollTop=box.scrollHeight;

 input.value="";
 btn.disabled=true;

 try{
  const r=await api("/chat",{
   method:"POST",
   body:JSON.stringify({message:text})
  });

  const reply=r.reply||r.response||r.message||"Terminé.";
  const working=document.querySelector("#working");
  if(working)working.outerHTML=messageHTML({role:"assistant",text:reply});

  state.messages.push({role:"assistant",text:reply});
  state.messages=state.messages.slice(-100);
  localStorage.setItem("gairus_chat",JSON.stringify(state.messages));
 }catch(e){
  const working=document.querySelector("#working");
  const reply="Erreur : "+e.message;
  if(working)working.outerHTML=messageHTML({role:"assistant",text:reply});
  state.messages.push({role:"assistant",text:reply});
  localStorage.setItem("gairus_chat",JSON.stringify(state.messages));
 }finally{
  btn.disabled=false;
  input.focus();
  box.scrollTop=box.scrollHeight;
 }
}

function updateChatStatus(){}

function missions(){
 const a=state.data.missions;
 return `
 ${head("Missions","Travaux confiés à Gaïrus")}
 <div class="missionForm">
  <strong>Créer une mission</strong>
  <input id="missionTitle" placeholder="Nom de la mission">
  <textarea id="missionObjective" placeholder="Objectif détaillé de la mission"></textarea>
  <button class="btn dark" data-action="create-mission-form">Créer la mission</button>
 </div>
 <div class="list">
 ${a.length?a.map(m=>`
  <div class="item">
   <div class="itemTop">
    <div><div class="itemTitle">${esc(m.title||m.objective)}</div><div class="meta">${esc(m.objective||"")} · ${esc(ident(m))}</div></div>
    ${badge(m.status)}
   </div>
   <div class="actions">
    <button class="btn" data-action="plan" data-id="${esc(m.mission_id)}">Planifier</button>
    <button class="btn dark" data-action="run" data-id="${esc(m.mission_id)}">Exécuter</button>
   </div>
  </div>`).join(""):`<div class="empty">Aucune mission pour le moment.</div>`}
 </div>`;
}

function tasks(){
 return head("Tâches","Décomposition du travail")+list(state.data.tasks,x=>`
 <div class="itemTop">
  <div><div class="itemTitle">${esc(x.title||x.description)}</div><div class="meta">Priorité ${esc(x.priority)} · ${esc(ident(x))}</div></div>
  ${badge(x.status)}
 </div>`);
}

function actions(){
 return head("Actions","Actions du moteur")+list(state.data.actions,x=>`
 <div class="itemTop">
  <div><div class="itemTitle">${esc(x.tool)}</div><div class="meta">${esc(ident(x))}</div></div>
  ${badge(x.status)}
 </div>`);
}

function approvals(){
 return head("Approbations","Actions nécessitant votre autorisation")+list(state.data.approvals,x=>`
 <div>
  <div class="itemTop">
   <div><div class="itemTitle">${esc(x.reason||"Autorisation requise")}</div><div class="meta">${esc(ident(x))}</div></div>
   ${badge(x.status)}
  </div>
  ${x.status==="pending"?`
   <div class="actions">
    <button class="btn dark" data-action="approve" data-id="${esc(x.approval_id)}">Autoriser</button>
    <button class="btn red" data-action="reject" data-id="${esc(x.approval_id)}">Refuser</button>
   </div>`:""}
 </div>`);
}

function memory(){
 return head("Mémoire","Informations conservées par Gaïrus")+
 `<div class="form">
   <textarea id="mem" placeholder="Information que Gaïrus doit mémoriser"></textarea>
   <button class="btn dark" data-action="save-memory">Enregistrer</button>
  </div>`+
 list(state.data.memory,x=>`<div class="item">${esc(x.content||x.memory||x.value||JSON.stringify(x))}</div>`);
}

function tools(){
 return head("Outils","Capacités disponibles")+
 `<div class="grid">
  ${["noop","system_status","memory_read","memory_write","http_get"].map(x=>`
   <div class="card"><div class="badge ok">Disponible</div><h3>${x}</h3><p>Outil enregistré dans le moteur d'exécution de Gaïrus.</p></div>
  `).join("")}
 </div>`;
}

function events(){
 return head("Activité","Journal du moteur")+
 list(state.data.events,x=>`
  <div><div class="itemTitle">${esc(x.message||x.event_type)}</div><div class="meta">${esc(x.event_type||"")} · ${esc(x.created_at||"")}</div></div>`);
}

function health(){
 const s=state.data.status||{};
 return head("Système","État du backend")+
 `<div class="grid">
  <div class="card"><div class="badge ok">Connecté</div><h3>Backend</h3><p>Gaïrus répond aux requêtes.</p></div>
  <div class="card"><div class="badge ok">Actif</div><h3>Moteur IA</h3><p>${esc(s.provider||s.brain||"automatique")}</p></div>
  <div class="card"><div class="badge ok">${state.data.missions.length}</div><h3>Missions</h3><p>Enregistrées.</p></div>
 </div>`;
}

function settings(){
 return head("Paramètres","Configuration serveur")+
 `<div class="card"><h3>Gaïrus</h3><p>Les clés API, les fournisseurs et les paramètres sensibles restent sur le serveur Render.</p></div>`;
}

function head(h,s){
 return `<div class="sectionHead"><h2>${h}</h2><span>${s||""}</span></div>`;
}

function badge(s){
 const c=s==="completed"||s==="done"?"ok":s==="waiting_approval"?"wait":"";
 return `<span class="badge ${c}">${esc(s||"pending")}</span>`;
}

function list(a,f){
 return `<div class="list">${a.length?a.map(f).join(""):`<div class="empty">Aucun élément.</div>`}</div>`;
}

async function createMission(){
 const title=document.querySelector("#missionTitle")?.value.trim();
 const objective=document.querySelector("#missionObjective")?.value.trim();

 if(!objective){
  alert("Indiquez l'objectif de la mission.");
  return;
 }

 try{
  await api("/autonomy/mission",{
   method:"POST",
   body:JSON.stringify({title:title||objective,objective})
  });
  await loadData();
  state.page="missions";
  location.hash="missions";
  render();
 }catch(e){alert(e.message)}
}

async function planMission(id){
 try{await api(`/autonomy/mission/${encodeURIComponent(id)}/plan`,{method:"POST"});await loadData()}
 catch(e){alert(e.message)}
}

async function runMission(id){
 try{await api(`/autonomy/mission/${encodeURIComponent(id)}/run`,{method:"POST"});await loadData()}
 catch(e){alert(e.message)}
}

async function approval(id,decision){
 try{
  await api(`/autonomy/approval/${encodeURIComponent(id)}/${decision}`,{method:"POST"});
  await loadData();
 }catch(e){alert(e.message)}
}

async function saveMemory(){
 const el=document.querySelector("#mem");
 if(!el)return;
 const content=el.value.trim();
 if(!content)return;

 try{
  await api("/memory",{method:"POST",body:JSON.stringify({content,memory:content})});
  await loadData();
  render();
 }catch(e){alert(e.message)}
}

async function newMissionPage(){
 state.page="missions";
 location.hash="missions";
 render();
 setTimeout(()=>document.querySelector("#missionObjective")?.focus(),50);
}

document.addEventListener("click",async e=>{
 const page=e.target.closest("[data-page]");
 if(page){
  state.page=page.dataset.page;
  location.hash=state.page;
  document.querySelector("#side")?.classList.remove("open");
  render();
  if(state.page!=="chat")await loadData();
  return;
 }

 const fill=e.target.closest("[data-fill]");
 if(fill){
  const input=document.querySelector("#chatInput");
  if(input){input.value=fill.dataset.fill;input.focus()}
  return;
 }

 const action=e.target.closest("[data-action]");
 if(!action)return;

 switch(action.dataset.action){
  case"menu":
   document.querySelector("#side")?.classList.toggle("open");
   break;
  case"new-mission":
  case"create-mission":
   await newMissionPage();
   break;
  case"create-mission-form":
   await createMission();
   break;
  case"plan":
   await planMission(action.dataset.id);
   break;
  case"run":
   await runMission(action.dataset.id);
   break;
  case"approve":
   await approval(action.dataset.id,"approve");
   break;
  case"reject":
   await approval(action.dataset.id,"reject");
   break;
  case"save-memory":
   await saveMemory();
   break;
 }
});

window.addEventListener("hashchange",()=>{
 state.page=location.hash.slice(1)||"chat";
 render();
 loadData();
});

render();
loadData();
setInterval(loadData,15000);
