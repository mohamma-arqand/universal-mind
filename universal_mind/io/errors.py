"""Gateway-layer error taxonomy.

Distinct from the substrate ``core.errors`` taxonomy: gateway errors describe
*provider* failures, and their retryability is decided by the :class:`Gateway`
itself. Subclassing the substrate base keeps them package-native without
entangling the two taxonomies (which have different retry rules).
"""

from __future__ import annotations

from universal_mind.core.errors import UniversalMindError


class ProviderError(UniversalMindError):
    """Base class for all provider/gateway failures."""


class ProviderTransient(ProviderError):
    """A temporary provider failure (timeout, 5xx, rate-limited).

    Safe (and expected) to retry with backoff or to fail over to a fallback
    provider. Never a caller mistake and never fatal on its own.
    """


class ProviderPermanent(ProviderError):
    """A permanent provider failure (model error, malformed response).

    Retrying will not help; the gateway should fail over to the next provider
    rather than burn retries on the same bad provider.
    """


class ProviderConfig(ProviderError):
    """A caller/configuration problem (missing API key, bad base URL).

    Not retryable and not a provider fault — the configuration must be fixed.
    """