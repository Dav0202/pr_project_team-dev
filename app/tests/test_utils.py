import io
import csv
import pytest
from datetime import datetime
from app import app as app1
from flask import Response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate

from reporting_module.utils import export_report_data, validate_dates

@pytest.fixture(autouse=True)
def app_context():
    app = app1
    with app.test_request_context():
        yield

# --- Tests for export_report_data ---

def test_export_csv_simple_list():
    data = [
        {"a": 1, "b": 2},
        {"a": 3, "b": 4},
    ]
    resp: Response = export_report_data(data, export_format="csv", filename="test")
    # Check headers
    assert resp.mimetype == "text/csv"
    assert resp.headers["Content-Disposition"] == "attachment; filename=test.csv"
    # Parse CSV
    text = resp.get_data(as_text=True)
    reader = list(csv.reader(io.StringIO(text)))
    assert reader[0] == ["a", "b"]
    assert reader[1] == ["1", "2"]
    assert reader[2] == ["3", "4"]

def test_export_csv_dict_input_treated_as_headers():
    d = {"x": 10, "y": 20}
    resp: Response = export_report_data(d, export_format="csv", filename="dtest")
    assert resp.mimetype == "text/csv"
    assert resp.headers["Content-Disposition"] == "attachment; filename=dtest.csv"
    text = resp.get_data(as_text=True)

    assert "x" in text.splitlines()[0].split(",")
    assert "y" in text.splitlines()[0].split(",")

    body_lines = text.splitlines()[1:]
    csv_body = "\n".join(body_lines)
    assert "10" in csv_body
    assert "20" in csv_body

def test_export_pdf_generates_pdf_header():
    data = [
        {"col1": "val1", "col2": "val2"},
    ]
    resp: Response = export_report_data(data, export_format="pdf", filename="mypdf")
    assert resp.mimetype == "application/pdf"
    cd = resp.headers["Content-Disposition"]
    assert cd.startswith("attachment;")
    assert "filename=mypdf.pdf" in cd
    b = resp.get_data()

    assert b.startswith(b"%PDF-")

def test_export_pdf_invalid_story_raises_500(monkeypatch):
    monkeypatch.setattr(
        SimpleDocTemplate, 
        "build", 
        lambda self, story: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    data = [{"h": 1}]
    result = export_report_data(data, export_format="pdf", filename="errpdf")

    if isinstance(result, tuple):
        resp, status = result
        assert status == 500
    else:
        resp = result
        assert resp.status_code == 500

    body = resp.get_json()
    assert body == {"error": "Could not generate PDF"}

def test_export_unsupported_format_returns_json():
    data = [{"k": 123}]
    resp = export_report_data(data, export_format="xml", filename="f")
    assert resp.mimetype == "application/json"
    assert resp.get_json() == data

# --- Tests for validate_dates ---

@pytest.mark.parametrize("start, end, want_valid, want_msg", [
    (None, None, True, None),
    ("2022-01-01", None, True, None),
    (None, "2022-12-31", True, None),
    ("2022-01-01", "2022-12-31", True, None),
])
def test_validate_dates_valid(start, end, want_valid, want_msg):
    ok, msg, sd, ed = validate_dates(start, end)
    assert ok is want_valid
    assert msg == want_msg
    # If provided, must echo the same string
    if start:
        assert sd == start
    else:
        assert sd is None
    if end:
        assert ed == end
    else:
        assert ed is None

@pytest.mark.parametrize("bad_start, bad_end, expect_error", [
    ("not-a-date", None, "Invalid date format. Please use YYYY-MM-DD."),
    (None, "31-12-2022", "Invalid date format. Please use YYYY-MM-DD."),
])
def test_validate_dates_invalid_format(bad_start, bad_end, expect_error):
    ok, msg, sd, ed = validate_dates(bad_start, bad_end)
    assert ok is False
    assert isinstance(msg, dict)
    assert msg["error"] == expect_error
    assert sd is None and ed is None

def test_validate_dates_start_after_end_comment_unchecked():
    # Although commented out, logic currently does not enforce start <= end
    ok, msg, sd, ed = validate_dates("2023-12-31", "2023-01-01")
    assert ok is True
    assert msg is None
    assert sd == "2023-12-31"
    assert ed == "2023-01-01"
