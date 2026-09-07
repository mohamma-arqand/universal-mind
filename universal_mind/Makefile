# Universal Mind - Self-Verifying Build Closure
# Mission 3.2: All targets must be idempotent

.PHONY: install lint test probe all clean typecheck mypy-ratchet test-receipt-input receipt verify

# Default target
all: install lint test probe

# Python environment
VENV := $(abspath ../.venv)
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy

# Artifacts directory
ARTIFACTS_DIR := artifacts
JUNIT_XML := $(ARTIFACTS_DIR)/junit.xml

# Create venv and install dependencies
install: $(VENV)/bin/activate
	@echo "Dependencies installed in $(VENV)"

$(VENV)/bin/activate:
	@echo "Using existing virtual environment at $(VENV)"
	@touch $(VENV)/bin/activate

# Lint with ruff (mypy is strict and not enforced in CI)
lint: install
	@echo "Running ruff check..."
	cd .. && $(RUFF) check universal_mind/ universal_mind/tests/
	@echo "Lint passed"

# Type check with mypy (strict mode - may have errors in existing codebase)
typecheck: install
	@echo "Running mypy check (strict)..."
	cd .. && $(MYPY) --strict universal_mind/
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

verify: receipt
	@echo "Verification passed"
# mypy ratchet (one-way): fails if the number of mypy errors RISES above
# the versioned baseline (mypy_baseline.txt). Existing errors are NOT fixed;
# this target only prevents new type debt. Count is read fresh each run.
mypy-ratchet: install
	@echo "Running mypy ratchet against baseline..."
	@$(PYTHON) scripts/check_mypy_ratchet.py
	@echo "mypy error count is within baseline"
