"""
Extended Tightly Coupled Baseline for RetailOps (Task 08).
Extends TightlyCoupledRetailOps to incorporate the 5th service (Supplier Intelligence)
into an extended 5-stage workflow:
Catalog Enrichment -> Forecasting -> Replenishment -> Supplier Intelligence -> Pricing Strategy.
"""
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from baseline.tightly_coupled import TightlyCoupledRetailOps
from baseline.supplier_intelligence import direct_get_supplier_intelligence
from client.telemetry import (
    ServiceCallTelemetry,
    ExecutionTelemetry,
    TelemetryLogger,
    now_iso
)
from datetime import datetime
import uuid


class ExtendedTightlyCoupledRetailOps(TightlyCoupledRetailOps):
    """
    Extended in-process baseline workflow incorporating direct Supplier Intelligence.
    Demonstrates the changes required to integrate a 5th capability in the tightly coupled paradigm.
    """

    def direct_get_supplier_intelligence(self, category: str, reorder_qty: Optional[int] = 100) -> Dict[str, Any]:
        """Direct method for supplier intelligence."""
        return direct_get_supplier_intelligence(category, reorder_qty)

    def run_extended_workflow(self, product_name: str, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Executes the extended 5-stage pipeline:
        1. Catalog Enrichment
        2. Forecasting
        3. Replenishment
        4. Supplier Intelligence
        5. Pricing Strategy
        """
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        workflow_name = "extended_tightly_coupled_baseline"
        start_time_iso = now_iso()
        t_start_perf = time.perf_counter()

        completed_steps = []
        failed_steps = []
        service_calls = []
        errors = []
        workflow_status = "running"

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
            workflow_status = "failed_enrichment"
            category = "general"
            enrichment_result = {"category": "general", "brand": "Unknown", "description": "", "narrative": ""}

        # Step 2: Forecasting
        forecast_result = {}
        if workflow_status != "failed_enrichment":
            t2_iso = now_iso()
            t2_start = time.perf_counter()
            try:
                forecast_result = self.direct_get_forecast(category, days_ahead)
                t2_dur = (time.perf_counter() - t2_start) * 1000
                service_calls.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="direct_get_forecast",
                    start_time=t2_iso,
                    end_time=now_iso(),
                    duration_ms=round(t2_dur, 2),
                    status="success"
                ).to_dict())
                completed_steps.append("forecast")
            except Exception as e:
                t2_dur = (time.perf_counter() - t2_start) * 1000
                err_msg = str(e)
                service_calls.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="direct_get_forecast",
                    start_time=t2_iso,
                    end_time=now_iso(),
                    duration_ms=round(t2_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
                failed_steps.append("forecast")
                errors.append(f"Forecasting: {err_msg}")
                workflow_status = "failed_forecast"

        # Step 3: Replenishment
        replenishment_result = {}
        if workflow_status not in ("failed_enrichment", "failed_forecast"):
            t3_iso = now_iso()
            t3_start = time.perf_counter()
            try:
                replenishment_result = self.direct_get_replenishment(forecast_data=forecast_result)
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

        # Step 4: Supplier Intelligence
        supplier_result = {}
        if workflow_status not in ("failed_enrichment", "failed_forecast", "failed_replenishment"):
            t_sup_iso = now_iso()
            t_sup_start = time.perf_counter()
            try:
                reorder_qty = replenishment_result.get("reorder_qty", 100)
                supplier_result = self.direct_get_supplier_intelligence(
                    category=category,
                    reorder_qty=reorder_qty
                )
                t_sup_dur = (time.perf_counter() - t_sup_start) * 1000
                service_calls.append(ServiceCallTelemetry(
                    service_name="Supplier Intelligence",
                    tool_name="direct_get_supplier_intelligence",
                    start_time=t_sup_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_sup_dur, 2),
                    status="success"
                ).to_dict())
                completed_steps.append("supplier")
            except Exception as e:
                t_sup_dur = (time.perf_counter() - t_sup_start) * 1000
                err_msg = str(e)
                service_calls.append(ServiceCallTelemetry(
                    service_name="Supplier Intelligence",
                    tool_name="direct_get_supplier_intelligence",
                    start_time=t_sup_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_sup_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
                failed_steps.append("supplier")
                errors.append(f"Supplier Intelligence: {err_msg}")
                workflow_status = "failed_supplier"

        # Step 5: Pricing Strategy
        pricing_result = {}
        if workflow_status not in ("failed_enrichment", "failed_forecast", "failed_replenishment", "failed_supplier"):
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
            "architecture": "extended_tightly_coupled",
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
            "supplier_intelligence": {
                "supplier_id": supplier_result.get("supplier_id"),
                "supplier_name": supplier_result.get("supplier_name"),
                "category": supplier_result.get("category"),
                "reliability_score": supplier_result.get("reliability_score"),
                "lead_time_days": supplier_result.get("lead_time_days"),
                "risk_category": supplier_result.get("risk_category"),
                "on_time_delivery_rate": supplier_result.get("on_time_delivery_rate"),
                "quality_rating": supplier_result.get("quality_rating"),
                "cost_index": supplier_result.get("cost_index"),
                "recommended_supplier": supplier_result.get("recommended_supplier"),
                "narrative": supplier_result.get("narrative")
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
            "supplier_intelligence": result["supplier_intelligence"],
            "pricing": result["pricing"]
        }
        result["partial_result"] = partial_result

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
            architecture="extended_tightly_coupled"
        )
        self.telemetry_logger.log_execution(telemetry)

        return result
