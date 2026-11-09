"""UCIE V04 premium dark customer-facing presentation.

No customer page presents internal owner, release or scheduler flags.
The existing validators, URLs, data contracts and machine health stay intact.
"""
from __future__ import annotations

from html import escape

from .local_v1_design_v02 import PAGE_METADATA
from .local_v1_design_v03 import STYLE as BASE_STYLE
from .local_v1_design_v03 import LEGACY_STYLE as BASE_NESTED_STYLE

PAGE_NAMES = {
    "시작": ("홈", "더 나은 개발을 위한 시작점", ""),
    "오류 예방": ("문제 예방", "문제를 미리 살펴보세요", "공개 기술 사례를 찾아보고 개선 방향을 확인하세요."),
    "후보 검토 작업": ("기술 검토", "개선 방향 자세히 보기", "출처와 참고 정보를 확인하고 다음 검토 단계를 살펴보세요."),
    "개발 엔진·스킬": ("개발 도구", "원하는 도구를 선택하세요", "실행 가능한 예제와 비교 도구를 한곳에서 확인하세요."),
    "통합 가상도서관": ("라이브러리", "지식을 찾는 더 간결한 방법", "기술 가이드, 학습 자료, 공개 사례를 살펴보세요."),
    "SkillBook 실행": ("예제 체험", "예제를 직접 살펴보세요", "UCIE 예제로 기능을 시험해 보세요."),
    "SkillBook 실행 결과": ("체험 결과", "실행 결과", "선택한 예제의 결과와 적용 범위를 확인하세요."),
    "근거 기반 개선": ("개선 제안", "변경에서 발견하는 개선 아이디어", "공개 기술 변경을 탐색하고 다음 단계를 살펴보세요."),
    "개발 규칙": ("이용 안내", "UCIE 사용 안내", "도구 이용과 기술 자료 확인 방법을 안내합니다."),
}

NAV = (
    ("/local", "홈", "home"),
    ("/local/error", "문제 예방", "shield"),
    ("/local/engine", "개발 도구", "tool"),
    ("/local/library", "라이브러리", "book"),
    ("/local/evolution", "개선 제안", "spark"),
    ("/local/policy", "이용 안내", "help"),
)

STYLE = BASE_STYLE + """
/* V04 visual surface: graphite, satin, soft shapes. No external assets. */
:root{color-scheme:dark;--canvas:#08090c;--paper:#0c0d11;--surface:#14161b;
 --ink:#f4f5f8;--muted:#a6abb7;--line:#2a2d37;--line-strong:#444854;
 --rail:#090a0e;--rail-text:#e5e7ee;--copper:#b8c6f9;--copper-light:#242938;
 --green:#b8c6f9;--green-light:#202430;--focus:#b6c8ff}
html{color-scheme:dark}
body{background:#08090c;color:#f4f5f8;font-size:15px;letter-spacing:-.01em}
a{color:#c0cbff}
a:hover{color:#fff}
.app-shell{grid-template-columns:230px minmax(0,1fr)}
.sidebar{background:#0a0b0e;border-right:1px solid #242630;
 padding:33px 19px 24px}
.brand{padding:3px 8px 34px}
.brand-mark{font-size:25px;font-weight:820;letter-spacing:-.04em;
 display:inline-grid;place-items:center;width:39px;height:39px;border-radius:12px;
 background:#f1f2f6;color:#0b0c0e}
.brand-name{font-size:22px;letter-spacing:-.04em;margin-left:10px;color:#f6f7fb}
.brand-caption{font:500 10px/1.5 system-ui,sans-serif;letter-spacing:.14em;
 color:#9297a6;margin-top:12px}
.sidebar-label{padding:1px 12px 13px;color:#828794;border-bottom:0;
 font:650 11px/1.4 system-ui,sans-serif;letter-spacing:.06em}
.main-nav{gap:5px}
.main-nav a{min-height:49px;display:flex;align-items:center;gap:12px;
 padding:12px 14px;background:transparent;border:0;border-radius:14px;
 color:#a8adb9;font-size:14px;font-weight:600;
 transition:background .16s ease,color .16s ease}
.main-nav a:hover{background:#1b1d24;color:#fff}
.main-nav a[aria-current="page"]{padding:12px 14px;border-left:0;
 background:#292c35;color:#fff;box-shadow:inset 0 0 0 1px #353946}
.nav-icon{font:750 11px/1 ui-monospace,Consolas,monospace;
 display:grid;place-items:center;width:29px;height:29px;flex:none;
 border-radius:9px;background:#20222a;color:#9da5b7}
.main-nav a[aria-current="page"] .nav-icon{color:#0e1017;background:#e8ebf8}
.sidebar-bottom{display:none}
.page-column{background:#0d0e12}
.topbar{min-height:78px;padding:17px clamp(22px,4vw,56px);
 background:#101116;border-bottom:1px solid #252831}
.breadcrumb{font:650 13px/1.5 system-ui,sans-serif;color:#a4abb9;letter-spacing:-.01em}
.breadcrumb span{color:#5d626e;margin:0 11px}
.top-tags{justify-content:flex-end}
.top-help{display:inline-flex;align-items:center;min-height:36px;
 border:1px solid #353945;border-radius:99px;padding:7px 15px;
 color:#c8ccd7;text-decoration:none;font-size:12px;font-weight:650}
.top-help:hover{background:#242730;color:#fff}
.workspace{max-width:1450px;padding:42px clamp(22px,4vw,56px) 76px}
.page-header{border-color:#262a33;margin-bottom:28px;grid-template-columns:minmax(0,1fr)}
.page-header h1{color:#f6f7fb;font-size:clamp(32px,3.1vw,46px);font-weight:750;
 letter-spacing:-.047em;margin:8px 0 8px;line-height:1.24}
.page-lede{color:#aeb3c0;font-size:15px}
.page-reference{display:none}
.page-header--home{border:0;padding:0;margin:0;height:0}
.page-header--home .eyebrow{display:none}
.eyebrow{font:700 11px/1.5 system-ui,sans-serif;letter-spacing:.10em;color:#aebcf9}
.visually-hidden{position:absolute!important;width:1px!important;
 height:1px!important;padding:0!important;margin:-1px!important;
 overflow:hidden!important;clip:rect(0,0,0,0)!important;
 white-space:nowrap!important;border:0!important}
.content-stack{gap:22px}
.content-stack>section,.content-stack>article{border:1px solid #2a2d35;
 border-radius:22px;background:#16181e;padding:29px 32px;box-shadow:none}
.content-stack section h2,.content-stack article h2{font-size:22px;
 color:#f3f4f8;font-weight:720}
.content-stack section h3,.content-stack article h3{color:#edf0f5}
.content-stack p{color:#aeb3bd;line-height:1.75}
.content-stack a{color:#c2cdff}
.content-stack a:hover{color:#fff}
.content-stack strong{color:#e9ebf3}
.content-stack label{color:#c8ccd6;font-size:13px}
.content-stack input,.content-stack select{background:#20222a;border:1px solid #434754;
 color:#f2f3f8;min-height:48px;border-radius:13px;padding:11px 15px}
.content-stack input::placeholder{color:#878c9a}
.content-stack button,.button-primary,.button-ghost{min-height:47px;
 border-radius:13px;padding:11px 23px;background:#f0f1f5;color:#101114;
 border:1px solid #f0f1f5;font-size:13px;font-weight:740;box-shadow:none}
.content-stack button:hover,.button-primary:hover{background:#dbe0ef;color:#121418}
.button-ghost{background:#272a33;border-color:#414550;color:#f1f2f7}
.button-ghost:hover{background:#343844;color:#fff}
.content-stack>.intro-workbench{border:0;border-radius:26px;
 overflow:hidden;background:#17191f;grid-template-columns:minmax(0,1.2fr) minmax(270px,.80fr);
 box-shadow:inset 0 0 0 1px #31343d;min-height:330px}
.intro-text{padding:clamp(32px,4vw,56px) clamp(27px,4vw,56px)}
.intro-text .eyebrow{color:#9ba6bd;letter-spacing:.09em;margin:0 0 21px}
.intro-title{color:#fbfcff!important;font-weight:760;
 font-size:clamp(33px,3.5vw,51px);letter-spacing:-.053em;
 max-width:16ch;margin:0 0 22px!important;line-height:1.22;word-break:keep-all}
.intro-title em{color:#c4cfff;font-style:normal}
.intro-text>p{color:#bfc3cf;font-size:14px;max-width:48ch}
.intro-note{border-color:#363943;color:#9ea5b2;padding-top:17px;
 margin-top:31px;font-size:12px}
.intro-note span:first-child{color:#abb9f2}
.quick-query{background:#20222a;border-left:1px solid #32353e;
 padding:clamp(28px,3.5vw,42px)}
.quick-query .eyebrow{color:#acb4c7}
.quick-query h3{color:#f1f2f7;font-size:23px;margin:11px 0}
.quick-query p{color:#afb4c0;font-size:13px}
.quick-query form{display:grid;gap:10px;margin-top:21px}
.quick-query button{width:100%}
.quick-examples{color:#89909f}
.content-stack>.section-heading{padding:16px 1px 0;border:0;background:transparent}
.section-heading h2{color:#f0f1f6!important;font-size:23px!important}
.section-heading p{color:#9da4b1;font-size:13px}
.content-stack>.pillar-grid{border:0;border-radius:20px;padding:0;
 background:transparent;display:grid;gap:9px}
.pillar-card{border:1px solid #2b2e37;border-radius:17px;
 background:#17191f;padding:23px 26px;min-height:105px;
 grid-template-columns:46px minmax(0,1fr) 27px;gap:18px;
 color:#e8eaf1;transition:background .16s ease,border-color .16s ease,transform .16s ease}
.pillar-card:last-child{border:1px solid #2b2e37}
.pillar-card:hover{background:#22252d;color:#fff;border-color:#555b6d;
 transform:translateY(-1px)}
.pillar-number{font:720 12px/1 ui-monospace,Consolas,monospace;
 color:#b6c0dd;letter-spacing:.04em}
.pillar-card h3{color:#f6f7fb;font-size:18px;font-weight:720;margin:0 0 3px}
.pillar-card p{color:#a7adbb;font-size:13px}
.pillar-arrow{color:#8d96ac;font-size:20px}
.content-stack>.trust-panel{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
 border:0;border-radius:18px;background:#15171c;padding:0}
.trust-item{border-right:1px solid #2f323b}
.trust-label{color:#949aaa}
.trust-value{color:#e2e4ec;font-weight:720}
.trust-value--hold{color:#c9d0e1}
.trust-detail{color:#9ea5b3}
.content-stack>.workbench-note{background:#171a20;border:1px solid #2d3038}
.workbench-note h2{color:#f3f5f9}
.content-stack>.search-panel{border:1px solid #2d303a;border-radius:22px;
 padding:30px 32px;background:#181a20}
.search-panel>p,.search-panel small{color:#a3aab8}
.content-stack>.result-summary{background:#181b24;border:1px solid #323745;
 border-radius:16px;padding:19px 24px}
.result-summary strong{color:#f4f6fb}
.content-stack>.evidence-item{background:#17191f;border:1px solid #2b2e38;
 border-radius:19px;overflow:hidden;padding:0}
.evidence-title{border-color:#2c3039;padding:22px 25px}
.evidence-title h3{color:#f3f4f8;font-size:18px;font-weight:720}
.record-stamp{color:#d4c39b;font:650 12px/1.5 system-ui,sans-serif;
 border-radius:30px;padding:4px 10px;background:#2e2923}
.evidence-properties>div{border-color:#30333c}
.evidence-properties>div:nth-child(odd){border-color:#30333c}
.evidence-properties dt{color:#969eaf}
.evidence-properties dd{color:#e3e5ec}
.evidence-properties code{color:#c3c9d8}
.evidence-guidance{background:#191d27;border-color:#303541;color:#b5bdce}
.evidence-actions{border-color:#323540}
.evidence-actions a{color:#ccd5ff}
.evidence-actions span{color:#929aad}
.content-stack>.pager-box{background:#16181e;border-radius:18px}
.pagination a{background:#20232a;border:1px solid #393e49;border-radius:11px;color:#d2d8ec}
.pagination a:hover{background:#2a2e39}
.content-stack>.shelf-title{border:0;border-bottom:1px solid #31353f;
 border-radius:0;background:transparent;padding:23px 2px 8px}
.shelf-title h2{color:#f2f3f8}
.shelf-title p{color:#a0a8b7}
.content-stack>.shelf-entry{border:1px solid #2c3039;border-left:1px solid #2c3039;
 background:#181a20;border-radius:17px;padding:24px 27px}
.shelf-entry h3{color:#f1f2f7}
.shelf-entry p{color:#a4a9b6}
.shelf-entry .entry-flag{color:#c7b893}
.recipe-list{border:0;gap:10px}
.recipe-list li{background:#1d2027;border:1px solid #353944;border-radius:13px}
.recipe-list li:last-child{border-bottom:1px solid #353944}
.recipe-list li>a{color:#dfe4f8;font:700 13px/1.5 system-ui,sans-serif;
 border-radius:13px}
.recipe-list li>a:hover{background:#2b303a;color:#fff}
.recipe-list .recipe-copy{color:#a2aabb;font-size:13px}
.review-steps li{border-color:#32353d}
.review-gates li{background:#1e2129;border-color:#333742}
.review-gates strong{color:#ccd4e8}
.inventory-grid{border-color:#343841;border-radius:13px;overflow:hidden}
.inventory-grid>div{border-color:#343841}
.inventory-grid>div:nth-child(odd){border-color:#343841}
.inventory-grid dt{color:#9da5b4}
.inventory-grid dd{color:#f3f4f8}
.page-footer{background:#0d0e12;border-color:#2a2e35;color:#8d95a3;
 padding:23px clamp(22px,4vw,56px)}
.page-footer a{color:#aeb9d6}
.technical-details{background:#1b1e25;border:1px solid #353944;
 border-radius:14px;overflow:hidden;margin:15px 0 0}
.technical-details summary{cursor:pointer;padding:15px 18px;
 color:#b4bece;font-weight:650;font-size:13px;list-style:none}
.technical-details summary:after{content:"+";float:right;font-size:19px;font-weight:400}
.technical-details[open] summary:after{content:"−"}
.technical-details[open] summary{border-bottom:1px solid #353944}
.technical-details .evidence-properties{margin:0}
.technical-details .inventory-grid{margin:15px}
.technical-details p{padding:0 17px}
.card-kicker{color:#8993a6;font-size:12px;font-weight:660;letter-spacing:.05em}
.customer-note{color:#a6acba;font-size:12px;line-height:1.65}
.page-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.page-controls a{color:#d5ddff}
@media (max-width:1100px){
 .app-shell{grid-template-columns:202px minmax(0,1fr)}
 .sidebar{padding:23px 11px}
 .workspace{padding:33px 24px 50px}
 .topbar{padding:13px 24px}
 .intro-workbench{grid-template-columns:minmax(0,1fr) 270px}
}
@media (max-width:880px){
 .app-shell{display:block}
 .sidebar{position:relative;top:auto;height:auto;min-height:0;overflow:visible;
   border-bottom:1px solid #2f323c;padding:16px}
 .brand{padding:0 4px 12px}
 .brand-caption,.sidebar-label{display:none}
 .main-nav{display:flex;gap:5px;overflow-x:auto}
 .main-nav a{flex:none;min-height:42px;border:0;padding:9px 13px;font-size:12px}
 .main-nav a[aria-current="page"]{padding:9px 13px}
 .nav-icon{width:23px;height:23px}
 .topbar{min-height:57px}
 .workspace{padding-top:25px}
}
@media (max-width:640px){
 .workspace{padding:23px 15px 39px}
 .topbar{padding:12px 15px;flex-wrap:wrap}
 .top-help{min-height:32px}
 .page-header h1{font-size:32px}
 .content-stack{gap:14px}
 .content-stack>section,.content-stack>article{padding:22px 19px}
 .content-stack>.intro-workbench{display:block;padding:0}
 .intro-text{padding:30px 22px}
 .intro-title{font-size:34px}
 .quick-query{border-left:0;border-top:1px solid #343741;padding:24px 22px}
 .content-stack>.pillar-grid{padding:0}
 .pillar-card{padding:19px 17px;grid-template-columns:30px minmax(0,1fr) 20px;gap:12px}
 .pillar-card h3{font-size:16px}
 .content-stack>.trust-panel{grid-template-columns:1fr;padding:0}
 .trust-item{border-right:0;border-bottom:1px solid #30343d}
 .content-stack>.shelf-entry{padding:22px 20px}
 .evidence-title,.evidence-properties>div,.evidence-actions,.evidence-guidance{
   padding-left:19px;padding-right:19px}
 .evidence-properties,.inventory-grid{grid-template-columns:1fr}
 .evidence-properties>div:nth-child(odd),.inventory-grid>div:nth-child(odd){border-right:0}
 .content-stack form{display:grid}
 .content-stack input,.content-stack select,.content-stack button{width:100%;max-width:100%}
 .page-footer{padding:17px 15px}
}
@media (max-width:380px){
 .intro-title{font-size:30px;word-break:keep-all}
 .pillar-card{gap:7px}
}
@media (prefers-reduced-motion:reduce){
 .pillar-card,.main-nav a{transition:none}
 .pillar-card:hover{transform:none}
}
"""

NESTED_STYLE = BASE_NESTED_STYLE + """
:root{color-scheme:dark;color:#f2f4f8;background:#0d0e12}
body{background:#0d0e12;color:#f2f4f8}
main{max-width:1320px;padding:33px clamp(16px,4vw,58px) 60px}
main>header{background:#17191f;border:1px solid #30333e;border-radius:23px;
 padding:30px 35px;color:#f4f5f9}
main>header h1{color:#f4f5f9;font-weight:740}
main>header .subtitle{color:#adb4c1}
main a{color:#c0ccff}
main a:hover{color:#fff}
.panel,.item,.empty,.detail,.v11-item{background:#191b22;border:1px solid #333742;
 border-radius:19px;box-shadow:none;color:#e6e8f0}
.panel{padding:28px}
.item{padding:22px}
.panel h2,.item h2,.detail h2{color:#f2f3f8}
.panel p,.item p,.detail p{color:#adb5c4}
.item .meta{color:#a5adc0}
main label,main dt{color:#b5bac8}
main dd{color:#f3f4f8}
main form{gap:12px}
main input,main select{background:#23262e;border:1px solid #444957;
 color:#f4f6fc;border-radius:12px;min-height:46px}
main button{background:#f0f1f6;border:1px solid #f0f1f6;color:#101115;
 border-radius:12px;min-height:46px}
main button:hover{background:#dce1f0;color:#131419}
.note{background:#262932;color:#c7cfdf;border-left:3px solid #9ca8d6;
 border-radius:11px}
.chip,.toolbar a,.pages a{border-radius:30px}
.chip.active{background:#333747;color:#e3e8ff;border-color:#57627e}
main table{width:100%;color:#dbe0ea;overflow-x:auto;border-color:#373b45}
main th,main td{border-color:#333743;color:#d9e0ea}
main th{background:#242831;color:#e4e8f3}
main details{background:#20232b;border:1px solid #373b47;border-radius:14px}
main summary{color:#e0e4ee}
nav[data-ucie-local-nav="true"]{background:#191b22!important;border:1px solid #353946!important;
 border-radius:17px!important;padding:17px 20px!important;color:#e2e5ed!important}
nav[data-ucie-local-nav="true"] strong{color:#e8ecf5}
nav[data-ucie-local-nav="true"] a{color:#cbd3f3}
main footer{border-color:#373b45;color:#a1a9b6}
@media(max-width:760px){
 main{padding:16px 12px 32px}
 main>header{padding:23px 20px;border-radius:18px}
 .panel,.item,.empty,.detail,.v11-item{padding:20px}
 .items{grid-template-columns:1fr}
 main input,main select,main button{width:100%;max-width:100%}
}
"""

def render_shell(name: str, content: str, routes: tuple) -> str:
    """Whitelisted customer-facing navigation, never infer release status."""
    if name not in PAGE_METADATA or name not in PAGE_NAMES or type(content) is not str:
        raise ValueError("unregistered UCIE page")
    expected = ("/local/error", "/local/engine", "/local/library", "/local/evolution")
    if (type(routes) is not tuple or len(routes) != 4 or
            tuple(r[0] for r in routes) != expected):
        raise ValueError("unrecognized UCIE route")
    label, headline, subtitle = PAGE_NAMES[name]
    active = PAGE_METADATA[name][0]
    nav = []
    for i, (href, text_label, _) in enumerate(NAV):
        if i == 0:
            symbol = "01"
        else:
            symbol = str(i + 1).zfill(2)
        nav.append(
            '<a href="' + href + '"' +
            (' aria-current="page"' if href == active else '') +
            '><span class="nav-icon" aria-hidden="true">' + symbol +
            '</span><span>' + escape(text_label) + '</span></a>'
        )
    if name == "시작":
        heading = '<h1 class="visually-hidden">UCIE 홈</h1>'
    else:
        heading = (
            '<header class="page-header"><div><span class="eyebrow">'
            'UCIE</span><h1>' + escape(headline) + '</h1>'
            '<p class="page-lede">' + escape(subtitle) +
            '</p></div></header>'
        )
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="dark">'
        '<title>UCIE · ' + escape(label) + '</title>'
        '<style>' + STYLE + '</style></head><body>'
        '<a class="skip-link" href="#workspace">본문으로 건너뛰기</a>'
        '<div class="app-shell"><aside class="sidebar" aria-label="UCIE 메뉴">'
        '<a class="brand" href="/local" aria-label="UCIE 홈">'
        '<span class="brand-mark" aria-hidden="true">U</span>'
        '<span class="brand-name">UCIE</span>'
        '<span class="brand-caption">INTELLIGENCE FOR DEVELOPMENT</span>'
        '</a><nav class="main-nav" aria-label="주요 기능">' +
        ''.join(nav) + '</nav></aside><div class="page-column">'
        '<header class="topbar"><span class="breadcrumb">UCIE'
        '<span aria-hidden="true">/</span>' + escape(label) + '</span>'
        '<a class="top-help" href="/local/policy">도움말</a></header>'
        '<main class="workspace" id="workspace" tabindex="-1">' +
        heading + '<div class="content-stack">' + content +
        '</div></main><footer class="page-footer">'
        '<span>UCIE</span><a href="/local/policy">자료 이용 안내</a>'
        '</footer></div></div></body></html>'
    )

def skin_nested_local_page(content: str) -> str:
    """Apply dark skin once to already validated UCIE nested HTML only."""
    if (type(content) is not str or not content.startswith("<!doctype html>")
            or content.count("<head>") != 1
            or content.count("</head>") != 1
            or content.count("<body>") != 1
            or content.count("</body>") != 1
            or content.count("</html>") != 1):
        raise ValueError("unexpected UCIE nested page")
    if 'data-ucie-nested-theme="v02"' in content:
        return content
    return content.replace(
        "</head>", '<style data-ucie-nested-theme="v02">' +
        NESTED_STYLE + '</style></head>', 1
    )
