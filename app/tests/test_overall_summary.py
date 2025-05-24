import pytest
from unittest.mock import patch, MagicMock
import psycopg2.extras
from app import app

# Assume these are defined elsewhere in your application
# For testing purposes, we'll mock them.
def get_user_context():
    """Mocks the function to get user context."""
    pass

def get_db_postgres_connection():
    """Mocks the function to get a database connection."""
    pass

def assert_query_called(mock_cursor, expected_substr, expected_params):
    """
    Verifies that mock_cursor.execute was called with a SQL containing
    expected_substr and exactly expected_params.
    """
    for call_args in mock_cursor.execute.call_args_list:
        sql, params = call_args[0]
        if expected_substr in sql and params == expected_params:
            return
    pytest.fail(f"Expected SQL containing:\n  {expected_substr}\nwith params {expected_params!r}\n\nActual calls:\n" +
               "\n".join(f"  {c[0][0]!r}, {c[0][1]!r}" for c in mock_cursor.execute.call_args_list))


# --- Pytest Test Suite ---

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Helper function to mock get_user_context
def mock_get_user_context_helper(role, company_id):
    """
    Helper to create mock user context dictionaries.
    """
    mock_user_context = MagicMock()
    mock_user_context.role = role
    mock_user_context.company_id = company_id
    mock_user_context.__getitem__.side_effect = lambda key: {
        "role": role,
        "company_id": company_id
    }[key]
    return mock_user_context

# Helper function to set up mock database cursor behavior
def setup_mock_db(mock_cursor, income_data, gen_exp_data, pay_exp_data, tender_counts_data, project_count_data):
    """
    A crucial helper that centralizes the setup of the mock database connection and cursor.
    It configures side effects for fetchone and fetchall based on expected query order.
    """

    fetchone_returns = [
        {"total_income": income_data},
        {"total_general_expenses": gen_exp_data},
        {"total_payroll_expenses": pay_exp_data},
        {"project_count": project_count_data}
    ]
    
    mock_cursor.fetchone.side_effect = fetchone_returns
    mock_cursor.fetchall.side_effect = [tender_counts_data]
    pass


# --- Test Cases ---

@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_overall_summary_report_success_no_filters(
    mock_get_db_conn, mock_get_user_context_func, client
):
    """
    Test the overall_summary_report API endpoint for a successful response with no filters.
    """

    test_company_id = "comp123"
    mock_get_user_context_func.return_value = mock_get_user_context_helper("Admin", test_company_id)

    mock_conn = MagicMock()
    mock_cursor = MagicMock(spec=psycopg2.extras.DictCursor)
    mock_get_db_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    income_data = 1000.0
    gen_exp_data = 200.0
    pay_exp_data = 300.0
    tender_counts_data = [
        {"status": "Open", "count": 5},
        {"status": "Closed", "count": 3}
    ]
    project_count_data = 8

    setup_mock_db(mock_cursor, income_data, gen_exp_data, pay_exp_data, tender_counts_data, project_count_data)

    response = client.get('/api/reports/overall-summary')

    assert response.status_code == 200
    data = response.get_json()
    assert data["total_income"] == income_data
    assert data["total_general_expenses"] == gen_exp_data
    assert data["total_payroll_expenses"] == pay_exp_data
    assert data["tender_counts"] == tender_counts_data
    assert data["project_count"] == project_count_data

    expected_params = [test_company_id]
    
    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount),0) AS total_income FROM income_entries WHERE company_id = %s",
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount),0) AS total_general_expenses FROM general_expenses WHERE company_id = %s",
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        f"SELECT COALESCE(SUM(amount),0) AS total_payroll_expenses FROM payroll_entries WHERE company_id = %s",
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        """SELECT t.status, COUNT(*) AS count FROM tenders t WHERE t.company_id = %s GROUP BY t.status ORDER BY t.status""" ,
        expected_params
    )
    mock_cursor.execute.assert_any_call(
        f"SELECT COUNT(*) AS project_count FROM projects WHERE company_id = %s",
        expected_params
    )

    # Ensure connection and cursor are closed
    mock_cursor.close.assert_called()
    mock_conn.close.assert_called()


@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_overall_summary_report_success_with_all_filters(
    mock_get_db_conn, mock_get_user_context_func, client
):
    """
    Test the overall_summary_report API endpoint for a successful response with all filters.
    """
    test_company_id   = "comp123"
    test_project_id   = "proj456"
    test_start_date   = "2023-01-01"
    test_end_date     = "2023-12-31"
    test_status       = "Approved"

    mock_get_user_context_func.return_value = mock_get_user_context_helper(
        "Finance", test_company_id
    )

    mock_conn   = MagicMock()
    mock_cursor = MagicMock(spec=psycopg2.extras.DictCursor)
    
    mock_get_db_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Setup the DB to return known values
    income_data          = 1500.0
    gen_exp_data         = 250.0
    pay_exp_data         = 350.0
    tender_counts_data   = [{"status": "Approved", "count": 2}]
    project_count_data   = 1
    setup_mock_db(
        mock_cursor,
        income_data, gen_exp_data, pay_exp_data,
        tender_counts_data, project_count_data
    )

    # Exercise
    response = client.get(
        f'/api/reports/overall-summary'
        f'?start_date={test_start_date}'
        f'&end_date={test_end_date}'
        f'&project_id={test_project_id}'
        f'&status={test_status}'
    )
    
    assert response.status_code == 200

    data = response.get_json()
    assert data["total_income"] == income_data
    assert data["total_general_expenses"] == gen_exp_data
    assert data["total_payroll_expenses"] == pay_exp_data
    assert data["tender_counts"] == tender_counts_data
    assert data["project_count"] == project_count_data

    # Now verify the three filtered sum queries:
    date_filter_sql_part = "company_id = %s AND project_id = %s AND date >= %s AND date <= %s"
    date_params = [test_company_id, test_project_id, test_start_date, test_end_date]

    assert_query_called(
        mock_cursor,
        "FROM income_entries WHERE " + date_filter_sql_part,
        date_params
    )
    assert_query_called(
        mock_cursor,
        "FROM general_expenses WHERE " + date_filter_sql_part,
        date_params
    )
    assert_query_called(
        mock_cursor,
        "FROM payroll_entries WHERE " + date_filter_sql_part,
        date_params
    )

    # Verify the filtered tender‐count query
    tender_filter_sql_part = (
        "t.company_id = %s AND t.project_id = %s AND t.status = %s "
        "AND t.start_date >= %s AND t.end_date <= %s"
    )
    tender_params = [
        test_company_id, test_project_id,
        test_status, test_start_date, test_end_date
    ]
    assert_query_called(
        mock_cursor,
        "SELECT t.status, COUNT(*) AS count FROM tenders t WHERE " + tender_filter_sql_part,
        tender_params
    )

    # Verify the filtered project count query
    proj_filter_sql_part = "company_id = %s AND id = %s"
    proj_params          = [test_company_id, test_project_id]
    assert_query_called(
        mock_cursor,
        "SELECT COUNT(*) AS project_count FROM projects WHERE " + proj_filter_sql_part,
        proj_params
    )

    # Cleanup
    mock_cursor.close.assert_called()
    mock_conn.close.assert_called()


@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_overall_summary_report_no_data_found(
    mock_get_db_conn, mock_get_user_context_func, client
):
    """
    Test the overall_summary_report API endpoint when no data is found for any query.
    COALESCE should ensure 0.0 for sums and empty list for tender counts.
    """
    test_company_id = "comp123"
    mock_get_user_context_func.return_value = mock_get_user_context_helper("Admin", test_company_id)

    mock_conn = MagicMock()
    mock_cursor = MagicMock(spec=psycopg2.extras.DictCursor)
    mock_get_db_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    income_data = 0.0
    gen_exp_data = 0.0
    pay_exp_data = 0.0
    tender_counts_data = []
    project_count_data = 0

    setup_mock_db(mock_cursor, income_data, gen_exp_data, pay_exp_data, tender_counts_data, project_count_data)

    response = client.get('/api/reports/overall-summary')

    assert response.status_code == 200
    data = response.get_json()
    assert data["total_income"] == 0.0
    assert data["total_general_expenses"] == 0.0
    assert data["total_payroll_expenses"] == 0.0
    assert data["tender_counts"] == []
    assert data["project_count"] == 0

    mock_cursor.close.assert_called()
    mock_conn.close.assert_called()


@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_overall_summary_report_insufficient_permissions(
    mock_get_db_conn, mock_get_user_context_func, client
):
    """
    Test the overall_summary_report API endpoint when the user has insufficient permissions.
    """
    
    mock_get_user_context_func.return_value = mock_get_user_context_helper("Staff", "comp123")
    
    response = client.get('/api/reports/overall-summary')

    # Assertion
    assert response.status_code == 403
    assert response.get_json() == {"error": "Access denied: insufficient permissions"}
    mock_get_db_conn.assert_not_called() # Ensure no DB connection is made


@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_overall_summary_report_missing_company_id(
    mock_get_db_conn, mock_get_user_context_func, client
):
    """
    Test the overall_summary_report API endpoint when company_id is missing from user context.
    """

    mock_get_user_context_func.return_value = mock_get_user_context_helper("Admin", None)
    
    response = client.get('/api/reports/overall-summary')

    # Assertion
    assert response.status_code == 400
    assert response.get_json() == {"error": "company_id is required in context"}
    mock_get_db_conn.assert_not_called()


@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_overall_summary_report_db_connection_error(
    mock_get_db_conn, mock_get_user_context_func, client
):
    """
    Test the overall_summary_report API endpoint when a database connection error occurs.
    """
    
    test_company_id = "comp123"
    mock_get_user_context_func.return_value = mock_get_user_context_helper("Admin", test_company_id)
    mock_get_db_conn.side_effect = Exception("DB Connection Failed")
    
    response = client.get('/api/reports/overall-summary')

    # Assertion
    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
    mock_get_db_conn.assert_called_once()


@patch('reporting_module.api.get_user_context')
@patch('reporting_module.api.get_db_postgres_connection')
def test_overall_summary_report_db_query_error(
    mock_get_db_conn, mock_get_user_context_func, client
):
    """
    Test the overall_summary_report API endpoint when a database query error occurs.
    """
    
    test_company_id = "comp123"
    mock_get_user_context_func.return_value = mock_get_user_context_helper("Admin", test_company_id)

    mock_conn = MagicMock()
    mock_cursor = MagicMock(spec=psycopg2.extras.DictCursor)
    mock_get_db_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Simulate an error on the first execute call (income query)
    mock_cursor.execute.side_effect = Exception("Database Query Error")
    
    response = client.get('/api/reports/overall-summary')

    # Assertion
    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
    mock_cursor.execute.assert_called_once() # Only the first query should have been attempted
    mock_cursor.close.assert_called_once() # Cursor should still be closed
    mock_conn.close.assert_called_once() # Connection should still be closed