"""Closed Beta Operations Platform (Task 026).

Read-only aggregation services that surface insights from the existing
bounded contexts (identity, learning, assessment, mastery, content,
administration, analytics, infrastructure) for beta operations,
product validation, and user success.

This module does NOT modify the domain model or existing APIs.
All queries are read-only SELECTs against existing tables plus the new
Task 026 tables (feedback votes, release notes, experiments).
"""

from __future__ import annotations

from app.application.beta_ops.service import BetaOpsService, get_beta_ops_service

__all__ = ["BetaOpsService", "get_beta_ops_service"]
