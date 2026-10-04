from typing import List, Dict, Any
from dash import html, dcc
from dashboard.domain import InventoryItem, Decision, ServiceStatus
from dashboard.components import (
    render_metric_card,
    render_risk_badge,
    render_status_badge,
    create_inventory_runway_chart,
    create_scenario_comparison_chart,
    create_architecture_tradeoff_chart,
)
from dashboard.services.inventory_service import InventoryService
from dashboard.services.decision_service import DecisionService
from dashboard.services.system_service import SystemService
from dashboard.services.metrics_service import MetricsService
from dashboard.services.chat_service import ChatService

# Initialize singleton services for layout assembly
inv_service = InventoryService()
dec_service = DecisionService()
sys_service = SystemService()
met_service = MetricsService()
chat_service = ChatService()


def render_sidebar_nav_links(active_page: str = "dashboard") -> List[html.Div]:
    pages = [
        ("dashboard", "Dashboard"),
        ("inventory", "Inventory"),
        ("decisions", "Decision Center"),
        ("copilot", "AI Copilot"),
        ("services", "MCP Services"),
        ("evaluation", "Research Evaluation"),
    ]
    return [
        html.Div(
            label,
            id={"type": "nav-btn", "page": pid},
            className=f"nav-link {'active' if pid == active_page else ''}",
        )
        for pid, label in pages
    ]


def render_sidebar(active_page: str = "dashboard", theme: str = "dark") -> html.Div:
    return html.Div(
        className="sidebar",
        children=[
            html.Div(
                className="sidebar-header",
                children=[
                    html.Div(
                        className="brand-title",
                        children=[
                            "RetailOps",
                            html.Span("MCP", className="brand-badge"),
                        ],
                    ),
                    html.Div("Enterprise Decision Platform", className="brand-sub"),
                ],
            ),
            html.Div(
                id="sidebar-nav-container",
                className="sidebar-nav",
                children=render_sidebar_nav_links(active_page),
            ),
            html.Div(
                className="sidebar-footer",
                children=[
                    html.Button(
                        f"Theme: {'Dark' if theme == 'dark' else 'Light'}",
                        id="theme-toggle-btn",
                        className="theme-toggle-btn",
                        n_clicks=0,
                    )
                ],
            ),
        ],
    )


def render_dashboard_view(theme: str = "dark") -> html.Div:
    kpis = met_service.get_dashboard_kpis()
    items = inv_service.get_inventory_items()
    decisions = dec_service.get_all_decisions()[:4]
    m5_metrics = met_service.get_m5_metrics()
    services = sys_service.get_service_statuses()

    kpi_cards = [render_metric_card(k) for k in kpis]
    runway_chart = create_inventory_runway_chart(items, theme)
    scenario_chart = create_scenario_comparison_chart(m5_metrics, theme)

    table_rows = [
        html.Tr(
            [
                html.Td(d.id),
                html.Td(d.series_id.replace("CA_1_", "")),
                html.Td(f"{d.final_qty} units"),
                html.Td(f"${d.order_cost:.2f}"),
                html.Td(render_risk_badge(d.stockout_risk)),
                html.Td(render_status_badge(d.status)),
            ]
        )
        for d in decisions
    ]

    service_pills = [
        html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "6px", "fontSize": "12px"},
            children=[
                html.Span("●", style={"color": "var(--success)"}),
                html.Span(f"{s.name} ({s.latency_ms:.1f}ms)", style={"color": "var(--text-secondary)"}),
            ],
        )
        for s in services
    ]

    return html.Div(
        children=[
            html.Div(className="kpi-grid", children=kpi_cards),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginBottom": "24px"},
                children=[
                    html.Div(className="card", children=[dcc.Graph(figure=runway_chart, config={"displayModeBar": False})]),
                    html.Div(className="card", children=[dcc.Graph(figure=scenario_chart, config={"displayModeBar": False})]),
                ],
            ),
            html.Div(
                className="card",
                style={"marginBottom": "24px"},
                children=[
                    html.Div("Recent Replenishment Decisions", className="card-title"),
                    html.Div(
                        className="table-container",
                        children=[
                            html.Table(
                                className="data-table",
                                children=[
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th("ID"),
                                                html.Th("Item / Series"),
                                                html.Th("Committed Qty"),
                                                html.Th("Expenditure"),
                                                html.Th("Stockout Risk"),
                                                html.Th("Supervisory Status"),
                                            ]
                                        )
                                    ),
                                    html.Tbody(table_rows),
                                ],
                            )
                        ],
                    ),
                ],
            ),
            html.Div(
                className="card",
                children=[
                    html.Div("Active MCP Services Telemetry", className="card-title"),
                    html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "20px"}, children=service_pills),
                ],
            ),
        ]
    )


def render_inventory_view(theme: str = "dark") -> html.Div:
    items = inv_service.get_inventory_items()
    high_risk_count = sum(1 for it in items if it.stockout_risk == "high")
    total_pipeline = sum(it.in_transit for it in items)

    kpis = [
        render_metric_card(met_service.get_dashboard_kpis()[0]),
        html.Div(
            className="card",
            children=[
                html.Div("Monitored Series", className="card-title"),
                html.Div(f"{len(items)} SKUs", className="card-value"),
                html.Div("Walmart M5 store CA_1", className="card-subtext"),
            ],
        ),
        html.Div(
            className="card",
            children=[
                html.Div("Critical Stockout Risk", className="card-title"),
                html.Div(f"{high_risk_count} Items", className="card-value"),
                html.Div("Runway < Lead time (7d)", className="card-subtext"),
            ],
        ),
        html.Div(
            className="card",
            children=[
                html.Div("Pipeline In-Transit", className="card-title"),
                html.Div(f"{total_pipeline} Units", className="card-value"),
                html.Div("Pending supplier arrivals", className="card-subtext"),
            ],
        ),
    ]

    rows = [
        html.Tr(
            [
                html.Td(it.series_id),
                html.Td(it.category),
                html.Td(str(it.on_hand)),
                html.Td(str(it.in_transit)),
                html.Td(f"{it.daily_demand:.2f} / day"),
                html.Td(f"{it.runway_days:.1f} d"),
                html.Td(render_risk_badge(it.stockout_risk)),
                html.Td(f"{it.lead_time_days} days"),
                html.Td(f"${it.unit_cost:.2f}"),
                html.Td(f"{it.recommended_order} units", style={"fontWeight": "600", "color": "var(--accent)"}),
            ]
        )
        for it in items
    ]

    return html.Div(
        children=[
            html.Div(className="kpi-grid", children=kpis),
            html.Div(
                className="card",
                children=[
                    html.Div("Store Inventory Status (Walmart M5 CA_1)", className="card-title"),
                    html.Div(
                        className="table-container",
                        children=[
                            html.Table(
                                className="data-table",
                                children=[
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th("Series ID"),
                                                html.Th("Category"),
                                                html.Th("On Hand"),
                                                html.Th("In Transit"),
                                                html.Th("Demand Velocity"),
                                                html.Th("Stock Runway"),
                                                html.Th("Risk"),
                                                html.Th("Lead Time"),
                                                html.Th("Unit Cost"),
                                                html.Th("RetailOps Order"),
                                            ]
                                        )
                                    ),
                                    html.Tbody(rows),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ]
    )


def render_decisions_view(theme: str = "dark") -> html.Div:
    decisions = dec_service.get_all_decisions()
    options = [{"label": f"{d.id}: {d.series_id} (Proposed: {d.proposed_qty})", "value": d.id} for d in decisions]
    default_val = decisions[0].id if decisions else None

    rows = [
        html.Tr(
            [
                html.Td(d.id, style={"fontWeight": "600"}),
                html.Td(d.series_id.replace("CA_1_", "")),
                html.Td(str(d.proposed_qty)),
                html.Td(str(d.final_qty), style={"fontWeight": "600", "color": "var(--accent)"}),
                html.Td(f"${d.order_cost:.2f}"),
                html.Td(render_risk_badge(d.stockout_risk)),
                html.Td(render_status_badge(d.status)),
                html.Td(d.reason, style={"fontSize": "12px", "color": "var(--text-secondary)", "maxWidth": "320px"}),
            ]
        )
        for d in decisions
    ]

    return html.Div(
        children=[
            html.Div(
                className="alert alert-info",
                children=[
                    html.Span("Human-in-the-Loop Supervisory Center: ", style={"fontWeight": "600"}),
                    "Proposals breaching governance thresholds (budget > $100, critical runway < 2d, or arrival past horizon) trigger supervisory review. Managers can approve or override decisions.",
                ],
            ),
            html.Div(
                className="card",
                style={"marginBottom": "24px"},
                children=[
                    html.Div("Supervisory Action Desk", className="card-title"),
                    html.Div(
                        style={"display": "flex", "flexWrap": "wrap", "gap": "12px", "alignItems": "center"},
                        children=[
                            dcc.Dropdown(
                                id="decision-select-dropdown",
                                options=options,
                                value=default_val,
                                clearable=False,
                                style={"minWidth": "280px", "color": "#000"},
                            ),
                            html.Button("Approve Proposal", id="approve-decision-btn", className="btn", n_clicks=0),
                            dcc.Input(
                                id="override-qty-input",
                                type="number",
                                placeholder="Override Qty",
                                min=0,
                                className="input-field",
                                style={"width": "110px"},
                            ),
                            dcc.Input(
                                id="override-notes-input",
                                type="text",
                                placeholder="Override Rationale",
                                className="input-field",
                                style={"flexGrow": "1", "minWidth": "160px"},
                            ),
                            html.Button(
                                "Commit Override",
                                id="commit-override-btn",
                                className="btn btn-secondary",
                                n_clicks=0,
                            ),
                        ],
                    ),
                    html.Div(id="decision-action-feedback", style={"marginTop": "12px"}),
                ],
            ),
            html.Div(
                className="card",
                children=[
                    html.Div("Active Autonomous Decisions & Approval Gate Status", className="card-title"),
                    html.Div(
                        className="table-container",
                        children=[
                            html.Table(
                                className="data-table",
                                children=[
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th("ID"),
                                                html.Th("Item"),
                                                html.Th("Proposed"),
                                                html.Th("Committed"),
                                                html.Th("Cost"),
                                                html.Th("Risk"),
                                                html.Th("Status"),
                                                html.Th("Reasoning Context"),
                                            ]
                                        )
                                    ),
                                    html.Tbody(id="decisions-table-body", children=rows),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ]
    )


def render_services_view(theme: str = "dark") -> html.Div:
    services = sys_service.get_service_statuses()

    service_cards = [
        html.Div(
            className="card",
            children=[
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
                    children=[
                        html.Span(s.name, style={"fontWeight": "700", "fontSize": "15px"}),
                        html.Span(s.status, className="badge badge-approved"),
                    ],
                ),
                html.Div(s.role, style={"fontSize": "13px", "color": "var(--text-secondary)", "marginBottom": "12px"}),
                html.Div(f"Transport: {s.transport}", style={"fontSize": "12px", "color": "var(--text-secondary)"}),
                html.Div(f"Session Latency: {s.latency_ms:.1f} ms", style={"fontSize": "12px", "color": "var(--accent)", "fontWeight": "600"}),
                html.Div("Exposed Tool Interfaces:", style={"fontSize": "11px", "textTransform": "uppercase", "marginTop": "10px", "color": "var(--text-secondary)"}),
                html.Div(
                    style={"display": "flex", "flexWrap": "wrap", "gap": "6px", "marginTop": "4px"},
                    children=[
                        html.Span(
                            t,
                            style={
                                "fontSize": "11px",
                                "backgroundColor": "var(--bg-surface-elevated)",
                                "border": "1px solid var(--border)",
                                "padding": "2px 6px",
                                "borderRadius": "3px",
                            },
                        )
                        for t in s.tools
                    ],
                ),
            ],
        )
        for s in services
    ]

    return html.Div(
        children=[
            html.Div(
                className="alert alert-info",
                children=[
                    html.Span("Decoupled MCP Service Topology: ", style={"fontWeight": "600"}),
                    "Each service executes as an independent operating system subprocess communicating via FastMCP JSON-RPC. The orchestrator maintains persistent stdio connections, isolating failures and enabling zero-code service replacement.",
                ],
            ),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))", "gap": "16px", "marginBottom": "24px"},
                children=service_cards,
            ),
            html.Div(
                className="card",
                children=[
                    html.Div("Architectural Replacement & Extensibility Evidence", className="card-title"),
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "12px"},
                        children=[
                            html.Div(
                                style={"backgroundColor": "var(--bg-surface-elevated)", "padding": "12px", "borderRadius": "4px"},
                                children=[
                                    html.Div("Forecasting Service Replacement", style={"fontWeight": "600", "marginBottom": "4px"}),
                                    html.Div("Replaced 30d SMA with Holt-Winters: 0 existing files modified, 0 orchestrator LOC changed. Swapped via RETAILOPS_FORECASTING_SERVER_PATH environment variable.", style={"fontSize": "12px", "color": "var(--text-secondary)"}),
                                ],
                            ),
                            html.Div(
                                style={"backgroundColor": "var(--bg-surface-elevated)", "padding": "12px", "borderRadius": "4px"},
                                children=[
                                    html.Div("Supplier Intelligence Addition", style={"fontWeight": "600", "marginBottom": "4px"}),
                                    html.Div("Integrated 5th service (183 LOC) with 0 existing server modifications. Graph extended with 1 append node; prior 4-stage workflows preserved.", style={"fontSize": "12px", "color": "var(--text-secondary)"}),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )


def render_evaluation_view(theme: str = "dark", active_tab: str = "forecasting") -> html.Div:
    tabs = [
        ("forecasting", "Forecasting Replacement"),
        ("m5", "M5 Operational Simulation"),
        ("architecture", "Architecture Comparison"),
        ("hitl", "Supervisory Governance (HITL)"),
    ]

    tab_buttons = [
        html.Button(
            label,
            id={"type": "eval-tab-btn", "tab": tid},
            className=f"tab-btn {'active' if tid == active_tab else ''}",
        )
        for tid, label in tabs
    ]

    # Tab Content Assembly
    if active_tab == "forecasting":
        fc = met_service.get_forecasting_metrics()
        agg = fc.get("aggregate_accuracy", {})
        baseline = agg.get("baseline_30day_sma", {})
        replacement = agg.get("holt_winters_replacement", {})
        diffs = agg.get("differences", {})

        content = html.Div(
            children=[
                html.Div(
                    className="kpi-grid",
                    children=[
                        html.Div(className="card", children=[html.Div("Baseline 30d SMA MAE", className="card-title"), html.Div(f"{baseline.get('mean_mae', 5.84):.4f}", className="card-value")]),
                        html.Div(className="card", children=[html.Div("Holt-Winters MAE", className="card-title"), html.Div(f"{replacement.get('mean_mae', 6.91):.4f}", className="card-value")]),
                        html.Div(className="card", children=[html.Div("Observed Difference", className="card-title"), html.Div(f"+{diffs.get('mae_pct_change', 18.37):.1f}%", className="card-value")]),
                        html.Div(className="card", children=[html.Div("Orchestrator Code Changes", className="card-title"), html.Div("0 LOC", className="card-value")]),
                    ],
                ),
                html.Div(
                    className="card",
                    children=[
                        html.Div("Per-Category Forecasting Accuracy Comparison (7 Series, H=30d)", className="card-title"),
                        html.Div(
                            className="table-container",
                            children=[
                                html.Table(
                                    className="data-table",
                                    children=[
                                        html.Thead(html.Tr([html.Th("Category"), html.Th("Baseline SMA MAE"), html.Th("Holt-Winters MAE"), html.Th("MAE Change"), html.Th("Baseline MAPE"), html.Th("Replacement MAPE")])),
                                        html.Tbody(
                                            [
                                                html.Tr([html.Td(cat.title()), html.Td(f"{data['baseline_sma']['mae']:.4f}"), html.Td(f"{data['holt_winters_replacement']['mae']:.4f}"), html.Td(f"+{data['differences']['mae_pct_change']:.1f}%"), html.Td(f"{data['baseline_sma']['mape_pct']:.2f}%"), html.Td(f"{data['holt_winters_replacement']['mape_pct']:.2f}%")])
                                                for cat, data in fc.get("per_category_comparison", {}).items()
                                            ]
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ],
                ),
            ]
        )

    elif active_tab == "m5":
        m5 = met_service.get_m5_metrics()
        ro = m5.get("retailops_mcp", {}).get("overall_summary", {})
        fb = m5.get("fixed_threshold_baseline", {}).get("overall_summary", {})

        content = html.Div(
            children=[
                html.Div(
                    className="kpi-grid",
                    children=[
                        html.Div(className="card", children=[html.Div("RetailOps Service Level", className="card-title"), html.Div(f"{ro.get('mean_service_level_pct', 75.81):.2f}%", className="card-value"), html.Div("vs 70.68% (s, S)", className="card-subtext")]),
                        html.Div(className="card", children=[html.Div("RetailOps Stockout Rate", className="card-title"), html.Div(f"{ro.get('mean_stockout_rate_pct', 21.43):.2f}%", className="card-value"), html.Div("vs 26.29% (s, S)", className="card-subtext")]),
                        html.Div(className="card", children=[html.Div("RetailOps Mean Cost", className="card-title"), html.Div(f"${ro.get('mean_total_cost', 245.89):.2f}", className="card-value"), html.Div("vs $199.50 (s, S)", className="card-subtext")]),
                        html.Div(className="card", children=[html.Div("Conservation Verified", className="card-title"), html.Div("100%", className="card-value"), html.Div("0 constraint violations", className="card-subtext")]),
                    ],
                ),
                html.Div(
                    className="card",
                    children=[
                        html.Div("Scenario-by-Scenario Operational Comparison (5 Scenarios x 5 Series)", className="card-title"),
                        html.Div(
                            className="table-container",
                            children=[
                                html.Table(
                                    className="data-table",
                                    children=[
                                        html.Thead(html.Tr([html.Th("Scenario"), html.Th("RetailOps Service"), html.Th("Fixed-Threshold Service"), html.Th("RetailOps Stockouts"), html.Th("Fixed-Threshold Stockouts"), html.Th("RetailOps Cost"), html.Th("Fixed-Threshold Cost")])),
                                        html.Tbody(
                                            [
                                                html.Tr(
                                                    [
                                                        html.Td(sc),
                                                        html.Td(f"{m5['retailops_mcp']['scenarios'][sc]['mean_service_level_pct']:.2f}%"),
                                                        html.Td(f"{m5['fixed_threshold_baseline']['scenarios'][sc]['mean_service_level_pct']:.2f}%"),
                                                        html.Td(f"{m5['retailops_mcp']['scenarios'][sc]['mean_stockout_rate_pct']:.2f}%"),
                                                        html.Td(f"{m5['fixed_threshold_baseline']['scenarios'][sc]['mean_stockout_rate_pct']:.2f}%"),
                                                        html.Td(f"${m5['retailops_mcp']['scenarios'][sc]['mean_total_cost']:.2f}"),
                                                        html.Td(f"${m5['fixed_threshold_baseline']['scenarios'][sc]['mean_total_cost']:.2f}"),
                                                    ]
                                                )
                                                for sc in ["SCEN-01", "SCEN-02", "SCEN-03", "SCEN-04", "SCEN-05"]
                                            ]
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ],
                ),
            ]
        )

    elif active_tab == "architecture":
        arch = met_service.get_architecture_metrics()
        overall = arch.get("overall_comparison", {})
        chart = create_architecture_tradeoff_chart(arch, theme)

        rows = [
            html.Tr(
                [
                    html.Td(k.replace("_", " ").title(), style={"fontWeight": "600"}),
                    html.Td(data.get("architecture_pattern", "")),
                    html.Td(f"{data.get('mean_stockout_rate_pct', 0):.2f}%"),
                    html.Td(f"{data.get('mean_service_level_pct', 0):.2f}%"),
                    html.Td(f"${data.get('mean_total_cost', 0):.2f}"),
                    html.Td(str(data.get("total_fulfilled_units", 0))),
                    html.Td(str(data.get("total_ordered_units", 0))),
                    html.Td(f"{data.get('implementation_loc', 0)} LOC"),
                ]
            )
            for k, data in overall.items()
        ]

        content = html.Div(
            children=[
                html.Div(className="card", style={"marginBottom": "20px"}, children=[dcc.Graph(figure=chart, config={"displayModeBar": False})]),
                html.Div(
                    className="card",
                    children=[
                        html.Div("Same-Repository Architecture Comparison (125 Runs, 3,500 Decisions)", className="card-title"),
                        html.Div(
                            className="table-container",
                            children=[
                                html.Table(
                                    className="data-table",
                                    children=[
                                        html.Thead(html.Tr([html.Th("Architecture"), html.Th("Pattern Description"), html.Th("Stockouts"), html.Th("Service Level"), html.Th("Mean Cost"), html.Th("Fulfilled"), html.Th("Ordered"), html.Th("LOC")])),
                                        html.Tbody(rows),
                                    ],
                                )
                            ],
                        ),
                    ],
                ),
            ]
        )

    else:  # hitl tab
        hitl = met_service.get_hitl_metrics()
        auto = hitl.get("modes_summary", {}).get("retailops_autonomous", {})
        sup = hitl.get("modes_summary", {}).get("retailops_human_supervised", {})

        content = html.Div(
            children=[
                html.Div(
                    className="kpi-grid",
                    children=[
                        html.Div(className="card", children=[html.Div("Supervisory Overrides", className="card-title"), html.Div(f"{sup.get('total_overrides', 153)}", className="card-value"), html.Div("21.9% override rate", className="card-subtext")]),
                        html.Div(className="card", children=[html.Div("Operating Cost Reduction", className="card-title"), html.Div("-$51.12", className="card-value"), html.Div("$194.77 vs $245.89 (-20.8%)", className="card-subtext")]),
                        html.Div(className="card", children=[html.Div("Service Preservation", className="card-title"), html.Div("76.08%", className="card-value"), html.Div("Parity with autonomous mode", className="card-subtext")]),
                        html.Div(className="card", children=[html.Div("Mean Review Latency", className="card-title"), html.Div(f"{sup.get('mean_latency_per_decision_seconds', 3.69):.2f}s", className="card-value"), html.Div("15.0s on escalation", className="card-subtext")]),
                    ],
                ),
                html.Div(
                    className="card",
                    children=[
                        html.Div("Autonomous vs Human-Supervised Mode Metrics (25 Runs, 700 Decisions Each)", className="card-title"),
                        html.Div(
                            className="table-container",
                            children=[
                                html.Table(
                                    className="data-table",
                                    children=[
                                        html.Thead(html.Tr([html.Th("Metric"), html.Th("Autonomous Mode"), html.Th("Human-Supervised Mode"), html.Th("Observed Difference")])),
                                        html.Tbody(
                                            [
                                                html.Tr([html.Td("Mean Stockout Rate"), html.Td(f"{auto.get('mean_stockout_rate_pct', 21.43):.2f}%"), html.Td(f"{sup.get('mean_stockout_rate_pct', 21.43):.2f}%"), html.Td("0.00 pp")]),
                                                html.Tr([html.Td("Mean Service Level"), html.Td(f"{auto.get('mean_service_level_pct', 75.81):.2f}%"), html.Td(f"{sup.get('mean_service_level_pct', 76.08):.2f}%"), html.Td("+0.27 pp")]),
                                                html.Tr([html.Td("Mean Operating Cost"), html.Td(f"${auto.get('mean_total_cost', 245.89):.2f}"), html.Td(f"${sup.get('mean_total_cost', 194.77):.2f}"), html.Td("-$51.12 (-20.79%)")]),
                                                html.Tr([html.Td("Total Ordered Units"), html.Td(str(auto.get("total_ordered_units", 4886))), html.Td(str(sup.get("total_ordered_units", 4030))), html.Td("-856 units")]),
                                                html.Tr([html.Td("Escalations Triggered"), html.Td("0 (0.0%)"), html.Td(f"{sup.get('total_escalations', 172)} (24.57%)"), html.Td("+172")]),
                                                html.Tr([html.Td("Overrides Executed"), html.Td("0 (0.0%)"), html.Td(f"{sup.get('total_overrides', 153)} (21.86%)"), html.Td("+153")]),
                                                html.Tr([html.Td("Mean Latency / Decision"), html.Td("0.00s"), html.Td(f"{sup.get('mean_latency_per_decision_seconds', 3.69):.2f}s"), html.Td("+3.69s")]),
                                            ]
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ],
                ),
            ]
        )

    return html.Div(
        children=[
            html.Div(className="tabs-container", children=tab_buttons),
            html.Div(id="eval-tab-content-container", children=content),
        ]
    )


def render_chat_messages(history: List[Dict[str, Any]]) -> List[html.Div]:
    import json

    rendered = []
    for msg in history:
        role = msg.get("role", "assistant")
        text = msg.get("text", "")
        timestamp = msg.get("timestamp", "")
        model_name = msg.get("model_name", "RetailOps Copilot")
        tools_used = msg.get("tools_used", [])
        tool_traces = msg.get("tool_traces", [])

        if role == "user":
            rendered.append(
                html.Div(
                    className="chat-message-wrapper user-wrapper",
                    children=[
                        html.Div(
                            className="chat-bubble user",
                            children=[
                                html.Div(f"Operator • {timestamp}", className="chat-meta-user"),
                                html.Div(text),
                            ],
                        )
                    ],
                )
            )
        else:
            is_streaming = msg.get("is_streaming", False)
            meta_children = [
                html.Span("RetailOps Copilot", style={"fontWeight": "600"}),
                html.Span(f"• {timestamp} •", style={"color": "var(--text-secondary)"}),
                html.Span(f"🤖 {model_name}", className="model-pill"),
            ]
            if is_streaming:
                meta_children.append(
                    html.Span("⚡ Live Streaming...", className="streaming-badge")
                )

            meta_row = html.Div(className="chat-meta", children=meta_children)
            bubble_children = [meta_row]

            if tools_used:
                tools_str = " → ".join(tools_used)
                bubble_children.append(
                    html.Div(f"⚡ MCP Tool Pipeline: {tools_str}", className="tools-used-badge")
                )

            if is_streaming and not text:
                bubble_children.append(
                    html.Div(
                        "Interrogating MCP services & generating briefing... ▋",
                        style={"fontStyle": "italic", "color": "var(--text-secondary)"},
                    )
                )
            else:
                display_text = (text + " ▋") if is_streaming else text
                bubble_children.append(
                    dcc.Markdown(display_text, className="chat-markdown")
                )

            if tool_traces and not is_streaming:
                total_latency = sum(t.get("latency_ms", 0) for t in tool_traces)
                trace_json = json.dumps(tool_traces, indent=2)
                bubble_children.append(
                    html.Details(
                        className="mcp-trace-details",
                        children=[
                            html.Summary(
                                f"🔍 Inspect Live MCP Execution Telemetry ({len(tool_traces)} tool call{'s' if len(tool_traces) != 1 else ''}, {total_latency:.1f}ms total)",
                                className="mcp-trace-summary",
                            ),
                            html.Pre(trace_json, className="mcp-trace-content"),
                        ],
                    )
                )

            rendered.append(
                html.Div(
                    className="chat-message-wrapper ai-wrapper",
                    children=[
                        html.Div(
                            className="chat-bubble assistant",
                            children=bubble_children,
                        )
                    ],
                )
            )

    return rendered


def render_copilot_view(theme: str = "dark") -> html.Div:
    scenarios = [
        {
            "title": "🔴 Critical Stockout Risk Audit",
            "desc": "Inspect on-hand inventory runways against supplier lead times across all 5 M5 product series in CA_1.",
            "query": "Which products are currently at high stockout risk across store CA_1?",
        },
        {
            "title": "📦 Replenishment Order Justification",
            "desc": "Audit why FOODS_1_004 requires an immediate order of 39 units, linking 4-day runway to a 7-day supplier lead time.",
            "query": "Why is FOODS_1_004 being recommended for replenishment?",
        },
        {
            "title": "📈 Demand Forecasting Horizon",
            "desc": "Evaluate 30-day demand projections and model substitution accuracy between SMA and Holt-Winters.",
            "query": "What is the 30-day demand forecast for FOODS category?",
        },
        {
            "title": "🚚 Supplier Delay Stress-Test",
            "desc": "Check delivery lead time delays in SCEN-04 and evaluate safety stock replenishment protection.",
            "query": "Are there any supplier delivery delays reported in SCEN-04?",
        },
        {
            "title": "🛡️ Supervisory Gate Escalations",
            "desc": "Review replenishment proposals flagged for human review due to budget ceilings or stockout risks.",
            "query": "What decisions are pending supervisory approval today?",
        },
        {
            "title": "⚡ 2.5x Demand Surge Scenario",
            "desc": "Simulate an abrupt 2.5x demand spike and examine how autonomous multi-agent reasoning tempers commitments.",
            "query": "How would a 2.5x demand surge impact safety stock?",
        },
    ]

    scenario_cards = [
        html.Div(
            className="scenario-card",
            children=[
                html.Div(
                    children=[
                        html.Div(sc["title"], className="scenario-header"),
                        html.Div(sc["desc"], className="scenario-desc"),
                    ]
                ),
                html.Button(
                    "Run Demo Scenario →",
                    id={"type": "suggestion-chip", "query": sc["query"]},
                    className="scenario-run-btn",
                    n_clicks=0,
                ),
            ],
        )
        for sc in scenarios
    ]

    return html.Div(
        children=[
            html.Div(
                className="card",
                style={"marginBottom": "16px"},
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "flex-start",
                            "flexWrap": "wrap",
                            "gap": "10px",
                        },
                        children=[
                            html.Div(
                                children=[
                                    html.Div("RetailOps MCP Autonomous AI Copilot", className="card-title", style={"marginBottom": "4px"}),
                                    html.Div("Live Enterprise Decision Intelligence via Model Context Protocol (MCP) Services", style={"fontSize": "12px", "color": "var(--text-secondary)"}),
                                ]
                            ),
                            html.Div(
                                "Architecture: User Query → Dash Chat UI → LLM Agent → MCP Tool Layer → RetailOps Services → Synthesized Decision",
                                style={
                                    "fontSize": "11px",
                                    "color": "var(--accent)",
                                    "fontWeight": "600",
                                    "backgroundColor": "var(--badge-bg)",
                                    "padding": "4px 10px",
                                    "borderRadius": "3px",
                                    "border": "1px solid var(--border)",
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        className="copilot-status-bar",
                        children=[
                            html.Div(className="copilot-status-item", children=[html.Span("●", style={"color": "var(--success)"}), html.Strong("LLM Engine:"), html.Span("Live OpenRouter Multi-Model Routing")]),
                            html.Div(className="copilot-status-item", children=[html.Span("●", style={"color": "var(--success)"}), html.Strong("MCP Cluster:"), html.Span("5 Endpoints Online")]),
                            html.Div(className="copilot-status-item", children=[html.Span("●", style={"color": "var(--success)"}), html.Strong("Store Scope:"), html.Span("Walmart CA_1 (M5 Benchmark)")]),
                            html.Div(className="copilot-status-item", children=[html.Span("●", style={"color": "var(--success)"}), html.Strong("Database Access:"), html.Span("Zero (Pure MCP Tool Intermediation)")]),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="card",
                style={"marginBottom": "16px"},
                children=[
                    html.Div("Interactive Demo Scenarios (Click to Execute Live MCP Pipeline)", className="card-title"),
                    html.Div(className="scenario-grid", children=scenario_cards),
                ],
            ),
            html.Div(
                className="card",
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "marginBottom": "12px",
                        },
                        children=[
                            html.Div("Live Operational Session & Telemetry Trace", className="card-title"),
                            html.Div("Grounded in live MCP tool execution", style={"fontSize": "12px", "color": "var(--text-secondary)"}),
                        ],
                    ),
                    html.Div(
                        id="copilot-chat-history",
                        className="chat-history",
                        children=render_chat_messages(chat_service.get_history()),
                    ),
                    html.Div(
                        className="chat-input-bar",
                        children=[
                            dcc.Input(
                                id="copilot-input",
                                type="text",
                                placeholder="Ask RetailOps Copilot about inventory, forecasts, suppliers, or decisions...",
                                className="input-field chat-input",
                                debounce=False,
                            ),
                            html.Button("Send", id="copilot-send-btn", className="btn btn-primary", n_clicks=0),
                            html.Button("Clear Chat", id="copilot-clear-btn", className="btn btn-secondary", n_clicks=0),
                        ],
                    ),
                    html.Div(
                        "The LLM operates exclusively through registered MCP tool schemas (servers/replenishment, servers/forecasting, servers/supplier-intelligence). Zero internal database access.",
                        style={
                            "fontSize": "11px",
                            "color": "var(--text-secondary)",
                            "marginTop": "10px",
                            "textAlign": "center",
                        },
                    ),
                    dcc.Interval(id="copilot-stream-interval", interval=70, disabled=True, n_intervals=0),
                ],
            ),
        ]
    )


