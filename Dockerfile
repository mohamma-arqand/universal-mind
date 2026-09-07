# Universal Mind — deployment shape (multi-stage, non-root).
#
# Build:   docker build -t universal-mind .
# Run:     docker run --rm universal-mind            # runs the reference demo
# Health:  docker run --rm universal-mind health     # JSON status, exit 0 = healthy
#
# External-provider keys are injected at runtime via environment (e.g.
# UM_OPENAI_API_KEY); image contains none.

FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY universal_mind ./universal_mind
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
# Non-root runtime user (no HOME writable beyond /tmp).
RUN useradd --system --uid 1001 um && mkdir -p /tmp/um && chown -R um:um /tmp/um
USER um
ENV PYTHONUNBUFFERED=1
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["universal-mind", "health"]
CMD ["universal-mind", "demo"]