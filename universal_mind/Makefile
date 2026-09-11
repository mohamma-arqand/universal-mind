# Universal Mind - Self-Verifying Build Closure
# Mission 3.2: All targets must be idempotent

.PHONY: install lint test probe all clean typecheck mypy-ratchet test-receipt-input receipt verify

# Default target
all: install lint test probe

# Python environment
# The historic venv (../.venv) is a WSL/Linux layout and does NOT run on the
# Windows host. Runtime tools resolve as: host python (pytest/probes) and
# uvx (ruff/mypy) which fetch pin-exact tool versions on demand.
PYTHON := python
PYTEST := python -m pytest
RUFF := uvx ruff
MYPY := uvx mypy

# Artifacts directory
ARTIFACTS_DIR := artifacts
JUNIT_XML := $(ARTIFACTS_DIR)/junit.xml

# No-op install (deps are fetched on demand by uvx / already present).
install:
	@echo "Toolchain ready (host python + uvx ruff/mypy)"

# Lint with ruff (mypy is enforced separately via the ratchet)
lint: install
	@echo "Running ruff check..."
	cd .. && $(RUFF) check universal_mind/ universal_mind/tests/
	@echo "Lint passed"

# Type check with mypy (whole-package, non-strict so it matches the release frame)
typecheck: install
	@echo "Running mypy check..."
	cd .. && $(MYPY) --no-pretty universal_mind/
	@echo "Type check passed"

# Run tests with junit output
test: install
	@mkdir -p $(ARTIFACTS_DIR)
	@echo "Running tests..."
	PYTHONPATH=.. $(PYTEST) -q --tb=short --junitxml=$(JUNIT_XML) tests/
	@echo "Tests passed"

# Run self-verifying probes with JUnit XML output
probe: install
	@mkdir -p $(ARTIFACTS_DIR)
	@echo "Running probe_precedence_immutability.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_precedence_immutability.py --junit-xml=$(ARTIFACTS_DIR)/probe_precedence.xml
	@echo "Running probe_powerzero_terminal.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_powerzero_terminal.py --junit-xml=$(ARTIFACTS_DIR)/probe_powerzero.xml
	@echo "Running probe_tombstone_bound.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_tombstone_bound.py --junit-xml=$(ARTIFACTS_DIR)/probe_tombstone.xml
	@echo "Running probe_decay_bounds.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_decay_bounds.py --junit-xml=$(ARTIFACTS_DIR)/probe_decay.xml
	@echo "Running probe_arete_arbitration.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_arete_arbitration.py --junit-xml=$(ARTIFACTS_DIR)/probe_arete.xml
	@echo "Running probe_io_gateway.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_io_gateway.py --junit-xml=$(ARTIFACTS_DIR)/probe_io_gateway.xml
	@echo "Running probe_prometheus_evolution.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_prometheus_evolution.py --junit-xml=$(ARTIFACTS_DIR)/probe_prometheus.xml
	@echo "Running probe_integration_loop.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_integration_loop.py --junit-xml=$(ARTIFACTS_DIR)/probe_integration.xml
	@echo "Running probe_evolution_apply.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_evolution_apply.py --junit-xml=$(ARTIFACTS_DIR)/probe_evolution.xml
	@echo "Running probe_durability.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_durability.py --junit-xml=$(ARTIFACTS_DIR)/probe_durability.xml
	@echo "Running probe_evolution_loop.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_evolution_loop.py --junit-xml=$(ARTIFACTS_DIR)/probe_evolution_loop.xml
	@echo "Running probe_synthesis_loop.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_synthesis_loop.py --junit-xml=$(ARTIFACTS_DIR)/probe_synthesis_loop.xml
	@echo "Running probe_arete_standard.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_arete_standard.py --junit-xml=$(ARTIFACTS_DIR)/probe_arete_standard.xml
	@echo "Running probe_augment_capabilities.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_augment_capabilities.py --junit-xml=$(ARTIFACTS_DIR)/probe_augment_capabilities.xml
	@echo "Running probe_lifecycle.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_lifecycle.py --junit-xml=$(ARTIFACTS_DIR)/probe_lifecycle.xml
	@echo "Running probe_continuous_judgment.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_continuous_judgment.py --junit-xml=$(ARTIFACTS_DIR)/probe_continuous_judgment.xml
	@echo "Running probe_closed_loop.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_closed_loop.py --junit-xml=$(ARTIFACTS_DIR)/probe_closed_loop.xml
	@echo "Running probe_independent_evaluation.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_independent_evaluation.py --junit-xml=$(ARTIFACTS_DIR)/probe_independent_evaluation.xml
	@echo "Running probe_evolutionary_architecture.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_evolutionary_architecture.py --junit-xml=$(ARTIFACTS_DIR)/probe_evolutionary_architecture.xml
	@echo "Running probe_scale_durability.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_scale_durability.py --junit-xml=$(ARTIFACTS_DIR)/probe_scale_durability.xml
	@echo "Running probe_counterfactual.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_counterfactual.py --junit-xml=$(ARTIFACTS_DIR)/probe_counterfactual.xml
	@echo "Running probe_hypotheses.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_hypotheses.py --junit-xml=$(ARTIFACTS_DIR)/probe_hypotheses.xml
	@echo "Running probe_causal.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_causal.py --junit-xml=$(ARTIFACTS_DIR)/probe_causal.xml
	@echo "Running probe_episodic.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_episodic.py --junit-xml=$(ARTIFACTS_DIR)/probe_episodic.xml
	@echo "Running probe_induction.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_induction.py --junit-xml=$(ARTIFACTS_DIR)/probe_induction.xml
	@echo "Running probe_uncertainty.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_uncertainty.py --junit-xml=$(ARTIFACTS_DIR)/probe_uncertainty.xml
	@echo "Running probe_cross_judge.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_cross_judge.py --junit-xml=$(ARTIFACTS_DIR)/probe_cross_judge.xml
	@echo "Running probe_goal_drift.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_goal_drift.py --junit-xml=$(ARTIFACTS_DIR)/probe_goal_drift.xml
	@echo "Running probe_self_code_audit.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_self_code_audit.py --junit-xml=$(ARTIFACTS_DIR)/probe_self_code_audit.xml
	@echo "Running probe_rubric_learning.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_rubric_learning.py --junit-xml=$(ARTIFACTS_DIR)/probe_rubric_learning.xml
	@echo "Running probe_red_team.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_red_team.py --junit-xml=$(ARTIFACTS_DIR)/probe_red_team.xml
	@echo "Running probe_policy_trace.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_policy_trace.py --junit-xml=$(ARTIFACTS_DIR)/probe_policy_trace.xml
	@echo "Running probe_multilingual.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_multilingual.py --junit-xml=$(ARTIFACTS_DIR)/probe_multilingual.xml
	@echo "Running probe_temporal_awareness.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_temporal_awareness.py --junit-xml=$(ARTIFACTS_DIR)/probe_temporal_awareness.xml
	@echo "Running probe_real_tools.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_real_tools.py --junit-xml=$(ARTIFACTS_DIR)/probe_real_tools.xml
	@echo "Running probe_shared.py..."
	PYTHONPATH=.. $(PYTHON) scripts/probe_shared.py --junit-xml=$(ARTIFACTS_DIR)/probe_shared.xml
	@echo "All probes passed"

# Clean artifacts
clean:
	rm -rf $(ARTIFACTS_DIR) .pytest_cache __pycache__ universal_mind/__pycache__ tests/__pycache__ gates/__pycache__ core/__pycache__ pantheon/__pycache__ feedback/__pycache__ memory/__pycache__ telemetry/__pycache__

# Ensure artifacts directory exists
$(ARTIFACTS_DIR):
	mkdir -p $(ARTIFACTS_DIR)
# Verification receipt (release-blocking). Receipt input is the JUnit XML
# produced by `test`; the flux is test -> receipt -> exit code. No `-`, `:`, or
# `|| true` here: a failing test or failing overall verdict must fail `make`.
RECEIPT := $(ARTIFACTS_DIR)/verification_receipt.json

test-receipt-input: test

receipt: test-receipt-input
	@echo "Generating verification receipt from $(JUNIT_XML)..."
	PYTHONPATH=$(CURDIR)/.. $(PYTHON) scripts/generate_receipt.py $(JUNIT_XML)
	@echo "Receipt written; exit code reflects overall verdict"

# Full release gate: only prints READY when every check is green. Each step
# fails the make on the first red; there is no '|| true' anywhere here.
VERIFIED := $(ARTIFACTS_DIR)/verification_status.txt

verify: lint mypy-ratchet receipt probe
	@echo "All gates green — writing READY stamp"
	@echo "READY" > $(VERIFIED)
	@echo ""
	@echo "==================================================="
	@echo " VERIFICATION: READY  (lint + ratchet + tests + receipt + probes)"
	@echo "==================================================="
# mypy ratchet (one-way): fails if the number of mypy errors RISES above
# the versioned baseline (mypy_baseline.txt). Existing errors are NOT fixed;
# this target only prevents new type debt. Count is read fresh each run.
mypy-ratchet: install
	@echo "Running mypy ratchet against baseline..."
	@$(PYTHON) scripts/check_mypy_ratchet.py
	@echo "mypy error count is within baseline"
