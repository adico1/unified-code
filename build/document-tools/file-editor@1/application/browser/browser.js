const ui={"actions":{"append-content":{"mode":"request","request":{"action":"append","path":{"$control":"editor-path"},"save":false,"value":{"$control":"editor-value"}}},"delete-content":{"mode":"request","request":{"action":"delete","count":{"$number":"editor-count"},"index":{"$number":"editor-index"},"path":{"$control":"editor-path"},"save":false}},"insert-content":{"mode":"request","request":{"action":"insert","index":{"$number":"editor-index"},"path":{"$control":"editor-path"},"save":false,"value":{"$control":"editor-value"}}},"load-file":{"mode":"request","request":{"action":"read","path":{"$control":"editor-path"}}},"preview-content":{"mode":"request","request":{"action":"write","path":{"$control":"editor-path"},"save":false,"value":{"$control":"editor-content"}}},"replace-content":{"mode":"request","request":{"action":"replace","match":{"$control":"editor-match"},"path":{"$control":"editor-path"},"save":false,"value":{"$control":"editor-value"}}},"save-content":{"mode":"request","request":{"action":"write","path":{"$control":"editor-path"},"save":true,"value":{"$control":"editor-content"}}}},"bindings":{"error":{"property":"text","target":"editor-error"},"result":[{"property":"value","source":"output.content","target":"editor-content"}],"root":{"property":"text","target":"editor-root"},"status":{"failure":"Operation failed; original preserved","property":"text","success":"Operation complete","target":"editor-status"}},"keyboard":[{"action":"save-content","key":"s"}],"layout":{"sections":[{"components":[{"accessible_name":"Authorized root","id":"editor-root","label":"Authorized root","type":"label"},{"accessible_name":"File path","id":"editor-path","label":"Relative file path","placeholder":"draft.txt","type":"file_path"},{"accessible_name":"Load file","action":"load-file","id":"editor-load","label":"Load","primary":true,"type":"button"},{"accessible_name":"Editor status","id":"editor-status","label":"Saved or unsaved status","type":"status"},{"accessible_name":"Editor error","id":"editor-error","label":"Validation or persistence error","type":"output"}],"id":"editor-file","title":"File"},{"components":[{"accessible_name":"Editable file content","id":"editor-content","label":"Editable content","type":"textarea"},{"accessible_name":"Text to replace","id":"editor-match","label":"Replace text","type":"text"},{"accessible_name":"Replacement or inserted text","id":"editor-value","label":"Change text","type":"text"},{"accessible_name":"Edit index","id":"editor-index","label":"Index","type":"number","value":0},{"accessible_name":"Delete count","id":"editor-count","label":"Delete count","type":"number","value":1},{"accessible_name":"Preview changes","action":"preview-content","id":"editor-preview","label":"Preview","type":"button"},{"accessible_name":"Save file","action":"save-content","id":"editor-save","label":"Save","primary":true,"type":"button"},{"accessible_name":"Replace text","action":"replace-content","id":"editor-replace","label":"Replace","type":"button"},{"accessible_name":"Append text","action":"append-content","id":"editor-append","label":"Append","type":"button"},{"accessible_name":"Insert text","action":"insert-content","id":"editor-insert","label":"Insert","type":"button"},{"accessible_name":"Delete text","action":"delete-content","id":"editor-delete","label":"Delete","type":"button"}],"id":"editor-content-panel","title":"Document","wide":true}]},"page":{"description":"Load, preview, and atomically save text inside the authorized root.","id":"editor-workbench","requires_root":true,"title":"File Editor"},"proof":{"expected_error":"resource-missing","fixtures":[{"path":"draft.txt","text":"alpha beta\n"}],"steps":[{"control":"editor-load","expect":{"equals":"alpha beta","target":"editor-content"},"set":{"editor-path":"draft.txt"}},{"control":"editor-preview","expect":{"equals":"gamma delta","target":"editor-content"},"set":{"editor-content":"gamma delta\n"}},{"control":"editor-save","expect":{"equals":"Operation complete","target":"editor-status"}},{"control":"editor-load","expect":{"equals":"gamma delta","target":"editor-content"}},{"control":"editor-load","expect":{"equals":"resource-missing","target":"editor-error"},"set":{"editor-path":"missing.txt"}}]},"responsive":{"breakpoint_px":760},"theme":{"background":"#101018","danger":"#ff8585","muted":"#c2bed4","primary":"#a8e063","surface":"#202038","text":"#faf8ff"}};
const generatedIdentity="db241022586960286bacc2e1a149499e1f2461140823d7f920ed3ea7ca5e9ff7";
const dependencyIdentity=null;
const dependencyContract=null;
const capability="__UC_SESSION_CAPABILITY__";
const query=new URLSearchParams(window.location.search);
const proofMode=query.get("uc-proof")==="1";
const values={};
const requestLog=[];
const responseLog=[];
let latest=null;
let interactionCount=0;

function byId(id){return document.getElementById(id)}
function pathValue(value,path){
  return String(path||"").split(".").filter(Boolean).reduce((current,key)=>current==null?undefined:current[key],value);
}
function componentValue(id){
  const element=byId(id);
  if(!element)return undefined;
  if(element.type==="number")return element.value===""?null:Number(element.value);
  return element.value!==undefined?element.value:element.textContent;
}
function resolve(value){
  if(Array.isArray(value))return value.map(resolve);
  if(value&&typeof value==="object"){
    if(Object.prototype.hasOwnProperty.call(value,"$control"))return componentValue(value.$control);
    if(Object.prototype.hasOwnProperty.call(value,"$number"))return Number(componentValue(value.$number));
    if(Object.prototype.hasOwnProperty.call(value,"$state"))return pathValue(latest,value.$state);
    return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,resolve(item)]));
  }
  return value;
}
function stable(value){
  if(Array.isArray(value))return value.map(stable);
  if(value&&typeof value==="object")return Object.fromEntries(Object.keys(value).sort().map(key=>[key,stable(value[key])]));
  return value;
}
async function summarize(response){
  const canonical=JSON.stringify(stable(response));
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(canonical));
  return {sha256:[...new Uint8Array(digest)].map(item=>item.toString(16).padStart(2,"0")).join(""),state:response.state,error:response.error};
}
function setTarget(id,value,property="text"){
  const element=byId(id);
  if(!element)return;
  const rendered=value==null?"":(typeof value==="object"?JSON.stringify(value,null,2):String(value));
  if(element.tagName==="UL"){
    element.replaceChildren(...Object.values(value||{}).map(item=>{const node=document.createElement("li");node.textContent=typeof item==="object"?JSON.stringify(item):String(item);return node}));
    return;
  }
  if(element.tagName==="TABLE"){
    const rows=Array.isArray(value)?value:Object.entries(value||{}).map(([key,item])=>({key,value:item}));
    element.replaceChildren(...rows.map(row=>{const tr=document.createElement("tr");for(const item of Object.values(row)){const td=document.createElement("td");td.textContent=typeof item==="object"?JSON.stringify(item):String(item);tr.appendChild(td)}return tr}));
    return;
  }
  if(property==="value")element.value=rendered;else element.textContent=rendered;
}
function applyBindings(response){
  latest=response;
  for(const binding of ui.bindings.result){
    setTarget(binding.target,pathValue(response,binding.source),binding.property);
  }
  const error=response.error||"";
  setTarget(ui.bindings.error.target,error,ui.bindings.error.property);
  byId(ui.bindings.error.target).dataset.error=String(Boolean(error));
  setTarget(ui.bindings.status.target,error?ui.bindings.status.failure:ui.bindings.status.success,ui.bindings.status.property);
  draw(response.output);
}
async function requestApplication(request){
  requestLog.push(request);
  const response=await fetch("/api",{
    method:"POST",
    headers:{"Content-Type":"application/json","X-UC-Capability":capability},
    body:JSON.stringify(request)
  }).then(item=>item.json());
  responseLog.push(await summarize(response));
  applyBindings(response);
  return response;
}
async function invoke(name){
  const action=ui.actions[name];
  interactionCount+=1;
  if(action.mode==="append"){const target=byId(action.target);target.value+=String(action.value);target.dispatchEvent(new Event("input",{bubbles:true}));return}
  if(action.mode==="backspace"){const target=byId(action.target);target.value=target.value.slice(0,-1);target.dispatchEvent(new Event("input",{bubbles:true}));return}
  if(action.mode==="clear"){const target=byId(action.target);target.value=action.value||"";target.dispatchEvent(new Event("input",{bubbles:true}));return}
  if(action.mode==="toggle"){const target=byId(action.target);target.value=target.value===String(action.first)?String(action.second):String(action.first);return}
  return requestApplication(resolve(action.request));
}
function makeComponent(component){
  const wrap=document.createElement("div");
  wrap.className=component.class||"uc-control";
  const label=document.createElement("label");
  label.htmlFor=component.id;
  label.textContent=component.label;
  let element;
  if(component.type==="button"){
    element=document.createElement("button");element.type="button";element.textContent=component.label;
    if(component.primary)element.classList.add("uc-primary");
    element.addEventListener("click",()=>{element._ucPending=invoke(component.action)});
  }else if(component.type==="textarea"){
    element=document.createElement("textarea");
  }else if(component.type==="select"){
    element=document.createElement("select");
    for(const option of component.options){const node=document.createElement("option");node.value=option.value;node.textContent=option.label;element.appendChild(node)}
  }else if(component.type==="output"||component.type==="status"){
    element=document.createElement("output");element.dataset.kind=component.type;
  }else if(component.type==="canvas"){
    element=document.createElement("canvas");element.width=component.width;element.height=component.height;
  }else if(component.type==="list"){
    element=document.createElement("ul");
  }else if(component.type==="table"){
    element=document.createElement("table");
  }else if(component.type==="label"){
    element=document.createElement("output");
  }else{
    element=document.createElement("input");element.type=component.type==="number"?"number":"text";
  }
  element.id=component.id;element.setAttribute("aria-label",component.accessible_name||component.label);
  if(component.placeholder)element.placeholder=component.placeholder;
  if(component.value!==undefined)element.value=String(component.value);
  if(component.derived==="export_identity")element.value=generatedIdentity;
  if(component.derived==="dependency_identity")element.value=dependencyIdentity||"unavailable";
  if(String(component.derived||"").startsWith("dependency_contract.")){
    const value=pathValue(dependencyContract,component.derived.slice("dependency_contract.".length));
    element.value=Array.isArray(value)?value.join(" through "):String(value);
  }
  if(component.readonly)element.readOnly=true;
  if(component.type!=="button"&&component.type!=="canvas")wrap.appendChild(label);
  wrap.appendChild(element);
  return wrap;
}
function draw(output){
  const scene=ui.bindings.canvas;
  if(!scene)return;
  const canvas=byId(scene.target);if(!canvas||!output)return;
  const context=canvas.getContext("2d");
  context.fillStyle=scene.background;context.fillRect(0,0,canvas.width,canvas.height);
  for(const shape of scene.shapes){
    const items=shape.collection?Object.values(pathValue(output,shape.collection)||{}):[pathValue(output,shape.path)];
    context.fillStyle=shape.color;
    for(const item of items.filter(Boolean))context.fillRect(item[shape.x]*(scene.scale_x||1),item[shape.y]*(scene.scale_y||1),item[shape.width]*(scene.scale_x||1),item[shape.height]*(scene.scale_y||1));
  }
  for(const text of scene.text){
    const value=pathValue(output,text.path)||{};context.fillStyle=text.color;
    context.fillText(Object.values(value).join(text.join),text.x,text.y);
  }
}
function mount(){
  document.title=ui.page.title;
  const root=byId("application");
  const header=document.createElement("header");header.innerHTML=`<h1>${ui.page.title}</h1><p>${ui.page.description}</p>`;
  root.appendChild(header);
  const grid=document.createElement("div");grid.className="uc-grid";root.appendChild(grid);
  for(const section of ui.layout.sections){
    const node=document.createElement("section");node.id=section.id;if(section.wide)node.classList.add("uc-wide");
    const heading=document.createElement("h2");heading.textContent=section.title;node.appendChild(heading);
    const components=document.createElement("div");components.className=section.class||"";
    for(const component of section.components)components.appendChild(makeComponent(component));
    node.appendChild(components);grid.appendChild(node);
  }
  setTarget(ui.bindings.root.target,document.documentElement.dataset.ucRoot||"authorized runtime root",ui.bindings.root.property);
  for(const binding of ui.keyboard)document.addEventListener("keydown",event=>{
    if(event.key===binding.key){event.preventDefault();document._ucPending=invoke(binding.action)}
  });
  if(ui.automation&&!proofMode)setInterval(()=>{
    if(pathValue(latest,ui.automation.while)===true)invoke(ui.automation.action);
  },ui.automation.interval_ms);
}
function nonblank(){
  const text=document.body.innerText.replace(/\s+/g," ").trim();
  const canvas=ui.bindings.canvas&&byId(ui.bindings.canvas.target);
  let pixels=0;
  if(canvas){const data=canvas.getContext("2d").getImageData(0,0,canvas.width,canvas.height).data;for(let i=0;i<data.length;i+=4)if(data[i]||data[i+1]||data[i+2]||data[i+3])pixels+=1}
  return {text_length:text.length,canvas_pixels:pixels};
}
async function runProof(){
  const assertions=[];
  for(const step of ui.proof.steps){
    for(const [id,value] of Object.entries(step.set||{})){byId(id).value=String(value);byId(id).dispatchEvent(new Event("input",{bubbles:true}))}
    if(step.keyboard){
      document.dispatchEvent(new KeyboardEvent("keydown",{key:step.keyboard,bubbles:true}));
      await document._ucPending;
    }else{
      const control=byId(step.control);control.click();await control._ucPending;
    }
    await new Promise(resolve=>setTimeout(resolve,step.wait_ms||10));
    const actual=componentValue(step.expect.target);
    assertions.push({target:step.expect.target,actual,expected:step.expect.equals,ok:String(actual).includes(String(step.expect.equals))});
  }
  const controls=[...document.querySelectorAll("input,textarea,select,button,canvas,output")];
  const result={
    title:ui.page.title,
    controls:controls.map(item=>item.id),
    accessible:controls.every(item=>Boolean(item.getAttribute("aria-label"))),
    interactions:interactionCount,
    requests:requestLog,
    responses:responseLog,
    assertions,
    rendered:nonblank(),
    error_presented:!ui.proof.expected_error||responseLog.some(item=>item.error===ui.proof.expected_error),
    window_created:typeof window==="object"
  };
  await fetch("/shutdown",{method:"POST",headers:{"X-UC-Capability":capability}});
  const encoded=btoa(unescape(encodeURIComponent(JSON.stringify(result))));
  byId("uc-proof").textContent=JSON.stringify(result);
  document.title="UC_PROOF_"+encoded;
}
mount();
if(proofMode)runProof();
