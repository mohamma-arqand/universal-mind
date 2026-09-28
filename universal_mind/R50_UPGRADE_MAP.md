# R50_UPGRADE_MAP — نقشهی «چهرهی دسکتاپِ تمام، ابزارهای واقعیِ بی-سوراخ»

## اصل (از سنجشِ واقعی R50 — نه حدس)
فول suite: **1,741 passed** در 414s؛ پوشش کل **95.7%** (28,792 stmt، 1,243 miss).
زیرِ ۹۰٪: هنوز ۴۴ ماژول — اما رنجها کوچک شدهاند: بزرگترین شکافِ باقیمانده
**desktop_app.py (141 miss، 77.3%)**؛ همهی بقیه <30 miss. این راند = بستنِ چهرهی
اپراتور تا >90% و ۸ ابزارِ واقعیِ دیگر (هرکدام ۷-19 miss — شاخههای خطا/خروجی).

## موج ۱ — چهرهی دسکتاپ (141 miss → ≤60)
- [ ] **۱. تستهای LIVE برای متدهای بی-تستِ desktop_app**: _builder_save (17)،
  _open_dashboard (14)، _run/_do_work (14)، _run_persian/_do_persian_work (10)،
  _run_chain (9)، _on_fa_typing (7)، _resume_goals (6)، _run_schedules (5)،
  _builder_add/_refresh_* (4×3)، _selected_chain (4)، _show_preview_in (4).
  الگو: همانی که جواب داد — tk_root withdraw، ارسال مستقیم متد، mock فقط برای
  subprocess/webbrowser در سطح ماژولِ desktop_app (نه جای دیگر).
  DoD: desktop_app >90%، فول suite سبز. KPI: هر دکمه + هر مسیر خطای واقعی تست شود.
  پیچیدگی: بالا.

## موج ۲ — ۸ ابزارِ کوچک (هرکدام تا >92%)
- [ ] **۲. real_clipboard (11)، seed_memory (7)، llm_connector (8)، conversational (18)،
  speech_tool (19)، email_outbox (19)، pdfreader_tool (12)، goal_parser (11)**.
  الگو: شاخههای خطا و خروجیهای واقعی — نه mock-در-تست بلکه ابزارِ واقعی با
  ورودیِ واقعی (فایل موقت، نویز، متن فارسی).
  DoD: هر ماژول >92%. KPI: ۱۰۱ miss این ۸ ماژول → ≤30. پیچیدگی: متوسط.

## موج ۳ — فول verify + کامیت ایزوله + حافظه
- [ ] **۳. فول verify**: VERIFY=READY؛ ratchet 0≤0؛ پوشش ≥96.5%؛ تستها ≥1,760.
  کامیت ایزوله در هر موج. KPI: زیرِ ۹۰٪ فقط ماژولهای سخت-محیط (اسمبلی/تلفن).

## ترتیب و قاعدهی پذیرش
هر قلم: پیادهسازی → تست سبز → شاهد زنده → ruff B,F=0 → ratchet 0≤0 → فول pytest →
کامیت ایزوله. تستی که رفتار غلط را pin کرده مقدس نیست.
