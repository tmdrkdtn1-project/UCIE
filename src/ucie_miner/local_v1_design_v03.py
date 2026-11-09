"""UCIE Evidence Workbench V03: editorial, task-first UI for LOCAL V1.

Static HTML/CSS only. Routes, source data, validation, approval states,
security headers and owner-operating ledgers remain owned by existing code.
"""
from __future__ import annotations

from html import escape
from .local_v1_design_v02 import PAGE_METADATA

STYLE = """
:root{
  color-scheme:light;
  --canvas:#f0efe9;--paper:#faf9f5;--surface:#fffefa;
  --ink:#202a28;--muted:#4f615c;--line:#c9cec7;
  --line-strong:#7f938a;--rail:#1c2927;--rail-text:#ecf1eb;
  --copper:#a33e26;--copper-light:#f4e8df;--green:#1f6759;
  --green-light:#e6eee8;--focus:#c75b24;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:
  system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;
  font-size:15px;line-height:1.7;-webkit-font-smoothing:antialiased}
a{color:#16584b;text-decoration:underline;text-decoration-thickness:1px;
  text-underline-offset:3px;overflow-wrap:anywhere}
a:hover{color:#a33e26}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,
summary:focus-visible{outline:3px solid var(--focus);outline-offset:3px}
.skip-link{position:fixed;top:-80px;left:12px;z-index:99;background:#fff;
  padding:12px 18px;color:var(--ink);border:2px solid var(--ink)}
.skip-link:focus{top:12px}
.app-shell{display:grid;grid-template-columns:220px minmax(0,1fr);min-height:100vh}
.sidebar{background:var(--rail);color:var(--rail-text);min-height:100vh;
  position:sticky;top:0;height:100vh;overflow-y:auto;
  display:flex;flex-direction:column;padding:25px 15px 22px;
  border-right:1px solid #34413c}
.brand{display:block;padding:5px 9px 34px;color:#fff;text-decoration:none;
  overflow-wrap:normal}
.brand:hover{color:#fff}
.brand-mark{display:inline-block;font-size:32px;line-height:1;font-weight:900;
  letter-spacing:-.08em;color:#e3a97e;vertical-align:middle}
.brand-name{display:inline-block;font-size:27px;line-height:1.1;font-weight:850;
  letter-spacing:-.08em;margin-left:9px;vertical-align:middle}
.brand-caption{display:block;font:700 10px/1.5 ui-monospace,Consolas,monospace;
  letter-spacing:.13em;color:#aabdb5;margin-top:12px}
.sidebar-label{font:700 10px/1.3 ui-monospace,Consolas,monospace;
  letter-spacing:.13em;color:#a3b6ac;padding:0 11px 12px;
  border-bottom:1px solid #44534a;margin-bottom:8px}
.main-nav{display:grid;gap:0}
.main-nav a{display:grid;grid-template-columns:27px minmax(0,1fr);gap:10px;
  align-items:center;min-height:54px;padding:10px 8px;
  border-bottom:1px solid #34433e;color:#d9e3dd;
  font-size:13px;font-weight:650;text-decoration:none;overflow-wrap:normal}
.main-nav a:hover{color:#fff;background:#293c36}
.main-nav a[aria-current="page"]{background:#ecede5;color:#1c2927;
  border-left:3px solid var(--copper);padding-left:5px;font-weight:820}
.nav-icon{font:750 11px/1 ui-monospace,Consolas,monospace;color:#8ea69a}
.main-nav a[aria-current="page"] .nav-icon{color:#a33e26}
.sidebar-bottom{margin-top:auto;padding:22px 9px 0}
.sidebar-sep{height:1px;background:#44534a;margin-bottom:17px}
.connection{font:750 11px/1.5 ui-monospace,Consolas,monospace;
  letter-spacing:.08em;color:#b5d3c3}
.connection-dot{display:inline-block;width:7px;height:7px;background:#85c6a3;
  border-radius:50%;margin-right:8px}
.sidebar-bottom p{font-size:12px;line-height:1.65;color:#b4c2b9;margin:9px 0 0}
.page-column{min-width:0;display:flex;flex-direction:column}
.topbar{min-height:58px;background:var(--paper);border-bottom:1px solid var(--line);
  padding:13px clamp(20px,3.5vw,50px);display:flex;gap:14px;align-items:center;
  justify-content:space-between}
.breadcrumb{font:720 11px/1.4 ui-monospace,Consolas,monospace;
  color:#455950;letter-spacing:.03em}
.breadcrumb span{color:#8b9a91;margin:0 8px}
.top-tags{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.status-tag{display:inline-block;border-left:2px solid #347c67;padding:1px 6px 1px 9px;
  background:transparent;color:#2e5046;letter-spacing:.01em;
  font-size:11px;font-weight:730;line-height:1.5}
.status-tag--hold{color:#913f26;border-color:#ae4a2c}
.workspace{width:100%;max-width:1380px;margin:0 auto;
  padding:36px clamp(20px,3.5vw,50px) 65px;flex:1}
.page-header{display:grid;grid-template-columns:minmax(0,1fr) 152px;gap:16px;
  padding:0 0 25px;border-bottom:1px solid var(--ink);margin-bottom:28px}
.eyebrow{font:750 11px/1.5 ui-monospace,Consolas,monospace;
  color:var(--copper);letter-spacing:.09em;display:block}
.page-header h1{font-size:clamp(30px,3.7vw,49px);letter-spacing:-.055em;
  font-weight:860;line-height:1.25;margin:8px 0 9px;word-break:keep-all}
.page-lede{font-size:14px;line-height:1.65;max-width:70ch;margin:0;color:var(--muted);
  word-break:keep-all}
.page-header--home{display:block;padding:0 0 12px;margin-bottom:16px;
  border-bottom:1px solid #b6bfb5}
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
  overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.page-reference{align-self:end;text-align:right;font:750 11px/1.5 ui-monospace,
  Consolas,monospace;color:#667971;letter-spacing:.06em}
.content-stack{display:grid;gap:18px;min-width:0;align-content:start}
.content-stack>section,.content-stack>article{background:var(--surface);
  border:1px solid var(--line);border-radius:2px;padding:25px 28px;min-width:0;margin:0}
.content-stack>section>h2:first-child,.content-stack>article>h2:first-child{margin-top:0}
.content-stack section h2,.content-stack article h2{font-size:21px;line-height:1.4;
  margin:0 0 14px;letter-spacing:-.035em;font-weight:780;word-break:keep-all}
.content-stack section h3,.content-stack article h3{font-size:17px;
  letter-spacing:-.025em;margin:0 0 10px;line-height:1.5}
.content-stack p{margin:8px 0;color:#42564f}
.content-stack ul,.content-stack ol{padding-left:22px}
.content-stack li{padding:4px 0;line-height:1.7}
.content-stack pre{white-space:pre-wrap}
.content-stack code,.content-stack pre{font-family:ui-monospace,Consolas,monospace;
  font-size:.9em;overflow-wrap:anywhere;word-break:break-word}
.content-stack a{font-weight:650}
.content-stack form{display:flex;flex-wrap:wrap;gap:11px;align-items:end;margin:17px 0 12px}
.content-stack label{flex:1 1 245px;min-width:0;display:grid;gap:6px;
  color:#354a42;font-size:13px;font-weight:750}
.content-stack input,.content-stack select{width:100%;max-width:560px;min-height:45px;
  border:1px solid #9aaea2;border-radius:2px;padding:10px 13px;background:#fff;
  color:#1d2924;font:inherit;font-size:14px}
.content-stack input::placeholder{color:#6d7e72}
.content-stack button,.button-primary,.button-ghost{border-radius:2px;min-height:45px;
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:10px 19px;border:1px solid #253f37;color:white;background:#244b40;
  font:750 13px/1.35 system-ui,"Malgun Gothic",sans-serif;cursor:pointer;
  text-decoration:none;white-space:normal}
.content-stack button:hover,.button-primary:hover{background:#163d33;color:#fff}
.button-ghost{background:transparent;border-color:#809286;color:#244b40}
.button-ghost:hover{background:#e8ede6;color:#153a32}
.content-stack .intro-workbench{display:grid;grid-template-columns:minmax(0,1.3fr)
  minmax(250px,.75fr);gap:0;padding:0;background:#f9f8f3;border:1px solid var(--ink)}
.intro-text{padding:clamp(26px,4vw,48px);min-width:0}
.intro-text .eyebrow{margin-bottom:20px}
.intro-title{font-size:clamp(30px,3.3vw,47px);line-height:1.23;
  letter-spacing:-.06em;margin:0 0 21px!important;color:#1d2b26;
  font-weight:860;word-break:keep-all;max-width:16ch}
.intro-title em{color:#a33e26;font-style:normal}
.intro-text>p{font-size:14px;line-height:1.75;color:#4b5b54;max-width:61ch}
.intro-note{border-top:1px solid #c6ccc4;font-size:12px;color:#46584f;
  margin-top:30px;padding-top:13px;display:flex;gap:12px;flex-wrap:wrap}
.intro-note span:first-child{font-family:ui-monospace,Consolas,monospace;font-size:11px;
  color:#a33e26;font-weight:800}
.quick-query{border-left:1px solid #293e35;background:#e7e9dd;
  padding:clamp(24px,3.3vw,37px);display:flex;flex-direction:column;justify-content:center}
.quick-query .eyebrow{color:#59695b}
.quick-query h3{font-size:23px;margin:13px 0 7px;letter-spacing:-.045em}
.quick-query p{font-size:13px;line-height:1.6;color:#4f6158}
.quick-query form{display:grid;gap:10px;margin:16px 0 0}
.quick-query input{max-width:none}
.quick-query button{width:100%;min-height:45px}
.quick-examples{font:650 11px/1.55 ui-monospace,Consolas,monospace;
  color:#50635a;margin-top:12px}
.content-stack>.section-heading{background:transparent;border:0;
  padding:14px 0 0}
.section-heading h2{font-size:24px!important;margin:4px 0 5px!important}
.section-heading p{font-size:13px;color:#51655d}
.content-stack>.pillar-grid{display:block;background:var(--surface);padding:0;
  border:1px solid var(--ink);border-top:4px solid var(--ink)}
.pillar-card{display:grid;grid-template-columns:52px minmax(0,1fr) 36px;
  gap:15px;align-items:center;padding:19px 24px;border-bottom:1px solid var(--line);
  min-height:105px;color:var(--ink);text-decoration:none;background:#fffefa}
.pillar-card:last-child{border-bottom:0}
.pillar-card:hover{background:#eaf0e7;color:var(--ink)}
.pillar-card:focus-visible{outline-offset:-3px}
.pillar-number{display:block;font:850 24px/1 ui-monospace,Consolas,monospace;
  color:#a1432a;letter-spacing:-.07em}
.pillar-content{display:block;min-width:0}
.pillar-card h3{font-size:19px;margin:0 0 4px;font-weight:780;
  line-height:1.45;color:#21312b}
.pillar-card p{margin:0;color:#4b6057;font-size:13px;line-height:1.55}
.pillar-arrow{justify-self:end;font-size:27px;line-height:1;color:#305448}
.content-stack>.trust-panel{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
  gap:0;padding:0;border-top:3px solid #a33e26;background:#fffefa}
.trust-item{min-width:0;padding:21px 24px;border-right:1px solid var(--line)}
.trust-item:last-child{border-right:0}
.trust-label{display:block;font:740 11px/1.4 ui-monospace,Consolas,monospace;
  color:#516b5e;letter-spacing:.05em}
.trust-value{display:block;margin-top:10px;color:#263f34;font-size:14px;
  font-weight:800;line-height:1.5}
.trust-value--hold{color:#993e27}
.trust-detail{font-size:12px;color:#52655b;display:block;margin-top:5px}
.content-stack>.workbench-note{padding:19px 25px;background:#eaeae1;border:1px solid #adb6ac}
.workbench-note h2{font-size:16px;margin:0 0 5px}
.workbench-note p{font-size:13px}
.workbench-note a{font-size:13px}
.content-stack>.search-panel{border-top:3px solid var(--ink);padding:27px 29px}
.search-panel h2{font-size:23px!important}
.search-panel>p{font-size:14px;max-width:88ch}
.search-panel small{display:block;margin:10px 0 0;font-size:12px;color:#556a60}
.content-stack>.result-summary{background:#e9ede5;border:1px solid #a9b8ab;padding:15px 20px}
.result-summary p{font-size:13px!important;margin:4px 0!important}
.result-summary strong{color:#1b4138}
.content-stack>.evidence-item{display:grid;gap:0;padding:0;background:#fffefa;
  border:1px solid #bbc7bd}
.evidence-title{padding:20px 26px 14px;border-bottom:1px solid var(--line);
  display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap}
.evidence-title h3{font:800 18px/1.4 system-ui,"Malgun Gothic",sans-serif;
  color:#213a32;letter-spacing:-.02em;margin:0}
.record-stamp{font:760 11px/1.6 ui-monospace,Consolas,monospace;color:#993f2b}
.evidence-properties{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:0;margin:0;padding:0}
.evidence-properties>div{min-width:0;border-bottom:1px solid #e1e5df;
  padding:12px 26px}
.evidence-properties>div:nth-child(odd){border-right:1px solid #e1e5df}
.evidence-properties dt{font:700 11px/1.5 system-ui,"Malgun Gothic",sans-serif;
  color:#52685d;margin-bottom:4px}
.evidence-properties dd{margin:0;font-size:13px;line-height:1.6;
  color:#243b32;overflow-wrap:anywhere;word-break:break-word}
.evidence-properties code{font-size:11px;color:#4e5d54}
.evidence-guidance{padding:12px 26px;background:#f0f2eb;border-bottom:1px solid var(--line)}
.evidence-guidance p{font-size:13px}
.evidence-actions{padding:13px 26px;display:flex;flex-wrap:wrap;gap:18px;align-items:center}
.evidence-actions a{font-size:13px;font-weight:780}
.evidence-actions span{font-size:12px;color:#5d7065}
.content-stack>.pager-box{padding:12px 20px}
.pagination{display:flex;gap:10px;flex-wrap:wrap}
.pagination a{border:1px solid #99ab9e;text-decoration:none;
  padding:8px 13px;background:#fff;font-size:13px}
.pagination a:hover{background:#e7ede6}
.content-stack>.shelf-title{background:transparent;border:0;padding:25px 0 4px;
  border-bottom:2px solid #8a988e}
.shelf-title h2{font-size:21px;margin:0 0 5px}
.shelf-title p{font-size:13px}
.content-stack>.shelf-entry{border-left:3px solid #7b9887;padding:19px 25px;
  background:#fffefa}
.shelf-entry h3{font-size:16px;margin-bottom:7px}
.shelf-entry p{font-size:13px;margin:5px 0}
.shelf-entry .entry-flag{display:inline-block;color:#993d25;font-weight:750}
.recipe-list{display:grid;grid-template-columns:1fr;margin:14px 0;padding:0!important;
  list-style:none;border:1px solid #c5d1c5}
.recipe-list li{padding:0;border-bottom:1px solid #c5d1c5;background:#fffefa}
.recipe-list li:last-child{border-bottom:0}
.recipe-list li>a{display:block;text-decoration:none;padding:16px 20px;
  font:770 12px/1.6 ui-monospace,Consolas,monospace;color:#225248}
.recipe-list li>a:hover{background:#e8eee6}
.recipe-list .recipe-copy{display:block;font:400 13px/1.65 system-ui,"Malgun Gothic",sans-serif;
  color:#4b5f55}
.review-steps li{padding:10px 3px 10px 6px;border-bottom:1px solid var(--line)}
.review-steps li:last-child{border-bottom:0}
.review-gates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:0;margin:0;padding:0;list-style:none}
.review-gates li{padding:13px 16px;border-bottom:1px solid #dae1d8;
  background:#f6f7f1}
.review-gates strong{color:#973e25}
.inventory-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  margin:12px 0;border:1px solid var(--line)}
.inventory-grid>div{padding:15px 18px;border-bottom:1px solid var(--line)}
.inventory-grid>div:nth-child(odd){border-right:1px solid var(--line)}
.inventory-grid dt{font-size:11px;color:#556960}
.inventory-grid dd{font-size:15px;font-weight:750;margin:5px 0 0;overflow-wrap:anywhere}
.page-footer{display:flex;align-items:center;justify-content:space-between;
  gap:12px;flex-wrap:wrap;padding:18px clamp(20px,3.5vw,50px);
  font:650 11px/1.6 ui-monospace,Consolas,monospace;
  color:#4d645a;border-top:1px solid var(--line);background:var(--paper)}
.page-footer a{color:#245649;font-size:11px}
@media (max-width:1100px){
  .app-shell{grid-template-columns:184px minmax(0,1fr)}
  .sidebar{padding-left:10px;padding-right:10px}
  .workspace{padding-left:22px;padding-right:22px}
  .topbar{padding-left:22px;padding-right:22px}
  .intro-workbench{grid-template-columns:minmax(0,1fr) 235px}
}
@media (max-width:880px){
  .app-shell{display:block}
  .sidebar{position:relative;top:auto;height:auto;min-height:0;overflow:visible;padding:13px 16px}
  .brand{padding:0 0 10px}
  .brand-mark{font-size:26px}.brand-name{font-size:23px}
  .brand-caption,.sidebar-label,.sidebar-bottom{display:none}
  .main-nav{display:flex;gap:0;overflow-x:auto;scrollbar-width:thin}
  .main-nav a{grid-template-columns:22px auto;flex:none;min-height:44px;
    padding:7px 11px;border-bottom:1px solid #44564a}
  .main-nav a[aria-current="page"]{padding-left:8px;border-left:3px solid var(--copper)}
  .topbar{min-height:52px}
}
@media (max-width:640px){
  body{font-size:14px}
  .workspace{padding:23px 15px 40px}
  .topbar{align-items:flex-start;flex-wrap:wrap;padding:12px 15px}
  .page-header{grid-template-columns:1fr;padding-bottom:18px;margin-bottom:18px}
  .page-reference{display:none}
  .page-header h1{font-size:31px}
  .content-stack{gap:12px}
  .content-stack>section,.content-stack>article{padding:18px 17px}
  .content-stack>.intro-workbench{display:block;padding:0}
  .intro-text{padding:27px 21px}
  .intro-title{font-size:34px}
  .quick-query{padding:21px;border-left:0;border-top:1px solid var(--ink)}
  .content-stack>.pillar-grid{padding:0}
  .pillar-card{grid-template-columns:36px minmax(0,1fr) 20px;
    padding:18px 13px;gap:9px}
  .pillar-card h3{font-size:16px}
  .pillar-number{font-size:19px}
  .content-stack>.trust-panel{grid-template-columns:1fr;padding:0}
  .trust-item{border-right:0;border-bottom:1px solid var(--line);padding:15px 19px}
  .trust-item:last-child{border-bottom:0}
  .evidence-properties{grid-template-columns:1fr}
  .evidence-properties>div:nth-child(odd){border-right:0}
  .evidence-title,.evidence-properties>div,.evidence-actions,.evidence-guidance{padding-left:18px;padding-right:18px}
  .review-gates,.inventory-grid{grid-template-columns:1fr}
  .inventory-grid>div:nth-child(odd){border-right:0}
  .content-stack form{display:grid}
  .content-stack input,.content-stack select,.content-stack button{max-width:100%;width:100%}
  .page-footer{padding:15px;display:block}
  .page-footer a{display:inline-block;margin-top:9px}
}
@media (max-width:400px){
  .intro-title{font-size:29px;overflow-wrap:anywhere}
  .page-header h1{font-size:28px}
  .pillar-card{gap:7px}
  .pillar-card p{font-size:12px}
}
@media (prefers-reduced-motion:reduce){
 html{scroll-behavior:auto}
}
"""

# Preserve the existing route taxonomy: changes below are presentation only.
def render_shell(name: str, content: str, routes: tuple) -> str:
    if (name not in PAGE_METADATA or type(content) is not str
            or type(routes) is not tuple or len(routes) != 4):
        raise ValueError("unregistered UCIE workbench page or routes")
    active, eyebrow, description = PAGE_METADATA[name]
    approved_routes = (
        "/local/error", "/local/engine", "/local/library", "/local/evolution"
    )
    if tuple(item[0] for item in routes) != approved_routes:
        raise ValueError("non-UCIE navigation route")
    nav = [
        '<a href="/local"' +
        (' aria-current="page"' if active == "/local" else '') +
        '><span class="nav-icon" aria-hidden="true">00</span><span>작업 개요</span></a>'
    ]
    for i, (href, label, _) in enumerate(routes, 1):
        nav.append(
            '<a href="' + escape(href, quote=True) + '"' +
            (' aria-current="page"' if active == href else '') +
            '><span class="nav-icon" aria-hidden="true">' +
            str(i).zfill(2) + '</span><span>' +
            escape(label, quote=True) + '</span></a>'
        )
    nav.append(
        '<a href="/local/policy"' +
        (' aria-current="page"' if active == "/local/policy" else '') +
        '><span class="nav-icon" aria-hidden="true">05</span>'
        '<span>운영 기준</span></a>'
    )
    if name == "시작":
        # Retain a semantic h1 without repeating a large generic "Start".
        page_heading = (
            '<div class="page-header page-header--home">'
            '<div><span class="eyebrow">WORK INDEX / 00</span>'
            '<h1 class="visually-hidden">UCIE 작업 개요</h1></div></div>'
        )
    else:
        page_heading = (
            '<div class="page-header"><div>'
            '<span class="eyebrow">' + escape(eyebrow, quote=True) + '</span>'
            '<h1>' + escape(name, quote=True) + '</h1>'
            '<p class="page-lede">' + escape(description, quote=True) +
            '</p></div><span class="page-reference" aria-hidden="true">'
            'UCIE / OWNER LOCAL<br>READ ONLY WORKSPACE</span></div>'
        )
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        '<title>UCIE Local V1 · ' + escape(name, quote=True) + '</title>'
        '<style>' + STYLE + '</style></head><body>'
        '<a class="skip-link" href="#workspace">본문으로 건너뛰기</a>'
        '<div class="app-shell"><aside class="sidebar" aria-label="UCIE 작업 공간">'
        '<a class="brand" href="/local" aria-label="UCIE 대시보드">'
        '<span class="brand-mark" aria-hidden="true">U.</span>'
        '<span class="brand-name">UCIE</span>'
        '<span class="brand-caption">EVIDENCE / CODE / REVIEW</span></a>'
        '<div class="sidebar-label">WORKBENCH&nbsp; / &nbsp;LOCAL</div>'
        '<nav class="main-nav" aria-label="주요 기능">' + ''.join(nav) +
        '</nav>'
        '<div class="sidebar-bottom"><div class="sidebar-sep"></div>'
        '<div class="connection"><span class="connection-dot" aria-hidden="true"></span>'
        'LOCAL · OWNER</div>'
        '<p>읽기 전용 기술 검토 공간<br>승인과 배포는 별도 절차</p></div>'
        '</aside><div class="page-column">'
        '<header class="topbar"><div class="breadcrumb">UCIE / WORKBENCH'
        '<span aria-hidden="true">/</span>' + escape(name, quote=True) +
        '</div><div class="top-tags">'
        '<span class="status-tag">LOCAL · 127.0.0.1</span>'
        '<span class="status-tag status-tag--hold">온라인·고객 출시 보류</span>'
        '</div></header>'
        '<main class="workspace" id="workspace" tabindex="-1">' +
        page_heading + '<div class="content-stack">' + content +
        '</div></main><footer class="page-footer">'
        '<span>UCIE Local V1 · 공개 근거만 사용 · 자동 규칙 승격 없음</span>'
        '<a href="/local/policy">운영·승인 기준 확인</a>'
        '</footer></div></div></body></html>'
    )


# The parent catalog retains all data / URLs / source validation. This skin
# changes *only* the presentation of full, already-rendered HTML envelopes.
LEGACY_STYLE = """
:root{color-scheme:light;color:#202a28;font:15px/1.75 system-ui,
  -apple-system,"Segoe UI","Malgun Gothic",sans-serif}
body{background:#f0efe9;color:#202a28}
main{max-width:1220px;margin:auto;padding:26px clamp(17px,3.5vw,45px) 55px}
main>header{border:1px solid #273d33;border-top:4px solid #a33e26;
  background:#f9f8f3;color:#202a28;padding:27px 31px}
main>header h1{font-size:clamp(27px,3.2vw,37px);line-height:1.25;
  letter-spacing:-.05em;margin:6px 0 12px;color:#1e2e26}
main>header .subtitle{color:#476053;font-size:13px}
main a{color:#1e5d4e;text-decoration-thickness:1px;text-underline-offset:3px}
main a:focus-visible,main button:focus-visible,main input:focus-visible,
main select:focus-visible,main summary:focus-visible{
  outline:3px solid #c75b24;outline-offset:3px}
.panel,.item,.empty,.detail,.v11-item{border:1px solid #bac8bc;
  border-radius:2px;background:#fffefa;box-shadow:none;padding:21px 24px}
.panel{margin:17px 0}
.panel h2{font-size:21px;line-height:1.35;color:#20382c}
.panel p,.item p,.detail p{font-size:14px;color:#435d50;line-height:1.8}
.items{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.item{padding:20px}
.item .meta{color:#315d4c}
main form{gap:13px}
main label{font-size:13px;color:#344d3e}
main input,main select{min-height:45px;border:1px solid #9aafa0;
  border-radius:2px;padding:10px 12px;background:#fff;color:#20352a}
main button{min-height:45px;background:#244b40;color:#fff;
  border-radius:2px;padding:9px 17px;border:1px solid #244b40}
main button:hover{background:#12392f}
.note{background:#edf0e7;border-left:3px solid #a33e26;
  padding:13px 16px;color:#3f564b;font-size:13px}
.toolbar{gap:8px;flex-wrap:wrap}
.chip,.toolbar a,.pages a{border-radius:2px}
.chip.active{background:#e3eee7;color:#235043;border-color:#97b4a0}
.pages{gap:11px;flex-wrap:wrap}
main dl{max-width:100%;overflow-wrap:anywhere}
main dt{font-size:12px;color:#4e6657}
main dd{overflow-wrap:anywhere}
main table{border-collapse:collapse;display:block;width:100%;
  max-width:100%;overflow-x:auto;font-size:13px}
main th,main td{text-align:left;padding:11px 12px;border:1px solid #d9e3d9;
  vertical-align:top;max-width:360px;overflow-wrap:anywhere}
main th{background:#e7ede4;color:#284536;white-space:nowrap}
main code,main pre{font:12px/1.65 ui-monospace,Consolas,monospace;
  white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}
main details{border:1px solid #b9c9bd;border-radius:2px;padding:12px;margin:10px 0}
main summary{cursor:pointer;font-weight:760}
nav[data-ucie-local-nav="true"]{display:flex;gap:10px;align-items:center;
  flex-wrap:wrap;margin:14px 0!important;border:1px solid #213c33!important;
  background:#223c33!important;border-radius:2px!important;
  padding:12px 18px!important;color:#e7eee8!important}
nav[data-ucie-local-nav="true"] strong,
nav[data-ucie-local-nav="true"] a{font-size:13px;color:#eaf1ea}
main footer{border-top:1px solid #c4d0c5;color:#4e6356;
  padding-top:18px;margin-top:28px}
@media(max-width:760px){
 main{padding:17px 13px 34px}
 main>header{padding:20px}
 main form{grid-template-columns:1fr}
 .panel,.item,.empty,.detail{padding:17px}
 .items{grid-template-columns:1fr}
 main input,main select,main button{max-width:100%;width:100%}
 nav[data-ucie-local-nav="true"]{gap:8px;padding:10px!important}
}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""


def skin_nested_local_page(content: str) -> str:
    """Enhance a validated UCIE first-party nested full HTML page once."""
    if (type(content) is not str or not content.startswith("<!doctype html>")
            or content.count("<head>") != 1
            or content.count("</head>") != 1
            or content.count("<body>") != 1
            or content.count("</body>") != 1
            or content.count("</html>") != 1):
        raise ValueError("unexpected UCIE nested HTML envelope")
    # Marker remains v02 for compatibility with existing owner-only receipts,
    # not a claim that the rendered visual system is the old V02 layout.
    if 'data-ucie-nested-theme="v02"' in content:
        return content
    return content.replace(
        "</head>",
        '<style data-ucie-nested-theme="v02">' + LEGACY_STYLE +
        '</style></head>', 1,
    )
