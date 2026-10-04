from dash import Input, Output, State, ALL, callback_context, html
from dashboard.layout import (
    render_sidebar,
    render_dashboard_view,
    render_inventory_view,
    render_decisions_view,
    render_copilot_view,
    render_services_view,
    render_evaluation_view,
    dec_service,
)
from dashboard.components import render_risk_badge, render_status_badge


def register_callbacks(app):

    # Theme toggle callback: toggles theme-store on user click
    @app.callback(
        Output("theme-store", "data"),
        Input("theme-toggle-btn", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_theme(n_clicks, current_theme):
        if not n_clicks:
            return current_theme or "dark"
        return "light" if current_theme == "dark" else "dark"

    # Sync theme to DOM attribute and button text
    @app.callback(
        Output("app-container", "data-theme"),
        Output("theme-toggle-btn", "children"),
        Input("theme-store", "data"),
    )
    def sync_theme_to_dom(current_theme):
        theme = current_theme or "dark"
        btn_text = f"Theme: {'Dark' if theme == 'dark' else 'Light'}"
        return theme, btn_text

    # Navigation callback: updates page-store
    @app.callback(
        Output("page-store", "data"),
        Input({"type": "nav-btn", "page": ALL}, "n_clicks"),
        State("page-store", "data"),
        prevent_initial_call=True,
    )
    def handle_navigation(n_clicks, current_page):
        ctx = callback_context
        if not ctx.triggered:
            return current_page
        prop_id = ctx.triggered[0]["prop_id"]
        import json

        trigger_data = json.loads(prop_id.split(".")[0])
        return trigger_data.get("page", current_page)

    # Update active class on nav links without touching theme button
    @app.callback(
        Output("sidebar-nav-container", "children"),
        Input("page-store", "data"),
    )
    def update_nav_links(active_page):
        from dashboard.layout import render_sidebar_nav_links
        return render_sidebar_nav_links(active_page or "dashboard")

    # Render main content & header title
    @app.callback(
        Output("page-content-area", "children"),
        Output("header-title", "children"),
        Input("page-store", "data"),
        Input("theme-store", "data"),
    )
    def render_content(active_page, active_theme):
        page_titles = {
            "dashboard": "Retail Operations Executive Dashboard",
            "inventory": "Store-Item Inventory & Runway Management",
            "decisions": "Autonomous Decision Center & Supervisory Gate",
            "copilot": "RetailOps AI Copilot & MCP Telemetry Interface",
            "services": "Model Context Protocol (MCP) Service Topology",
            "evaluation": "Empirical Research & Benchmark Evidence",
        }
        theme = active_theme or "dark"
        page = active_page or "dashboard"
        title = page_titles.get(page, "RetailOps Platform")

        if page == "inventory":
            content = render_inventory_view(theme=theme)
        elif page == "decisions":
            content = render_decisions_view(theme=theme)
        elif page == "copilot":
            content = render_copilot_view(theme=theme)
        elif page == "services":
            content = render_services_view(theme=theme)
        elif page == "evaluation":
            content = render_evaluation_view(theme=theme)
        else:
            content = render_dashboard_view(theme=theme)

        return content, title

    # Evaluation tab switching callback
    @app.callback(
        Output("eval-tab-content-container", "children"),
        Input({"type": "eval-tab-btn", "tab": ALL}, "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def handle_eval_tab_switch(n_clicks, theme):
        ctx = callback_context
        if not ctx.triggered:
            return None
        import json

        prop_id = ctx.triggered[0]["prop_id"]
        trigger_data = json.loads(prop_id.split(".")[0])
        tab_id = trigger_data.get("tab", "forecasting")
        view = render_evaluation_view(theme=theme, active_tab=tab_id)
        # Extract the tab content container children
        return view.children[1].children

    # Decision Center interactive actions (Approve & Override)
    @app.callback(
        Output("decision-action-feedback", "children"),
        Output("decisions-table-body", "children"),
        Input("approve-decision-btn", "n_clicks"),
        Input("commit-override-btn", "n_clicks"),
        State("decision-select-dropdown", "value"),
        State("override-qty-input", "value"),
        State("override-notes-input", "value"),
        prevent_initial_call=True,
    )
    def handle_decision_action(approve_clicks, override_clicks, decision_id, override_qty, override_notes):
        ctx = callback_context
        if not ctx.triggered or not decision_id:
            return None, None

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        feedback = None

        if button_id == "approve-decision-btn":
            dec = dec_service.approve_decision(decision_id)
            if dec:
                feedback = html.Div(
                    f"✓ Decision {decision_id} successfully approved ({dec.final_qty} units committed to supplier).",
                    className="alert alert-success",
                )
        elif button_id == "commit-override-btn":
            qty = int(override_qty) if override_qty is not None else 0
            dec = dec_service.override_decision(decision_id, qty, override_notes)
            if dec:
                feedback = html.Div(
                    f"⚠ Decision {decision_id} overridden by supervisor to {qty} units. Order commitment updated.",
                    className="alert alert-info",
                )

        # Refresh table rows
        updated_decisions = dec_service.get_all_decisions()
        new_rows = [
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
            for d in updated_decisions
        ]

        return feedback, new_rows

    # AI Copilot interactions (Send, Suggestion chips, Clear)
    @app.callback(
        Output("copilot-chat-history", "children"),
        Output("copilot-input", "value"),
        Output("copilot-stream-interval", "disabled"),
        Input("copilot-send-btn", "n_clicks"),
        Input("copilot-input", "n_submit"),
        Input({"type": "suggestion-chip", "query": ALL}, "n_clicks"),
        Input("copilot-clear-btn", "n_clicks"),
        State("copilot-input", "value"),
        prevent_initial_call=True,
    )
    def handle_copilot_interaction(send_clicks, n_submit, chip_clicks, clear_clicks, input_val):
        from dashboard.layout import render_chat_messages, chat_service

        ctx = callback_context
        if not ctx.triggered:
            return render_chat_messages(chat_service.get_history()), "", True

        trigger_id = ctx.triggered[0]["prop_id"]

        if "copilot-clear-btn" in trigger_id:
            chat_service.clear_history()
            return render_chat_messages(chat_service.get_history()), "", True

        query_to_send = None
        if "suggestion-chip" in trigger_id:
            import json

            prop_json = json.loads(trigger_id.split(".")[0])
            query_to_send = prop_json.get("query")
        elif "copilot-send-btn" in trigger_id or "copilot-input" in trigger_id:
            if input_val and input_val.strip():
                query_to_send = input_val.strip()

        if query_to_send:
            chat_service.start_streaming_query(query_to_send)
            # Immediately display user message and streaming placeholder with 0ms lag
            return render_chat_messages(chat_service.get_history()), "", False

        return render_chat_messages(chat_service.get_history()), "", True

    # Live progressive streaming interval callback
    @app.callback(
        Output("copilot-chat-history", "children", allow_duplicate=True),
        Output("copilot-stream-interval", "disabled", allow_duplicate=True),
        Input("copilot-stream-interval", "n_intervals"),
        prevent_initial_call=True,
    )
    def update_copilot_stream(n_intervals):
        from dashboard.layout import render_chat_messages, chat_service

        history = chat_service.get_history()
        is_streaming = chat_service.is_streaming()
        return render_chat_messages(history), not is_streaming
