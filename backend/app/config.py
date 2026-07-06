"""Shared configuration constants for the backend.

The full Config loader and environment-variable validation (LLM_API_KEY,
LLM_ENDPOINT, BACKEND_PORT) is implemented by task 4.1. This module only fixes
the agreed local loopback defaults so every component references one source.
"""

# Local loopback host. Frontend<->Backend traffic never leaves the machine
# (Requirement 10.3). Only the LLM API call reaches the network.
BACKEND_HOST = "127.0.0.1"

# Agreed default local port. Overridable via the BACKEND_PORT environment
# variable (see project root .env.example). Chosen in the high, uncommon range
# to reduce the chance of a port conflict on a developer PC (Requirement 10.8).
DEFAULT_BACKEND_PORT = 8756

# Names of the required environment variables. Startup validation (task 4.1)
# reports any missing entry by these names (Requirements 10.6, 11.9).
ENV_LLM_API_KEY = "LLM_API_KEY"
ENV_LLM_ENDPOINT = "LLM_ENDPOINT"
ENV_BACKEND_PORT = "BACKEND_PORT"
