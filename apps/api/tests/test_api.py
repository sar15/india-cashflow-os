import os
import tempfile
import unittest
from pathlib import Path

STATE_DIR = tempfile.mkdtemp(prefix="cashflow-os-api-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(STATE_DIR) / "cashflow.db")
os.environ["CASHFLOW_REPORT_STORAGE_PATH"] = str(Path(STATE_DIR) / "report-files")

from fastapi.testclient import TestClient

from cashflow_os.api.main import STORE, app


OWNER_HEADERS = {"Authorization": "Bearer demo-owner-token"}
VIEWER_HEADERS = {"Authorization": "Bearer demo-viewer-token"}


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_missing_auth_is_rejected(self):
        response = self.client.get("/v1/dashboards/cash")
        self.assertEqual(response.status_code, 401)

    def test_dashboard_demo(self):
        response = self.client.get("/v1/dashboards/cash?demo=1", headers=VIEWER_HEADERS)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("forecast_run", payload)
        self.assertIn("report_pack", payload)

    def test_dashboard_lookup_by_org_id(self):
        response = self.client.get("/v1/dashboards/cash?org_id=demo-org", headers=VIEWER_HEADERS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["forecast_run"]["org_id"], "demo-org")



    def test_viewer_cannot_create_import(self):
        response = self.client.post("/v1/imports", json={"use_demo": True}, headers=VIEWER_HEADERS)
        self.assertEqual(response.status_code, 403)

    def test_report_export_cycle(self):
        dashboard = self.client.get("/v1/dashboards/cash?demo=1", headers=VIEWER_HEADERS).json()
        forecast_run_id = dashboard["forecast_run"]["forecast_run_id"]
        report_response = self.client.post(
            "/v1/reports",
            json={"forecast_run_id": forecast_run_id, "include_scenarios": True},
            headers=OWNER_HEADERS,
        )
        self.assertEqual(report_response.status_code, 200)
        report_id = report_response.json()["report_id"]

        pdf_response = self.client.get(f"/v1/reports/{report_id}/download?format=pdf", headers=VIEWER_HEADERS)
        xlsx_response = self.client.get(f"/v1/reports/{report_id}/download?format=xlsx", headers=VIEWER_HEADERS)
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(xlsx_response.status_code, 200)
        self.assertGreater(len(pdf_response.content), 100)
        self.assertGreater(len(xlsx_response.content), 100)

    def test_state_file_is_created(self):
        self.assertTrue(Path(os.environ["DATABASE_URL"].replace("sqlite:///", "")).exists())

    def test_duplicate_import_returns_existing_batch(self):
        payload = {
            "source_type": "manual",
            "filename": "manual-upload.csv",
            "text_content": (
                "counterparty,event_type,amount_inr,due_date,document_number\n"
                "Acme Retail,inflow,125000,2026-04-10,INV-001\n"
            ),
        }

        first_response = self.client.post("/v1/imports", json=payload, headers=OWNER_HEADERS)
        second_response = self.client.post("/v1/imports", json=payload, headers=OWNER_HEADERS)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        first_batch = first_response.json()["import_batch"]
        second_batch = second_response.json()["import_batch"]
        self.assertEqual(first_batch["import_batch_id"], second_batch["import_batch_id"])
        self.assertEqual(first_batch["checksum"], second_batch["checksum"])

    def test_demo_import_populates_review_counts(self):
        response = self.client.post("/v1/imports", json={"use_demo": True}, headers=OWNER_HEADERS)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        batch = payload["import_batch"]
        self.assertGreater(batch["event_count"], 0)
        self.assertGreater(batch["counterparty_count"], 0)
        self.assertGreater(batch["obligation_count"], 0)

    def test_confirm_mapping_accepts_custom_obligations_and_scenario(self):
        import_response = self.client.post("/v1/imports", json={"use_demo": True}, headers=OWNER_HEADERS)
        self.assertEqual(import_response.status_code, 200)
        import_batch_id = import_response.json()["import_batch"]["import_batch_id"]

        response = self.client.post(
            f"/v1/imports/{import_batch_id}/confirm-mapping",
            json={
                "company_name": "Shakti Components Pvt Ltd",
                "industry": "Manufacturing",
                "as_of_date": "2026-04-01",
                "minimum_cash_buffer_minor_units": 80000000,
                "scenario": {
                    "name": "Collections Slip",
                    "description": "Adds pressure to inflows and opening liquidity.",
                    "inflow_delay_days": 9,
                    "outflow_delay_days": 2,
                    "inflow_scalar_bps": 9300,
                    "outflow_scalar_bps": 10300,
                    "opening_cash_adjustment_minor_units": -1500000,
                },
                "obligations": [
                    {
                        "name": "Factory Insurance",
                        "obligation_type": "other",
                        "frequency": "one_time",
                        "amount_minor_units": 2500000,
                        "start_date": "2026-04-18",
                        "notes": "Quarterly insurance top-up",
                    }
                ],
            },
            headers=OWNER_HEADERS,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["scenario"]["name"], "Collections Slip")
        self.assertEqual(payload["scenario"]["kind"], "custom")
        self.assertEqual(payload["scenario"]["inflow_delay_days"], 9)
        self.assertEqual(payload["scenario"]["outflow_scalar_bps"], 10300)
        self.assertEqual(payload["scenario"]["minimum_cash_buffer_minor_units"], 80000000)
        self.assertTrue(any(item["name"] == "Factory Insurance" for item in payload["obligations"]))

    def test_chart_trace_endpoint_returns_event_details(self):
        dashboard_response = self.client.get("/v1/dashboards/cash?demo=1", headers=VIEWER_HEADERS)
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.json()
        report_pack = dashboard["report_pack"]
        weekly_chart = next(chart for chart in report_pack["charts"] if chart["title"] == "13-Week Cash Balance")
        point_key = weekly_chart["meta"]["trace_points"][0]["key"]

        trace_response = self.client.get(
            f"/v1/reports/{report_pack['report_id']}/charts/{weekly_chart['chart_id']}/trace?point_key={point_key}",
            headers=VIEWER_HEADERS,
        )
        self.assertEqual(trace_response.status_code, 200)
        payload = trace_response.json()
        self.assertEqual(payload["chart_title"], "13-Week Cash Balance")
        self.assertEqual(payload["point_key"], point_key)
        self.assertGreaterEqual(payload["totals"]["trace_count"], 0)
        self.assertIn("summary", payload)

    def test_upload_rejects_unsupported_extension(self):
        response = self.client.post(
            "/v1/imports",
            data={"org_id": "demo-org", "source_type": "manual"},
            files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
            headers=OWNER_HEADERS,
        )
        self.assertEqual(response.status_code, 415)
        self.assertIn(".exe", response.json()["detail"])

    def test_upload_malformed_csv_returns_structured_400(self):
        csv_content = (
            "counterparty,event_type,gross_amount_inr,due_date,document_number\n"
            "Acme Retail,inflow,125000,2026-04-10,INV-001\n"
            "Bad Row,inflow,NOT_A_NUMBER,2026-04-15,INV-002\n"
        )
        response = self.client.post(
            "/v1/imports",
            data={"org_id": "demo-org", "source_type": "manual"},
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
            headers=OWNER_HEADERS,
        )
        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertEqual(detail["error_code"], "parse_error")
        self.assertIn("Row", detail["message"])

    def test_template_download_returns_xlsx(self):
        response = self.client.get("/v1/templates/cashflow-os-template.xlsx")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["content-type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertGreater(len(response.content), 1000)
        # Verify it's a valid XLSX by checking the ZIP signature
        self.assertTrue(response.content[:4] == b"PK\x03\x04")


if __name__ == "__main__":
    unittest.main()

