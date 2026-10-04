import sys
import io
sys.path.insert(0, r'D:\workspaces\baddanKhoda')
sys.stdin = io.StringIO('ساعت چنده؟\nیادآور تست-درب ساعت ۱۴ فردا\nخروج\n')
from universal_mind.__main__ import main
main()
print('DOOR-OK')
