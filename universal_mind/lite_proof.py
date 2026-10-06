import sys
sys.path.insert(0, r'D:/UM-LITE-TEST/app')
from universal_mind.persian_router import route_and_run
print('DOOR:', route_and_run('ساعت چنده؟')['agent_report'][:26])
import universal_mind.vision_suite as vs
conn = vs.VisionSuiteConnector()
out = conn.connect(None, {'operation':'stats'})
print('REFUSAL:', out.ok is False, '|', str(getattr(out,'error',''))[:50])
print('LITE-INSTALLED-OK')
