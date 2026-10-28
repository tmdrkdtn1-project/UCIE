# UCIE P9 actual Windows host import regression: optional signed verifier (2026-10-28)

## Incident / owner-provided real host evidence

The owner ran both:
```powershell
& $py -B -m ucie_miner.product_v1 --ucie-root 'D:\UCIE' --query API_CONTRACT --limit 5
& $py -B -m ucie_miner.product_v1 --ucie-root 'D:\UCIE' --demo
```
Both failed **before executing the P9 entrypoint** with:

```text
product_v1.py -> signed_rule_library.py ->
ModuleNotFoundError: No module named 'ucie_public.fifth_owner_addendum'
```

The new P9 product module imported the original optional W07 signed-rule verifier eagerly. The user's UCIE Windows checkout does not have the Serial5 dependency at that module path. Ubuntu/Windows CI had the dependency available, so PR #116 CI 4/4 was **not sufficient evidence** that the existing user's dirty Windows checkout could start the application.

## Minimal exact fix

- Remove *only* the eager `from .signed_rule_library import inspect_signed_library` statement from `src/ucie_miner/product_v1.py`.
- Load the **unchanged original** signed Rulepack verifier only inside the branch where the owner provided both `--serial4-pack` and `--owner-public-trust`. On missing verifier module with explicit pack request, fail closed: `P9_PRODUCT_FAIL_CLOSED` and `ProductIntegrationError('EXPLICIT_SIGNED_RULEPACK_VERIFIER_DEPENDENCY_MISSING_NO_GO')`. No fake signed rule verification or silently trusted pack.
- Normal public library, Stage14, P8, first-party demo and portable draft **must not import the signed verifier or require its optional Serial5 source file**.
- Preserve existing Stage10/12/14 data, signed originals, running public miner, original two P8 events, P9 draft, all unrelated dirty files. Do not restore/import unrelated modules or overwrite local `ucie_public` files.

## Regression test and acceptance

`tests/test_ucie_p9_product_v1.py` now launches a fresh Python `-I` subprocess with a test-only import trap reproducing the missing `ucie_public.fifth_owner_addendum` and asserts:
1. `product_v1.main()` with `--demo` returns normal read-only `P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO` output.
2. Optional signed shelf reports `NOT_INSPECTED_NO_GO`.
3. The portable first-party demo still proves exact-result equivalence.
4. When explicit signed paths are supplied, the unavailable dependency **fails closed**.
5. Zero network and operating DB writes.

The owner should repeat original two commands on Windows after the source fix is applied. Until that observed receipt is supplied, classify **GitHub CI PASS only** and `OWNER_HOST_P9_FIXED_RUN_UNOBSERVED` — never declare P9/V1 accepted.

This is a narrow startup regression repair, **not another W05 miner/research expansion**.
