# لاگ شیفت شب — NIGHT SHIFT LOG

هر ران یک خط: [زمان] Nx — کار — commit — گواه

- [2026-10-01 01:18] run started (lock acquired)
- [2026-10-01 01:37] watchdog: 4 commits in the last 2h, 10 open item(s)
- [2026-10-01 02:00] N1 — نگهبان SSRF برای webfetch: ۱۶ آدرس خصوصی/loopback/link-local رد می‌شوند (blocked_target + درمان فارسی)، پیش از هر اتصال؛ ریدایرکت به file:// و به متادیتای ابری روی سوکت واقعی رد شد؛ allow_private=True تنها راه خواندن محلی است. 22 تست + probe_r57_ssrf (۸ گواه زنده) — commit بعدی
- [2026-10-01 02:04] run started (lock acquired)
- [2026-10-01 02:40] STAND-DOWN — این ران N1 را کامل کرد و کامیت شد (811c072: نگهبان SSRF، ۹۸ تست سبز + ۸ گواه زندهٔ probe_r57_ssrf، ruff/ratchet پاک). اما یک رانِ هم‌زمانِ دوم همین حالا N2 را می‌سازد (injection_ledger.py، persian_router.py، webfetch_tool.py، tests/test_injection_ledger.py، scripts/probe_r57_ledger.py — همه در حال تغییر، آخرین ۰۲:۳۹). برای جلوگیری از پاک‌شدن کارِ او، این ران هیچ فایلی را لمس نکرد و قفل را آزاد نکرد. ⚠ قفل مسابقه داد: دو ران هم‌زمان هر دو «lock acquired» گرفتند — مکانیزم قفل باید در N8 بررسی شود.
- [2026-10-01 02:45] N2 — دفتر تزریق‌ها: جدول injection_attempts با ساعت محلی؛ هر fetch با حکم ناپاک یک ردیف ثبت می‌کند؛ فرمان «تزریق‌ها را نشان بده» از استور واقعی می‌خواند و فارسی گزارش می‌دهد. دو باگ واقعی رفع شد: (۱) x داخل «exfiltration» به × تبدیل می‌شد، (۲) contacts.py هنوز CURRENT_TIMESTAMP یعنی UTC بود (نقض قانون یک ساعت). 18 تست + probe_r57_ledger (۸ گواه زنده روی سوکت واقعی)
- [2026-10-01 03:15] run started (lock acquired)
- [2026-10-01 03:37] watchdog: 3 commits in the last 2h, 8 open item(s)
- [2026-10-01 02:55] N6 — docs/SECURITY.md: جدول مدل تهدید (۱۲ ردیف، هر ردیف گواه واقعی) به‌علاوهٔ بخش «سه شکست صادقانهٔ همین دوره». پروب تازه probe_r57_docs: هر ارجاع سند را می‌سنجد — فایل تست، نام تست، وجود probe، و ثبتش در verify. ادعا: «سند نمی‌تواند از کد جدا شود» — ۶ گواه، همه سبز.
- [2026-10-01 04:23] run started (lock acquired)
- [2026-10-01 04:23] run started (lock acquired)
- [2026-10-01 05:38] watchdog: 2 commits in the last 2h, 7 open item(s)
- [2026-10-01 07:39] watchdog: 0 commits in the last 2h, 7 open item(s)
- [2026-10-01 09:12] run started (lock acquired)
- [2026-10-01 09:29] run started (lock acquired)
- [2026-10-01 09:29] run started (lock acquired)
- [2026-10-01 04:35] N3 — خط قرنطینه در گزارش فارسی: `_quarantine_note` + درجِ 🔒 در `persian_report` (صفحهٔ خصمانه → «اجرا نشد» با نام‌های فارسی خانواده‌ها؛ صفحهٔ پاک → «اسکن شد، چیزی نبود»). ۱۲ تست سبز. | N8 — رفعِ باگِ مسابقهٔ قفل که خودِ رانِ شب کشف و ثبت کرده بود: قفل حالا اتمیک است (O_CREAT|O_EXCL) و قفلِ کهنه اول unlink سپس create می‌شود. پروب یک باگ در رفعِ اولم گرفت: O_EXCL روی فایلِ موجود شکست می‌خورد و مسیرِ تصرفِ کهنه هرگز اجرا نمی‌شد. اثبات زنده: ۶ شروع هم‌زمان → دقیقاً ۱ برنده؛ قفلِ تازه رد می‌کند، کهنه تصرف می‌شود. probe_r57_report (۸ گواه زنده، ثبت‌شده در verify)
- [2026-10-01 09:40] watchdog: 0 commits in the last 2h, 5 open item(s)
