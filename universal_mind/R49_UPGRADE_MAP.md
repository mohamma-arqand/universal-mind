# R49_UPGRADE_MAP — نقشهی «شفافیتِ کامل، زمانبندِ تمام، چهرهی زنده»

## اصل (از سنجشِ واقعی R49 — نه حدس)
پوشش کل: **95%** (28,345 stmt، 1,399 miss، 1,674 تست سبز در 477s). تولید زیرِ ۱۰۰٪:
۱۲۸ ماژول؛ زیرِ ۹۰٪: ۴۴. تحلیلِ واردکننده (production importers) مردهها را از زندهها
جدا کرد: فقط **۲ ماژول مردهی واقعی** (`path_optimization.py`, `merit_learning.py` —
imp=0، self-refs=0، تستِ خودشان، جایگزین زنده: planner_learning + absorption benchmark).
۴۴ LIVE زیرِ ۹۰٪ = چهرههای واقعی اپراتور: رندرِ گزارشِ فارسی، زمانبند، اپِ دسکتاپ،
اورکستراتور، CLI. ریشهی شکافها شاخههای بی-تستِ رفتارهای REAL است، نه کد مرده.

## موج ۱ — حذفِ مردهها + اصطکاکها (پایه)
- [ ] **۱. حذف path_optimization.py + merit_learning.py + تستهایشان** (تولید-مرده؛
  جایگزین زنده موجود). DoD: حذف تمیز، رفرنس باقیمانده=۰ (AST guard)، تستها -۱۶ (صحیح)،
  فول suite سبز، ruff/mypy 0≤0. KPI: تولید بدونِ مردهی بی-خواننده. پیچیدگی: کم.
- [ ] **۲. فیکسهای B,F**: B007 (probe_r44: `_constructor`)، B009 (conftest:
  `config.addinivalue_line`)، B905 (test_r45_wave2: `zip(strict=True)`).
  B027 = hook اختیاری (per-file ignore). DoD: ruff B,F تولید=۰. KPI: ۰ یافتهی تولید.
  پیچیدگی: کم.

## موج ۲ — تستهای LIVE (شناختِ کامل)
- [ ] **۳. persian_report تا >95%**: تستهای goal-report (۷)، speech (۷)، excel-read (۳)،
  screenshot/webfetch/pdfreader/ocr/database (هرکدام ۱). DoD: 55 miss → ≤10.
  KPI: هر جملهی گزارش از تست عبور کند. پیچیدگی: متوسط.
- [ ] **۴. scheduler تا >95%**: run_due contest/voice/fail (15)، backup_database (13)،
  _contest_for (11)، parse_folder_watcher/_resolve_known_folder (5). DoD: 57 → ≤15.
  KPI: همهی شاخههای tick از تست عبور. پیچیدگی: متوسط.
- [ ] **۵. desktop_app تا >85%**: _run_new_goal/_resume_goals/_refresh_*/_chat_send/
  _vote/_register_schedule (UI headless با tk_root withdraw). DoD: 201 → ≤120.
  KPI: هر دکمهی اپ یک تست. پیچیدگی: بالا.
- [ ] **۶. cli.py تا >95%**: dispatch شاخهها (61 miss: goal/fa-contest/remote-face/
  health-tick). DoD: 61 → ≤15. KPI: هر زیر-فرمان یک تست. پیچیدگی: متوسط.

## موج ۳ — تراز جهانی + بستن
- [ ] **۷. orchestration/_flow_params + superplatform_dashboard + zip_suite/webfetch
  + vocab_breathing تا >92%**. DoD: شاخههای flow از تست. KPI: flowهای واقعی پوشیده.
  پیچیدگی: متوسط.
- [ ] **۸. فول verify v49 + کامیت ایزوله + حافظه**. DoD: VERIFY=READY؛ ratchet 0≤0؛
  پوشش گزارشی per-module. KPI: تستها ≥1,680؛ پوشش ≥95.5%.

## ترتیب و قاعدهی پذیرش
هر قلم: پیادهسازی → تست سبز → شاهد زنده → ruff تمیز → ratchet 0≤0 → فول pytest →
کامیت ایزوله. تستی که رفتارِ غلط را pin کرده مقدس نیست. حذفِ کد مرده = تستها کم
میشود — صحیح است، نه رگرسیون.
