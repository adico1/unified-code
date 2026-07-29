"""Generic seed-defined graphical interface specialization for Application v3."""

from __future__ import annotations

import json


COMPONENT_TYPES = frozenset(
    {
        "button",
        "canvas",
        "file_path",
        "label",
        "list",
        "number",
        "output",
        "select",
        "status",
        "table",
        "text",
        "textarea",
    }
)
ACTION_MODES = frozenset({"append", "backspace", "clear", "request", "toggle"})


def validate_ui(ui):
    if not isinstance(ui, dict):
        return ["ui:not-object"]
    required = {
        "page",
        "theme",
        "layout",
        "actions",
        "bindings",
        "keyboard",
        "responsive",
        "proof",
    }
    errors = [f"ui.missing:{key}" for key in sorted(required - set(ui))]
    errors.extend(
        f"ui.unknown:{key}" for key in sorted(set(ui) - (required | {"automation"}))
    )
    if errors:
        return errors
    page = ui["page"]
    if (
        not isinstance(page, dict)
        or not all(isinstance(page.get(key), str) and page[key] for key in ("id", "title", "description"))
        or not isinstance(page.get("requires_root"), bool)
    ):
        errors.append("ui.page")
    theme = ui["theme"]
    if not isinstance(theme, dict) or not all(
        isinstance(theme.get(key), str)
        for key in ("background", "surface", "text", "muted", "primary", "danger")
    ):
        errors.append("ui.theme")
    layout = ui["layout"]
    sections = layout.get("sections") if isinstance(layout, dict) else None
    components = []
    if not isinstance(sections, list) or not sections:
        errors.append("ui.layout")
    else:
        for section_index, section in enumerate(sections):
            if (
                not isinstance(section, dict)
                or not isinstance(section.get("id"), str)
                or not isinstance(section.get("title"), str)
                or not isinstance(section.get("components"), list)
            ):
                errors.append(f"ui.layout.sections[{section_index}]")
                continue
            components.extend(section["components"])
    identifiers = []
    for index, component in enumerate(components):
        if (
            not isinstance(component, dict)
            or not isinstance(component.get("id"), str)
            or component.get("type") not in COMPONENT_TYPES
            or not isinstance(component.get("label"), str)
        ):
            errors.append(f"ui.component[{index}]")
            continue
        identifiers.append(component["id"])
        if component["type"] == "select" and not isinstance(component.get("options"), list):
            errors.append(f"ui.component[{index}].options")
        if component["type"] == "button" and not isinstance(component.get("action"), str):
            errors.append(f"ui.component[{index}].action")
    if len(identifiers) != len(set(identifiers)):
        errors.append("ui.component:duplicate-id")
    actions = ui["actions"]
    if not isinstance(actions, dict) or not actions:
        errors.append("ui.actions")
    else:
        for name, action in actions.items():
            if not isinstance(name, str) or not isinstance(action, dict):
                errors.append("ui.action")
                continue
            if action.get("mode") not in ACTION_MODES:
                errors.append(f"ui.action.{name}.mode")
            if action.get("mode") == "request" and not isinstance(action.get("request"), dict):
                errors.append(f"ui.action.{name}.request")
            if action.get("mode") in {"append", "backspace", "clear", "toggle"} and action.get("target") not in identifiers:
                errors.append(f"ui.action.{name}.target")
    button_actions = {
        component.get("action")
        for component in components
        if isinstance(component, dict) and component.get("type") == "button"
    }
    if isinstance(actions, dict):
        errors.extend(
            f"ui.button:unknown-action:{name}"
            for name in sorted(button_actions - set(actions))
        )
    bindings = ui["bindings"]
    if (
        not isinstance(bindings, dict)
        or set(("result", "error", "status", "root")) - set(bindings)
        or set(bindings) - {"result", "error", "status", "root", "canvas"}
    ):
        errors.append("ui.bindings")
    keyboard = ui["keyboard"]
    if not isinstance(keyboard, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("key"), str)
        or item.get("action") not in actions
        for item in keyboard
    ):
        errors.append("ui.keyboard")
    responsive = ui["responsive"]
    if (
        not isinstance(responsive, dict)
        or not isinstance(responsive.get("breakpoint_px"), int)
        or responsive["breakpoint_px"] <= 0
    ):
        errors.append("ui.responsive")
    proof = ui["proof"]
    if (
        not isinstance(proof, dict)
        or not isinstance(proof.get("fixtures"), list)
        or not isinstance(proof.get("steps"), list)
        or len(proof["steps"]) < 3
        or not isinstance(proof.get("expected_error"), str)
    ):
        errors.append("ui.proof")
    automation = ui.get("automation")
    if automation is not None and (
        not isinstance(automation, dict)
        or automation.get("action") not in actions
        or not isinstance(automation.get("interval_ms"), int)
        or automation["interval_ms"] <= 0
        or not isinstance(automation.get("while"), str)
    ):
        errors.append("ui.automation")
    return sorted(errors)


def html_source():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Unified application</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main id="application" aria-live="polite"></main>
  <output id="uc-proof" aria-label="Verification evidence" hidden></output>
  <script src="browser.js"></script>
</body>
</html>
"""


def css_source(ui):
    theme = ui["theme"]
    breakpoint = ui["responsive"]["breakpoint_px"]
    return f""":root{{
  color-scheme:dark;
  --background:{theme["background"]};
  --surface:{theme["surface"]};
  --text:{theme["text"]};
  --muted:{theme["muted"]};
  --primary:{theme["primary"]};
  --danger:{theme["danger"]};
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif
}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;background:linear-gradient(145deg,var(--background),var(--surface));color:var(--text)}}
main{{width:min(1080px,calc(100% - 2rem));margin:0 auto;padding:2.5rem 0 4rem}}
header{{margin-bottom:1.5rem}}h1{{margin:.2rem 0;font-size:clamp(1.8rem,5vw,3rem)}}header p{{color:var(--muted);max-width:70ch}}
.uc-grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:1rem}}
section{{grid-column:span 6;background:color-mix(in srgb,var(--surface) 90%,white 10%);border:1px solid color-mix(in srgb,var(--muted) 25%,transparent);border-radius:1rem;padding:1rem;box-shadow:0 18px 55px #0004}}
section.uc-wide{{grid-column:1/-1}}h2{{font-size:1rem;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}}
.uc-control{{display:flex;flex-direction:column;gap:.4rem;margin:.75rem 0}}label{{font-weight:650}}
input,textarea,select,button,output{{font:inherit;border-radius:.65rem;border:1px solid color-mix(in srgb,var(--muted) 45%,transparent)}}
input,textarea,select{{width:100%;padding:.75rem;background:var(--background);color:var(--text)}}textarea{{min-height:13rem;resize:vertical}}
button{{padding:.72rem 1rem;background:color-mix(in srgb,var(--surface) 75%,white 8%);color:var(--text);cursor:pointer;font-weight:700}}
button:hover,button:focus-visible{{outline:3px solid color-mix(in srgb,var(--primary) 55%,transparent);outline-offset:2px}}
button.uc-primary{{background:var(--primary);color:#081018}}.uc-actions{{display:flex;flex-wrap:wrap;gap:.55rem}}
output{{display:block;min-height:2.8rem;padding:.75rem;background:var(--background);white-space:pre-wrap;overflow-wrap:anywhere}}
[data-kind=status]{{color:var(--muted)}}[data-error=true]{{color:var(--danger);border-color:var(--danger)}}
canvas{{display:block;width:100%;height:auto;aspect-ratio:5/3;background:var(--background);border-radius:.75rem}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:.55rem;border-bottom:1px solid var(--muted)}}
.uc-keypad{{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem}}.uc-keypad button{{width:100%}}
@media(max-width:{breakpoint}px){{main{{width:min(100% - 1rem,1080px);padding-top:1rem}}section{{grid-column:1/-1}}}}
"""


def browser_source(
    specification,
    export_identity,
    dependency_identity,
    dependency_contract=None,
):
    encoded = json.dumps(specification["ui"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return f"""const ui={encoded};
const generatedIdentity={json.dumps(export_identity)};
const dependencyIdentity={json.dumps(dependency_identity)};
const dependencyContract={json.dumps(dependency_contract, ensure_ascii=False, separators=(",", ":"), sort_keys=True)};
const capability="__UC_SESSION_CAPABILITY__";
const query=new URLSearchParams(window.location.search);
const proofMode=query.get("uc-proof")==="1";
const values={{}};
const requestLog=[];
const responseLog=[];
let latest=null;
let interactionCount=0;

function byId(id){{return document.getElementById(id)}}
function pathValue(value,path){{
  return String(path||"").split(".").filter(Boolean).reduce((current,key)=>current==null?undefined:current[key],value);
}}
function componentValue(id){{
  const element=byId(id);
  if(!element)return undefined;
  if(element.type==="number")return element.value===""?null:Number(element.value);
  return element.value!==undefined?element.value:element.textContent;
}}
function resolve(value){{
  if(Array.isArray(value))return value.map(resolve);
  if(value&&typeof value==="object"){{
    if(Object.prototype.hasOwnProperty.call(value,"$control"))return componentValue(value.$control);
    if(Object.prototype.hasOwnProperty.call(value,"$number"))return Number(componentValue(value.$number));
    if(Object.prototype.hasOwnProperty.call(value,"$state"))return pathValue(latest,value.$state);
    return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,resolve(item)]));
  }}
  return value;
}}
function stable(value){{
  if(Array.isArray(value))return value.map(stable);
  if(value&&typeof value==="object")return Object.fromEntries(Object.keys(value).sort().map(key=>[key,stable(value[key])]));
  return value;
}}
async function summarize(response){{
  const canonical=JSON.stringify(stable(response));
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(canonical));
  return {{sha256:[...new Uint8Array(digest)].map(item=>item.toString(16).padStart(2,"0")).join(""),state:response.state,error:response.error}};
}}
function setTarget(id,value,property="text"){{
  const element=byId(id);
  if(!element)return;
  const rendered=value==null?"":(typeof value==="object"?JSON.stringify(value,null,2):String(value));
  if(element.tagName==="UL"){{
    element.replaceChildren(...Object.values(value||{{}}).map(item=>{{const node=document.createElement("li");node.textContent=typeof item==="object"?JSON.stringify(item):String(item);return node}}));
    return;
  }}
  if(element.tagName==="TABLE"){{
    const rows=Array.isArray(value)?value:Object.entries(value||{{}}).map(([key,item])=>({{key,value:item}}));
    element.replaceChildren(...rows.map(row=>{{const tr=document.createElement("tr");for(const item of Object.values(row)){{const td=document.createElement("td");td.textContent=typeof item==="object"?JSON.stringify(item):String(item);tr.appendChild(td)}}return tr}}));
    return;
  }}
  if(property==="value")element.value=rendered;else element.textContent=rendered;
}}
function applyBindings(response){{
  latest=response;
  for(const binding of ui.bindings.result){{
    setTarget(binding.target,pathValue(response,binding.source),binding.property);
  }}
  const error=response.error||"";
  setTarget(ui.bindings.error.target,error,ui.bindings.error.property);
  byId(ui.bindings.error.target).dataset.error=String(Boolean(error));
  setTarget(ui.bindings.status.target,error?ui.bindings.status.failure:ui.bindings.status.success,ui.bindings.status.property);
  draw(response.output);
}}
async function requestApplication(request){{
  requestLog.push(request);
  const response=await fetch("/api",{{
    method:"POST",
    headers:{{"Content-Type":"application/json","X-UC-Capability":capability}},
    body:JSON.stringify(request)
  }}).then(item=>item.json());
  responseLog.push(await summarize(response));
  applyBindings(response);
  return response;
}}
async function invoke(name){{
  const action=ui.actions[name];
  interactionCount+=1;
  if(action.mode==="append"){{const target=byId(action.target);target.value+=String(action.value);target.dispatchEvent(new Event("input",{{bubbles:true}}));return}}
  if(action.mode==="backspace"){{const target=byId(action.target);target.value=target.value.slice(0,-1);target.dispatchEvent(new Event("input",{{bubbles:true}}));return}}
  if(action.mode==="clear"){{const target=byId(action.target);target.value=action.value||"";target.dispatchEvent(new Event("input",{{bubbles:true}}));return}}
  if(action.mode==="toggle"){{const target=byId(action.target);target.value=target.value===String(action.first)?String(action.second):String(action.first);return}}
  return requestApplication(resolve(action.request));
}}
function makeComponent(component){{
  const wrap=document.createElement("div");
  wrap.className=component.class||"uc-control";
  const label=document.createElement("label");
  label.htmlFor=component.id;
  label.textContent=component.label;
  let element;
  if(component.type==="button"){{
    element=document.createElement("button");element.type="button";element.textContent=component.label;
    if(component.primary)element.classList.add("uc-primary");
    element.addEventListener("click",()=>{{element._ucPending=invoke(component.action)}});
  }}else if(component.type==="textarea"){{
    element=document.createElement("textarea");
  }}else if(component.type==="select"){{
    element=document.createElement("select");
    for(const option of component.options){{const node=document.createElement("option");node.value=option.value;node.textContent=option.label;element.appendChild(node)}}
  }}else if(component.type==="output"||component.type==="status"){{
    element=document.createElement("output");element.dataset.kind=component.type;
  }}else if(component.type==="canvas"){{
    element=document.createElement("canvas");element.width=component.width;element.height=component.height;
  }}else if(component.type==="list"){{
    element=document.createElement("ul");
  }}else if(component.type==="table"){{
    element=document.createElement("table");
  }}else if(component.type==="label"){{
    element=document.createElement("output");
  }}else{{
    element=document.createElement("input");element.type=component.type==="number"?"number":"text";
  }}
  element.id=component.id;element.setAttribute("aria-label",component.accessible_name||component.label);
  if(component.placeholder)element.placeholder=component.placeholder;
  if(component.value!==undefined)element.value=String(component.value);
  if(component.derived==="export_identity")element.value=generatedIdentity;
  if(component.derived==="dependency_identity")element.value=dependencyIdentity||"unavailable";
  if(String(component.derived||"").startsWith("dependency_contract.")){{
    const value=pathValue(dependencyContract,component.derived.slice("dependency_contract.".length));
    element.value=Array.isArray(value)?value.join(" through "):String(value);
  }}
  if(component.readonly)element.readOnly=true;
  if(component.type!=="button"&&component.type!=="canvas")wrap.appendChild(label);
  wrap.appendChild(element);
  return wrap;
}}
function draw(output){{
  const scene=ui.bindings.canvas;
  if(!scene)return;
  const canvas=byId(scene.target);if(!canvas||!output)return;
  const context=canvas.getContext("2d");
  context.fillStyle=scene.background;context.fillRect(0,0,canvas.width,canvas.height);
  for(const shape of scene.shapes){{
    const items=shape.collection?Object.values(pathValue(output,shape.collection)||{{}}):[pathValue(output,shape.path)];
    context.fillStyle=shape.color;
    for(const item of items.filter(Boolean))context.fillRect(item[shape.x]*(scene.scale_x||1),item[shape.y]*(scene.scale_y||1),item[shape.width]*(scene.scale_x||1),item[shape.height]*(scene.scale_y||1));
  }}
  for(const text of scene.text){{
    const value=pathValue(output,text.path)||{{}};context.fillStyle=text.color;
    context.fillText(Object.values(value).join(text.join),text.x,text.y);
  }}
}}
function mount(){{
  document.title=ui.page.title;
  const root=byId("application");
  const header=document.createElement("header");header.innerHTML=`<h1>${{ui.page.title}}</h1><p>${{ui.page.description}}</p>`;
  root.appendChild(header);
  const grid=document.createElement("div");grid.className="uc-grid";root.appendChild(grid);
  for(const section of ui.layout.sections){{
    const node=document.createElement("section");node.id=section.id;if(section.wide)node.classList.add("uc-wide");
    const heading=document.createElement("h2");heading.textContent=section.title;node.appendChild(heading);
    const components=document.createElement("div");components.className=section.class||"";
    for(const component of section.components)components.appendChild(makeComponent(component));
    node.appendChild(components);grid.appendChild(node);
  }}
  setTarget(ui.bindings.root.target,document.documentElement.dataset.ucRoot||"authorized runtime root",ui.bindings.root.property);
  for(const binding of ui.keyboard)document.addEventListener("keydown",event=>{{
    if(event.key===binding.key){{event.preventDefault();document._ucPending=invoke(binding.action)}}
  }});
  if(ui.automation&&!proofMode)setInterval(()=>{{
    if(pathValue(latest,ui.automation.while)===true)invoke(ui.automation.action);
  }},ui.automation.interval_ms);
}}
function nonblank(){{
  const text=document.body.innerText.replace(/\\s+/g," ").trim();
  const canvas=ui.bindings.canvas&&byId(ui.bindings.canvas.target);
  let pixels=0;
  if(canvas){{const data=canvas.getContext("2d").getImageData(0,0,canvas.width,canvas.height).data;for(let i=0;i<data.length;i+=4)if(data[i]||data[i+1]||data[i+2]||data[i+3])pixels+=1}}
  return {{text_length:text.length,canvas_pixels:pixels}};
}}
async function runProof(){{
  const assertions=[];
  for(const step of ui.proof.steps){{
    for(const [id,value] of Object.entries(step.set||{{}})){{byId(id).value=String(value);byId(id).dispatchEvent(new Event("input",{{bubbles:true}}))}}
    if(step.keyboard){{
      document.dispatchEvent(new KeyboardEvent("keydown",{{key:step.keyboard,bubbles:true}}));
      await document._ucPending;
    }}else{{
      const control=byId(step.control);control.click();await control._ucPending;
    }}
    await new Promise(resolve=>setTimeout(resolve,step.wait_ms||10));
    const actual=componentValue(step.expect.target);
    assertions.push({{target:step.expect.target,actual,expected:step.expect.equals,ok:String(actual).includes(String(step.expect.equals))}});
  }}
  const controls=[...document.querySelectorAll("input,textarea,select,button,canvas,output")];
  const result={{
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
  }};
  await fetch("/shutdown",{{method:"POST",headers:{{"X-UC-Capability":capability}}}});
  const encoded=btoa(unescape(encodeURIComponent(JSON.stringify(result))));
  byId("uc-proof").textContent=JSON.stringify(result);
  document.title="UC_PROOF_"+encoded;
}}
mount();
if(proofMode)runProof();
"""


def host_source(package, requires_root):
    return f'''"""Generated loopback-only GUI host boundary."""

import argparse
import json
import mimetypes
import secrets
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from .cli import execute

REQUIRES_ROOT = {requires_root!r}
MAXIMUM_REQUEST_BYTES = 1048576


def _response(connection, status, body, content_type):
    payload = body if isinstance(body, bytes) else body.encode("utf-8")
    headers = (
        "HTTP/1.1 " + status + "\\r\\n"
        "Content-Type: " + content_type + "\\r\\n"
        "Content-Length: " + str(len(payload)) + "\\r\\n"
        "Cache-Control: no-store\\r\\n"
        "Connection: close\\r\\n\\r\\n"
    ).encode("ascii")
    connection.sendall(headers + payload)


def _receive(connection):
    raw = b""
    while b"\\r\\n\\r\\n" not in raw and len(raw) <= MAXIMUM_REQUEST_BYTES:
        block = connection.recv(65536)
        if not block:
            break
        raw += block
    heading, _, body = raw.partition(b"\\r\\n\\r\\n")
    lines = heading.decode("iso-8859-1").split("\\r\\n")
    method, target, _ = lines[0].split(" ", 2)
    headers = dict(line.split(":", 1) for line in lines[1:] if ":" in line)
    length = int(headers.get("Content-Length", "0").strip())
    while len(body) < length and len(body) <= MAXIMUM_REQUEST_BYTES:
        body += connection.recv(min(65536, length - len(body)))
    return method, target.split("?", 1)[0], {{key.lower(): value.strip() for key, value in headers.items()}}, body[:length]


def _serve(connection, browser_root, authority_root, capability, stop):
    try:
        method, target, headers, body = _receive(connection)
        if method == "POST" and target in ("/api", "/shutdown"):
            if not secrets.compare_digest(headers.get("x-uc-capability", ""), capability):
                _response(connection, "403 Forbidden", '{{"error":"capability-required"}}', "application/json")
                return
            if target == "/shutdown":
                stop.set()
                _response(connection, "200 OK", '{{"stopped":true}}', "application/json")
                return
            if len(body) > MAXIMUM_REQUEST_BYTES:
                _response(connection, "413 Content Too Large", '{{"error":"request-too-large"}}', "application/json")
                return
            try:
                request = json.loads(body.decode("utf-8"))
            except (UnicodeError, ValueError):
                result = {{"state":"invalid","output":None,"error":"invalid-host-json","evidence":[]}}
            else:
                result = execute(request, str(authority_root))
            _response(connection, "200 OK", json.dumps(result, separators=(",", ":"), sort_keys=True), "application/json")
            return
        relative = "index.html" if target in ("/", "/index.html") else target.removeprefix("/")
        if relative not in ("index.html", "style.css", "browser.js"):
            _response(connection, "404 Not Found", "not found", "text/plain")
            return
        path = browser_root / relative
        payload = path.read_bytes()
        if relative == "browser.js":
            payload = payload.replace(b"__UC_SESSION_CAPABILITY__", capability.encode("ascii"))
        if relative == "index.html":
            payload = payload.replace(b"<html lang=\\"en\\">", ("<html lang=\\"en\\" data-uc-root=\\"" + str(authority_root).replace("&", "&amp;").replace('"', "&quot;") + "\\">").encode("utf-8"))
        _response(connection, "200 OK", payload, mimetypes.guess_type(relative)[0] or "application/octet-stream")
    except (OSError, TypeError, ValueError):
        try:
            _response(connection, "400 Bad Request", "bad request", "text/plain")
        except OSError:
            pass
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(prog={package!r} + "-gui")
    parser.add_argument("--root")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--proof", action="store_true")
    args = parser.parse_args(argv)
    if REQUIRES_ROOT and not args.root:
        parser.error("--root is required")
    authority_root = Path(args.root or ".").resolve(strict=True)
    browser_root = Path(__file__).resolve().parents[1] / "browser"
    capability = secrets.token_urlsafe(32)
    stop = threading.Event()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(16)
    server.settimeout(0.25)
    port = server.getsockname()[1]
    url = "http://127.0.0.1:" + str(port) + ("/?uc-proof=1" if args.proof else "/")
    sys.stdout.write(json.dumps({{"url": url, "host": "127.0.0.1", "port": port}}, separators=(",", ":"), sort_keys=True) + "\\n")
    sys.stdout.flush()
    if not args.no_open:
        webbrowser.open(url)
    try:
        while not stop.is_set():
            try:
                connection, address = server.accept()
            except socket.timeout:
                continue
            if address[0] != "127.0.0.1":
                connection.close()
                continue
            threading.Thread(target=_serve, args=(connection, browser_root, authority_root, capability, stop), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
    return 0
'''


def entry_source(package):
    return f'''#!/usr/bin/env python3
import sys
from pathlib import Path

installation = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(item) for item in sorted(installation.parent.iterdir()) if item.is_dir()]
sys.path.insert(0, str(installation))
from {package}.gui_host import main

raise SystemExit(main())
'''
