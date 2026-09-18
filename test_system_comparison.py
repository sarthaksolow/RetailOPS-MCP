"""
Quality-Control Test Suite for Task 09: Research-Paper-Ready System Comparison for RetailOps.

Tests verify:
1. All required comparison files exist.
2. JSON files are syntactically valid.
3. All required systems are covered (Flowr, WorkflowLLM, Agentic Inventory Replenishment, RetailOps).
4. Required comparison dimensions are present in matrix and tables.
5. Every documented numerical claim has a valid source reference.
6. Unsupported claims are not presented as verified facts (uncertainty labels used).
7. No ranking, winner, or universal superiority fields are present.
8. No fabricated external benchmark values are present.
9. RetailOps implementation claims match the repository artifacts.
10. Comparison tables contain evidence-status or comparability information.
11. Literature-based and experimentally obtained results are strictly distinguished.
12. No unsupported feature absence is recorded as a fact.
"""

import os
import json
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SYS_COMP_DIR = ROOT_DIR / "experiments" / "system_comparison"


class TestSystemComparisonQualityControl(unittest.TestCase):

    REQUIRED_FILES = [
        "README.md",
        "source_verification.md",
        "system_comparison_matrix.md",
        "comparison_analysis.md",
        "comparison_protocol.md",
        "evaluation_framework.md",
        "system_scope_table.md",
        "architecture_comparison_table.md",
        "evaluation_methodology_table.md",
        "retailops_evaluation_mapping.md",
        "evidence_registry.json",
        "results_summary.json"
    ]

    REQUIRED_SYSTEMS = [
        "RetailOps",
        "Flowr",
        "WorkflowLLM",
        "Agentic Inventory Replenishment"
    ]

    FORBIDDEN_PHRASES = [
        "retailops is superior",
        "retailops outperforms",
        "winner",
        "ranking 1",
        "overall winner",
        "overall advantage",
        "sub-2ms",
        "1.81 ms",
        "1.81ms"
    ]

    # Test 1: All required comparison files exist
    def test_01_all_required_comparison_files_exist(self):
        for fname in self.REQUIRED_FILES:
            fpath = SYS_COMP_DIR / fname
            self.assertTrue(fpath.exists(), f"Required file missing: {fname}")
            self.assertGreater(fpath.stat().st_size, 50, f"File appears empty: {fname}")

    # Test 2: JSON files are valid
    def test_02_json_files_are_valid(self):
        json_files = ["evidence_registry.json", "results_summary.json"]
        for jf in json_files:
            fpath = SYS_COMP_DIR / jf
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict, f"Root of {jf} must be a dict")

    # Test 3: Required systems are included across comparison matrix and tables
    def test_03_required_systems_included(self):
        matrix_file = SYS_COMP_DIR / "system_comparison_matrix.md"
        with open(matrix_file, "r", encoding="utf-8") as f:
            content = f.read()
        for sys_name in self.REQUIRED_SYSTEMS:
            self.assertIn(sys_name, content, f"System '{sys_name}' missing from comparison matrix")

    # Test 4: Required comparison dimensions are included
    def test_04_required_dimensions_included(self):
        matrix_file = SYS_COMP_DIR / "system_comparison_matrix.md"
        with open(matrix_file, "r", encoding="utf-8") as f:
            content = f.read().lower()
        required_dimensions = [
            "primary domain",
            "workflow scope",
            "orchestration mechanism",
            "inter-service / tool protocol",
            "service decoupling",
            "service extensibility",
            "service replacement",
            "human supervision",
            "reliability & fault handling",
            "evaluation focus",
            "public reproducibility"
        ]
        for dim in required_dimensions:
            self.assertIn(dim, content, f"Dimension '{dim}' missing from comparison matrix")

    # Test 5: Every documented numerical claim has a source reference
    def test_05_evidence_registry_records_have_sources(self):
        registry_file = SYS_COMP_DIR / "evidence_registry.json"
        with open(registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        self.assertIn("records", registry)
        self.assertGreaterEqual(len(registry["records"]), 8)
        for rec in registry["records"]:
            self.assertIn("system", rec)
            self.assertIn("claim", rec)
            self.assertIn("evidence_type", rec)
            self.assertIn("source", rec)
            self.assertIn("confidence", rec)
            self.assertIn(rec["evidence_type"], ["literature", "implementation", "experiment", "inference"])
            self.assertIn(rec["confidence"], ["high", "medium", "low"])
            self.assertTrue(len(rec["source"]) > 0, "Source must not be empty")

    # Test 6: Missing information uses standard uncertainty labels
    def test_06_uncertainty_labels_used(self):
        matrix_file = SYS_COMP_DIR / "system_comparison_matrix.md"
        with open(matrix_file, "r", encoding="utf-8") as f:
            content = f.read()
        uncertainty_phrases = [
            "Not reported in the reviewed source",
            "Not established",
            "Not directly comparable"
        ]
        found = any(phrase in content for phrase in uncertainty_phrases)
        self.assertTrue(found, "Matrix must use standardized uncertainty labels for missing information")

    # Test 7: No ranking, winner, or universal superiority fields
    def test_07_no_ranking_or_winner_fields(self):
        md_files = list(SYS_COMP_DIR.glob("*.md"))
        for mdf in md_files:
            with open(mdf, "r", encoding="utf-8") as f:
                content = f.read().lower()
            for phrase in self.FORBIDDEN_PHRASES:
                self.assertNotIn(phrase, content, f"Forbidden phrase '{phrase}' found in {mdf.name}")

    # Test 8: No fabricated external benchmark values
    def test_08_no_fabricated_external_benchmarks(self):
        summary_file = SYS_COMP_DIR / "results_summary.json"
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        # Ensure external systems have NO quantitative latency or throughput numbers fabricated
        ext = summary.get("external_systems_reviewed", {})
        for sys_key, data in ext.items():
            self.assertNotIn("mean_latency_ms", data, f"Fabricated latency in {sys_key}")
            self.assertNotIn("throughput_qps", data, f"Fabricated throughput in {sys_key}")
            self.assertNotIn("runtime_ms", data, f"Fabricated runtime in {sys_key}")

    # Test 9: RetailOps implementation claims match repository artifacts
    def test_09_retailops_measurements_match_artifacts(self):
        summary_file = SYS_COMP_DIR / "results_summary.json"
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        m = summary["verified_retailops_measurements"]

        # Check Task 04
        t4_path = ROOT_DIR / m["task_04_service_replacement"]["source_artifact"]
        self.assertTrue(t4_path.exists())

        # Check Task 06
        t6_path = ROOT_DIR / m["task_06_persistent_mcp_sessions"]["source_artifact"]
        self.assertTrue(t6_path.exists())
        self.assertEqual(m["task_06_persistent_mcp_sessions"]["persistent_mcp_mean_ms"], 37.75)

        # Check Task 07
        t7_path = ROOT_DIR / m["task_07_fault_tolerance_and_cleanup"]["source_artifact"]
        self.assertTrue(t7_path.exists())
        self.assertEqual(m["task_07_fault_tolerance_and_cleanup"]["zombie_processes_remaining"], 0)

        # Check Task 08
        t8_path = ROOT_DIR / m["task_08_extensibility"]["source_artifact"]
        self.assertTrue(t8_path.exists())
        self.assertEqual(m["task_08_extensibility"]["existing_service_files_modified"], 0)

    # Test 10: Comparison tables contain evidence status or comparability information
    def test_10_tables_contain_comparability_info(self):
        table_files = [
            SYS_COMP_DIR / "system_scope_table.md",
            SYS_COMP_DIR / "architecture_comparison_table.md",
            SYS_COMP_DIR / "evaluation_methodology_table.md",
            SYS_COMP_DIR / "retailops_evaluation_mapping.md"
        ]
        for tf in table_files:
            self.assertTrue(tf.exists(), f"Table file missing: {tf.name}")
            with open(tf, "r", encoding="utf-8") as f:
                lines = f.readlines()
            table_lines = [l for l in lines if l.strip().startswith("|")]
            self.assertGreater(len(table_lines), 2, f"Table not found in {tf.name}")
            header = table_lines[0].lower()
            self.assertTrue(
                "comparability" in header or
                "evidence" in header or
                "source" in header or
                "limitation" in header,
                f"Table {tf.name} header missing evidence/comparability/source column: '{header}'"
            )

    # Test 11: Literature and experimentally obtained results are distinguished
    def test_11_evidence_registry_distinguishes_types(self):
        registry_file = SYS_COMP_DIR / "evidence_registry.json"
        with open(registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        types_found = {rec["evidence_type"] for rec in registry["records"]}
        self.assertIn("literature", types_found)
        self.assertIn("implementation", types_found)
        self.assertIn("experiment", types_found)
        self.assertIn("inference", types_found)

    # Test 12: No unsupported feature absence is recorded as a fact
    def test_12_no_unsupported_feature_absence_as_fact(self):
        matrix_file = SYS_COMP_DIR / "system_comparison_matrix.md"
        with open(matrix_file, "r", encoding="utf-8") as f:
            content = f.read()
        # Ensure phrases asserting absence as a fact without qualification are absent
        bad_phrases = [
            "flowr has no mcp",
            "flowr lacks governance",
            "workflowllm cannot execute",
            "agentic inventory has no forecasting"
        ]
        for bp in bad_phrases:
            self.assertNotIn(bp, content.lower(), f"Unqualified absence claim found: {bp}")


if __name__ == "__main__":
    unittest.main()
