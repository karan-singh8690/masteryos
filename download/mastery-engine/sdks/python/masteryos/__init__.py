"""MasteryOS Python SDK — official client library for the MasteryOS API.

Usage:
    from masteryos import MasteryOS
    client = MasteryOS(api_key="your-api-key")
    dashboard = client.learning.get_dashboard()
"""

from masteryos.client import MasteryOS

__version__ = "1.0.0"
__all__ = ["MasteryOS"]
