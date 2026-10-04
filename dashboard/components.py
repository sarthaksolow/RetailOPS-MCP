from typing import List, Dict, Any
from dash import html
import plotly.graph_objects as go
from dashboard.domain import MetricCardData, InventoryItem, Decision, ServiceStatus


def render_metric_card(card: MetricCardData) -> html.Div:
    trend_elem = html.Div(card.trend, className="card-trend") if card.trend else None
    return html.Div(
        className="card",
        children=[
            html.Div(card.title, className="card-title"),
            html.Div(card.value, className="card-value"),
            html.Div(card.subtitle, className="card-subtext"),
            trend_elem,
        ],
    )


def render_risk_badge(risk: str) -> html.Span:
    norm = risk.lower()
    return html.Span(risk.upper(), className=f"badge badge-{norm}")


def render_status_badge(status: str) -> html.Span:
    norm = "approved" if "Approved" in status else "pending" if "Pending" in status else "overridden"
    return html.Span(status, className=f"badge badge-{norm}")


def create_inventory_runway_chart(items: List[InventoryItem], theme: str = "dark") -> go.Figure:
    is_dark = theme == "dark"
    bg = "#04290e" if is_dark else "#e2fed0"
    txt = "#e6eee8" if is_dark else "#02240b"
    grid = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"

    series_names = [it.series_id.replace("CA_1_", "") for it in items]
    runways = [it.runway_days for it in items]
    lead_times = [it.lead_time_days for it in items]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Stock Runway (Days)",
            x=series_names,
            y=runways,
            marker_color="#4f61d8",
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Lead Time Boundary (7d)",
            x=series_names,
            y=lead_times,
            mode="lines+markers",
            line=dict(color="#f1b434", width=2, dash="dash"),
        )
    )
    fig.update_layout(
        title="Inventory Runway vs Supplier Lead Time",
        plot_bgcolor=bg,
        paper_bgcolor=bg,
        font=dict(color=txt, size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor=grid),
        yaxis=dict(gridcolor=grid, title="Days"),
        height=280,
    )
    return fig


def create_scenario_comparison_chart(m5_data: Dict[str, Any], theme: str = "dark") -> go.Figure:
    is_dark = theme == "dark"
    bg = "#04290e" if is_dark else "#e2fed0"
    txt = "#e6eee8" if is_dark else "#02240b"
    grid = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"

    scenarios = ["SCEN-01", "SCEN-02", "SCEN-03", "SCEN-04", "SCEN-05"]
    sc_names = ["Normal", "Surge", "Low Inv", "Delay", "Stress"]
    retailops_sc = m5_data.get("retailops_mcp", {}).get("scenarios", {})
    baseline_sc = m5_data.get("fixed_threshold_baseline", {}).get("scenarios", {})

    ro_service = [retailops_sc.get(s, {}).get("mean_service_level_pct", 0) for s in scenarios]
    base_service = [baseline_sc.get(s, {}).get("mean_service_level_pct", 0) for s in scenarios]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="RetailOps Service Level (%)", x=sc_names, y=ro_service, marker_color="#4f61d8"))
    fig.add_trace(go.Bar(name="Fixed-Threshold (s, S) (%)", x=sc_names, y=base_service, marker_color="#8ea594"))
    fig.update_layout(
        title="Service Level Across Operational Scenarios",
        barmode="group",
        plot_bgcolor=bg,
        paper_bgcolor=bg,
        font=dict(color=txt, size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor=grid),
        yaxis=dict(gridcolor=grid, title="Service Level (%)", range=[0, 105]),
        height=280,
    )
    return fig


def create_architecture_tradeoff_chart(arch_data: Dict[str, Any], theme: str = "dark") -> go.Figure:
    is_dark = theme == "dark"
    bg = "#04290e" if is_dark else "#e2fed0"
    txt = "#e6eee8" if is_dark else "#02240b"
    grid = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"

    overall = arch_data.get("overall_comparison", {})
    names, stockouts, costs = [], [], []
    for k, v in overall.items():
        label = k.replace("_", " ").title()
        names.append(label)
        stockouts.append(v.get("mean_stockout_rate_pct", 0))
        costs.append(v.get("mean_total_cost", 0))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=costs,
            y=stockouts,
            mode="markers+text",
            text=names,
            textposition="top center",
            marker=dict(size=12, color="#4f61d8"),
        )
    )
    fig.update_layout(
        title="Operating Cost vs Stockout Rate Trade-off",
        plot_bgcolor=bg,
        paper_bgcolor=bg,
        font=dict(color=txt, size=12),
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(gridcolor=grid, title="Mean Operating Cost ($)"),
        yaxis=dict(gridcolor=grid, title="Stockout Rate (%)"),
        height=300,
    )
    return fig
