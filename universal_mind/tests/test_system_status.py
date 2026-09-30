"""R53 wave-6 — SYSTEM STATUS: the machine's REAL vitals, one honest report.

«وضعیت سیستم را بگو» used to fall to the goal board. Now: real uptime,
RAM, per-disk free space, battery — every number measured via CIM, every
unreadable signal NAMED. «وضعیت» (bare) still opens the goal board.
"""

from __future__ import annotations


class TestSystemStatusTool:
    def test_real_vitals_on_this_machine(self) -> None:
        from universal_mind.system_status_tool import SystemStatusTool

        res = SystemStatusTool().status()
        assert res["ok"] is True
        # RAM is readable on this machine — real numbers, not None
        ram = res.get("ram")
        assert ram is not None
        assert ram["total_gb"] > 0
        assert 0 <= ram["used_pct"] <= 100
        # disks: at least C: with real free space
        disks = res.get("disks")
        assert disks, "no disks read"
        c = next((d for d in disks if d["drive"].startswith("C")), None)
        assert c is not None and c["free_gb"] > 0
        assert c["total_gb"] >= c["free_gb"]

    def test_uptime_is_measured_or_named(self) -> None:
        from universal_mind.system_status_tool import SystemStatusTool

        res = SystemStatusTool().status()
        up = res.get("uptime")
        # Either real (non-negative) or absent — never invented
        if up is not None:
            assert up["days"] >= 0 and up["hours"] >= 0
        else:
            assert any("uptime" in n for n in res.get("notes", []))

    def test_notes_name_every_missing_signal(self) -> None:
        """The honesty law: a signal that cannot be read is NAMED, not silent."""
        from universal_mind.system_status_tool import SystemStatusTool

        res = SystemStatusTool().status()
        keys = ("uptime", "ram", "disks")
        missing = [k for k in keys if res.get(k) in (None, [])]
        for k in missing:
            assert any(k in n for n in res.get("notes", [])), f"{k} missing but not named"


class TestRouterSplit:
    def test_machine_status_routes_to_sysstatus(self) -> None:
        from universal_mind.persian_router import route_and_run

        res = route_and_run("وضعیت سیستم را بگو")
        assert "sysstatus" in (res.get("route") or [])

    def test_bare_status_still_opens_goal_board(self) -> None:
        from universal_mind.persian_router import route_and_run

        res = route_and_run("وضعیت")
        assert "goal" in (res.get("route") or [])

    def test_ram_question_routes_to_sysstatus(self) -> None:
        from universal_mind.persian_router import route_and_run

        res = route_and_run("رم چقدر آزاد است؟")
        assert "sysstatus" in (res.get("route") or [])

    def test_report_is_persian_with_real_numbers(self) -> None:
        from universal_mind.persian_router import route_and_run

        res = route_and_run("وضعیت سیستم را بگو")
        rep = str(res.get("agent_report", ""))
        assert "رم" in rep or "دیسک" in rep
        assert any(ch in rep for ch in "۰۱۲۳۴۵۶۷۸۹")  # Persian digits only
