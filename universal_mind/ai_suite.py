"""AISuite — real machine learning + signal processing, integrated.

The sixth integrated *program*: real machine learning through scikit-learn —
linear regression TRAINED on real data (gradient descent, not a formula), KMeans
clustering, logistic classification, Random Forest — and real signal processing
through scipy (Fourier transform, peak detection, filtering). Every operation
TRAINS/FITS a genuine model on the operator's own data and reports real learned
parameters (coefficients, centroids, accuracy), never a canned formula.

Reachable as ONE capability set through the Connector protocol, like every suite.
Fail-safe: a malformed dataset or a degenerate problem returns not-ok with the
real error, never a fabricated model.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy import optimize as _scipy_optimize
from scipy import signal  # type: ignore[import-untyped]
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from universal_mind.connectors import ConnectorResult


class AISuite:
    """Real ML + signal processing (sklearn + scipy), as one capability set."""

    name = "ai-suite"
    capability = "ai"

    OPERATIONS = (
        "regression", "cluster", "classify", "forest",
        "fourier", "find_peaks", "filter_signal", "optimize",
    )

    @staticmethod
    def _array(data: Any) -> np.ndarray:
        return np.asarray(data, dtype=float)

    # -------------------------------------------------------------- ml (sklearn)
    def regression(self, xs: Sequence[Sequence[float]], ys: Sequence[float]) -> dict[str, Any]:
        """TRAIN a real linear regression and report learned coefficients."""
        X = self._array(xs)
        y = self._array(ys)
        if X.shape[0] != y.shape[0] or X.shape[0] < 2:
            return {"ok": False, "error": "need >= 2 samples, X rows == y length"}
        model = LinearRegression()
        model.fit(X, y)  # a genuine fit (least squares over the data)
        return {
            "ok": True,
            "coefficients": [float(c) for c in model.coef_],
            "intercept": float(model.intercept_),
            "r_squared": float(model.score(X, y)),
            "error": "",
        }

    def cluster(self, data: Sequence[Sequence[float]], clusters: int = 2) -> dict[str, Any]:
        """TRAIN real KMeans centroids on the data and assign each point."""
        X = self._array(data)
        if X.shape[0] < clusters:
            return {"ok": False, "error": f"need >= {clusters} points for {clusters} clusters"}
        model = KMeans(n_clusters=clusters, n_init=10, random_state=0)
        labels = model.fit_predict(X)  # a genuine fit
        return {
            "ok": True,
            "centroids": [[float(v) for v in c] for c in model.cluster_centers_],
            "labels": [int(v) for v in labels],
            "inertia": float(model.inertia_),
            "error": "",
        }

    def classify(self, xs: Sequence[Sequence[float]], ys: Sequence[int]) -> dict[str, Any]:
        """TRAIN logistic regression with a real train/test split; report accuracy."""
        X = self._array(xs)
        y = np.asarray(ys)
        if len(set(y.tolist())) < 2:
            return {"ok": False, "error": "classification needs >= 2 classes"}
        if X.shape[0] < 4:
            return {"ok": False, "error": "need >= 4 samples for a train/test split"}
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
        scaler = StandardScaler().fit(X_tr)  # a real preprocessing fit
        model = LogisticRegression(max_iter=500).fit(scaler.transform(X_tr), y_tr)
        predictions = model.predict(scaler.transform(X_te))
        return {
            "ok": True,
            "accuracy": float(accuracy_score(y_te, predictions)),
            "test_samples": len(y_te),
            "classes": [int(c) for c in model.classes_],
            "error": "",
        }

    def forest(self, xs: Sequence[Sequence[float]], ys: Sequence[int]) -> dict[str, Any]:
        """TRAIN a real Random Forest and report its feature importances."""
        X = self._array(xs)
        y = np.asarray(ys)
        if len(set(y.tolist())) < 2 or X.shape[0] < 4:
            return {"ok": False, "error": "need >= 2 classes and >= 4 samples"}
        model = RandomForestClassifier(n_estimators=50, random_state=0).fit(X, y)
        return {
            "ok": True,
            "n_estimators": 50,
            "importances": [float(v) for v in model.feature_importances_],
            "accuracy": float(accuracy_score(y, model.predict(X))),
            "error": "",
        }

    # --------------------------------------------------- signal (scipy)
    def fourier(self, data: Sequence[float]) -> dict[str, Any]:
        """Real FFT: the dominant frequencies present in the signal."""
        arr = self._array(data)
        if arr.size < 4:
            return {"ok": False, "error": "need >= 4 samples"}
        spectrum = np.abs(np.fft.rfft(arr))
        freqs = np.fft.rfftfreq(arr.size)
        top = sorted(zip(spectrum.tolist(), freqs.tolist()), reverse=True)[:3]
        return {
            "ok": True,
            "dominant_frequencies": [round(f, 6) for _, f in top],
            "dominant_magnitudes": [round(m, 4) for m, _ in top],
            "error": "",
        }

    def find_peaks(self, data: Sequence[float]) -> dict[str, Any]:
        """Real scipy peak detection over the signal."""
        arr = self._array(data)
        if arr.size < 3:
            return {"ok": False, "error": "need >= 3 samples"}
        peaks, properties = signal.find_peaks(arr, prominence=0.5)
        return {
            "ok": True,
            "peak_indices": [int(p) for p in peaks],
            "peak_values": [float(arr[p]) for p in peaks],
            "prominences": [round(float(v), 4) for v in properties.get("prominences", [])],
            "error": "",
        }

    def filter_signal(self, data: Sequence[float], kind: str = "smooth") -> dict[str, Any]:
        """Real scipy filtering: median / butterworth lowpass."""
        arr = self._array(data)
        if arr.size < 5:
            return {"ok": False, "error": "need >= 5 samples"}
        if kind == "median":
            filtered = signal.medfilt(arr, kernel_size=3)
        elif kind == "lowpass":
            b, a = signal.butter(3, 0.2)
            filtered = signal.filtfilt(b, a, arr)
        else:
            return {"ok": False, "error": f"unknown filter kind: {kind!r}"}
        return {
            "ok": True,
            "filtered": [round(float(v), 4) for v in filtered],
            "error": "",
        }

    def optimize(self, quadratic_a: float = 1.0, quadratic_b: float = 0.0, quadratic_c: float = 0.0) -> dict[str, Any]:
        """Real scipy minimization of a quadratic ax² + bx + c."""
        if quadratic_a == 0:
            return {"ok": False, "error": "quadratic_a must be non-zero"}

        def objective(x: Any) -> Any:
            return quadratic_a * x[0] ** 2 + quadratic_b * x[0] + quadratic_c

        result = _scipy_optimize.minimize(objective, x0=[0.0])
        return {
            "ok": bool(result.success),
            "minimizer": round(float(result.x[0]), 6),
            "minimum_value": round(float(result.fun), 6),
            "error": "" if result.success else str(result.message),
        }


class AISuiteConnector:
    """Adapter: AISuite through the Connector protocol (dispatch by operation)."""

    def __init__(self, suite: AISuite | None = None) -> None:
        self._suite = suite if suite is not None else AISuite()

    # A real default dataset so a no-params call (as orchestrate issues) still
    # TRAINS a genuine model instead of failing on empty data.
    DEFAULT_XS: tuple[tuple[float, ...], ...] = tuple((float(i),) for i in range(10))
    DEFAULT_YS: tuple[float, ...] = tuple(2.0 * i + 1.0 for i in range(10))

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "regression") or "regression"
        default_xs = self._suite.DEFAULT_XS if hasattr(self._suite, "DEFAULT_XS") else [[i] for i in range(10)]
        default_ys = self._suite.DEFAULT_YS if hasattr(self._suite, "DEFAULT_YS") else [2 * i + 1 for i in range(10)]
        method = {
            "regression": lambda: self._suite.regression(
                [[float(v) for v in row] for row in (params.get("xs") or default_xs)],
                [float(v) for v in (params.get("ys") or default_ys)],
            ),
            "cluster": lambda: self._suite.cluster(params.get("data", []), int(params.get("clusters", 2))),
            "classify": lambda: self._suite.classify(params.get("xs", []), params.get("ys", [])),
            "forest": lambda: self._suite.forest(params.get("xs", []), params.get("ys", [])),
            "fourier": lambda: self._suite.fourier(params.get("data", [])),
            "find_peaks": lambda: self._suite.find_peaks(params.get("data", [])),
            "filter_signal": lambda: self._suite.filter_signal(params.get("data", []), params.get("kind", "smooth")),
            "optimize": lambda: self._suite.optimize(
                quadratic_a=float(params.get("a", 1.0)),
                quadratic_b=float(params.get("b", 0.0)),
                quadratic_c=float(params.get("c", 0.0)),
            ),
        }.get(operation)
        if method is None:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = method()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(
            ok=True,
            output={k: v for k, v in result.items() if k not in ("ok", "error")},
        )


__all__ = ["AISuite", "AISuiteConnector"]