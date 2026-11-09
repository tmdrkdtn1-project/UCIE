"""UCIE Local V1: self-contained visual shell, no network assets or JS.

This presentation layer does not read sources, grant release, or alter any
request, review, approval, scheduled-task or database contract.
"""
from __future__ import annotations

from html import escape

STYLE = """
:root{
  color-scheme:light;
  --ink:#162640;--ink-2:#344762;--muted:#566981;
  --navy:#111d34;--navy-2:#1a2b48;--surface:#ffffff;
  --canvas:#f4f7fc;--line:#dfe6f1;--blue:#255cd8;
  --blue-dark:#1d4ebb;--aqua:#74e0ca;--warning:#9e551c;
  --shadow:0 12px 40px rgba(26,49,85,.055);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--canvas);color:var(--ink);
  font:15px/1.7 system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--blue);text-decoration-thickness:1px;text-underline-offset:3px;
  overflow-wrap:anywhere}
a:hover{color:var(--blue-dark)}
a:focus-visible,button:focus-visible,input:focus-visible,
select:focus-visible{outline:3px solid #f59e42;outline-offset:3px}
.skip-link{position:fixed;top:-70px;left:16px;z-index:100;
  background:#fff;color:#132746;padding:10px 16px;border-radius:10px;
  box-shadow:var(--shadow)}
.skip-link:focus{top:12px}
.app-shell{display:grid;grid-template-columns:264px minmax(0,1fr);min-height:100vh}
.sidebar{position:sticky;top:0;height:100vh;min-height:590px;overflow-y:auto;
  display:flex;flex-direction:column;padding:33px 19px 22px;
  color:#ebf4ff;background:radial-gradient(circle at 25% 0%,#24395e 0,#14243e 41%,#0d182d 100%)}
.brand{display:flex;gap:12px;align-items:center;padding:2px 10px 38px;
  color:#f7fbff;text-decoration:none;overflow-wrap:normal}
.brand:hover{color:#fff}
.brand-mark{display:grid;place-items:center;flex:none;width:44px;height:44px;
  border-radius:14px;background:linear-gradient(140deg,#c8fff2,#60ceb7);
  color:#12304b;font-weight:900;font-size:26px;letter-spacing:-2px;
  box-shadow:0 8px 24px rgba(91,224,191,.18)}
.brand-name{display:block;font-size:23px;font-weight:820;letter-spacing:.02em;line-height:1.15}
.brand-caption{display:block;margin-top:4px;font-size:9px;
  letter-spacing:.14em;color:#b1c4df;font-weight:720}
.sidebar-label{margin:3px 15px 13px;color:#8098ba;
  letter-spacing:.16em;font-size:10px;font-weight:800}
.main-nav{display:flex;flex-direction:column;gap:6px}
.main-nav a{display:flex;gap:12px;align-items:center;min-height:47px;
  padding:11px 12px;border:1px solid transparent;border-radius:12px;
  color:#bacbe3;text-decoration:none;font-size:13px;font-weight:640;
  transition:background .18s,color .18s,border-color .18s;overflow-wrap:normal}
.main-nav a:hover{background:rgba(255,255,255,.08);color:#fff}
.main-nav a[aria-current="page"]{color:#fff;background:rgba(126,168,233,.15);
  border-color:rgba(157,193,246,.2);box-shadow:inset 3px 0 0 #7ee6ce}
.nav-icon{display:grid;place-items:center;flex:none;width:29px;height:29px;
  border-radius:9px;background:rgba(255,255,255,.065);color:#a5bede;
  font-size:10px;letter-spacing:.04em;font-weight:850}
.main-nav a[aria-current="page"] .nav-icon{background:#6cddc4;color:#12304a}
.sidebar-bottom{margin-top:auto;padding:24px 12px 2px;
  color:#b4c6e1;font-size:12px}
.sidebar-sep{border-top:1px solid rgba(220,233,250,.13);margin-bottom:19px}
.connection{display:flex;gap:9px;align-items:center;color:#e3f3f4;font-weight:720}
.connection-dot{display:inline-block;width:8px;height:8px;border-radius:50%;
  background:#6fe2c5;box-shadow:0 0 0 4px rgba(111,226,197,.11)}
.sidebar-bottom p{margin:9px 0 0;color:#8fa6c5;line-height:1.55}
.page-column{min-width:0;display:flex;flex-direction:column}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;
  min-height:78px;padding:16px clamp(23px,3.5vw,58px);
  border-bottom:1px solid var(--line);background:rgba(255,255,255,.89)}
.breadcrumb{color:#536682;font-weight:680;font-size:12px;letter-spacing:.015em}
.breadcrumb span{padding:0 10px;color:#9cabc1}
.top-tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.status-tag{display:inline-flex;gap:7px;align-items:center;white-space:nowrap;
  padding:5px 11px;border-radius:999px;border:1px solid #dfebf5;
  background:#f5fafc;color:#42607a;font-size:11px;font-weight:780}
.status-tag--hold{color:#985625;background:#fff6ea;border-color:#f2dcc2}
.workspace{width:100%;max-width:1360px;padding:37px clamp(23px,3.5vw,58px) 50px;
  margin:0 auto;flex:1}
.page-header{margin-bottom:27px}
.eyebrow{display:block;color:#2356b7;font-size:10px;
  letter-spacing:.17em;font-weight:850;text-transform:uppercase}
.page-header h1{margin:5px 0 8px;line-height:1.25;font-size:clamp(28px,3vw,40px);
  font-weight:820;letter-spacing:-.045em}
.page-lede{margin:0;color:var(--muted);font-size:14px;max-width:760px}
.content-stack{display:grid;gap:18px;min-width:0}
.content-stack>section,.content-stack>article{
  margin:0;background:var(--surface);border:1px solid var(--line);
  border-radius:18px;padding:clamp(20px,2.5vw,29px);
  box-shadow:var(--shadow);min-width:0}
.content-stack>section>h2:first-child,.content-stack>article>h2:first-child{margin-top:0}
section h2,article h2{font-weight:810;letter-spacing:-.035em;font-size:21px;line-height:1.4}
section h3,article h3{font-size:17px;font-weight:770;letter-spacing:-.025em}
.content-stack p{margin:10px 0;color:var(--ink-2)}
.content-stack strong{color:#172b4e}
.content-stack small,.muted{color:var(--muted)}
.content-stack article a{font-weight:720}
main section ul,main section ol{padding-left:22px}
main li{padding:4px 0}
main code,main pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
  font-size:.91em;overflow-wrap:anywhere}
main pre{white-space:pre-wrap}
.content-stack form{display:flex;align-items:end;gap:12px;flex-wrap:wrap;
  margin:20px 0 13px}
.content-stack label{display:flex;flex-direction:column;gap:5px;
  font-size:12px;font-weight:730;color:#455d7b;flex:1 1 240px}
.content-stack input,.content-stack select{min-height:46px;
  padding:10px 14px;margin:0;width:min(100%,500px);
  border-radius:11px;border:1px solid #ced9e9;background:#fff;
  font:inherit;font-size:14px;color:#172a47;box-shadow:0 2px 5px rgba(16,46,80,.025)}
.content-stack input::placeholder{color:#93a2b6}
.content-stack button,.button-primary,.button-ghost{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  min-height:46px;padding:10px 19px;border-radius:11px;
  border:1px solid #245cd0;background:var(--blue);color:#fff;
  font:inherit;font-size:13px;font-weight:790;text-decoration:none;
  box-shadow:0 8px 22px rgba(37,92,216,.15);cursor:pointer;white-space:normal}
.content-stack button:hover,.button-primary:hover{background:var(--blue-dark);color:#fff}
.button-ghost{background:rgba(255,255,255,.09);border-color:rgba(255,255,255,.3);
  box-shadow:none;color:#fff}
.button-ghost:hover{background:rgba(255,255,255,.17);color:#fff}
.content-stack .hero{position:relative;isolation:isolate;overflow:hidden;
  display:grid;grid-template-columns:minmax(0,1.2fr) minmax(240px,.8fr);
  align-items:center;gap:18px;min-height:324px;padding:39px clamp(23px,4vw,48px);
  border:1px solid #263d60;background:linear-gradient(125deg,#152944 0%,#122e4c 59%,#124b60 100%);
  box-shadow:0 18px 45px rgba(10,40,70,.12);color:#fff}
.hero:before{content:"";position:absolute;z-index:-1;width:330px;height:330px;
  border-radius:50%;right:-70px;top:-120px;border:70px solid rgba(141,237,221,.06)}
.hero-copy{position:relative;z-index:1}
.hero .eyebrow{color:#81e4ce}
.hero h2{font-size:clamp(28px,3.3vw,46px);line-height:1.19;
  letter-spacing:-.055em;margin:12px 0 19px;color:#fff;font-weight:850}
.hero h2 em{font-style:normal;color:#8bf2d8}
.hero p{max-width:560px;color:#c5d7e9;margin-bottom:22px;font-size:14px;line-height:1.75}
.hero-actions{display:flex;gap:10px;flex-wrap:wrap}
.hero-visual{min-height:240px;display:grid;place-items:center;position:relative}
.hero-visual:before,.hero-visual:after{content:"";position:absolute;
  width:222px;height:222px;border-radius:50%;border:1px solid rgba(151,220,228,.22)}
.hero-visual:after{width:174px;height:174px;border-color:rgba(151,220,228,.13)}
.hero-core{width:119px;height:119px;border-radius:28px;display:grid;place-items:center;
  background:linear-gradient(140deg,rgba(140,229,215,.27),rgba(64,120,173,.32));
  border:1px solid rgba(181,244,235,.45);
  box-shadow:0 18px 55px rgba(3,10,30,.2);font-size:23px;letter-spacing:.06em;font-weight:880}
.hero-node{position:absolute;padding:7px 12px;background:#193753;
  border:1px solid rgba(163,231,230,.32);border-radius:999px;
  color:#d9f7ef;font-size:10px;font-weight:820;letter-spacing:.04em}
.hero-node--a{top:14px;left:4%}.hero-node--b{top:24px;right:-3%}
.hero-node--c{bottom:22px;left:0}.hero-node--d{bottom:19px;right:-2%}
.content-stack>.section-heading{background:transparent;border:0;box-shadow:none;
  padding:17px 0 1px}
.section-heading h2{margin:0 0 4px;font-size:23px}
.section-heading p{margin:0;color:var(--muted);font-size:13px}
.content-stack>.pillar-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:16px;border:0;padding:0;background:transparent;box-shadow:none}
.pillar-card{display:flex;flex-direction:column;min-height:225px;padding:25px;
  border:1px solid var(--line);border-radius:18px;background:#fff;
  color:var(--ink);box-shadow:var(--shadow);text-decoration:none;
  transition:transform .18s,border-color .18s,box-shadow .18s}
.pillar-card:hover{transform:translateY(-3px);border-color:#9cb8e6;
  color:var(--ink);box-shadow:0 17px 38px rgba(29,68,126,.11)}
.pillar-card:focus-visible{outline-offset:2px}
.pillar-card:nth-child(2){background:linear-gradient(135deg,#fff,#f6faff)}
.pillar-card:nth-child(3){background:linear-gradient(135deg,#fff,#f5fbfa)}
.pillar-top{display:flex;justify-content:space-between;align-items:center}
.pillar-number{display:grid;place-items:center;width:40px;height:40px;
  border-radius:11px;background:#eaf1ff;color:var(--blue);font-size:12px;font-weight:880}
.pillar-card:nth-child(3) .pillar-number{background:#e6f6f1;color:#137665}
.pillar-arrow{font-size:24px;color:#8c9db7;line-height:1}
.pillar-card h3{font-size:20px;font-weight:810;margin:19px 0 5px;color:#1a2e4b}
.pillar-card p{color:#566981;font-size:13px;line-height:1.68;flex:1;margin:0 0 12px}
.pillar-action{display:inline-flex;gap:8px;color:var(--blue);font-size:12px;font-weight:800}
.content-stack>.trust-panel{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
  padding:0;gap:0;overflow:hidden}
.trust-item{padding:23px 25px;border-right:1px solid var(--line)}
.trust-item:last-child{border-right:0}
.trust-label{display:block;color:#566981;font-size:11px;font-weight:780;margin-bottom:6px}
.trust-value{display:block;font-weight:850;font-size:15px;color:#1b3354}
.trust-value--hold{color:#a36228}
.trust-detail{display:block;margin-top:3px;color:#607187;font-size:11px;line-height:1.5}
.content-stack .result-summary{background:#f7faff;border-color:#ceddf7;box-shadow:none}
.content-stack nav.pagination{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.content-stack nav.pagination a{display:inline-flex;padding:8px 14px;border-radius:10px;
  text-decoration:none;border:1px solid #d4e1f3;background:#fff;font-weight:720}
.content-stack>.pager-box{padding:14px 20px;box-shadow:none}
.recipe-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  padding-left:0!important;gap:10px;list-style:none}
.recipe-list li{padding:14px 16px;border:1px solid var(--line);
  background:#f8fafd;border-radius:12px;font-size:13px}
.recipe-list a{display:inline-block;font-weight:790;letter-spacing:.01em}
.page-footer{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
  padding:20px clamp(23px,3.5vw,58px) 28px;border-top:1px solid var(--line);
  color:#566981;font-size:11px}
.page-footer a{color:#526e9f}
@media (max-width:1100px){
  .app-shell{grid-template-columns:222px minmax(0,1fr)}
  .sidebar{padding-left:12px;padding-right:12px}
  .hero-visual{transform:scale(.85)}
}
@media (max-width:880px){
  .app-shell{display:block}
  .sidebar{position:relative;top:auto;height:auto;min-height:0;overflow:visible;
    padding:14px 20px 15px}
  .brand{padding:3px 1px 14px}
  .brand-mark{height:37px;width:37px;font-size:23px;border-radius:11px}
  .brand-name{font-size:20px}
  .sidebar-label,.sidebar-bottom{display:none}
  .main-nav{flex-direction:row;gap:7px;overflow-x:auto;padding-bottom:3px}
  .main-nav a{min-height:40px;flex:none;padding:8px 10px}
  .nav-icon{width:23px;height:23px}
  .topbar{min-height:59px;padding-top:11px;padding-bottom:11px}
  .workspace{padding-top:27px}
}
@media (max-width:640px){
  .topbar{align-items:flex-start;flex-wrap:wrap;gap:5px}
  .top-tags{justify-content:flex-start}
  .status-tag{font-size:10px;padding:4px 9px}
  .workspace{padding:22px 15px 32px}
  .page-header h1{font-size:29px}
  .content-stack>.hero{display:block;min-height:0;padding:28px 22px}
  .hero h2{font-size:32px}
  .hero-visual{display:none}
  .content-stack>.pillar-grid{grid-template-columns:1fr}
  .pillar-card{min-height:170px}
  .content-stack>.trust-panel{grid-template-columns:1fr}
  .trust-item{border-right:0;border-bottom:1px solid var(--line);padding:16px 21px}
  .trust-item:last-child{border-bottom:0}
  .recipe-list{grid-template-columns:1fr}
  .content-stack form{align-items:stretch}
  .content-stack input,.content-stack select{width:100%}
  .content-stack button{width:100%}
  .page-footer{padding:20px 15px}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .pillar-card,.main-nav a{transition:none}
  .pillar-card:hover{transform:none}
}
"""

PAGE_METADATA = {
    "시작": ("/local", "OVERVIEW / 00", "네 가지 핵심 기술 영역과 로컬 검토 상태를 살펴보세요."),
    "오류 예방": ("/local/error", "PREVENTION / 01", "출처가 연결된 미검증 기술 근거를 검색하고 안전한 검토안을 만듭니다."),
    "후보 검토 작업": ("/local/error", "PREVENTION / REVIEW", "선택한 공개 근거의 수정 방향과 회귀시험 계획을 검토합니다."),
    "개발 엔진·스킬": ("/local/engine", "ENGINE / 02", "UCIE가 작성한 한정형 엔진과 합성 실험을 직접 선택합니다."),
    "통합 가상도서관": ("/local/library", "LIBRARY / 03", "SkillBook·편집 초안·공개 근거를 각각의 승인 상태와 함께 탐색합니다."),
    "SkillBook 실행": ("/local/library", "LIBRARY / RECIPE", "UCIE 작성 시험용 예제를 제한된 범위에서 실행합니다."),
    "SkillBook 실행 결과": ("/local/library", "LIBRARY / RESULT", "UCIE 자체 예제의 결과와 미검증 범위를 확인합니다."),
    "근거 기반 개선": ("/local/evolution", "EVOLUTION / 04", "이미 수집된 공개 근거의 개정과 검토 대기 상태를 살펴봅니다."),
    "개발 규칙": ("/local/policy", "GOVERNANCE", "로컬 인수 범위와 출시 전 필수 검토 기준을 확인합니다."),
}


def render_shell(name: str, content: str, routes: tuple) -> str:
    """Render only UCIE-authored markup within a fixed local-only shell."""
    if name not in PAGE_METADATA or type(content) is not str:
        raise ValueError("unregistered UCIE local visual page")
    active, eyebrow, description = PAGE_METADATA[name]
    nav = [
        '<a href="/local"' + (' aria-current="page"' if active == "/local" else '') +
        '><span class="nav-icon" aria-hidden="true">00</span><span>대시보드</span></a>'
    ]
    for index, (href, title, _) in enumerate(routes, 1):
        if href not in ("/local/error", "/local/engine", "/local/library",
                        "/local/evolution"):
            raise ValueError("unsupported UCIE local route")
        nav.append(
            '<a href="' + escape(href, quote=True) + '"' +
            (' aria-current="page"' if href == active else '') + '>' +
            '<span class="nav-icon" aria-hidden="true">' + str(index).zfill(2) +
            '</span><span>' + escape(title, quote=True) + '</span></a>'
        )
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        '<title>UCIE Local V1 · ' + escape(name, quote=True) + '</title><style>' +
        STYLE + '</style></head><body>'
        '<a class="skip-link" href="#workspace">본문으로 건너뛰기</a>'
        '<div class="app-shell"><aside class="sidebar" aria-label="UCIE 작업 공간">'
        '<a class="brand" href="/local" aria-label="UCIE 대시보드">'
        '<span class="brand-mark" aria-hidden="true">U</span>'
        '<span><span class="brand-name">UCIE</span>'
        '<span class="brand-caption">CODE INTELLIGENCE ENGINE</span></span></a>'
        '<div class="sidebar-label">FOUR PILLARS / LOCAL V1</div>'
        '<nav class="main-nav" aria-label="주요 기능">' + ''.join(nav) +
        '<a href="/local/policy"' +
        (' aria-current="page"' if active == "/local/policy" else '') +
        '><span class="nav-icon" aria-hidden="true">↳</span>'
        '<span>운영·검증 기준</span></a></nav>'
        '<div class="sidebar-bottom"><div class="sidebar-sep"></div>'
        '<div class="connection"><span class="connection-dot" aria-hidden="true"></span>'
        'LOCAL WORKSPACE</div>'
        '<p>소유자 PC에서만 접근합니다.<br>자료 승인과 배포 승인은 별도입니다.</p>'
        '</div></aside><div class="page-column">'
        '<header class="topbar"><div class="breadcrumb">UCIE WORKSPACE'
        '<span aria-hidden="true">/</span>' + escape(name, quote=True) + '</div>'
        '<div class="top-tags"><span class="status-tag">LOCAL · 127.0.0.1</span>'
        '<span class="status-tag status-tag--hold">온라인·고객 출시 보류</span>'
        '</div></header>'
        '<main class="workspace" id="workspace" tabindex="-1">'
        '<div class="page-header"><span class="eyebrow">' + eyebrow + '</span>'
        '<h1>' + escape(name, quote=True) + '</h1>'
        '<p class="page-lede">' + description + '</p></div>'
        '<div class="content-stack">' + content + '</div></main>'
        '<footer class="page-footer"><span>UCIE LOCAL V1 · 공개 근거만 사용'
        ' · 자동 규칙 승격 없음</span>'
        '<a href="/local/policy">운영·승인 기준 확인</a>'
        '</footer></div></div></body></html>'
    )
