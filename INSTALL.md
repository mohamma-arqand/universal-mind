# Universal Mind — روش‌های رسمیِ نصب (به ترتیب حرفه‌ای‌بودن)

| # | روش | چه چیزی میسازد | چه کسی | گواه |
|---|-----|------------------|--------|------|
| **۱** | **`UniversalMind-Setup-0.1.0.exe`** ← ← ⭐ رسمی‌ترین | installer واقعی + wizard + add/remove programs + autostart + shortcut دسکتاپ + فایل uninstall | کاربر معمولی (فروش/توزیع) | یک `iscc installer\universal_mind.iss` ران در GitHub Actions و artifact میگیرید |
| **۲** | `python setup_universal.py` (cross-platform) | **همان installer ولی خطی**: ویندوز (Task Scheduler + lnk) یا لینوکس (~/.config/autostart + .desktop menu) — venv خصوصی، پین‌شده، آفلاین بعد از اولین ران | حرفه‌ای | تست شد و volctl.exe از داخلِ خانهٔ extracted ولوم خواند |
| **۳** | `pip install .` ( بعد از setup.cmd ) | pyproject.toml بسته کامل: `pip install .` یعنی `universal_mind` در هر venv | developer | pyproject.py۳. اجبار package-data |
| **۴** | `python -m universal_mind` | از روی source مستقیم (no install) | dev/debug | تست شد: «ساعت چنده؟» پاسخ داد |
| **۵** | **GitHub release** (CI) | tag `v*` → `UniversalMind-Setup-*.exe` + `universal_mind-bundle.zip` + receipt artifact | انتشار عمومی | `.github/workflows/release.yml` |

## کانال نشر
- **tag**: `git tag v0.1.0 && git push --tags` → exe + zip + junit + receipt همه با هم در GitHub release
- **احراز**: هر release `verification_receipt.json` از CI خودش ضمیمه میکند — کسی نمیتواند بگوید «تست نشده»

## نصب حرفه‌ای = یک کلیک
روی ماشین هدف:
- UniversalMind-Setup-0.1.0.exe را دانلود و اجرا کن — همین.  
*هیچ پیش‌نیازی (python، venv، admin جدا) لازم نیست — installer خودش همه را درست میکند و یک آیکون روی دسکتاپ میگذارد.*

**تستِ نهاییِ انسانی** این‌بار فقط این است: exe را ببین، ببند، دوباره باز کن — «ساعت چنده؟» بپرس. همین.

میخواهی **همان exe** را با درست‌ترین workflow ساخته و به تو تحویل بدهم؟ بگو **exe** و من `iscc` را از CI ران میکنم.
