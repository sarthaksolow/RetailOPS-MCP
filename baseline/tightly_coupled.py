"""
Tightly Coupled Baseline for RetailOps.
Performs the same 4-stage workflow (Catalog Enrichment -> Forecasting -> Replenishment -> Pricing)
via direct in-process Python function calls without MCP protocol or subprocess isolation.
"""
import os
import sys
import json
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Ensure root is in path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from client.telemetry import (
    ServiceCallTelemetry,
    ExecutionTelemetry,
    TelemetryLogger,
    now_iso
)

load_dotenv()


class TightlyCoupledRetailOps:
    """
    Direct in-process retail operations workflow.
    Reuses the same underlying data files and deterministic domain algorithms
    as the 4 MCP servers, but executes directly in-memory.
    """

    def __init__(
        self,
        telemetry_logger: Optional[TelemetryLogger] = None,
        forecasting_service: Optional[Callable[..., Dict[str, Any]]] = None
    ):
        self.root_dir = ROOT_DIR
        self.telemetry_logger = telemetry_logger or TelemetryLogger()
        self.forecasting_service = forecasting_service

        # Load shared datasets directly
        self._load_datasets()

    def _load_datasets(self):
        """Load datasets identically to the MCP servers."""
        # 1. Catalog Enricher datasets
        enricher_data_dir = self.root_dir / "servers" / "catalog-enricher" / "data"
        self.product_catalog = {}
        self.category_mappings = {}
        try:
            p_cat = enricher_data_dir / "product_catalog.json"
            if p_cat.exists():
                with open(p_cat, "r", encoding="utf-8") as f:
                    self.product_catalog = json.load(f)
            c_map = enricher_data_dir / "category_mappings.json"
            if c_map.exists():
                with open(c_map, "r", encoding="utf-8") as f:
                    self.category_mappings = json.load(f)
        except Exception:
            pass

        # 2. Forecasting datasets
        forecasting_data_dir = self.root_dir / "servers" / "forecasting" / "data"
        sales_csv = forecasting_data_dir / "sales_history.csv"
        events_json = forecasting_data_dir / "events.json"
        surge_json = forecasting_data_dir / "surge_profile.json"

        self.sales_df = pd.read_csv(sales_csv) if sales_csv.exists() else pd.DataFrame()
        self.events = {"events": []}
        if events_json.exists():
            with open(events_json, "r", encoding="utf-8") as f:
                self.events = json.load(f)
        self.surge_profiles = {}
        if surge_json.exists():
            with open(surge_json, "r", encoding="utf-8") as f:
                self.surge_profiles = json.load(f)

        # 3. Pricing datasets
        pricing_data_dir = self.root_dir / "servers" / "pricing-strategy" / "data"
        elasticity_json = pricing_data_dir / "price_elasticity.json"
        competitor_json = pricing_data_dir / "competitor_prices.json"

        self.elasticity_data = {}
        if elasticity_json.exists():
            with open(elasticity_json, "r", encoding="utf-8") as f:
                self.elasticity_data = json.load(f)
        self.competitor_data = {}
        if competitor_json.exists():
            with open(competitor_json, "r", encoding="utf-8") as f:
                self.competitor_data = json.load(f)

    # -----------------------------------------------------------------
    # Stage 1: Catalog Enrichment (Direct function)
    # -----------------------------------------------------------------
    def direct_enrich_product(self, product_name: str, product_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Direct catalog enrichment logic without MCP/LangGraph subprocess.
        Applies cleaning, categorization rules, attribute extraction, and alternatives.
        """
        product_data = product_data or {}
        name = product_name.strip()
        name_clean = " ".join(name.split())
        for prefix in ["New", "Best", "Premium", "Super"]:
            if name_clean.startswith(prefix + " "):
                name_clean = name_clean[len(prefix) + 1:]

        # Categorization logic
        category = product_data.get("category")
        if not category:
            name_lower = name_clean.lower()
            if any(word in name_lower for word in ["tv", "television", "screen"]):
                category = "electronics"
            elif any(word in name_lower for word in ["laptop", "computer", "notebook"]):
                category = "electronics"
            elif any(word in name_lower for word in ["phone", "smartphone", "mobile"]):
                category = "electronics"
            elif any(word in name_lower for word in ["detergent", "soap", "shampoo", "pack"]):
                category = "groceries"
            elif any(word in name_lower for word in ["shirt", "pants", "dress", "fashion"]):
                category = "fashion"
            elif any(word in name_lower for word in ["kitchen", "blender", "oven", "cooker"]):
                category = "kitchen_appliances"
            else:
                category = "general"

        # Brand extraction
        brand = product_data.get("brand")
        if not brand:
            words = name_clean.split()
            brand = words[0].title() if words else "Unknown"

        description = product_data.get("description", f"Product: {name_clean}")

        # Find alternatives
        alternatives = []
        if self.product_catalog:
            for pid, prod in self.product_catalog.items():
                if prod.get("category") == category and prod.get("name", "").lower() != name_clean.lower():
                    alternatives.append({
                        "name": prod.get("name", ""),
                        "brand": prod.get("brand", ""),
                        "category": prod.get("category", ""),
                        "price": prod.get("price", 0),
                        "margin": prod.get("margin_pct", 0)
                    })
                    if len(alternatives) >= 3:
                        break

        narrative = f"Enriched product: {name_clean}. Category: {category}, Brand: {brand}. Found {len(alternatives)} alternatives."

        return {
            "product_name": name_clean,
            "category": category,
            "brand": brand,
            "description": description,
            "attributes": product_data.get("attributes", {}),
            "missing_fields": [],
            "alternatives": alternatives,
            "narrative": narrative
        }

    # -----------------------------------------------------------------
    # Stage 2: Forecasting (Direct function)
    # -----------------------------------------------------------------
    def direct_get_forecast(self, category: str, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Direct forecasting calculations matching forecasting/server.py simple_moving_average
        and surge profiles.
        """
        if self.sales_df.empty:
            return {"error": "Sales data unavailable."}

        filtered = self.sales_df[self.sales_df["category"] == category]
        if filtered.empty:
            return {"error": f"No data found for category '{category}'."}

        # Simple moving average
        last_days = filtered.tail(days_ahead)
        base = round(last_days["sales"].mean(), 2)

        # Seasonal events
        today = datetime.now()
        event_name = None
        season_mult = 1.0
        for e in self.events.get("events", []):
            try:
                event_date = datetime.strptime(e["date"], "%Y-%m-%d")
                days_until = (event_date - today).days
                if 0 <= days_until <= 180:
                    event_name = e["name"]
                    season_mult = e["multiplier"]
                    break
            except Exception:
                continue

        # Historical surge factor
        hist_mult = 1.0
        if event_name and event_name in self.surge_profiles:
            hist_mult = self.surge_profiles[event_name].get(category, 1.0)

        final_forecast = round(base * season_mult * hist_mult, 2)
        narrative = f"Base forecast {base} adjusted by seasonal factor {season_mult}x and event surge {hist_mult}x for {event_name or 'None'}."

        return {
            "category": category,
            "base_forecast": base,
            "seasonal_multiplier": season_mult,
            "historical_surge_factor": hist_mult,
            "final_forecast": final_forecast,
            "event": event_name,
            "narrative": narrative
        }

    # -----------------------------------------------------------------
    # Stage 3: Replenishment (Direct function)
    # -----------------------------------------------------------------
    def direct_get_replenishment(self, forecast_data: Dict[str, Any], current_stock: Optional[int] = None, in_transit: Optional[int] = None) -> Dict[str, Any]:
        """
        Direct replenishment reasoning matching replenishment/server.py equations.
        """
        inventory_levels = {
            "tv": {"current": 45, "in_transit": 10},
            "laptop": {"current": 25, "in_transit": 5},
            "phone": {"current": 80, "in_transit": 20},
            "electronics": {"current": 150, "in_transit": 50},
            "fashion": {"current": 350, "in_transit": 50},
            "groceries": {"current": 800, "in_transit": 200},
        }

        category = forecast_data.get("category", "general")
        inv = inventory_levels.get(category, {"current": 200, "in_transit": 50})

        curr = current_stock if current_stock is not None else inv["current"]
        transit = in_transit if in_transit is not None else inv["in_transit"]
        effective_stock = curr + transit

        final_forecast = forecast_data.get("final_forecast", 0)
        avg_daily = final_forecast / 30 if final_forecast else 1.0

        lead_time_days = 10
        moq = 50
        volatility_multiplier = 1.25  # medium
        festival_multiplier = 1.0     # default

        event_name = forecast_data.get("event")
        if event_name:
            festival_multiplier = 1.2

        # Safety stock
        base_safety = avg_daily * lead_time_days
        safety_stock = round(base_safety * volatility_multiplier * festival_multiplier)

        # Reorder qty
        raw_qty = max(0, int(final_forecast + safety_stock - effective_stock))
        if raw_qty > 0:
            raw_qty = max(raw_qty, moq)

        runway_days = round(effective_stock / max(0.1, avg_daily), 1)

        if runway_days < lead_time_days:
            timing = "immediate"
            stockout_risk = "high"
        elif runway_days < 30:
            timing = "soon"
            stockout_risk = "medium"
        else:
            timing = "defer"
            stockout_risk = "low"

        narrative = f"Reorder {raw_qty} units ({timing}) with {stockout_risk} stockout risk based on runway of {runway_days} days."

        return {
            "reorder_qty": raw_qty,
            "reorder_timing": timing,
            "stockout_risk": stockout_risk,
            "narrative": narrative
        }

    # -----------------------------------------------------------------
    # Stage 4: Pricing Strategy (Direct function)
    # -----------------------------------------------------------------
    def direct_get_pricing(self, category: str, forecasted_demand: float, current_price: Optional[float] = None, inventory_level: Optional[int] = None) -> Dict[str, Any]:
        """
        Direct pricing logic matching pricing-strategy/server.py rules.
        """
        default_prices = {
            "electronics": 9000,
            "tv": 28000,
            "laptop": 48000,
            "phone": 16000,
            "kitchen_appliances": 5500,
            "fashion": 1500,
            "groceries": 220,
        }

        price = current_price if current_price is not None else default_prices.get(category, 5000)
        inv = inventory_level if inventory_level is not None else 100

        competitor_price = self.competitor_data.get(category, {}).get("competitor_avg_price", price)
        inv_ratio = inv / max(1.0, forecasted_demand)

        new_price = price
        rec_type = "maintain"

        if inv_ratio > 2:
            new_price = price * 0.92
            rec_type = "clearance"
        elif inv_ratio < 0.5:
            new_price = price * 1.05
            rec_type = "premium"
        elif price > competitor_price * 1.1:
            new_price = price * 0.95
            rec_type = "competitive"

        recommended = round(new_price, 2)
        change_pct = round(((new_price - price) / price) * 100, 2)

        narrative = f"{rec_type.capitalize()} pricing recommended: adjustment from Rs {price} to Rs {recommended} ({change_pct}%)."

        return {
            "category": category,
            "current_price": float(price),
            "recommended_price": recommended,
            "price_change_pct": change_pct,
            "recommendation_type": rec_type,
            "narrative": narrative
        }

    # -----------------------------------------------------------------
    # Full Workflow Execution (Direct In-Memory)
    # -----------------------------------------------------------------
    def run_full_workflow(self, product_name: str, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Run the full 4-stage retail operations pipeline sequentially in-process.
        Records execution-level and per-function telemetry with architecture='tightly_coupled'.
        """
        execution_id = f"exec-tc-{uuid.uuid4().hex[:10]}"
        workflow_name = "tightly_coupled_orchestrator"
        start_time_iso = now_iso()
        t_start_perf = time.perf_counter()

        service_calls = []
        completed_steps = []
        failed_steps = []
        errors = []

        # Step 1: Catalog Enrichment
        t1_iso = now_iso()
        t1_start = time.perf_counter()
        try:
            enrichment_result = self.direct_enrich_product(product_name)
            t1_dur = (time.perf_counter() - t1_start) * 1000
            service_calls.append(ServiceCallTelemetry(
                service_name="Catalog Enricher",
                tool_name="direct_enrich_product",
                start_time=t1_iso,
                end_time=now_iso(),
                duration_ms=round(t1_dur, 2),
                status="success"
            ).to_dict())
            completed_steps.append("enrich")
            category = enrichment_result.get("category", "general")
        except Exception as e:
            t1_dur = (time.perf_counter() - t1_start) * 1000
            err_msg = str(e)
            service_calls.append(ServiceCallTelemetry(
                service_name="Catalog Enricher",
                tool_name="direct_enrich_product",
                start_time=t1_iso,
                end_time=now_iso(),
                duration_ms=round(t1_dur, 2),
                status="failure",
                error=err_msg
            ).to_dict())
            failed_steps.append("enrich")
            errors.append(f"Enrichment: {err_msg}")
            enrichment_result = {}
            category = "general"

        # Step 2: Forecasting
        t2_iso = now_iso()
        t2_start = time.perf_counter()
        if self.forecasting_service is not None:
            forecast_result = self.forecasting_service(
                category=category,
                days_ahead=days_ahead,
                sales_df=self.sales_df,
                events=self.events,
                surge_profiles=self.surge_profiles
            )
            forecast_tool_name = getattr(self.forecasting_service, "__name__", "custom_forecasting_service")
        else:
            forecast_result = self.direct_get_forecast(category, days_ahead=days_ahead)
            forecast_tool_name = "direct_get_forecast"
        t2_dur = (time.perf_counter() - t2_start) * 1000
        if "error" in forecast_result:
            service_calls.append(ServiceCallTelemetry(
                service_name="Forecasting",
                tool_name=forecast_tool_name,
                start_time=t2_iso,
                end_time=now_iso(),
                duration_ms=round(t2_dur, 2),
                status="failure",
                error=forecast_result["error"]
            ).to_dict())
            failed_steps.append("forecast")
            errors.append(f"Forecasting: {forecast_result['error']}")
            workflow_status = "failed_forecast"
        else:
            service_calls.append(ServiceCallTelemetry(
                service_name="Forecasting",
                tool_name=forecast_tool_name,
                start_time=t2_iso,
                end_time=now_iso(),
                duration_ms=round(t2_dur, 2),
                status="success"
            ).to_dict())
            completed_steps.append("forecast")
            workflow_status = "running"

        # Step 3: Replenishment (only if forecast succeeded)
        replenishment_result = {}
        if workflow_status != "failed_forecast":
            t3_iso = now_iso()
            t3_start = time.perf_counter()
            try:
                replenishment_result = self.direct_get_replenishment(forecast_result)
                t3_dur = (time.perf_counter() - t3_start) * 1000
                service_calls.append(ServiceCallTelemetry(
                    service_name="Replenishment",
                    tool_name="direct_get_replenishment",
                    start_time=t3_iso,
                    end_time=now_iso(),
                    duration_ms=round(t3_dur, 2),
                    status="success"
                ).to_dict())
                completed_steps.append("replenish")
            except Exception as e:
                t3_dur = (time.perf_counter() - t3_start) * 1000
                err_msg = str(e)
                service_calls.append(ServiceCallTelemetry(
                    service_name="Replenishment",
                    tool_name="direct_get_replenishment",
                    start_time=t3_iso,
                    end_time=now_iso(),
                    duration_ms=round(t3_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
                failed_steps.append("replenish")
                errors.append(f"Replenishment: {err_msg}")
                workflow_status = "failed_replenishment"

        # Step 4: Pricing Strategy (only if prior steps succeeded)
        pricing_result = {}
        if workflow_status not in ("failed_forecast", "failed_replenishment"):
            t4_iso = now_iso()
            t4_start = time.perf_counter()
            try:
                pricing_result = self.direct_get_pricing(
                    category=category,
                    forecasted_demand=forecast_result.get("final_forecast", 0)
                )
                t4_dur = (time.perf_counter() - t4_start) * 1000
                service_calls.append(ServiceCallTelemetry(
                    service_name="Pricing Strategy",
                    tool_name="direct_get_pricing",
                    start_time=t4_iso,
                    end_time=now_iso(),
                    duration_ms=round(t4_dur, 2),
                    status="success"
                ).to_dict())
                completed_steps.append("price")
                workflow_status = "completed"
            except Exception as e:
                t4_dur = (time.perf_counter() - t4_start) * 1000
                err_msg = str(e)
                service_calls.append(ServiceCallTelemetry(
                    service_name="Pricing Strategy",
                    tool_name="direct_get_pricing",
                    start_time=t4_iso,
                    end_time=now_iso(),
                    duration_ms=round(t4_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
                failed_steps.append("price")
                errors.append(f"Pricing: {err_msg}")
                workflow_status = "failed_pricing"

        t_end_perf = time.perf_counter()
        end_time_iso = now_iso()
        total_duration_ms = round((t_end_perf - t_start_perf) * 1000, 2)

        result = {
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "architecture": "tightly_coupled",
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "total_duration_ms": total_duration_ms,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "service_calls": service_calls,
            "product_name": product_name,
            "category": category if workflow_status == "completed" else enrichment_result.get("category"),
            "timestamp": datetime.now().isoformat(),
            "status": workflow_status,
            "enrichment": {
                "category": enrichment_result.get("category"),
                "brand": enrichment_result.get("brand"),
                "description": enrichment_result.get("description"),
                "narrative": enrichment_result.get("narrative")
            },
            "forecast": {
                "final": forecast_result.get("final_forecast"),
                "event": forecast_result.get("event"),
                "narrative": forecast_result.get("narrative")
            },
            "replenishment": {
                "reorder_qty": replenishment_result.get("reorder_qty"),
                "timing": replenishment_result.get("reorder_timing"),
                "narrative": replenishment_result.get("narrative")
            },
            "pricing": {
                "recommended_price": pricing_result.get("recommended_price"),
                "change_pct": pricing_result.get("price_change_pct"),
                "narrative": pricing_result.get("narrative")
            },
            "errors": errors
        }

        partial_result = {
            "category": result["category"],
            "enrichment": result["enrichment"],
            "forecast": result["forecast"],
            "replenishment": result["replenishment"],
            "pricing": result["pricing"]
        }
        result["partial_result"] = partial_result

        # Log baseline telemetry
        telemetry = ExecutionTelemetry(
            execution_id=execution_id,
            workflow_name=workflow_name,
            product_name=product_name,
            category=result["category"],
            start_time=start_time_iso,
            end_time=end_time_iso,
            total_duration_ms=total_duration_ms,
            workflow_status=workflow_status,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            service_calls=service_calls,
            partial_result=partial_result,
            errors=errors,
            architecture="tightly_coupled"
        )
        self.telemetry_logger.log_execution(telemetry)

        return result
