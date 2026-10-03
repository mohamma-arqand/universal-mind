# Changelog — Universal Mind

All notable changes to this project. The waves (R##) are the project's own
release rhythm; each wave is measured live, fixed with pinned tests, and
sealed only behind `python scripts/verify.py` printing READY.

## R63 — جاروی جمله‌های ترکیبی (2026-10-03)

جاروی ۱۵ فرمان واقعیِ ترکیبی/روزمره: ۱ OK / ۸ کلاس شکاف — همه بسته شدند. مهر پنج‌ران شد چون قانون صداقتِ نمودار، ۴ باگ واقعیِ پنهان را بیرون کشید:

- **P1 گیت teach**: «قابلیت جدید یاد بگیر: ... برق رفت یعنی ...» overlay مسموم می‌ساخت (رفت→برق)؛ تعریف باید کلِ جمله باشد + قابلیت واقعی یا ردِ نام‌دار.
- **P2 جملهٔ فایل+محتوا**: «فایل گزارش.md بساز و داخلش بنویس X» → فایل واقعی با محتوای دقیق (نام فارسی؛ ناحیهٔ کاری؛ بدون نام = ردِ نام‌دار).
- **P3 نمودار بدون داده = رد نام‌دار** (قانون «پیش‌فرضی که جواب می‌دهد»، نسخهٔ چارت): ChartSuite رد می‌دهد؛ A/B دیگر DEFAULT_SERIES تزریق نمی‌کند و برنده series اپراتور را نگه می‌دارد؛ سرخط گزارش وقتی همهٔ گام‌ها مردند «❌» می‌گوید.
- **P4 اکشن پنجره**: «پنجره‌های نوتپد را ببند» — بستنِ GRACEFUL واقعی با نام‌های فارسی، escape در PowerShell، ردِ نام‌دار با لیست واقعی. گواه زنده: Notepad واقعی بسته شد.
- **P5 فیلتر RAM**: «بیشتر از ۱ گیگ رم» → فیلتر واقعی یا «هیچ پردازشی ...» صادقانه.
- **P6 env-var**: TEMP واقعی؛ نامِ راز‌نما mask (توکن کاشته‌شده هرگز چاپ نشد)؛ ناموجود = رد نام‌دار.
- **P7 زمان از فکت آموخته‌شده**: «چند ساعت از خواب من گذشته؟» → محاسبهٔ واقعی از timestamp فکت/یادآور؛ بدون آن ردِ صادقانه + جملهٔ راه‌گشا.
- **P8 agenda هفته‌ای**: «برنامه هفته آینده من چیست؟» دیگر به llm نمی‌افتد.
- **P9 probe_r63_sweep**: ۱۰ گواه زنده ۱۰/۱۰ + ثبت در verify.

**۴ باگ واقعی که مهر بیرون کشید**: (۱) goal_parser فهرست‌های «۲ و ۵ و ۹» را وسط می‌شکافت؛ (۲) آنافورا دادهٔ ران قبلی را می‌انداخت؛ (۳) teach رجیستری را غلط می‌پرسید؛ (۴) CLI پارامز را پارس و رها می‌کرد.

مهر: verify 6/6 READY (overall=pass، ۲۴۹۰ تست/۰ شکست، pin ccc81ad). ۲۸ قابلیت.

## R62 — صف کلاس‌های باقی‌مانده (2026-10-03)

جاروی ۱۷ فرمانی روی کلاس‌های باقی‌مانده از بازبینی هفت‌پرسونایی: ۱ OK / ۱۶ شکاف در ۶ کلاس — همه بسته شدند.

- **T1 قرار/تقویم**: «جلسه شنبه ساعت ۱۰ است — یادت باشد» حالا یادآور واقعی می‌سازد (روز-هفته با فاصلهٔ محاسبه‌شده (target-today)%7؛ «آینده» = چرخهٔ بعد؛ قانون زیررشتهٔ بار چهارم: «جل**سه شنبه**» شامل «سه شنبه» است — مچ در مرز واژه؛ نیم‌فاصله پیش از جدول نرمال می‌شود). «قرارهایم» نمای agenda.
- **T2 دانش-پرسش**: «هوا تهران چطوره؟» → «پرسشِ «هوا» دادهٔ بیرونی می‌خواهد — جوابِ حدسی نمی‌سازم» + دو راه واقعی (مدل زنده / «سایت X را بخوان») + برداشت به unknown_terms برای harvest واقعی. «خبر چیست؟» به تلهٔ تاپیک‌ها افتاد و در ران-۲ برگشت به وضعیت ۵ سیگنال خود پلتفرم.
- **T3 قابلیت ۲۸ textsummarize**: خلاصه‌سازی استخراجی فارسی بدون LLM — جمله‌های خودِ متن (همپوشانی واژه + پاداش جملهٔ اول)، هرگز جملهٔ تولیدی، «۳ جمله از ۷ جملهٔ متن».
- **T4 دسترس‌پذیری گفتار**: «کندتر حرف بزن» → prefِ speech_rate ±۲ (کف/سقف ±۱۰) → هر «بلند بخوان» + دیده‌شدن در تنظیمات.
- **T5 لغو صادقانه + باگ تاریخی**: «لغو کن» = ردِ نام‌دار + نام آخرین کار واقعی + درمان هر نوع اثر. باگ تاریخی: ثبت یادآور هیچ‌وقت در run_history ردیف نمی‌گذاشت — بسته شد.
- **T6 probe_r62_sweep**: ۱۲ گواه زنده همه PASS + ثبت در verify.

مهر: verify 6/6 READY (overall=pass، ۲۴۴۵ تست/۰ شکست، receipt pin e2ed3f1). ۲۸ قابلیت، ۲۴۷ واژه.

## R61 — 2026-10-02 — The Deep-Review Wave (honesty + safety + voice)

Born from a 150-command live review through seven personas
(docs/DEEP_REVIEW_R61.md), not from imagination.

### Fixed — honesty law breaks
- `«قیمت دلار الان چنده؟»` answered «نتیجه ۴» (the 2+2 default leaked):
  compute without a real expression now refuses BY NAME.
- `«۲۰ درصد از ۵۰۰ چنده؟»` answered ۵۲۰ (percent built as a sum): percent
  belongs to the data suite alone; the answer is «برابر ۱۰۰».
- `«ساعت چنده؟` mixed two calendars («۲ دی» + «۱۴۰۵/۰۷/۱۰»): one clock,
  one calendar — Jalali day and month.
- `«رگرسیون روی این اعداد»` silently trained on default data: no data in
  the sentence is a named refusal.

### Fixed — security
- The file-WRITE path had no policy (the review wrote ~/.ssh/id_rsa live):
  .ssh/.gnupg/hosts/sam/system and Windows/Program Files/ProgramData are
  refused BY NAME, before the exists-check.

### Fixed — the operator's voice
- «گزارش بساز و برایم ایمیل کن» ran half the sentence silently: the
  quality gate's shrunken route now CONFESSES the dropped half, and the
  gate's reasoning renders in every report (⚖).
- Reminder deletion: numbered listing, «یادآوری N را حذف کن», and the bulk
  delete law (only with an explicit «تأیید کن»).
- Suggestions are domain-aware («یادم باشی…» → the reminder recipe, not
  «سایت/لبه/برش»); colloquial reminder forms (باشی/بشه/بادی…) and
  sentence-shaped social talk answer; a defaulted reminder hour confesses.
- Reports state WHERE the artifact is («— در «C:\...\line.png»») and keep
  every digit Persian (A/B margin, coefficient count, page count).

### Added
- docs/DEEP_REVIEW_R61.md — the seven-persona review, with evidence.
- scripts/probe_r61_review.py — 16 live proofs, registered in verify.
- scripts/gen_commands.py — COMMANDS.md is now GENERATED from _VOCAB +
  the registry (27 capabilities, 241 words).

## R60 — 2026-10-01 — The Text-File Wave

- New capability 27: textfile (read/write/list) — no silent overwrite,
  secrets (.env/keys) never read aloud.
- Time-until («تا نیمه‌شب … مانده») and weekday distance (all seven days,
  longest-match-first against the شنبه/یکشنبه substring trap).
- «فضای درایو C» shows one drive; unknown drives are named with the seen list.
- «تنظیماتت را نشان بده» — the operator's own settings, secrets masked.
- The email listing (MIME-decoded subjects) and social answers.

## R59 — 2026-10-01 — The Sweep Wave (math, units, machine views)

- Sentence-named arithmetic operators («۵ منهای ۳» = ۲, not the old + lie).
- New capability: unit_convert — 30 units, factor families + the
  temperature formula, with a conversion-shape gate.
- window_view: real open windows (UTF-8 law) and heavy processes.
- Memory/chain listings; ChainsStore injectable-db (a test leak, confessed
  and cleaned).

## R58 — 2026-09-30/01 — The Folder Wave

- Folder routing, relative dates, named-memory recall, the agenda view,
  the OCR remedy, the R58 sweep probe.

Earlier waves (R37–R57): the pantheon registry, ARETĒ evidence judgment,
the six-gate verify, the night shift, SSRF guard, quarantine, injection
ledger, provenance gate, security drift probes — see docs/NIGHT_SHIFT_LOG.md
for the wave-by-wave record.
