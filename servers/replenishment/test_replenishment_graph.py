import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import replenishment_graph

with open("mock_replenishment_inputs.json") as f:
    mock_inputs = json.load(f)

def run_test(index: int):
    test_case = mock_inputs[index]

    print("\n==============================")
    print(f"Scenario: {test_case['scenario']}")
    print("==============================")

    result = replenishment_graph.invoke({
        "input": test_case
    })

    print("Reorder Qty:", result["reorder_qty"])
    print("Timing:", result["reorder_timing"])
    print("Risk:", result["stockout_risk"])
    print("Narrative:", result["narrative"])


if __name__ == "__main__":
    # Test 1: Festival too close
    run_test(0)

    # Test 2: Slow sales, overstocked
    run_test(1)
