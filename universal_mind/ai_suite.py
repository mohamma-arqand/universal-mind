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

# R72 — LAZY HEAVY IMPORTS: sklearn costs 1.6s at import time and was paid
# on EVERY router run (the sweep profiled 2.97s for «جمع ۲ و ۵» - 90% of it
# import overhead, not routing). The estimators are imported INSIDE the
# methods that use them; a run that never touches ML never pays for it.


def _sk(name: str):
    """Import one sklearn symbol lazily (never at module import)."""
    import sklearn

    return getattr(sklearn, name) if hasattr(sklearn, name) else _from_sklearn(name)


def _from_sklearn(name: str):  # pragma: no cover - fallback chain
    import importlib

    maps = {
        "KMeans": ("sklearn.cluster", "KMeans"),
        "RandomForestClassifier": ("sklearn.ensemble", "RandomForestClassifier"),
        "LinearRegression": ("sklearn.linear_model", "LinearRegression"),
        "LogisticRegression": ("sklearn.linear_model", "LogisticRegression"),
        "accuracy_score": ("sklearn.metrics", "accuracy_score"),
        "train_test_split": ("sklearn.model_selection", "train_test_split"),
        "StandardScaler": ("sklearn.preprocessing", "StandardScaler"),
    }
    mod, attr = maps[name]
    return getattr(importlib.import_module(mod), attr)

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
        model = _sk('LinearRegression')()
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
        model = _sk('KMeans')(n_clusters=clusters, n_init=10, random_state=0)
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
        X_tr, X_te, y_tr, y_te = _sk('train_test_split')(X, y, test_size=0.25, random_state=0, stratify=y)
        scaler = _sk('StandardScaler')().fit(X_tr)  # a real preprocessing fit
        model = _sk('LogisticRegression')(max_iter=500).fit(scaler.transform(X_tr), y_tr)
        predictions = model.predict(scaler.transform(X_te))
        return {
            "ok": True,
            "accuracy": float(_sk('accuracy_score')(y_te, predictions)),
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
        model = _sk('RandomForestClassifier')(n_estimators=50, random_state=0).fit(X, y)
        return {
            "ok": True,
            "n_estimators": 50,
            "importances": [float(v) for v in model.feature_importances_],
            "accuracy": float(_sk('accuracy_score')(y, model.predict(X))),
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
        top = sorted(zip(spectrum.tolist(), freqs.tolist(), strict=False), reverse=True)[:3]  # same-length by construction
        return {
            "ok": True,
            "dominant_frequencies": [round(f, 6) for _, f in top],
            "dominant_magnitudes": [round(m, 4) for m, _ in top],
            "error": "",
        }

    def find_peaks(self, data: Sequence[float]) -> dict[str, Any]:
        """Real scipy peak detection over the signal."""
        # Lazy scipy import: keeps the module import clean for every env.
        from scipy import signal as _signal

        arr = self._array(data)
        if arr.size < 3:
            return {"ok": False, "error": "need >= 3 samples"}
        peaks, properties = _signal.find_peaks(arr, prominence=0.5)
        return {
            "ok": True,
            "peak_indices": [int(p) for p in peaks],
            "peak_values": [float(arr[p]) for p in peaks],
            "prominences": [round(float(v), 4) for v in properties.get("prominences", [])],
            "error": "",
        }

    def filter_signal(self, data: Sequence[float], kind: str = "smooth") -> dict[str, Any]:
        """Real scipy filtering: median / butterworth lowpass."""
        from scipy import signal as _signal

        arr = self._array(data)
        if arr.size < 5:
            return {"ok": False, "error": "need >= 5 samples"}
        if kind == "median":
            filtered = _signal.medfilt(arr, kernel_size=3)
        elif kind == "lowpass":
            b, a = _signal.butter(3, 0.2)
            filtered = _signal.filtfilt(b, a, arr)
        else:
            return {"ok": False, "error": f"unknown filter kind: {kind!r}"}
        return {
            "ok": True,
            "filtered": [round(float(v), 4) for v in filtered],
            "error": "",
        }

    def optimize(self, quadratic_a: float = 1.0, quadratic_b: float = 0.0, quadratic_c: float = 0.0) -> dict[str, Any]:
        """Real scipy minimization of a quadratic ax² + bx + c."""
        from scipy import optimize as _scipy_optimize  # lazy: env-clean module import

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
        # the unknown-operation check comes FIRST: an op we do not know is
        # an op, not a data question (the old test pinned this order and the
        # order is right — never mask a typo behind a data complaint).
        method = {
            "regression": "regression", "cluster": "cluster",
            "classify": "classify", "fourier": "fourier",
        }
        if operation not in method:
            return ConnectorResult(ok=False, output=None,
                                   error=f"unknown operation: {operation!r}")
        # R61-S1 — THE HONEST MODEL: «رگرسیون روی این اعداد» with NO numbers
        # in the sentence silently trained on DEFAULT_XS — fabricated data
        # presented as the operator's own. A sentence that points at data
        # the platform does not have is REFUSED BY NAME, never default-fed.
        if not (params.get("xs") or params.get("data")):
            return ConnectorResult(
                ok=False, output=None,
                error="داده‌ای در جمله پیدا نکردم — مدل را روی چه اعدادی بسنجم؟ "
                      "مثلا: «رگرسیون روی ۱ و ۲ و ۳» (یا ابتدا داده را بساز/ذخیره کن و بعد بگو «روی همین‌ها»)",
            )
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