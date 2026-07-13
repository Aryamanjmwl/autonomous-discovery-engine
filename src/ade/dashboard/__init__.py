"""Static local dashboard generation for ADE reports."""

from __future__ import annotations

from ade.dashboard.local_dashboard import (
    LocalDashboardExportResult,
    collect_dashboard_data,
    export_local_dashboard,
    render_dashboard_html,
)
from ade.dashboard.service import DashboardBuildResult, generate_dashboard

__all__ = [
    "DashboardBuildResult",
    "LocalDashboardExportResult",
    "collect_dashboard_data",
    "export_local_dashboard",
    "generate_dashboard",
    "render_dashboard_html",
]
