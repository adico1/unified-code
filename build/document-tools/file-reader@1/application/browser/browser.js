const ui={"actions":{"read-resource":{"mode":"request","request":{"action":"read","path":{"$control":"reader-path"}}}},"bindings":{"error":{"property":"text","target":"reader-error"},"result":[{"property":"value","source":"output.content","target":"reader-content"},{"property":"text","source":"output.encoding","target":"reader-encoding"},{"property":"text","source":"output.size","target":"reader-size"},{"property":"text","source":"output.sha256","target":"reader-hash"},{"property":"text","source":"output.empty","target":"reader-empty"}],"root":{"property":"text","target":"reader-root"},"status":{"failure":"Read failed","property":"text","success":"Read complete","target":"reader-status"}},"keyboard":[{"action":"read-resource","key":"Enter"}],"layout":{"sections":[{"components":[{"accessible_name":"Authorized root","id":"reader-root","label":"Authorized root","type":"label"},{"accessible_name":"File path","id":"reader-path","label":"Relative file path","placeholder":"message.txt","type":"file_path"},{"accessible_name":"Read file","action":"read-resource","id":"reader-read","label":"Read","primary":true,"type":"button"},{"accessible_name":"Read status","id":"reader-status","label":"Status","type":"status"},{"accessible_name":"Read error","id":"reader-error","label":"Error","type":"output"}],"id":"reader-input","title":"Authorized file"},{"components":[{"accessible_name":"File content","id":"reader-content","label":"Content","readonly":true,"type":"textarea"},{"accessible_name":"File encoding","id":"reader-encoding","label":"Encoding","type":"output"},{"accessible_name":"File size","id":"reader-size","label":"File size","type":"output"},{"accessible_name":"File SHA-256","id":"reader-hash","label":"SHA-256","type":"output"},{"accessible_name":"Empty file state","id":"reader-empty","label":"Empty file","type":"output"}],"id":"reader-result","title":"Content and identity","wide":true}]},"page":{"description":"Read a text file inside the authorized root and verify its metadata.","id":"reader-workbench","requires_root":true,"title":"File Reader"},"proof":{"expected_error":"resource-missing","fixtures":[{"path":"message.txt","text":"hello\n"}],"steps":[{"control":"reader-read","expect":{"equals":"hello","target":"reader-content"},"set":{"reader-path":"message.txt"}},{"control":"reader-read","expect":{"equals":"resource-missing","target":"reader-error"},"set":{"reader-path":"empty.txt"}},{"expect":{"equals":"5891b5b5","target":"reader-hash"},"keyboard":"Enter","set":{"reader-path":"message.txt"}}]},"responsive":{"breakpoint_px":760},"theme":{"background":"#08111f","danger":"#ff8f8f","muted":"#a9bdd2","primary":"#62d6c8","surface":"#10243b","text":"#f2f7ff"}};
const generatedIdentity="c75ff261bf661d44075ad02c3e363c49f6e4d4c8b755208a40b5455f3fece6a0";
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
