#!/usr/bin/env bash
# universal_mind — CREATE the installer artifact (no external tools needed).
# The result: build/universal_mind-bundle.zip — one archive the new user
# unzips, then drags install.cmd onto a double-click. The RELAUNCH-AS-ADMIN
# box lives INSIDE install.cmd (Task Scheduler's Startup folder + the
# interactive session need it); nothing here asks for admin silently.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/build"
rm -rf "$OUT"; mkdir -p "$OUT/bundle"

# 1) the source (no caches, no local DBs — a fresh home for the new user)
(cd universal_mind && find . -type d -name __pycache__ -prune -o -type f -print \
  | grep -v -E '\.pyc$|/tests/|um_central\.db' | tar -cf - -T -) \
  | (cd "$OUT/bundle" && mkdir universal_mind && cd universal_mind && tar -xf -)

# 2) the runtime pins the interpreter needs
cp "$ROOT/requirements.txt" "$OUT/bundle/requirements.txt"

# 3) the LAUNCHER — the assistant's front door
cat > "$OUT/bundle/universal_mind.cmd" <<'CMD'
@echo off
title universal_mind
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo First run: making the private Python home ^(a minute, once^)... & python -m venv .venv ^
    && .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
)
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'%CD%'); from universal_mind.__main__ import main; main()"
CMD

# 4) the INSTALLER — autostart-forever + a desktop shortcut; asks admin ONCE
cat > "$OUT/bundle/install.cmd" <<'CMD'
@echo off
:: universal_mind installer — autostart at login + a desktop shortcut.
:: Right-click -> Run as administrator (the task needs it, once, forever).
cd /d "%~dp0"
set NAME=UniversalMind
schtasks /create /tn "%NAME%" /tr "\"%~dp0universal_mind.cmd\"" /sc onlogon /rl highest /f ^
  && echo [OK] starts at every login
echo Set oWS=WScript.CreateObject("WScript.Shell") > %TEMP%\um_l.vbs
echo sLinkFile=oWS.SpecialFolders("Desktop")^&"\universal_mind.lnk" >> %TEMP%\um_l.vbs
echo Set l=oWS.CreateShortcut(sLinkFile): l.TargetPath="%~dp0universal_mind.cmd": l.Save >> %TEMP%\um_l.vbs
cscript //nologo %TEMP%\um_l.vbs && del %TEMP%\um_l.vbs && echo [OK] desktop shortcut made
echo Done. Double-click the desktop icon, or restart.
pause
CMD

# 5) the one-face README the new user reads first
cat > "$OUT/bundle/ÉØÇÃÓ.md" <<'MD' 2>/dev/null || cat > "$OUT/bundle/SHOROO.md" <<'MD'
MD
cat > "$OUT/bundle/شروع.md" <<'MD'
# شروع (فقط همین)
۱. این پوشه را جایی بگذار (مثلاً D:) و عوضش نکن.
۲. روی **install.cmd** راست‌کلیک و «Run as administrator» (فقط یک‌بار، برای autostart).
۳. از این پس با هر روشن‌شدن بالا میآید؛ برای الان: آیکونِ **universal_mind** روی دسکتاپ.

## چه چیزی واقعاً میداند (بدون اینترنت، همه از همین دستگاه)
ساعت/تاریخ زندۀ فارسی · یادآور/یادداشت/قرار (همه ذخیره و پاسخ داده میشوند) · تغییرِ واقعیِ صدا (ولوم بالا/پایین/بیصدا/با‌صدا — از روی سیستم اندازه میگیرد) · بستنِ پنجرۀ برنامه‌ها (نوت‌پد، کروم، ...) · آزادکردنِ واقعیِ RAM (قبل/بعد گزارش میشود) · وضعیتِ سیستم (CPU/RAM/دیسک زنده) · گزارش/نمودار/PDF/تصویر تحلیلی واقعی از داده‌هایت · تبدیلِ فرمت (csv/json/…) · جمع‌کردنِ فایل‌های تکراری (در پوشۀ خودش) · بستۀ فشرده (zip) · | و هر چه نمیداند را صریح میگه، جعل نمیکنه.

## یک جلسهٔ واقعی (همین حالا تست کن)
universal_mind.cmd را باز کن و بنویس: ساعت چنده؟ / یادآور فردا ۹ صبح ورزش / چند یادآور دارم؟ / صدا رو زیاد کن / صدا رو روی ۲۵ بذار / یادآورها رو نشون بده / وضعیت سیستم چطوره؟
MD

# 6) seal IT: the bundle must list everything
# شروع.md (the name is Persian; tar handles it, but we force-copy to be sure)
cp "$OUT/bundle/شروع.md" "$OUT/bundle/START-فارسی.md" 2>/dev/null || true
(cd "$OUT/bundle" && find . -type f | sort > "$OUT/MANIFEST.txt")
powershell.exe -NoProfile -Command "Compress-Archive -Path '$OUT/bundle/*' -DestinationPath '$OUT/universal_mind-bundle.zip' -Force" >/dev/null 2>&1
ls -la "$OUT/universal_mind-bundle.zip"
echo "--- the bundle now ships:" && cat "$OUT/MANIFEST.txt" | head -20 && echo "(+ tools/volctl.exe + all source)"
