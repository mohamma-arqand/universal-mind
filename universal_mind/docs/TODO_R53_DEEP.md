# R53+ — TODO عمیق (کشفشده از زمین، نه از تخیل)

## موج ۱ — زبان عملیاتی واقعی (Vocabulary Waves)
گپهای زبانی واقعیِ سنجیدهشده با ران زنده (هرکدام الان «نشناختم» برمیگردانند):
- [ ] «یادم بنداز که فردا زود بیدار شوم» → یادآور یکبارمصرف (one-shot: فردا/امشب/ساعت ۸ به run_at ISO مپ؛ run_at到期 => toast + حذف)
- [ ] «چند وقته دستگاه روشن است؟» → uptime واقعی از Windows (PowerShell GetTickCount / WMI LastBootUpTime)
- [ ] «فایل‌های بزرگ دیسک را پیدا کن» → جستجوی واقعی فایل (os.walk + size sort، رعایت کاربرگ)
- [ ] «فایل‌های تکراری را پاک کن» → dedupe با SHA-256 (تأیید قبل از حذف — قانون بکاپ)
- [ ] «وضعیت سیستم را بگو» → گزارش یکپارچه از self_status + disk + uptime (یک route واحد)
- [ ] «هویج چیه؟» → route به llm (UM_LLM_BASE_URL) با fallback صادقانه وقتی وصل نیست
- [ ] «چه کارهایی بلدی؟» / «وضعیتت چطوره؟» / «اسمت چیه؟» / «تو کی هستی؟» → reflexive/identity answers
- [ ] «رم را چطور آزاد کنم؟» → advice از real signals (advisor_suggest wired به متریکهای زنده)
- [ ] «اسم‌های تکراری در پوشه را یکسان کن» → batch rename واقعی با پیشنمایش و rollback plan
- [ ] «هر روز ساعت ۸ گزارش بده» → الان به pdf میافتد (نباید) — باید scheduled goal شود

## موج ۲ — هستهی یادآور یکبارمصرف (One-shot Reminder Engine)
- [ ] parse_one_shot(text): فردا/پس‌فردا/امشب/ساعت H[:M] → run_at LOCAL ISO
- [ ] schedules جدول: ستون run_at + kind=once (back-compat: kind خالی = repeating)
- [ ] tick handler: run_at <= now-local => fire (toast + optional speech), then delete
- [ ] «یادآورهای من» → فهرست واقعی از DB با next-due فارسی
- [ ] حذف یادآور: «یادآور X را حذف کن» (استعلام، تأیید)
- [ ] 12+ تست زنده برای موتور one-shot (فردا صبح/امشب/ساعت ۸/پس‌فردا/invalid honest)

## موج ۳ — هویت و معرفی (Identity & Introductions)
- [ ] conversational: «اسمت چیه؟» → «ذهن جهانی» (همیشه فارسی)
- [ ] «تو کی هستی؟» → معرفی ۳-جملهای state-aware (قابلیتها + امروز)
- [ ] «وضعیتت چطوره؟» → self_status خلاصه + یادآورهای فعال + اهداف فعال
- [ ] «چه کارهایی بلدی؟» → همان help line (22 قابلیت) + بهترین ۳ نمونهفرمان
- [ ] «سلام خودت را معرفی کن» → ترکیب معرفی + پیشنهاد سه کار
- 15+ تست identity

## موج  &nbsp;&nbsp;4 — سامانه‌ی جستجوی فایل واقعی (Real File Search)
- [ ] file_search capability جدید + verbs: «فایل‌های بزرگ»، «پیدا کن در»، «جستجوی فایل»
- [ ] بزرگترین N فایل در پوشه/درایو (top-K by size, walking depth محدود، timeout)
- [ ] جستجو با wildcard/name-contains؛ خروجی CSV/سند اختیاری
- [ ] شمارش honest: پوشههای غیرقابل‌خواندن report میشوند (skip، نه سکوت)
- [ ] 10+ تست زنده (tmpdir بزرگ، نامهای فارسی، permission-denied honest)

## موج ۵ — پاککنندهی تکراریها (Deduplicate Cleaner)
- [ ] file_dedupe capability: SHA-256 hash، گروهبندی، پیشنمایش گروهها + سرجمع بایت آزادشده
- [ ] قانون حذف: پیش‌فرض پیشنمایش فقط (هیچ حذفی بدون «تأیید کن» یا flag اجرا نمیشود)
- [ ] report PDF/CSV از گروهها؛ بکاپ فهرست حذفشدها در DB (rollback list)
- 10+ تست

## موج ۶ — گزارش وضعیت سیستم (System Status Report)
- [ ] sys_status capability: uptime (WMI LastBootUpTime)، RAM/دیگ، disk_watch merge، battery
- [ ] uptime فارسی («۳ روز و ۴ ساعت»)
- [ ] route «وضعیت سیستم» به sys_status نه goal/pdf
- [ ] desktop_app: یک تب «سیستم» (uptime/RAM/disk، live)
- [ ] 8+ تست (mock WMI روی headless، real روی این ویندوز)

## موج ۶ — سامانهی جستجوی فایل واقعی (Real File Search)
[merged into wave 4]

## موج ۷ — دانش (LLM knowledge route)
- [ ] «هویج چیه؟» / «تعریف X» / «بنویس دربارهی X» → llm route با پرسش فارسی
- [ ] وقتی UM_LLM_BASE_URL نیست: پاسخ صادقانه + پیشنهاد وصل کردن + ذخیره درس در unknown_harvest
- [ ] unknown_harvest→llm integration: بعدا وقتی endpoint وصل شد، سوالات پرسیدهشده را یاد بگیرد

## موج ۸ — رجیستری ابزار و ران المپیاد
- [ ] tool_registry.capabilities() که [] برگرداند — باید real_tool_registry با ثبت خودکار هر suite باشد
- [ ] spec_introspection + real registry merge (یک منبع حقیقت قابلیت)
- [ ] probe مسیرهای جدید: probe_r53_vocab (همهی verbهای جدید، real run)
- [ ] probe one-shot engine + identity answers

## موج ۹ — دسکتاپ و UX
- [ ] desktop_app: tab جدید «یادآورها» (فهرست + افزودن + حذف + next-due)
- [ ] tab سیستم (موج ۶) + بازطراحی today_page با یادآورهای امروز
- بازطراحی today_page با یادآورهای امروز
- [ ] status bar: mute state (بیصدا/باصدا) — «بیصدا» مساوی پیش از route

## موج 9b — دستیار گزارش‌نویس
- [ ] weekly_letter: LLM-write-up اختیاری وقتی endpoint وصل است (فراروید صادقانه)
- [ ] persian_report: چکها موازی (ability.g. تنها وقتی واقعا کار میکنند)

## موج 10 — سخت‌افزار واقعی: فاین‌گهداری
- [ ] mypy ratchet: هر راند floor را بالا ببر (تعداد errors فعلی را ببین)
- [ ] coverage ratchet: فقط سخت‌محیطها میمانند (تا 95%)
- [ ] probes از 89 به 100+ (هر capability نویی یک probe)
- 5 گیت verify + full suite + probe sweep

## موج 11 — مستندات و انتشار
- [ ] README فارسی + فهرست ۱۰۰+ فعل فارسی (فرمان‌نامه)
- فرمان‌نامه (COMMANDS.md): جدول فعل → قابلیت → نمونه
- [ ] CONTRIBUTING + ARCHITECTURE.md (35 ماژول واقعی، لایهها)
- [ ] PyPI-ready: pyproject polish، sdist/wheel build probe
- [ ] بسته‌بندی desktop_app: pyinstaller standalone probe
- [ ] کاتالوگ تصویری: بریفینگ روزانه + yearbook → یک HTML dashboard سالانه

## موج 12 — مقاومت
- [ ] red_team: hostile corpus جدید فارسی (200 جملهی خصمانه: injection via fake dialogs, fake OS alerts)
- [ ] restore_drill: پروب بازگردانی بکاپ روی یک backup واقعی
- rugged: all connectors w/ real error handling (already ok)
