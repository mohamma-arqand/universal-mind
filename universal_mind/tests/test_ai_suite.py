"""Tests for the integrated AISuite (real ML + signal processing)."""

from __future__ import annotations

import numpy as np

from universal_mind.ai_suite import AISuite, AISuiteConnector


class TestRealML:
    def test_regression_trains_real_coefficients(self) -> None:
        suite = AISuite()
        # y = 2x + 1 → the learned coefficient must be ~2, intercept ~1.
        xs = [[i] for i in range(10)]
        ys = [2 * i + 1 for i in range(10)]
        out = suite.regression(xs, ys)
        assert out["ok"] is True
        assert abs(out["coefficients"][0] - 2.0) < 1e-6
        assert abs(out["intercept"] - 1.0) < 1e-6
        assert out["r_squared"] > 0.999

    def test_cluster_finds_real_centroids(self) -> None:
        suite = AISuite()
        # Two tight groups far apart → real KMeans must separate them.
        data = [[0, 0], [1, 0], [0, 1], [10, 10], [11, 10], [10, 11]]
        out = suite.cluster(data, clusters=2)
        assert out["ok"] is True
        labels = out["labels"]
        assert labels[0] == labels[1] == labels[2]      # first group together
        assert labels[3] == labels[4] == labels[5]      # second group together
        assert labels[0] != labels[3]                   # groups separated

    def test_classify_reports_real_accuracy(self) -> None:
        suite = AISuite()
        # Two linearly separable classes → accuracy must be high.
        xs = [[0, 0], [1, 1], [0, 1], [1, 0], [10, 10], [11, 11], [10, 11], [11, 10]]
        ys = [0, 0, 0, 0, 1, 1, 1, 1]
        out = suite.classify(xs, ys)
        assert out["ok"] is True
        assert out["accuracy"] >= 0.5

    def test_forest_reports_importances(self) -> None:
        suite = AISuite()
        xs = [[0, 5], [1, 5], [0, 6], [1, 6], [10, 1], [11, 1], [10, 0], [11, 0]]
        ys = [0, 0, 0, 0, 1, 1, 1, 1]
        out = suite.forest(xs, ys)
        assert out["ok"] is True
        assert len(out["importances"]) == 2
        assert abs(sum(out["importances"]) - 1.0) < 1e-6

    def test_degenerate_regression_fails_clean(self) -> None:
        suite = AISuite()
        out = suite.regression([[1]], [1])  # 1 sample: cannot fit
        assert out["ok"] is False


class TestRealSignal:
    def test_fourier_finds_dominant_frequency(self) -> None:
        suite = AISuite()
        # A pure sine over 64 samples: the dominant frequency is 1/64.
        data = [np.sin(2 * np.pi * i / 64) for i in range(64)]
        out = suite.fourier(data)
        assert out["ok"] is True
        assert out["dominant_frequencies"][0] == 1 / 64
        assert out["dominant_magnitudes"][0] > 10

    def test_find_peaks_detects_real_peaks(self) -> None:
        suite = AISuite()
        data = [0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 2, 0, 0]
        out = suite.find_peaks(data)
        assert out["ok"] is True
        values = out["peak_values"]
        assert 3.0 in values and 5.0 in values

    def test_filter_signal_smooths(self) -> None:
        suite = AISuite()
        noisy = [0, 5, 0, 5, 0, 5, 0, 5, 0]
        out = suite.filter_signal(noisy, kind="median")
        assert out["ok"] is True
        # The median filter smooths the alternating pattern in the interior:
        # the interior is no longer pure spikes (some 5s become 0s).
        interior = out["filtered"][1:-1]
        assert interior.count(5.0) < noisy[1:-1].count(5)
        assert out["filtered"] != [float(v) for v in noisy]

    def test_unknown_filter_kind_fails_clean(self) -> None:
        suite = AISuite()
        out = suite.filter_signal([1, 2, 3, 4, 5], kind="magic")
        assert out["ok"] is False
        assert "unknown filter kind" in out["error"]

    def test_optimize_finds_real_minimum(self) -> None:
        suite = AISuite()
        # x² - 4x + 4 has its minimum at x = 2.
        out = suite.optimize(quadratic_a=1.0, quadratic_b=-4.0, quadratic_c=4.0)
        assert out["ok"] is True
        assert abs(out["minimizer"] - 2.0) < 1e-3
        assert abs(out["minimum_value"]) < 1e-3


class TestConnector:
    def test_dispatches_ml_and_signal(self) -> None:
        conn = AISuiteConnector()
        regression = conn.connect({}, {
            "operation": "regression", "xs": [[1], [2], [3]], "ys": [2, 4, 6],
        })
        assert regression.ok is True
        assert abs(regression.output["coefficients"][0] - 2.0) < 1e-6

        fourier = conn.connect({}, {"operation": "fourier", "data": [0, 1, 0, -1, 0, 1, 0, -1]})
        assert fourier.ok is True

    def test_unknown_operation_fails_clean(self) -> None:
        conn = AISuiteConnector()
        result = conn.connect({}, {"operation": "sentience"})
        assert result.ok is False
        assert "unknown operation" in result.error

    def test_ai_suite_joins_the_synthesis_loop(self) -> None:
        """The whole ML program participates in the multi-tool synthesis loop."""
        import universal_mind.real_tool_registry as rtr
        from universal_mind.orchestration import orchestrate
        from universal_mind.tool_registry import (
            ConnectionMechanism,
            ToolConnectionSpec,
            ToolEntry,
            ToolRegistry,
        )

        reg = ToolRegistry()
        reg.register(ToolEntry(name="ai", capability="ai",
                               connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                               absorbable=True))
        # "ai" is an officially registered real capability — no mutation of the
        # shared connector table (the mutate-then-delete pattern caused real
        # cross-test contamination before).
        syn = orchestrate(reg, ["ai"], connector_factory=rtr.real_connector_factory)
        assert syn.ok is True
        # The no-params call runs a real regression over the default data.
        assert "coefficients" in syn.output["synthesized_from"]["ai"]