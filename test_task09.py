"""
Test Suite for Task 09: Flowr-Based Architectural Comparison and Evaluation Framework.

Validates:
1. Comparison matrix file exists.
2. Comparison matrix is valid JSON.
3. All required 17 comparison dimensions are present.
4. Every Flowr-specific claim includes a verifiable source reference.
5. Evidence types strictly use allowed vocabulary ('literature', 'implementation', 'experiment').
6. Evaluation framework files exist (README.md, metrics_schema.json, evaluation_protocol.md, experiment_matrix.json).
7. Metrics schema is valid JSON Schema Draft 2020-12.
8. Experiment matrix contains all required core research questions.
9. Existing Task 08 artifacts remain intact and valid.
10. No unsupported automatic superiority or ranking claims are generated.
11. No fabricated Flowr performance values are present.
12. Research report contains explicit limitations, evidence classification, and cautious conclusion.
"""
import os
import sys
import json
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FLOWR_DIR = ROOT_DIR / "experiments" / "flowr_comparison"
EVAL_DIR = ROOT_DIR / "experiments" / "evaluation_framework"


class TestTask09FlowrComparison(unittest.TestCase):

    REQUIRED_DIMENSIONS = {
        "Problem scope",
        "Retail workflow coverage",
        "Agent responsibilities",
        "Orchestration strategy",
        "MCP usage",
        "Service/tool interoperability",
        "Modularity",
        "Extensibility",
        "Service replacement",
        "Governance mechanisms",
        "Auditability",
        "Fault handling",
        "Recovery behavior",
        "Human interaction",
        "Evaluation methodology",
        "Public reproducibility",
        "Reported limitations"
    }

    ALLOWED_EVIDENCE_TYPES = {"literature", "implementation", "experiment"}

    # Test 1: Comparison matrix exists
    def test_01_comparison_matrix_files_exist(self):
        json_file = FLOWR_DIR / "flowr_comparison_matrix.json"
        md_file = FLOWR_DIR / "flowr_comparison_matrix.md"
        self.assertTrue(json_file.exists(), f"Missing {json_file}")
        self.assertTrue(md_file.exists(), f"Missing {md_file}")

    # Test 2: Comparison matrix is valid JSON
    def test_02_comparison_matrix_is_valid_json(self):
        json_file = FLOWR_DIR / "flowr_comparison_matrix.json"
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("comparison_scope", data)
        self.assertIn("dimensions", data)
        self.assertIn("overall_limitations", data)

    # Test 3: Required comparison dimensions are present (all 17)
    def test_03_required_dimensions_present(self):
        json_file = FLOWR_DIR / "flowr_comparison_matrix.json"
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        dim_names = {d["dimension"] for d in data.get("dimensions", [])}
        for req in self.REQUIRED_DIMENSIONS:
            self.assertIn(req, dim_names, f"Missing required dimension: '{req}'")

    # Test 4: Every Flowr-specific claim includes a source reference
    def test_04_flowr_claims_include_source(self):
        json_file = FLOWR_DIR / "flowr_comparison_matrix.json"
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for d in data["dimensions"]:
            flowr_entry = d.get("flowr", {})
            self.assertIn("source", flowr_entry, f"Dimension '{d['dimension']}' missing Flowr source citation")
            self.assertTrue(len(flowr_entry["source"]) > 5, f"Empty source citation in '{d['dimension']}'")
            self.assertIn("Bandara", flowr_entry["source"])

    # Test 5: Evidence types use an allowed vocabulary
    def test_05_evidence_types_allowed_vocabulary(self):
        json_file = FLOWR_DIR / "flowr_comparison_matrix.json"
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for d in data["dimensions"]:
            ro_ev = d.get("retailops", {}).get("evidence_type")
            fl_ev = d.get("flowr", {}).get("evidence_type")
            self.assertIn(ro_ev, self.ALLOWED_EVIDENCE_TYPES, f"Invalid RetailOps evidence type: {ro_ev}")
            self.assertIn(fl_ev, self.ALLOWED_EVIDENCE_TYPES, f"Invalid Flowr evidence type: {fl_ev}")

    # Test 6: Evaluation framework files exist
    def test_06_evaluation_framework_files_exist(self):
        required_files = [
            EVAL_DIR / "README.md",
            EVAL_DIR / "metrics_schema.json",
            EVAL_DIR / "evaluation_protocol.md",
            EVAL_DIR / "experiment_matrix.json"
        ]
        for rf in required_files:
            self.assertTrue(rf.exists(), f"Missing required evaluation framework file: {rf}")

    # Test 7: Metrics schema is valid
    def test_07_metrics_schema_is_valid(self):
        schema_file = EVAL_DIR / "metrics_schema.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
        self.assertIn("properties", schema)
        required_sections = [
            "metadata", "integration_effort", "extensibility",
            "service_replacement", "performance",
            "reliability_and_fault_handling", "model_or_service_quality"
        ]
        for sec in required_sections:
            self.assertIn(sec, schema["properties"], f"Missing section '{sec}' in metrics schema")

    # Test 8: Experiment matrix contains required research questions
    def test_08_experiment_matrix_contains_required_questions(self):
        mat_file = EVAL_DIR / "experiment_matrix.json"
        with open(mat_file, "r", encoding="utf-8") as f:
            mat = json.load(f)
        questions = [exp["research_question"] for exp in mat.get("experiments", [])]
        self.assertGreaterEqual(len(questions), 6)

        expected_substrings = [
            "Can a new service be added without changing existing service implementations?",
            "Can a service be replaced while preserving the interface",
            "runtime cost",
            "persistent",
            "service failure",
            "Flowr"
        ]
        for exp_sub in expected_substrings:
            matched = any(exp_sub.lower() in q.lower() for q in questions)
            self.assertTrue(matched, f"Expected research question substring not found: '{exp_sub}'")

    # Test 9: Existing Task 08 artifacts remain intact
    def test_09_task_08_artifacts_intact(self):
        ext_dir = ROOT_DIR / "experiments" / "extensibility"
        self.assertTrue((ext_dir / "summary.json").exists())
        self.assertTrue((ext_dir / "raw_results.jsonl").exists())
        self.assertTrue((ext_dir / "results.md").exists())
        self.assertTrue((ROOT_DIR / "test_extensibility.py").exists())
        self.assertTrue((ROOT_DIR / "servers" / "supplier-intelligence" / "server.py").exists())

    # Test 10: No unsupported automatic superiority or ranking claims
    def test_10_no_unsupported_superiority_claims(self):
        report_file = FLOWR_DIR / "results.md"
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read().lower()
        forbidden_phrases = [
            "retailops is superior to flowr",
            "retailops outperforms flowr",
            "winner",
            "ranking 1",
            "overall winner"
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, content, f"Forbidden superiority claim found: '{phrase}'")

    # Test 11: No fabricated Flowr performance values are present
    def test_11_no_fabricated_flowr_performance_values(self):
        json_file = FLOWR_DIR / "flowr_comparison_matrix.json"
        with open(json_file, "r", encoding="utf-8") as f:
            raw = f.read()
        # Ensure no fabricated latency values (e.g. "Flowr latency: 12ms") exist
        self.assertNotIn("flowr_mean_latency", raw)
        self.assertNotIn("flowr_p95", raw)
        self.assertNotIn("flowr_runtime_ms", raw)

    # Test 12: Research report contains explicit limitations and cautious conclusion
    def test_12_report_structure_and_cautious_conclusion(self):
        report_file = FLOWR_DIR / "results.md"
        with open(report_file, "r", encoding="utf-8") as f:
            report = f.read()
        self.assertIn("## 1. Objective", report)
        self.assertIn("## 2. Sources Reviewed", report)
        self.assertIn("## 9. Comparability Limitations", report)
        self.assertIn("## 10. What Was Not Evaluated", report)
        self.assertIn("## 12. Conclusion", report)
        self.assertIn("Because the available sources do not establish equivalent experimental conditions, the analysis does not claim that either architecture is universally superior", report)


if __name__ == "__main__":
    unittest.main()
