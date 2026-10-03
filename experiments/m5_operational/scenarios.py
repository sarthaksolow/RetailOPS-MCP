"""
Scenario Configuration Module for M5 Operational Simulation.
Encapsulates the five frozen scenarios specified in PROTOCOL-EXP-FROZEN-V1:

- SCEN-01: Normal Demand
- SCEN-02: Demand Spike
- SCEN-03: Low Inventory
- SCEN-04: Supplier Delay
- SCEN-05: Compound Stockout Risk

All scenarios use fixed random seed 42 and deterministic disturbance parameters.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

RANDOM_SEED = 42


@dataclass
class ScenarioParameters:
    """Explicit parameters governing an operational evaluation scenario."""
    scenario_id: str
    scenario_name: str
    description: str
    
    # Inventory initialization factor: I_0 = round(k_init * mean_daily_sales * base_lead_time)
    initial_inventory_factor: float = 1.0
    
    # Demand multiplier applied to realized historical demand during simulation
    demand_multiplier: float = 1.0
    
    # Supplier parameters
    supplier_lead_time_days: int = 7
    supplier_reliability: float = 0.95
    minimum_order_quantity: int = 20
    maximum_order_quantity: int = 500
    
    # Order frequency constraint: minimum days between order placements
    reorder_cycle_days: int = 1
    
    # Holding & procurement cost factors
    holding_cost_rate_daily: float = 0.001  # 0.1% per day
    supplier_cost_index: float = 1.0
    fixed_order_cost: float = 0.0
    
    # Additional scenario attributes
    random_seed: int = RANDOM_SEED


# Five frozen scenario configurations
SCENARIOS: Dict[str, ScenarioParameters] = {
    "SCEN-01": ScenarioParameters(
        scenario_id="SCEN-01",
        scenario_name="Normal Demand",
        description="Baseline steady-state operations; historical realized sales unmodified; standard 7-day supplier lead time; initial inventory covers lead time.",
        initial_inventory_factor=1.0,
        demand_multiplier=1.0,
        supplier_lead_time_days=7,
        supplier_reliability=0.95,
        minimum_order_quantity=20,
        maximum_order_quantity=500
    ),
    "SCEN-02": ScenarioParameters(
        scenario_id="SCEN-02",
        scenario_name="Demand Spike",
        description="Surge condition; realized customer demand elevated by 2.5x across the evaluation horizon; tests replenishment responsiveness.",
        initial_inventory_factor=1.0,
        demand_multiplier=2.5,
        supplier_lead_time_days=7,
        supplier_reliability=0.95,
        minimum_order_quantity=20,
        maximum_order_quantity=500
    ),
    "SCEN-03": ScenarioParameters(
        scenario_id="SCEN-03",
        scenario_name="Low Inventory",
        description="Initial stock depleted below safety threshold (initial_inventory_factor=0.2, covering < 2 days); tests emergency recovery under standard demand.",
        initial_inventory_factor=0.2,
        demand_multiplier=1.0,
        supplier_lead_time_days=7,
        supplier_reliability=0.95,
        minimum_order_quantity=20,
        maximum_order_quantity=500
    ),
    "SCEN-04": ScenarioParameters(
        scenario_id="SCEN-04",
        scenario_name="Supplier Delay",
        description="Logistics disruption triples supplier lead time from 7 to 21 days; supplier reliability downgraded to 0.65; tests pipeline buffering.",
        initial_inventory_factor=1.0,
        demand_multiplier=1.0,
        supplier_lead_time_days=21,
        supplier_reliability=0.65,
        minimum_order_quantity=20,
        maximum_order_quantity=500
    ),
    "SCEN-05": ScenarioParameters(
        scenario_id="SCEN-05",
        scenario_name="Compound Stockout Risk",
        description="Compound stress combining 2.5x demand spike with severely depleted initial stock (0.2x) and doubled lead time (14 days); critical stress test.",
        initial_inventory_factor=0.2,
        demand_multiplier=2.5,
        supplier_lead_time_days=14,
        supplier_reliability=0.70,
        minimum_order_quantity=20,
        maximum_order_quantity=500
    )
}


def get_scenario(scenario_id: str) -> ScenarioParameters:
    """Retrieve scenario configuration by identifier."""
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario ID: {scenario_id}. Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[scenario_id]
