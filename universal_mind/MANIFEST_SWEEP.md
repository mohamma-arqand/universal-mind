# MANIFEST — Coverage-to-bug-fix sweep (live modules < 90%)

Continues the de-risking method that just measured 91%→96%: for each LIVE module
below 90% coverage, read the exact uncovered lines, fix any real bug found there,
then cover every branch with direct tests. No dead-code deletion this time —
these are all reachable, so the work is *prove them correct*, not remove them.

Priority is by (uncovered lines × bug-likelihood), most impactful first.

- [ ] W1 core/executive.py  (86%, 60 lines) — the heart: handle/_validate/_gate/
      _throttle/_execute_and_audit/fault path. Largest gap.
- [ ] W2 cli.py             (78%, 40 lines) — public interface; error/arg paths.
- [ ] W3 pantheon/registry.py (74%, 33 lines) — capability dossier + resolver.
- [ ] W4 powers/boundary.py (73%, 16 lines) — refusal/escalation/deferral.
- [ ] W5 mouth/commit.py    (88%, 15 lines) — guarded commit + attack veto.
- [ ] W6 powers/summon.py   (77%, 6 lines)  — small; close the gap.

## Success = each module coverage up, any found bug fixed, mypy 0, READY.