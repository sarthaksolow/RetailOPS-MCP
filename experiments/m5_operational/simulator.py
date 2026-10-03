"""
Discrete-Event Inventory Simulation Engine for M5 Operational Evaluation.
Simulates daily inventory transitions over a fixed evaluation horizon (H=28 days).

Daily Sequence of Events (Inventory Measurement Timing):
1. MORNING (Receipts Arrival):
   Orders placed at day (t - L) arrive and are added to on_hand inventory:
   on_hand = on_hand + arrivals
2. MID-DAY (Customer Demand & Fulfillment):
   Realized customer demand d_t arrives.
   Fulfilled = min(d_t, on_hand)
   Lost Sales = max(0, d_t - on_hand)
   on_hand = on_hand - Fulfilled
3. AFTERNOON (Holding Cost & Stockout Assessment):
   Daily ending inventory recorded. Holding cost accrued on ending on-hand stock.
   Stockout event flagged if lost sales > 0.
4. EVENING (Decision Provider Review & Replenishment):
   Decision provider evaluates state context.
   If order_quantity > 0:
     Enforce MOQ and capacity constraints (log violation if broken).
     Pipeline order queued to arrive at day (t + L).
     Procurement / reorder cost accrued.
"""
import copy
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import numpy as np

from experiments.m5_operational.scenarios import ScenarioParameters, get_scenario
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision
)


@dataclass
class DailySimulationLog:
    """Record of operational state and events on a single simulation day t."""
    day: int
    date: str
    starting_inventory: int
    arrivals: int
    available_inventory: int
    realized_demand: int
    fulfilled_demand: int
    lost_sales: int
    ending_inventory: int
    stockout_occurred: bool
    order_placed: int
    lead_time: int
    in_transit_inventory: int
    holding_cost: float
    reorder_cost: float
    constraint_violation: bool
    decision_rationale: str


@dataclass
class SimulationResults:
    """Consolidated operational metrics and logs for a simulation run."""
    series_id: str
    scenario_id: str
    provider_id: str
    horizon_days: int
    
    # Primary Operational Metrics
    stockout_rate_pct: float
    service_level_pct: float
    total_holding_cost: float
    total_replenishment_cost: float
    total_cost: float
    constraint_violations_count: int
    
    # Quantity Totals
    total_demand: int
    total_fulfilled: int
    total_lost_sales: int
    total_ordered: int
    
    # Detailed Trace
    daily_trace: List[DailySimulationLog]


class InventorySimulator:
    """
    Standardized, isolated discrete-event inventory simulator.
    Evaluates any BaseDecisionProvider under identical scenario and demand conditions.
    """
    
    def __init__(self, scenario: ScenarioParameters):
        self.scenario = scenario

    def run_simulation(
        self,
        series_data: Dict[str, Any],
        provider: BaseDecisionProvider
    ) -> SimulationResults:
        """
        Executes a 28-day rolling inventory simulation for the given series and provider.
        """
        meta = series_data["metadata"]
        train_records = series_data["train_records"]
        eval_records = series_data["eval_records"]
        horizon = len(eval_records)  # Expected 28
        
        # 1. Compute historical daily demand from train split (prevent future leakage)
        train_sales = [r["sales"] for r in train_records]
        mean_daily_d = float(np.mean(train_sales[-90:])) if len(train_sales) >= 90 else float(np.mean(train_sales))
        
        # 2. Initialize inventory according to scenario parameters
        base_L = self.scenario.supplier_lead_time_days
        k_init = self.scenario.initial_inventory_factor
        init_on_hand = int(round(k_init * mean_daily_d * base_L))
        init_on_hand = max(0, init_on_hand)
        
        on_hand = init_on_hand
        
        # Pipeline orders queue: list of dicts: {"arrival_day": int, "quantity": int}
        pending_orders: List[Dict[str, int]] = []
        
        daily_logs: List[DailySimulationLog] = []
        
        unit_cost = meta["unit_procurement_cost"] * self.scenario.supplier_cost_index
        unit_sell_price = meta["unit_sell_price"]
        holding_rate = self.scenario.holding_cost_rate_daily
        
        total_demand = 0
        total_fulfilled = 0
        total_lost_sales = 0
        total_ordered = 0
        total_holding_cost = 0.0
        total_reorder_cost = 0.0
        constraint_violations = 0
        stockout_days = 0
        
        for t_idx, eval_day in enumerate(eval_records):
            day_num = t_idx + 1  # 1 to 28
            date_str = eval_day["date"]
            weekday_str = eval_day["weekday"]
            event_str = eval_day.get("event_name")
            
            # --- STEP 1: MORNING ARRIVALS ---
            day_start_inv = on_hand
            arrivals = 0
            remaining_orders = []
            for order in pending_orders:
                if order["arrival_day"] <= day_num:
                    arrivals += order["quantity"]
                else:
                    remaining_orders.append(order)
            pending_orders = remaining_orders
            
            avail_inv = on_hand + arrivals
            on_hand = avail_inv
            
            # --- STEP 2: CUSTOMER DEMAND & FULFILLMENT ---
            raw_demand = eval_day["sales"]
            sim_demand = int(round(raw_demand * self.scenario.demand_multiplier))
            sim_demand = max(0, sim_demand)
            
            fulfilled = min(on_hand, sim_demand)
            lost_sales = sim_demand - fulfilled
            on_hand -= fulfilled
            
            total_demand += sim_demand
            total_fulfilled += fulfilled
            total_lost_sales += lost_sales
            
            # --- STEP 3: ENDING INVENTORY & HOLDING COST ---
            ending_inv = on_hand
            day_holding_cost = round(ending_inv * unit_cost * holding_rate, 4)
            total_holding_cost += day_holding_cost
            
            is_stockout = (lost_sales > 0) or (ending_inv == 0 and sim_demand > 0)
            if is_stockout:
                stockout_days += 1
                
            # --- STEP 4: REPLENISHMENT DECISION ---
            in_transit_sum = sum(o["quantity"] for o in pending_orders)
            
            context = OperationalDecisionContext(
                series_id=meta["series_id"],
                item_id=meta["item_id"],
                store_id=meta["store_id"],
                category=meta["cat_id"],
                current_day=day_num,
                date=date_str,
                weekday=weekday_str,
                event_name=event_str,
                on_hand_inventory=ending_inv,
                in_transit_inventory=in_transit_sum,
                pipeline_orders_count=len(pending_orders),
                mean_historical_daily_demand=round(mean_daily_d, 2),
                supplier_lead_time_days=base_L,
                supplier_reliability=self.scenario.supplier_reliability,
                minimum_order_quantity=self.scenario.minimum_order_quantity,
                maximum_order_quantity=self.scenario.maximum_order_quantity,
                unit_cost=unit_cost,
                unit_sell_price=unit_sell_price,
                scenario_id=self.scenario.scenario_id
            )
            
            decision: ReplenishmentDecision = provider.decide(context)
            order_qty = int(decision.order_quantity)
            
            # Constraint verification
            violation = False
            if order_qty > 0:
                if order_qty < self.scenario.minimum_order_quantity:
                    violation = True
                    constraint_violations += 1
                elif order_qty > self.scenario.maximum_order_quantity:
                    violation = True
                    constraint_violations += 1
            
            day_reorder_cost = 0.0
            if order_qty > 0:
                day_reorder_cost = round((order_qty * unit_cost) + self.scenario.fixed_order_cost, 4)
                total_reorder_cost += day_reorder_cost
                total_ordered += order_qty
                
                # Queue order arrival
                arrival_day = day_num + base_L
                pending_orders.append({
                    "arrival_day": arrival_day,
                    "quantity": order_qty
                })
                
            updated_in_transit = sum(o["quantity"] for o in pending_orders)
            
            log_entry = DailySimulationLog(
                day=day_num,
                date=date_str,
                starting_inventory=day_start_inv,
                arrivals=arrivals,
                available_inventory=avail_inv,
                realized_demand=sim_demand,
                fulfilled_demand=fulfilled,
                lost_sales=lost_sales,
                ending_inventory=ending_inv,
                stockout_occurred=is_stockout,
                order_placed=order_qty,
                lead_time=base_L,
                in_transit_inventory=updated_in_transit,
                holding_cost=day_holding_cost,
                reorder_cost=day_reorder_cost,
                constraint_violation=violation,
                decision_rationale=decision.rationale
            )
            daily_logs.append(log_entry)
            
        # Metric Calculations (Strictly per PROTOCOL-EXP-FROZEN-V1)
        stockout_rate = round((stockout_days / horizon) * 100, 2)
        service_level = round((total_fulfilled / total_demand * 100), 2) if total_demand > 0 else 100.0
        
        return SimulationResults(
            series_id=meta["series_id"],
            scenario_id=self.scenario.scenario_id,
            provider_id=provider.provider_id,
            horizon_days=horizon,
            stockout_rate_pct=stockout_rate,
            service_level_pct=service_level,
            total_holding_cost=round(total_holding_cost, 2),
            total_replenishment_cost=round(total_reorder_cost, 2),
            total_cost=round(total_holding_cost + total_reorder_cost, 2),
            constraint_violations_count=constraint_violations,
            total_demand=total_demand,
            total_fulfilled=total_fulfilled,
            total_lost_sales=total_lost_sales,
            total_ordered=total_ordered,
            daily_trace=daily_logs
        )
