"""Validated clients for external biomedical services."""

from genegarden_api.services.clients.europe_pmc import EuropePmcClient
from genegarden_api.services.clients.open_targets import OpenTargetsClient

__all__ = ["EuropePmcClient", "OpenTargetsClient"]
