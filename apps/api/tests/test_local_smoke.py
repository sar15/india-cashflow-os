from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from cashflow_os.api.main import STORE, app


VIEWER_HEADERS = {"Authorization": "Bearer demo-viewer-token"}


class LocalSmokeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_dashboard_handles_mixed_timestamp_state(self):
        template_run = next(iter(STORE.forecast_runs.values()))
        legacy_run = template_run.model_copy(
            deep=True,
            update={
                "forecast_run_id": "legacy-naive-run",
                "generated_at": datetime(2026, 3, 31, 13, 23, 19, 516638),
            },
        )
        current_run = template_run.model_copy(
            deep=True,
            update={
                "forecast_run_id": "current-aware-run",
                "generated_at": datetime(2026, 3, 31, 14, 45, 21, 530242, tzinfo=timezone.utc),
            },
        )

        with patch.dict(
            STORE.forecast_runs,
            {
                legacy_run.forecast_run_id: legacy_run,
                current_run.forecast_run_id: current_run,
            },
            clear=True,
        ), patch.dict(STORE.reports, {}, clear=True), patch.object(STORE, "_save_state", return_value=None):
            response = self.client.get("/v1/dashboards/cash?org_id=demo-org", headers=VIEWER_HEADERS)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["forecast_run"]["forecast_run_id"], current_run.forecast_run_id)


if __name__ == "__main__":
    unittest.main()
