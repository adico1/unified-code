const ui={"actions":{"append-0":{"mode":"append","target":"calculator-display","value":"0"},"append-1":{"mode":"append","target":"calculator-display","value":"1"},"append-2":{"mode":"append","target":"calculator-display","value":"2"},"append-3":{"mode":"append","target":"calculator-display","value":"3"},"append-4":{"mode":"append","target":"calculator-display","value":"4"},"append-5":{"mode":"append","target":"calculator-display","value":"5"},"append-6":{"mode":"append","target":"calculator-display","value":"6"},"append-7":{"mode":"append","target":"calculator-display","value":"7"},"append-8":{"mode":"append","target":"calculator-display","value":"8"},"append-9":{"mode":"append","target":"calculator-display","value":"9"},"append-add":{"mode":"append","target":"calculator-display","value":"+"},"append-divide":{"mode":"append","target":"calculator-display","value":"/"},"append-left":{"mode":"append","target":"calculator-display","value":"("},"append-multiply":{"mode":"append","target":"calculator-display","value":"*"},"append-power":{"mode":"append","target":"calculator-display","value":"^"},"append-remainder":{"mode":"append","target":"calculator-display","value":"%"},"append-right":{"mode":"append","target":"calculator-display","value":")"},"append-subtract":{"mode":"append","target":"calculator-display","value":"-"},"backspace-expression":{"mode":"backspace","target":"calculator-display"},"clear-expression":{"mode":"clear","target":"calculator-display","value":""},"evaluate-expression":{"mode":"request","request":{"expression":{"$control":"calculator-display"}}}},"bindings":{"error":{"property":"text","target":"calculator-error"},"result":[{"property":"text","source":"output.result","target":"calculator-result"}],"root":{"property":"text","target":"calculator-root"},"status":{"failure":"Calculation rejected","property":"text","success":"Calculation complete","target":"calculator-status"}},"keyboard":[{"action":"evaluate-expression","key":"Enter"},{"action":"backspace-expression","key":"Backspace"},{"action":"clear-expression","key":"Escape"}],"layout":{"sections":[{"components":[{"accessible_name":"Runtime root","id":"calculator-root","label":"Runtime root","type":"label"},{"accessible_name":"Generated math library identity","derived":"dependency_identity","id":"calculator-library","label":"Math library identity","readonly":true,"type":"label"},{"accessible_name":"Inherited bounded integer range","derived":"dependency_contract.range","id":"calculator-range","label":"Bounded range","readonly":true,"type":"label"},{"accessible_name":"Inherited division rule","derived":"dependency_contract.result_rules.division","id":"calculator-division","label":"Division rule","readonly":true,"type":"label"},{"accessible_name":"Calculator status","id":"calculator-status","label":"Status","type":"status"},{"accessible_name":"Calculator error","id":"calculator-error","label":"Error","type":"output"}],"id":"calculator-identity","title":"Dependency"},{"class":"uc-keypad","components":[{"accessible_name":"Expression and result display","id":"calculator-display","label":"Expression","type":"text"},{"accessible_name":"Left parenthesis","action":"append-left","id":"calculator-left","label":"(","type":"button"},{"accessible_name":"Right parenthesis","action":"append-right","id":"calculator-right","label":")","type":"button"},{"accessible_name":"Clear expression","action":"clear-expression","id":"calculator-clear","label":"Clear","type":"button"},{"accessible_name":"Backspace","action":"backspace-expression","id":"calculator-backspace","label":"Backspace","type":"button"},{"accessible_name":"Digit zero","action":"append-0","id":"calculator-0","label":"0","type":"button"},{"accessible_name":"Digit one","action":"append-1","id":"calculator-1","label":"1","type":"button"},{"accessible_name":"Digit two","action":"append-2","id":"calculator-2","label":"2","type":"button"},{"accessible_name":"Digit three","action":"append-3","id":"calculator-3","label":"3","type":"button"},{"accessible_name":"Digit four","action":"append-4","id":"calculator-4","label":"4","type":"button"},{"accessible_name":"Digit five","action":"append-5","id":"calculator-5","label":"5","type":"button"},{"accessible_name":"Digit six","action":"append-6","id":"calculator-6","label":"6","type":"button"},{"accessible_name":"Digit seven","action":"append-7","id":"calculator-7","label":"7","type":"button"},{"accessible_name":"Digit eight","action":"append-8","id":"calculator-8","label":"8","type":"button"},{"accessible_name":"Digit nine","action":"append-9","id":"calculator-9","label":"9","type":"button"},{"accessible_name":"Add operator","action":"append-add","id":"calculator-add","label":"+","type":"button"},{"accessible_name":"Subtract operator","action":"append-subtract","id":"calculator-subtract","label":"−","type":"button"},{"accessible_name":"Multiply operator","action":"append-multiply","id":"calculator-multiply","label":"×","type":"button"},{"accessible_name":"Divide operator","action":"append-divide","id":"calculator-divide","label":"÷","type":"button"},{"accessible_name":"Remainder operator","action":"append-remainder","id":"calculator-remainder","label":"%","type":"button"},{"accessible_name":"Power operator","action":"append-power","id":"calculator-power","label":"^","type":"button"},{"accessible_name":"Evaluate expression","action":"evaluate-expression","id":"calculator-equals","label":"=","primary":true,"type":"button"},{"accessible_name":"Calculation result","id":"calculator-result","label":"Result","type":"output"}],"id":"calculator-controls","title":"Expression","wide":true}]},"page":{"description":"Editable infix expressions over -1000000 through 1000000; division always floors.","id":"calculator-desk","requires_root":false,"title":"Bounded Integer Expression Calculator"},"proof":{"expected_error":"zero-divisor","fixtures":[],"steps":[{"control":"calculator-left","expect":{"equals":"(","target":"calculator-display"}},{"control":"calculator-2","expect":{"equals":"(2","target":"calculator-display"}},{"control":"calculator-add","expect":{"equals":"(2+","target":"calculator-display"}},{"control":"calculator-3","expect":{"equals":"(2+3","target":"calculator-display"}},{"control":"calculator-right","expect":{"equals":"(2+3)","target":"calculator-display"}},{"control":"calculator-multiply","expect":{"equals":"(2+3)*","target":"calculator-display"}},{"control":"calculator-4","expect":{"equals":"(2+3)*4","target":"calculator-display"}},{"control":"calculator-equals","expect":{"equals":"20","target":"calculator-result"}},{"control":"calculator-clear","expect":{"equals":"","target":"calculator-display"}},{"control":"calculator-8","expect":{"equals":"8","target":"calculator-display"}},{"control":"calculator-remainder","expect":{"equals":"8%","target":"calculator-display"}},{"control":"calculator-3","expect":{"equals":"8%3","target":"calculator-display"}},{"control":"calculator-equals","expect":{"equals":"2","target":"calculator-result"}},{"control":"calculator-clear","expect":{"equals":"","target":"calculator-display"}},{"control":"calculator-3","expect":{"equals":"3","target":"calculator-display"}},{"control":"calculator-power","expect":{"equals":"3^","target":"calculator-display"}},{"control":"calculator-4","expect":{"equals":"3^4","target":"calculator-display"}},{"control":"calculator-equals","expect":{"equals":"81","target":"calculator-result"}},{"expect":{"equals":"zero-divisor","target":"calculator-error"},"keyboard":"Enter","set":{"calculator-display":"9/0"}}]},"responsive":{"breakpoint_px":680},"theme":{"background":"#11131a","danger":"#ff7f8f","muted":"#b8bdca","primary":"#ffcc66","surface":"#232631","text":"#ffffff"}};
const generatedIdentity="02aebde7505be9dd6d8a10814d676b8978f99d559ec4b110fdec589c3c4bd2c5";
const dependencyIdentity="e962f575d085938a4a9ddf03173f320fc28951c14ae02d4cc284e3501dffe167";
const dependencyContract={"exported_contract":"part(thing)->thing","numeric_type":"integer","operations":["absolute","add","divide","maximum","minimum","multiply","negate","power","remainder","subtract","sum"],"range":[-1000000,1000000],"result_rules":{"division":"floor","overflow":"reject"}};
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
