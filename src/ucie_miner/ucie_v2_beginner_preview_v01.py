"""UCIE V2 B2 isolated HTML preview, composed from actual B1 case.

No V04 routes, operating server, POST, uploads, LLM or customer file access.
Render to stdout only; browser/owner integration is a separate release gate.
"""
from __future__ import annotations

import json
import sys

from .ucie_v2_capsule_v01 import (
    read_only_default, SCHEMA, CASE_ID, CAPSULE_ID,
)
from .ucie_v2_first_use_linked_v01 import render_existing_action_sections

TEMPLATE = r'''<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>UCIE — 격리 초보자 확인 화면</title>
<style>
:root{color-scheme:dark;font-family:system-ui,"Malgun Gothic",sans-serif}
*{box-sizing:border-box}body{background:#0d1523;color:#edf3fc;margin:0;line-height:1.65}
main{max-width:690px;margin:0 auto;padding:28px 18px 80px}
h1{font-size:clamp(1.55rem,4vw,2.2rem);line-height:1.3}
h2{font-size:1.4rem}.subtle{color:#b4c4d9}header{display:flex;justify-content:space-between;gap:15px}
button{font:inherit;background:#203450;color:#f4f8ff;border:1px solid #6481a5;border-radius:14px;display:block;width:100%;text-align:left;min-height:48px;padding:13px 16px;margin:12px 0;cursor:pointer}
button:hover{background:#2b4771}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #bedfff;outline-offset:3px}
a.review-action{display:block;background:#203450;border:1px solid #6481a5;border-radius:12px;padding:12px 14px;margin:10px 0}a.review-action[aria-disabled]{opacity:.6;pointer-events:none}.note{padding:14px;border:1px solid #647c9b;background:#1b2f4b;border-radius:12px}
.stage[hidden],[hidden]{display:none!important}a{color:#b4d7ff;overflow-wrap:anywhere}
details{border:1px solid #506481;border-radius:12px;padding:14px;margin-top:20px}
summary{cursor:pointer;font-weight:700}.stepper{border-bottom:1px solid #3a4e66;padding-bottom:12px}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style>
<script type="application/json" id="ucie-b1-evidence">__UCIE_PINNED_B1__</script>
<script>
"use strict";
document.addEventListener("DOMContentLoaded",()=>{
const p=JSON.parse(document.getElementById("ucie-b1-evidence").textContent);
const safe=()=>p&&p.schema==="UCIE_VERIFIED_TECH_CAPSULE_V01_REVIEW_ONLY"&&p.case_id==="mcp-prompts"&&
p.capsule_id==="UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01"&&p.decision==="HOLD"&&
p.applicability==="UNKNOWN_NO_PROOF"&&p.independent_qa==="NOT_VERIFIED"&&
p.rights==="NOT_APPROVED"&&p.customer_release==="NOT_AUTHORIZED"&&
p.customer_pc_tested===false&&p.sdk_reexecuted_now===false&&
p.auto_promoted===false&&p.actual_code_repaired===false&&
p.official_source_url==="https://github.com/modelcontextprotocol/python-sdk/pull/3696";
let flow=null;
function show(n){
 [1,2,3].forEach(i=>document.getElementById("stage"+i).hidden=i!==n);
 document.getElementById("progress").textContent=n+" / 3 단계";
 const h=document.querySelector("#stage"+n+" h1,#stage"+n+" h2");
 h.focus();
}
function pick(f){
 flow=f;
 document.getElementById("issues").hidden=f!=="solve";
 document.getElementById("continue").hidden=f==="solve";
 show(2);
}
function finish(issue){
 const detail=document.getElementById("proof");
 detail.hidden=true;
 const title=document.getElementById("result-title"),body=document.getElementById("result-body");
 if(flow==="solve"&&issue==="mcp-prompts"){
  if(!safe()){
   title.textContent="증거를 확인할 수 없어요";
   body.textContent="이 사례의 확인 기록이 달라 안내를 보류합니다.";
  }else{
   title.textContent="비슷한 기술 사례를 찾았어요";
   body.textContent=p.message+" "+p.safe_next_step;
   detail.hidden=false;
   document.getElementById("e-title").textContent=p.title;
   document.getElementById("e-test").textContent=p.what_was_tested;
   document.getElementById("e-limit").textContent=p.what_is_unknown;
   document.getElementById("e-qa").textContent="독립 QA "+p.independent_qa+" / 배포 권리 "+p.rights+" / 고객 출시 "+p.customer_release;
   document.getElementById("e-book").textContent=p.skillbook_id+" (미승인 초안)";
   document.getElementById("e-link").href=p.official_source_url;
  }
 } else if(flow==="solve"&&issue==="unmatched"){
  title.textContent="아직 이 문제는 안내하지 못해요";
  body.textContent="준비된 대표 사례 외에는 원인을 추측하지 않아요.";
 } else if(flow==="solve"){
  title.textContent="기존 UCIE의 대표 문제예요";
  body.textContent="이 사례에 관한 별도 기술 확인 기록은 현재 시안에 연결되지 않았어요. MCP의 증거를 잘못 적용하지 않습니다.";
 } else if(flow==="try"){
  title.textContent="준비된 예제를 살펴볼 수 있어요";
  body.textContent="실제 개인 코드가 아닌 UCIE 자체 예제를 설명합니다.";
 } else {
  title.textContent="쉬운 기술 설명을 볼 수 있어요";
  body.textContent="기존 라이브러리의 자료를 참고하되 환경과 버전은 별도 확인이 필요해요.";
 }
 const links=document.getElementById("existing-actions");
 const allowed=!(flow==="solve"&&issue==="mcp-prompts"&&!safe());
 links.hidden=!allowed;
 document.querySelectorAll("[data-route-flow]").forEach(x=>x.hidden=!allowed||x.dataset.routeFlow!==flow);
 document.querySelectorAll("[data-route-case]").forEach(x=>x.hidden=!allowed||flow!=="solve"||x.dataset.routeCase!==issue);
 show(3);
}
document.querySelectorAll("[data-flow]").forEach(b=>b.addEventListener("click",()=>pick(b.dataset.flow)));
document.querySelectorAll("[data-issue]").forEach(b=>b.addEventListener("click",()=>finish(b.dataset.issue)));
document.getElementById("continue").addEventListener("click",()=>finish(""));
document.getElementById("back1").addEventListener("click",()=>show(1));
document.getElementById("back2").addEventListener("click",()=>show(2));
document.getElementById("restart").addEventListener("click",()=>show(1));
// Static file previews must not navigate to an invented file:///local path.
// Real local links work only when the reviewed existing owner app hosts them.
if(window.location.protocol!=="http:"||window.location.hostname!=="127.0.0.1"){
 document.querySelectorAll("#existing-actions a[href],#direct-start-actions a[href]").forEach(x=>{
  x.removeAttribute("href");x.setAttribute("aria-disabled","true");
  x.setAttribute("title","기존 UCIE 로컬 서버에서만 열 수 있어요");
 });
}
show(1);
});
</script></head>
<body><main><header><strong>UCIE</strong><small class="subtle">격리 개발 시안 · 운영 V04 아님</small></header>
<p id="progress" class="stepper">1 / 3 단계</p>
<section class="stage" id="stage1"><h1 tabindex="-1">지금 어떤 도움이 필요하세요?</h1>
<p class="subtle">할 수 있는 일을 선택하세요. 새 앱 자동 제작이나 고객 코드 수리는 아직 하지 않아요.</p>
<button type="button" data-flow="solve">코드가 잘 안 돼요</button>
<button type="button" data-flow="try">간단한 예제를 보고 싶어요</button>
<button type="button" data-flow="learn">차근차근 배우고 싶어요</button></section>
<section class="stage" id="stage2" hidden>
<button id="back1" type="button" class="back">← 이전</button><h2 tabindex="-1">어떤 일이 있었나요?</h2>
<p>다음 중 하나를 고르세요. 코드·로그·경로·비밀번호를 입력하지 않습니다.</p>
<div id="issues">
<button type="button" data-issue="python-env">파이썬에서 모듈을 찾지 못해요</button>
<button type="button" data-issue="powershell-command">파워셸 명령을 찾지 못해요</button>
<button type="button" data-issue="git-repository">깃 저장소를 찾지 못해요</button>
<button type="button" data-issue="mcp-prompts">MCP 요청의 입력값이 맞지 않아요</button>
<button type="button" data-issue="unmatched">해당되는 문제가 없어요</button>
</div><button type="button" id="continue" hidden>다음 확인 방법 보기</button></section>
<section class="stage" id="stage3" hidden><button id="back2" type="button" class="back">← 이전</button>
<h2 tabindex="-1">지금 확인해 볼 일</h2><h3 id="result-title"></h3><p id="result-body"></p>
<p class="note">실제 PC와 코드는 검사하지 않았어요. 다른 버전의 사용 가능성은 확인하지 못했고, 고객 제공·배포 권리는 승인되지 않았어요.</p>
<p class="subtle">이 화면은 격리 소스 시안입니다. 아래 링크는 기존 UCIE 로컬 서버에서 제공할 때만 실제 기능을 엽니다. 이 파일이 운영 서비스에 설치된 것은 아닙니다.</p>
<details id="proof" hidden><summary>왜 이렇게 안내하나요?</summary>
<p id="e-title"></p><p id="e-test"></p><p id="e-limit"></p><p id="e-qa"></p>
<p id="e-book"></p><a id="e-link" target="_blank" rel="noopener noreferrer">공식 변경 기록 보기</a></details>
<button id="restart" type="button">처음부터 다시 선택하기</button></section>
__UCIE_LINKED_EXISTING_ROUTES__</main></body></html>'''


def render_preview() -> str:
    proof = read_only_default()  # Real existing UCIE modules, not a standalone fixture.
    if (proof.get("schema") != SCHEMA or proof.get("case_id") != CASE_ID
            or proof.get("capsule_id") != CAPSULE_ID or proof.get("decision") != "HOLD"
            or proof.get("rights") != "NOT_APPROVED"
            or proof.get("independent_qa") != "NOT_VERIFIED"):
        raise ValueError("B1 evidence drift blocks isolated preview")
    payload = json.dumps(proof, sort_keys=True, ensure_ascii=False)
    payload = (payload.replace("<", "\\u003c").replace(">", "\\u003e")
               .replace("&", "\\u0026").replace("\u2028", "\\u2028")
               .replace("\u2029", "\\u2029"))
    if (TEMPLATE.count("__UCIE_PINNED_B1__") != 1
            or TEMPLATE.count("__UCIE_LINKED_EXISTING_ROUTES__") != 1):
        raise ValueError("preview template drift")
    links = render_existing_action_sections(proof)
    return (TEMPLATE.replace("__UCIE_PINNED_B1__", payload)
            .replace("__UCIE_LINKED_EXISTING_ROUTES__", links))


def main() -> int:
    sys.stdout.write(render_preview())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
