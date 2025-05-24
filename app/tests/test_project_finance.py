import pytest
from unittest.mock import patch, MagicMock
from app import app
import psycopg2.extras
import psycopg2


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def mock_get_user_context(role='Admin', company_id='1'):
    """Helper to create a mock user context."""
    return {"role": role, "company_id": company_id}

def setup_mock_db(mock_db_conn_func, fetchone_side_effect=None, fetchall_side_effect=None):
    """Helper to set up mock database connection and cursor."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Configure cursor to return DictCursor-like objects
    mock_cursor.cursor_factory = psycopg2.extras.DictCursor
    mock_db_conn_func.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    if fetchone_side_effect is not None:
        mock_cursor.fetchone.side_effect = fetchone_side_effect
    if fetchall_side_effect is not None:
        mock_cursor.fetchall.side_effect = fetchall_side_effect

    return mock_conn, mock_cursor

# --- Test Cases ---

@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_success_no_filters(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval of project finance summary without filters."""
    mock_projects_data = [
        {'id': 1, 'name': 'Project Alpha'},
        {'id': 2, 'name': 'Project Beta'}
    ]

    mock_fetchone_data = [
        # Project 1 data
        {'total_income': 10000},
        {'general_expense': 2000},
        {'payroll_expense': 1000},
        # Project 2 data
        {'total_income': 5000},
        {'general_expense': 1000},
        {'payroll_expense': 500},
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_projects_data]
    )

    response = client.get('/api/reports/project-finance')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 2

    # Assertions for Project 1
    project1_data = next((item for item in data if item['project_id'] == 1), None)
    assert project1_data is not None
    assert project1_data['project_name'] == 'Project Alpha'
    assert project1_data['income'] == 10000.0
    assert project1_data['expenses'] == 3000.0
    assert project1_data['net'] == 7000.0

    # Assertions for Project 2
    project2_data = next((item for item in data if item['project_id'] == 2), None)
    assert project2_data is not None
    assert project2_data['project_name'] == 'Project Beta'
    assert project2_data['income'] == 5000.0
    assert project2_data['expenses'] == 1500.0
    assert project2_data['net'] == 3500.0

    mock_cursor.execute.assert_any_call(
        "SELECT id, name FROM projects WHERE company_id = %s",
        ('1',)
    )
    mock_cursor.execute.assert_any_call(
        "SELECT COALESCE(SUM(amount), 0) AS total_income FROM income_entries WHERE company_id = %s AND project_id = %s",
        ['1', 1]
    )
    mock_cursor.execute.assert_any_call(
        "SELECT COALESCE(SUM(amount), 0) AS general_expense FROM general_expenses WHERE company_id = %s AND project_id = %s",
        ['1', 1]
    )
    mock_cursor.execute.assert_any_call(
        "SELECT COALESCE(SUM(amount), 0) AS payroll_expense FROM payroll_entries WHERE company_id = %s AND project_id = %s",
        ['1', 1]
    )
    mock_cursor.execute.assert_any_call(
        "SELECT COALESCE(SUM(amount), 0) AS total_income FROM income_entries WHERE company_id = %s AND project_id = %s",
        ['1', 2]
    )
    mock_cursor.execute.assert_any_call(
        "SELECT COALESCE(SUM(amount), 0) AS general_expense FROM general_expenses WHERE company_id = %s AND project_id = %s",
        ['1', 2]
    )
    mock_cursor.execute.assert_any_call(
        "SELECT COALESCE(SUM(amount), 0) AS payroll_expense FROM payroll_entries WHERE company_id = %s AND project_id = %s",
        ['1', 2]
    )

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Finance', company_id='2'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_success_with_all_filters(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval with start_date, end_date, and project_id filters."""
    mock_project_data = [{'id': 5, 'name': 'Filtered Project'}]
    mock_fetchone_data = [
        {'total_income': 15000},
        {'general_expense': 3000},
        {'payroll_expense': 2500},
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_project_data]
    )

    response = client.get('/api/reports/project-finance?start_date=2024-01-01&end_date=2024-12-31&project_id=5')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['project_id'] == 5
    assert data[0]['project_name'] == 'Filtered Project'
    assert data[0]['income'] == 15000.0
    assert data[0]['expenses'] == 5500.0
    assert data[0]['net'] == 9500.0

    mock_cursor.execute.assert_any_call(
        "SELECT id, name FROM projects WHERE id = %s AND company_id = %s",
        ('5', '2')
    )
    expected_filter_sql = (
        "company_id = %s "
        "AND project_id = %s "
        "AND date >= %s "
        "AND date <= %s "
        "AND project_id = %s"
    )

    expected_params = ['2', '5', '2024-01-01', '2024-12-31', 5]

    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount), 0) AS total_income FROM income_entries WHERE {expected_filter_sql}",
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount), 0) AS general_expense FROM general_expenses WHERE {expected_filter_sql}",
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount), 0) AS payroll_expense FROM payroll_entries WHERE {expected_filter_sql}",
        expected_params
    )

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='HR', company_id='3'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_success_date_filters_only(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval with only start_date and end_date filters."""
    mock_projects_data = [{'id': 10, 'name': 'Project Gamma'}]
    mock_fetchone_data = [
        {'total_income': 8000},
        {'general_expense': 1500},
        {'payroll_expense': 500},
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_projects_data]
    )

    response = client.get('/api/reports/project-finance?start_date=2023-07-01&end_date=2023-12-31')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['project_id'] == 10
    assert data[0]['project_name'] == 'Project Gamma'
    assert data[0]['income'] == 8000.0
    assert data[0]['expenses'] == 2000.0
    assert data[0]['net'] == 6000.0

    mock_cursor.execute.assert_any_call(
        "SELECT id, name FROM projects WHERE company_id = %s",
        ('3',)
    )
    expected_filter_sql = (
        "company_id = %s "
        "AND date >= %s "
        "AND date <= %s "
        "AND project_id = %s"
    )
    expected_params = ['3', '2023-07-01', '2023-12-31', 10]

    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount), 0) AS total_income FROM income_entries WHERE {expected_filter_sql}",
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount), 0) AS general_expense FROM general_expenses WHERE {expected_filter_sql}",
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount), 0) AS payroll_expense FROM payroll_entries WHERE {expected_filter_sql}",
        expected_params
    )

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='4'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_no_projects_found(mock_db_conn, mock_user_context, client):
    """Tests the case where no projects are found for the given company/filters."""
    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchall_side_effect=[[]]
    )

    response = client.get('/api/reports/project-finance')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 0 # Expect an empty list

    mock_cursor.execute.assert_any_call(
        "SELECT id, name FROM projects WHERE company_id = %s",
        ('4',)
    )
    assert mock_cursor.fetchone.call_count == 0
    
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Finance', company_id='5'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_project_no_financial_data(mock_db_conn, mock_user_context, client):
    """Tests the case where a project is found but has no associated financial data."""
    mock_projects_data = [{'id': 15, 'name': 'Project Delta'}]
    mock_fetchone_data = [
        {'total_income': 0},
        {'general_expense': 0},
        {'payroll_expense': 0},
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_projects_data]
    )

    response = client.get('/api/reports/project-finance')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['project_id'] == 15
    assert data[0]['project_name'] == 'Project Delta'
    assert data[0]['income'] == 0.0
    assert data[0]['expenses'] == 0.0
    assert data[0]['net'] == 0.0

    mock_cursor.execute.assert_any_call(
        "SELECT id, name FROM projects WHERE company_id = %s",
        ('5',)
    )
    mock_cursor.execute.assert_any_call(
        "SELECT COALESCE(SUM(amount), 0) AS total_income FROM income_entries WHERE company_id = %s AND project_id = %s",
        ['5', 15]
    )

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Staff', company_id='1'))
def test_project_finance_summary_unauthorized(mock_user_context, client):
    """Tests that a user with an unauthorized role receives a 403."""
    
    response = client.get('/api/reports/project-finance')

    assert response.status_code == 403
    assert response.get_json() == {"error": "Access denied: insufficient permissions"}


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id=None))
def test_project_finance_summary_missing_company_id(mock_user_context, client):
    """Tests that a request with missing company_id in context receives a 400."""
    
    response = client.get('/api/reports/project-finance')

    assert response.status_code == 400
    assert response.get_json() == {"error": "company_id is required in context"}

@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_invalid_date_format(mock_db_conn, mock_user_context, client):
    """Tests handling of invalid date format in query parameters."""

    mock_conn, mock_cursor = setup_mock_db(mock_db_conn) # Basic setup

    response = client.get('/api/reports/project-finance?start_date=not-a-date&end_date=2024-12-31')

    assert response.status_code == 200
    assert response.get_json() == []

    mock_db_conn.assert_called_once()


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_invalid_project_id_format(mock_db_conn, mock_user_context, client):
    """Tests handling of invalid project_id format in query parameters."""
    mock_conn, mock_cursor = setup_mock_db(mock_db_conn) # Basic setup

    response = client.get('/api/reports/project-finance?project_id=not-a-number')

    assert response.status_code == 200
    assert response.get_json() == []

    mock_db_conn.assert_called_once()


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection', side_effect=psycopg2.OperationalError("Database connection failed"))
def test_project_finance_summary_db_connection_error(mock_db_conn, mock_user_context, client):
    """Tests handling of a database connection error."""
    response = client.get('/api/reports/project-finance')

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}

    mock_db_conn.assert_called_once()


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_project_finance_summary_db_query_error(mock_db_conn, mock_user_context, client):
    """Tests handling of an error during database query execution."""
    mock_conn, mock_cursor = setup_mock_db(mock_db_conn)
    mock_cursor.execute.side_effect = psycopg2.ProgrammingError("Invalid query syntax")

    response = client.get('/api/reports/project-finance')

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}

    mock_db_conn.assert_called_once()
    mock_cursor.execute.assert_called_once() # Verify execute was called at least once
