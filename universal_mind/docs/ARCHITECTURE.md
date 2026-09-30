# معماری ذهن جهانی (Universal Mind) — سند بازیابی

> این سند برای **بازیابی** نوشته شده: هر کسی (یا هر عاملی) با خواندن این فایل بفهمد سیستم از چه لایههایی ساخته شده، کجا چیست، و چطور راستیآزمایی میشود. همهی اعداد اندازهگیریشدهاند.

## اعداد زنده (اندازهگیریشده)

| سنجه | مقدار |
|---|---|
| ماژولهای پایتون | **۱۱۲** |
| خطوط کد مؤثر (بدون تست) | **~۱۷٫۷۴۲** |
| فایلهای تست | **۲۵۳** |
| تستها | **~۲٫۰۱۴** |
| probeهای زنده | **۹۰** |
| قابلیتهای واقعی ثبتشده | **۲۵** |
| گیتهای verify | **۵** (interpreter / lint / mypy-ratchet / tests / receipt / probes) |

## نقشهی لایهها

### ۱. لایهی زبان (ورودی فارسی)
| ماژول | نقش |
|---|---|
| `persian_router.py` (۱۲۱۷ خط) | قلب: جدول واژگان `_VOCAB` (فعل فارسی → قابلیت)، ترتیب وابستگیها (`_PRIORITY`)، mode-verbs (بیصدا/توضیح بده/هدف)، disambiguation نیت |
| `persian_params.py` | استخراج پارامترهای واقعی از جمله (اعداد، مسیرها، بازهها، نوع عملیات) — یک branch برای هر قابلیت |
| `persian_report.py` | گزارش فارسی: نام فارسی قابلیتها، ارقام فارسی، روایت نتیجهی هر قابلیت |
| `persian_date.py` | تقویم جلالی (`jalali_date`)، resolve زمانهای نسبی (فردا/دیروز) |
| `spelling_recovery.py` | بازیابی غلط املایی فارسی |
| `learned_vocab.py` | واژههای یادگرفتهشده («واژهی X یعنی Y») — overlay روی `_VOCAB` |
| `unknown_harvest.py` | برداشت واژههای ناشناخته در لحظهی رد صادقانه (نقشهی شکاف دانشی) |

### ۲. لایهی تصمیم و اجرا
| ماژول | نقش |
|---|---|
| `orchestration.py` (۶۳۳) | اجرای زنجیره؛ جریان دادهی تولیدکننده → مصرفکننده (flows) |
| `tool_registry.py` / `real_tool_registry.py` | دایرةالمعارف ابزارها؛ `capability → connector` (۲۵ ورودی) |
| `connectors.py` | پروتکل `Connector`/`ConnectorResult` + `SubprocessConnector` (allowlist) |
| `arete/` (پکیج) | داوری ARETĒ: حکمت/شهامت/اعتدال/عدالت روی هر اجرا |
| `contested_execution.py` + `ab_contest.py` | مسابقهی A/B روی مسیرهای مبهم؛ برنده اعلام میشود |
| `adaptive_orchestration.py` / `adaptive_weaver.py` | ترتیب بهینهی گامها از تاریخچهی واقعی |
| `dependency_planner.py` | مرتبسازی گامها بر اساس نیاز واقعی (تولیدکننده قبل از مصرفکننده) |
| `quality_gate.py` / `live_judge.py` / `cross_examiner.py` | دروازههای کیفیت و وارسی مستقل نتیجه |

### ۳. لایهی قابلیتهای واقعی (ابزارها)
| گروه | ماژولها |
|---|---|
| اسناد | `pdf_suite.py`، `pdfreader_tool.py`، `excel_suite.py`، `csv_suite.py`، `zip_suite.py` |
| داده و محاسبه | `data_suite.py` (numpy)، `ai_suite.py` (sklearn)، `compute_adapter.py` (node)، `chart_suite.py` (matplotlib) |
| ادراک | `screenshot_tool.py`، `ocr_tool.py`، `vision_suite.py`، `hearing.py` (STT) |
| عمل سیستمی | `speech_tool.py` (SAPI TTS)، `real_notify.py` (toast)، `real_clipboard.py`، `real_media.py`، `real_archive.py` |
| شبکه | `webfetch_tool.py`، `email_outbox.py` (RFC-822 + SMTP) |
| **جدید R53** | `file_search_tool.py` (جستجوی دیسک، فقطخواندنی)، `file_dedupe_tool.py` (SHA-256، پیشنمایش-اول)، `system_status_tool.py` (uptime/RAM/دیسک/باتری) |
| مدل زبانی | `llm_connector.py` (OpenAI-compatible؛ **نیازمند `UM_LLM_BASE_URL`** — فعلاً غیرفعال) |

### ۴. لایهی حافظه و هوش تجمعی
| ماژول | نقش |
|---|---|
| `database_suite.py` | استور پایدار SQLite (`~/.universal-mind/mind.db`)، journal=DELETE، pool خواندن |
| `run_history.py` | تاریخچهی هر اجرا (route، flows، durations، outcome_class) |
| `named_memory.py` | حافظهی نامدار («یادت باشد …») |
| `conversation_memory.py` | ضمیر و ارجاع («حالا نمودارش را بکش») |
| `operator_preferences.py` | ترجیحهای یادگرفتهشده (شامل `voice_muted`) |
| `planner_learning.py` / `success_predictor.py` / `semantic_predictor.py` | یادگیری از نتیجهی اجراها |
| `episodic`/`named_memory`/`seed_memory`/`synthesis.py` | حافظهی رویدادی و ترکیب دانش |
| `today_page.py` / `daily_briefing.py` / `weekly_letter.py` / `yearbook.py` / `tick_pulse.py` | گزارشهای زمانی از دادهی واقعی |

### ۵. لایهی زمانبند و خودمختاری
| ماژول | نقش |
|---|---|
| `scheduler.py` (۶۸۹) | زمانبند تکرارشونده + **یادآور یکبارمصرف** (`kind='once'`, `run_at`)؛ tick؛ backup چرخشی؛ وفادار به قانون بیصدا |
| `agent_loop.py` | حالت هدف چندگامی: parse → start → run → report، با poison-down |
| `goal_parser.py` / `goal_map.py` | تجزیه و نقشهی اهداف |
| `tick_pulse.py` / `disk_watch.py` / `drift.py` | ضربان، پایش دیسک، رانش کارایی + `backup_health.py` |

### ۶. لایهی رابطها
| ماژول | نقش |
|---|---|
| `desktop_app.py` (۹۱۶) | اپ Tk: تکقابلیت، تحلیل، زمانبندی، **یادآورها**، **سیستم**، اهداف، نشست، فرمان فارسی، زنجیره، گفتگو |
| `cli.py` (۵۲۵) | CLI |
| `reflexive.py` (۴۲۶) | پرسشهای دربارهی خود (اعداد واقعی از DB) |
| `conversational.py` | مکالمهی کوتاه + **هویت** (اسمت/کی هستی/وضعیتت/چه بلدی) |
| `dashboard.py` / `superplatform_dashboard.py` / `remote_face.py` | داشبوردهای HTML از دادهی واقعی |

## قوانین بنیادین (Laws)

1. **قانون صداقت** — هیچ عددی جعل نمیشود؛ سیگنال خواندهنشده *نام برده* میشود؛ فرمان ناشناخته «نشناختن» میگوید نه حدس.
2. **قانون یک ساعت** — همهی زمانها محلی؛ جدولها `datetime('now','localtime')`؛ روزهای «امروز» محلیاند.
3. **قانون بیصدا (MUTE)** — یک سوئیچ (`voice_muted` رکورد ماندگار یا `UM_MUTE=1`) که `speak()` زنده میخواند؛ بیصدا صادقانه است (`ok/spoken/muted/voice='(muted)'`). جزئیات: `docs/MUTE_LAW.md`.
4. **قانون ایموجی** — SAPI نام ایموجی را بلند میخواند؛ `speak()` ایموجیها را قبل از سیم حذف میکند.
5. **قانون حذف** — هیچ فایلی بدون «تأیید کن» حذف نمیشود؛ پیشنمایش پیشفرض است؛ اصل هر گروه حفظ میشود.
6. **قانون بکاپ** — بکاپ با API خود SQLite + `PRAGMA integrity_check`؛ چرخش keep=3.

## راستیآزمایی (Verification)

```bash
cd D:/workspaces/baddanKhoda/universal_mind
PYTHONPATH=.. python scripts/verify.py     # ۵ گیت: interpreter/lint/ratchet/tests/receipt/probes
PYTHONPATH=.. python scripts/probe_r53_waves.py   # ۱۰ گواه زندهی قابلیتهای جدید
```

- گیت تست با JUnit به `artifacts/junit.xml` مینویسد؛ `generate_receipt.py` رسید میسازد.
- گیت lint در حالت آفلاین به ruff پینشدهی venv برمیگردد (fallback اندازهگیریشده).
- هر probe با `--junit-xml=` قابل ثبت در artifacts است.

## فرمانهای کلیدی برای شروع کار مجدد

| کار | فرمان / پرسش فارسی |
|---|---|
| آزمون سلامت | «وضعیت سیستم را بگو» / «وضعیتت چطوره؟» |
| قابلیتها | «چه کارهایی بلدی؟» / `docs/COMMANDS.md` |
| یادآور | «یادم بنداز که فردا ساعت ۸ …» / «یادآورهای من» |
| جستجوی فایل | «فایلهای بزرگ دیسک D را پیدا کن» |
| تکراریها | «فایلهای تکراری در دانلودها را نشان بده» سپس «— تأیید کن» |
| بیصدا/صدا | «بیصدا» / «باز صدا» |
| تست و گیت | `scripts/verify.py` |

## شکافهای شناختهشده (صادقانه)

- **مدل زبانی وصل نیست** — پرسشهای دانشی («هویج چیه؟») مسیر llm میگیرند ولی بدون `UM_LLM_BASE_URL` پاسخ صادقانهی «وصل نیست + راهنمای وصلکردن» میدهند و پرسش در `unknown_harvest` ثبت میشود. (طبق تصمیم اپراتور عقب افتاده.)
- **لینوکس/مک پشتیبانی نمیشود** — ابزارهای OS-level (SAPI/OCR/toast/WMI) ویندوزیاند.
- **توزیع PyPI ندارد** — روی همین ماشین اجرا میشود.
