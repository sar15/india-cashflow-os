import tempfile
import unittest
from pathlib import Path

from cashflow_os.api.store import InMemoryStore
from cashflow_os.domain.models import ForecastScenario, ScenarioKind


class StorePersistenceTestCase(unittest.TestCase):
    def test_store_persists_across_instances(self):
        temp_dir = tempfile.mkdtemp(prefix="cashflow-os-store-tests-")
        state_path = Path(temp_dir) / "state.json"

        first_store = InMemoryStore(state_path=state_path)
        demo_run_ids = sorted(first_store.forecast_runs.keys())
        self.assertTrue(demo_run_ids)

        first_store.upsert_scenario(
            ForecastScenario(
                name="Custom Stress",
                kind=ScenarioKind.CUSTOM,
                description="Persisted scenario check",
            )
        )

        second_store = InMemoryStore(state_path=state_path)
        self.assertEqual(sorted(second_store.forecast_runs.keys()), demo_run_ids)
        self.assertEqual(len(second_store.scenarios), 1)

    def test_report_files_are_read_back_from_disk(self):
        temp_dir = tempfile.mkdtemp(prefix="cashflow-os-report-tests-")
        state_path = Path(temp_dir) / "state.json"
        report_storage_path = Path(temp_dir) / "reports"

        first_store = InMemoryStore(state_path=state_path, report_storage_path=report_storage_path)
        first_store.cache_report_file("report-123", "pdf", b"%PDF-1.7")

        second_store = InMemoryStore(state_path=state_path, report_storage_path=report_storage_path)
        self.assertEqual(second_store.read_report_file("report-123", "pdf"), b"%PDF-1.7")
        self.assertTrue((report_storage_path / "report-123.pdf").exists())


if __name__ == "__main__":
    unittest.main()
