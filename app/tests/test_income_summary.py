import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_income_summary_success(mock_db_conn, mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "123",
        "role": "Finance",
        "company_id": "1"
    }

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db_conn.return_value = mock_conn

    # First query result: total_income
    mock_cursor.fetchone.return_value = {"total_income": 15000}

    # Second query result: monthly_trend
    mock_cursor.fetchall.return_value = [
        {"month": "2025-01", "amount": 5000},
        {"month": "2025-02", "amount": 10000}
    ]

    response = client.get("/api/reports/income-summary")
    assert response.status_code == 200

    data = response.get_json()
    assert data["total_income"] == 15000.0
    assert data["monthly_trend"] == [
        {"month": "2025-01", "amount": 5000.0},
        {"month": "2025-02", "amount": 10000.0}
    ]

# --------- Role-based Access Denied ---------
@patch('reporting_module.api.get_user_context')
def test_income_summary_forbidden_role(mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "123",
        "role": "Intern",
        "company_id": "1"
    }

    response = client.get("/api/reports/income-summary")
    assert response.status_code == 403
    assert response.get_json()["error"] == "Access denied: insufficient permissions"

# --------- Missing company_id ---------
@patch('reporting_module.api.get_user_context')
def test_income_summary_missing_company(mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "123",
        "role": "Admin",
        "company_id": None
    }

    response = client.get("/api/reports/income-summary")
    assert response.status_code == 400
    assert response.get_json()["error"] == "company_id is required in context"

# --------- Test with query parameters ---------
@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_income_summary_with_filters(mock_db_conn, mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "123",
        "role": "Finance",
        "company_id": "1"
    }

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db_conn.return_value = mock_conn

    mock_cursor.fetchone.return_value = {"total_income": 8000}
    mock_cursor.fetchall.return_value = [{"month": "2025-03", "amount": 8000}]

    response = client.get("/api/reports/income-summary?start_date=2025-01-01&end_date=2025-03-31&project_id=22")

    assert response.status_code == 200
    data = response.get_json()
    assert data["total_income"] == 8000.0
    assert data["monthly_trend"] == [{"month": "2025-03", "amount": 8000.0}]

# --------- Internal Error ---------
@patch('reporting_module.api.get_user_context', side_effect=Exception("Mocked error"))
def test_income_summary_internal_error(mock_user_context, client):
    response = client.get("/api/reports/income-summary")
    assert response.status_code == 500
    assert response.get_json()["error"] == "Internal server error"