import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --------- Successful Access ---------
@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_expense_summary_success(mock_db_conn, mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "321",
        "role": "Admin",
        "company_id": "1"
    }

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db_conn.return_value = mock_conn

    mock_cursor.fetchone.return_value = {"total_expense": 12000}

    mock_cursor.fetchall.return_value = [
        {"month": "2025-01", "amount": 3000},
        {"month": "2025-02", "amount": 9000}
    ]

    response = client.get("/api/reports/expense-summary")
    assert response.status_code == 200

    data = response.get_json()
    assert data["total_expense"] == 12000.0
    assert data["monthly_trend"] == [
        {"month": "2025-01", "amount": 3000.0},
        {"month": "2025-02", "amount": 9000.0}
    ]

# --------- Role-based Access Denied ---------
@patch('reporting_module.api.get_user_context')
def test_expense_summary_forbidden_role(mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "321",
        "role": "Sales",
        "company_id": "1"
    }

    response = client.get("/api/reports/expense-summary")
    assert response.status_code == 403
    assert response.get_json()["error"] == "Access denied: insufficient permissions"

@patch('reporting_module.api.get_user_context')
def test_expense_summary_missing_company(mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "321",
        "role": "Admin",
        "company_id": None
    }

    response = client.get("/api/reports/expense-summary")
    assert response.status_code == 400
    assert response.get_json()["error"] == "company_id is required in context"

@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_expense_summary_with_filters(mock_db_conn, mock_user_context, client):
    mock_user_context.return_value = {
        "user_id": "321",
        "role": "Finance",
        "company_id": "1"
    }

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db_conn.return_value = mock_conn

    mock_cursor.fetchone.return_value = {"total_expense": 5000}
    mock_cursor.fetchall.return_value = [{"month": "2025-03", "amount": 5000}]

    response = client.get("/api/reports/expense-summary?start_date=2025-01-01&end_date=2025-03-31&project_id=10")

    assert response.status_code == 200
    data = response.get_json()
    assert data["total_expense"] == 5000.0
    assert data["monthly_trend"] == [{"month": "2025-03", "amount": 5000.0}]

@patch('reporting_module.api.get_user_context', side_effect=Exception("Mocked exception"))
def test_expense_summary_internal_error(mock_user_context, client):
    response = client.get("/api/reports/expense-summary")
    assert response.status_code == 500
    assert response.get_json()["error"] == "Internal server error"
