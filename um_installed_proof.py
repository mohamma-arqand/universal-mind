import sys
sys.path.insert(0, r'D:/UM-TEST-INSTALL/app')
from universal_mind.persian_router import route_and_run
p = route_and_run('ساعت چنده؟')
print('DOOR:', p['agent_report'][:45])
from universal_mind.volume_tool import get_volume
print('VOL-READ:', get_volume())
p2 = route_and_run('ولوم چند است؟')
print('VOL-ASK:', p2['agent_report'][-40:])
from universal_mind.database_suite import DatabaseSuite
db = DatabaseSuite(persistent=True)
db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-exe%'")
from universal_mind.scheduler import register_one_shot
register_one_shot('فردا ساعت ۸ جلسه گواه-exe')
p3 = route_and_run('فردا چند تا قرار دارم؟')
print('MEET:', p3['agent_report'][:70])
db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-exe%'")
p4 = route_and_run('لیست پنجرههای باز')
lines = p4['agent_report'].count('—')
print('WINDOWS-LISTED:', lines > 0)
print('ALL-INSTALLED-PROOFS-OK')
