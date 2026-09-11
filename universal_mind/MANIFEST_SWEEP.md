# MANIFEST — Coverage-to-bug-fix sweep (live modules < 90%)

Continues the de-risking method that just measured 91%→96%: for each LIVE module
below 90% coverage, read the exact uncovered lines, fix any real bug found there,
then cover every branch with direct tests. No dead-code deletion this time —
these are all reachable, so the work is *prove them correct*, not remove them.

Priority is by (uncovered lines × bug-likelihood), most impactful first.

- [x] W1 core/executive.py  (86%→94%, 27 cases) — throttle/risk/fallback/fault/
      selection branches proven.
- [x] W2 cli.py             (78%→91%, 5 cases) — dashboard/cycle/chat-local +
      health-failure fail-safe.
- [x] W3 pantheon/registry.py (74%→100%, 7 cases) — organ/search/restore/key-error.
- [x] W4 powers/boundary.py (73%→100%, 6 cases) — refusal/escalation/allow.
- [x] W5 mouth/commit.py    (88%→99%, 9 cases) — vagueness/conflict/caution/guard.
- [x] W6 powers/summon.py   (77%→100%, 2 cases) — summon body; also fixed a flaky
      localhost HTTP test (retry_policy=max_retries=0 race).

## Success = each module coverage up, any found bug fixed, mypy 0, READY.