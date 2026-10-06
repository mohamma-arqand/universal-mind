#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# publish-v1.0.0.sh — انتشارِ عمومیِ Universal Mind در یک دستور
# (وقتی اینترنت/پروکسی وصل است — V2Ray روشن یا شبکهٔ آزاد)
#
# پیش‌نیازها:
#   1. gh  نصب است (هست: C:\Program Files\GitHub CLI\gh)
#   2. gh auth login  انجام شده باشد — توکنِ فعلی منقضی است؛
#      در ترمینالِ خودت اجرا کن:  gh auth login -h github.com -w
#   3. V2Ray روشن (پورتِ 10808) یا شبکهٔ بدونِ فیلتر
#
# اجرا:  bash publish-v1.0.0.sh  <نام-کاربری-گیت‌هاب>
# ─────────────────────────────────────────────────────────────
set -euo pipefail
USER="${1:?استفاده: bash publish-v1.0.0.sh <github-username>}"
REPO="universal-mind"
ROOT="$(cd "$(dirname "$0")" && pwd)"

# ۰) شبکه — اگر V2Ray روشن است، gh را از پروکسی عبور بده
export GH_HOST=github.com
if powershell.exe -NoProfile -Command "Test-NetConnection 127.0.0.1 -Port 10808 -InformationLevel Quiet" 2>/dev/null | grep -q True; then
  echo "[net] V2Ray فعال — gh از پروکسی میرود"
  export HTTPS_PROXY=socks5://127.0.0.1:10808
  export HTTP_PROXY=socks5://127.0.0.1:10808
fi

# ۱) احراز
gh auth status >/dev/null 2>&1 || { echo "❌ gh وصل نیست — اول: gh auth login -h github.com -w"; exit 1; }

# ۲) ریپوی خصوصی/عمومی + push
gh repo create "$USER/$REPO" --public --source="$ROOT" --push 2>/dev/null \
  || git remote add origin "https://github.com/$USER/$REPO.git"
git push -u origin master
git push origin --tags

# ۳) ساختِ Release با هر دو EXE + چک‌سام + راهنما + رسیدِ تست
gh release create v1.0.0 \
  --title "Universal Mind v1.0.0 — دستیارِ فارسیِ ویندوز" \
  --notes "$(cat <<'MD'
## نصب — یک دابل‌کلیک
- **UniversalMind-Setup-1.0.0.exe** (Full, 88MB): همهٔ قابلیتها — بینایی (OpenCV)، سیگنال (scipy)، یادگیری ماشین (sklearn)
- **UniversalMind-Lite-Setup-1.0.0.exe** (Lite, 44MB): همان درِ کامل؛ موتورهای سنگین در نبودشان «ردِ نامدار» میدهند

بدونِ پیش‌نیاز: نه پایتون، نه pip، نه اینترنت هنگامِ نصب. راهنمایِ فارسی: README-FA.md

## گواهِ کیفیت (همراهِ همین release)
- ۲۶۹۹ تست / ۰ شکست · ۶۹ پروبِ زنده · verification_receipt.json
- هر دو EXE با نصبِ silent روی ماشینِ واقعی گواه شدند: درِ فارسی، ولومِ واقعیِ اندازه‌گیری‌شده، ثبتِ قرار، لیستِ پنجره‌ها — همه از درونِ نصبِ خودشان
- SHA256SUMS.txt برای تأییدِ دانلود

## قانونِ صداقت
هر کاری را که نتواند واقعاً انجام دهد صریح میگوید و راهش را نشان میدهد — هرگز نتیجه جعل نمیکند.
MD
)" \
  build/release-1.0.0/UniversalMind-Setup-1.0.0.exe \
  build/release-1.0.0/UniversalMind-Lite-Setup-1.0.0.exe \
  build/release-1.0.0/SHA256SUMS.txt \
  build/release-1.0.0/README-FA.md \
  build/release-1.0.0/verification_receipt.json

echo "✅ منتشر شد: https://github.com/$USER/$REPO/releases/tag/v1.0.0"
