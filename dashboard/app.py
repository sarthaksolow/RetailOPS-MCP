import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dash
from dash import html, dcc
from dashboard.callbacks import register_callbacks
from dashboard.layout import render_sidebar_nav_links

# Root path for dashboard assets
assets_dir = Path(__file__).resolve().parent / "assets"

app = dash.Dash(
    __name__,
    title="RetailOps | MCP Decision Platform",
    assets_folder=str(assets_dir),
    suppress_callback_exceptions=True,
)

server = app.server

# Root application layout
app.layout = html.Div(
    id="app-container",
    **{"data-theme": "dark"},
    children=[
        dcc.Store(id="theme-store", data="dark", storage_type="local"),
        dcc.Store(id="page-store", data="dashboard"),
        html.Div(
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
                    children=render_sidebar_nav_links("dashboard"),
                ),
                html.Div(
                    className="sidebar-footer",
                    children=[
                        html.Button(
                            "Theme: Dark",
                            id="theme-toggle-btn",
                            className="theme-toggle-btn",
                            n_clicks=0,
                        )
                    ],
                ),
            ],
        ),
        html.Div(
            className="main-wrapper",
            children=[
                html.Div(
                    className="header-bar",
                    children=[
                        html.Div(id="header-title", className="header-title", children="Retail Operations Dashboard"),
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "10px"},
                            children=[
                                html.Span("●", style={"color": "var(--success)"}),
                                html.Span("MCP Cluster Online", style={"fontSize": "12px", "color": "var(--text-secondary)"}),
                            ],
                        ),
                    ],
                ),
                html.Div(id="page-content-area", className="content-body"),
            ],
        ),
    ],
)

# Register callbacks
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
