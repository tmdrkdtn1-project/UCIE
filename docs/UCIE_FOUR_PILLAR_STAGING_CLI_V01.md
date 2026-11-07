# UCIE 4대 제품 기능 — 설치형 실행 진입점 V0.1

**상태:** UCIE 자체 작성 기능의 합성·격리 실행을 제공하는 스테이징 빌드. **지정 고객에게 최종 배포되는 완전본이 아니며**, SkillBook 외부 반출, 고객 사용권 발급, 자동 규칙 승격, 실제 고객 프로젝트 스캔을 승인하지 않는다.

## 실제로 실행하는 구성

| 제품 축 | 호출되는 실제 첫-party 모듈 | 반환하는 증거 |
|---|---|---|
| 오류 예방 | `guarded_scandir.GuardedScandir`, `skillbook_scandir_recipe_v01.bounded_regular_file_names` | OS 임시 폴더의 합성 파일 2개에 대한 경계·자원 종료 결과 |
| 개발 엔진·스킬·학습 로직 | `capability_trials.evaluate_ucie_owned_recipe` | 세 종류 UCIE 자체 알고리즘의 실제 동등성·작업량 결과 |
| 가상도서관·SkillBook | `skillbook_product_v01.search_skillbooks/get_skillbook`, `skillbook_git_porcelain_recipe_v01.summarize_porcelain_v1_z` | Python/Git 2권의 출처 해시·장 수·기계용 계약과, 경로를 노출하지 않는 합성 Git 소비 결과. 두 권 모두 미승인 상태를 그대로 반환 |
| 근거 기반 개선 | `experience_evolution.run_evolution_cycle(record=False)` | 별도 임시 UCIE 실험에 따른 데이터셋 해시·정확한 결과 동등성·다음 실험 제안. 운영 알고리즘 변경·기록·승격 없음 |

이 실행 경로는 실제 구현된 모듈을 호출하지만 **합성 워크로드에 한정**된다. 실제 고객 사용성·기능 완성·독립 보안 검증을 대체하지 않는다.

## 실행 명령

깨끗한 스테이징 PC나 검증용 독립 가상환경에서 이 소스 커밋으로 패키지를 구축·설치한 경우:

```powershell
# 설치된 실행 명령으로 네 축을 모두 확인
ucie-product-preview --pillar all

# 실제 UCIE 작성 SkillBook 도서관의 Git 자료 검색
ucie-product-preview --pillar virtual_library_and_skillbooks --query porcelain

# 세 개발·스킬·학습 알고리즘의 합성 실험
ucie-product-preview --pillar development_engines_and_skills
```

Python 직접 호출:

```powershell
python -m ucie_miner.customer_staging_v01 --pillar all
```

출력은 JSON 한 건이다. 명령은 **경로·실제 소스 코드·개인키·고객 신원·작업 스케줄러 인자**를 받지 않는다. `--query`는 48자 이내 도서관 검색에만 사용된다. 내부 예외는 실패 상태로만 표시하여 로컬 파일명과 비밀이 예외 메시지로 노출되지 않도록 한다.

## 고객 배포 이전에 남아 있는 실제 기능

1. C0: 미승인 SkillBook 2권의 인간 검토·출처 재검증·내용 정확성·상업 재배포 권리 판정. 현재 `FIRST_PARTY_DRAFT_NOT_APPROVED`를 자동으로 바꾸지 않는다.
2. C1: 고객용 설치·제거·Windows 설정/서비스·원본 서명·필수 문서·4대 기능 전체의 실제 사용자 워크플로를 하나의 완전본으로 패키징. 이 CLI는 **진입점 스테이징 시험**이지 최종 설치 프로그램이 아니다.
3. C2: 고객별 상용 권리·보안/의존성 점검, 독립 시험 또는 승인된 완전본 범위의 위험 수용.
4. C3: 고객별 사용권과 소유자 키 서명, 비공개 배포 저장소, 취소·재발급·만료·장비 범위 검증.
5. C4/C5: 승인된 고객의 격리 환경에서 설치→네 기능 사용→업데이트→롤백→제거 인수 및 최종 소유자 배포 승인.

## 보안·QA 게이트

- `tests/test_ucie_customer_staging_v01.py`는 각 네 축 실제 실행, 기능 분리, 부정 인자·비밀 비노출, 출시 거부를 시험한다.
- `tests/test_ucie_staging_wheel_smoke_v01.py`는 오프라인 구축한 wheel의 설치 경로에 `ucie-product-preview` entry point가 실제 존재하는지 확인하고, 그 **설치된 wheel**에서 네 축을 실행한다.
- GitHub CI 네 환경 (Windows/Ubuntu × Python 3.13/3.15) 모두 통과해야 병합. `D:\UCIE`의 미정리 소유자 작업본이나 시간당 운영 수집기는 변경하지 않으며, 오전 9시 보고 재가동도 하지 않는다.
- `customer_distribution_authorized=false`, `customer_bundle_signed=false`, `complete_customer_functional_acceptance=false`가 실제 고객/권리 검증 전에 유지돼야 한다.

출시 최종 기준: [완전본 고객 전용 배포 계약](UCIE_FULL_PRODUCT_PRIVATE_CUSTOMER_RELEASE_V1.md) / [이슈 #199](https://github.com/tmdrkdtn1-project/UCIE/issues/199).
