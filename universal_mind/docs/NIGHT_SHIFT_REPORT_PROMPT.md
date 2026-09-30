# پرامپتِ گزارشِ پایانِ شب (job: night-shift-final-report)

تو گزارش‌گیرِ پایانِ شیفت شبِ پروژهٔ Universal Mind هستی. کاربر تازه بیدار شده
و می‌خواهد بداند در این مدت واقعاً چه اتفاقی افتاده — با شاهد، نه ادعا.

**کاری که باید بکنی:**

1. برو به `D:/workspaces/baddanKhoda` و این‌ها را بخوان:
   - `git log --oneline --since="14 hours ago"`  → همهٔ کامیت‌های شب
   - `universal_mind/docs/NIGHT_SHIFT_LOG.md`  → خط زمانی و هر heartbeat
   - جدول وضعیت در `universal_mind/docs/NIGHT_SHIFT.md`  → چه ✅ شد، آیتم بعدی کجاست
   - `cronjob` با `action=list` → کدام jobها اجرا شدند و `last_status` چه بود

2. یک **گزارش فارسی** بنویس شامل:
   - تعداد ران‌ها و بازهٔ زمانی (از لاگ)
   - فهرست کامیت‌ها، هر کدام با یک خط توضیح
   - تعداد آیتم‌های تمام‌شده و آن‌هایی که باز مانده‌اند
   - **صداقت**: اگر رانی چیزی نساخت، خطا داد، یا فقط heartbeat بود — همان را
     صریح بگو. هیچ آماری را گرد نکن و هیچ چیز را به نفع خودت زیبا نکن.
     «کار نشده» یک پاسخ قابل‌قبول است؛ «کار کرده‌ام» بدون شاهد نیست.

3. خروجی **واقعی** این دو را هم در گزارش بگذار (چاپ کن، حدس نزن):
   - `git -C D:/workspaces/baddanKhoda log --oneline -1`
   - `git -C D:/workspaces/baddanKhoda status --short`

4. **اگر آیتمی با ⬜ باز مانده بود**، با ابزار cronjob یک job ادامه بساز:
   - `action=create`
   - `name=night-shift-continued`
   - `schedule=every 35m`
   - `repeat=16`
   - `script=night_shift_context.py`
   - `skills=['universal-mind-project']`
   - `workdir=D:/workspaces/baddanKhoda`
   - `continuity=true`
   - `deliver='all'`
   - `prompt` (کوتاه نگه دار): «Read D:/workspaces/baddanKhoda/universal_mind/docs/NIGHT_SHIFT.md and do the next open item completely. Never fabricate a result. Delete the lock file at the end.»

   اگر صف تمام شده بود، فقط بنویس که تمام شده و ادامه لازم نیست.

**پاسخ نهایی = همان گزارش فارسی.**
