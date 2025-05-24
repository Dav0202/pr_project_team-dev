import pytest
from unittest.mock import patch, MagicMock
from app import app
import psycopg2.extras
import psycopg2
from datetime import date
from reporting_module.utils import build_tender_status_query

@pytest.fixture
def client():
    """Fixture for Flask test client."""
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
    # Configure cursor to return DictCursor-like objects for fetchall
    mock_cursor.cursor_factory = psycopg2.extras.DictCursor
    mock_db_conn_func.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    if fetchone_side_effect is not None:
        # fetchone is called multiple times, configure side_effect with a list
        mock_cursor.fetchone.side_effect = fetchone_side_effect
    if fetchall_side_effect is not None:
        # fetchall is called once for the main tender query
        mock_cursor.fetchall.side_effect = fetchall_side_effect

    return mock_conn, mock_cursor

# --- Test Cases ---

@pytest.mark.parametrize("inputs, expected", [
    # no filters
    (
        {"company_id": "1"},
        (
            """
            SELECT
                t.id AS tender_id,
                t.status,
                t.start_date,
                t.end_date,
                p.id AS project_id,
                p.name AS project_name,
                p.description AS project_description
            FROM tenders t
            JOIN projects p 
                ON p.id = t.project_id AND p.company_id = t.company_id
            WHERE t.company_id = %s
            ORDER BY t.start_date DESC
            """,
            ["1"]
        )
    ),
    (
        {
            "company_id": "2",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "project_id": 5,
            "status": "Pending"
        },
        (
            """
            SELECT
                t.id AS tender_id,
                t.status,
                t.start_date,
                t.end_date,
                p.id AS project_id,
                p.name AS project_name,
                p.description AS project_description
            FROM tenders t
            JOIN projects p 
                ON p.id = t.project_id AND p.company_id = t.company_id
            WHERE t.company_id = %s AND t.start_date >= %s AND t.end_date <= %s AND t.project_id = %s AND t.status = %s
            ORDER BY t.start_date DESC
            """,
            ["2", "2024-01-01", "2024-06-30", 5, "Pending"]
        )
    ),

    (
        {"company_id": "3", "status": "Completed"},
        (
            """
            SELECT
                t.id AS tender_id,
                t.status,
                t.start_date,
                t.end_date,
                p.id AS project_id,
                p.name AS project_name,
                p.description AS project_description
            FROM tenders t
            JOIN projects p 
                ON p.id = t.project_id AND p.company_id = t.company_id
            WHERE t.company_id = %s AND t.status = %s
            ORDER BY t.start_date DESC
            """,
            ["3", "Completed"]
        )
    )
])
def test_build_tender_status_query(inputs, expected):
    raw_sql, params = build_tender_status_query(**inputs)
    def norm(s: str) -> str:
        return "\n".join(line.strip() for line in s.strip().splitlines())

    expected_sql, expected_params = expected
    assert norm(raw_sql) == norm(expected_sql)
    assert params == expected_params


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_success_no_filters(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval of tender status report without filters."""
    mock_tenders_data = [
        {'tender_id': 1, 'status': 'Open', 'start_date': date(2024, 1, 1), 'end_date': date(2024, 3, 31),
         'project_id': 101, 'project_name': 'Project X', 'project_description': 'Desc X'},
        {'tender_id': 2, 'status': 'Closed', 'start_date': date(2023, 10, 1), 'end_date': date(2023, 12, 31),
         'project_id': 102, 'project_name': 'Project Y', 'project_description': 'Desc Y'}
    ]

    # Side effect for fetchone calls (general_expenses, payroll_entries, income_entries for each tender)
    mock_fetchone_data = [
        # Data for Tender 1 (Project 101)
        (1000.0,), # general_expenses
        (500.0,),  # payroll_entries
        (15000.0,), # income_entries
        # Data for Tender 2 (Project 102)
        (2000.0,), # general_expenses
        (1000.0,),  # payroll_entries
        (8000.0,), # income_entries
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_tenders_data] # First fetchall for tenders
    )

    response = client.get('/api/reports/tender-status')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 2

    # Assertions for Tender 1
    tender1_data = next((item for item in data if item['tender_id'] == 1), None)
    assert tender1_data is not None
    assert tender1_data['status'] == 'Open'
    assert tender1_data['start_date'] == '2024-01-01'
    assert tender1_data['end_date'] == '2024-03-31'
    assert tender1_data['project_id'] == 101
    assert tender1_data['project_name'] == 'Project X'
    assert tender1_data['project_description'] == 'Desc X'
    assert tender1_data['general_expenses_incurred']['amount'] == 1000.0
    assert tender1_data['payroll_expenses_incurred']['amount'] == 500.0
    assert tender1_data['total_income']['amount'] == 15000.0

    # Assertions for Tender 2
    tender2_data = next((item for item in data if item['tender_id'] == 2), None)
    assert tender2_data is not None
    assert tender2_data['status'] == 'Closed'
    assert tender2_data['start_date'] == '2023-10-01'
    assert tender2_data['end_date'] == '2023-12-31'
    assert tender2_data['project_id'] == 102
    assert tender2_data['project_name'] == 'Project Y'
    assert tender2_data['project_description'] == 'Desc Y'
    assert tender2_data['general_expenses_incurred']['amount'] == 2000.0
    assert tender2_data['payroll_expenses_incurred']['amount'] == 1000.0
    assert tender2_data['total_income']['amount'] == 8000.0


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Finance', company_id='2'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_success_with_all_filters(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval with start_date, end_date, project_id, and status filters."""
    mock_tenders_data = [
        {'tender_id': 3, 'status': 'Pending', 'start_date': date(2024, 4, 1), 'end_date': date(2024, 6, 30),
         'project_id': 201, 'project_name': 'Project Z', 'project_description': 'Desc Z'}
    ]

    mock_fetchone_data = [
        (500.0,),  # general_expenses
        (200.0,),  # payroll_entries
        (10000.0,), # income_entries
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_tenders_data]
    )

    response = client.get('/api/reports/tender-status?start_date=2024-04-01&end_date=2024-06-30&project_id=201&status=Pending')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['tender_id'] == 3
    assert data[0]['status'] == 'Pending'
    assert data[0]['start_date'] == '2024-04-01'
    assert data[0]['end_date'] == '2024-06-30'
    assert data[0]['project_id'] == 201
    assert data[0]['project_name'] == 'Project Z'
    assert data[0]['general_expenses_incurred']['amount'] == 500.0
    assert data[0]['payroll_expenses_incurred']['amount'] == 200.0
    assert data[0]['total_income']['amount'] == 10000.0


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='HR', company_id='3'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_success_date_filters_only(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval with only start_date and end_date filters."""
    mock_tenders_data = [
        {'tender_id': 4, 'status': 'Open', 'start_date': date(2023, 7, 1), 'end_date': date(2023, 9, 30),
         'project_id': 301, 'project_name': 'Project A', 'project_description': 'Desc A'},
        {'tender_id': 5, 'status': 'Closed', 'start_date': date(2023, 10, 1), 'end_date': date(2023, 12, 31),
         'project_id': 302, 'project_name': 'Project B', 'project_description': 'Desc B'}
    ]

    mock_fetchone_data = [
        # Data for Tender 4 (Project 301)
        (100.0,), # general_expenses
        (50.0,),  # payroll_entries
        (5000.0,), # income_entries
        # Data for Tender 5 (Project 302)
        (200.0,), # general_expenses
        (100.0,),  # payroll_entries
        (6000.0,), # income_entries
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_tenders_data]
    )

    response = client.get('/api/reports/tender-status?start_date=2023-07-01&end_date=2023-12-31')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 2



@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='4'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_success_project_id_filter_only(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval with only project_id filter."""
    mock_tenders_data = [
        {'tender_id': 6, 'status': 'Awarded', 'start_date': date(2024, 1, 15), 'end_date': date(2024, 7, 31),
         'project_id': 401, 'project_name': 'Project C', 'project_description': 'Desc C'}
    ]

    mock_fetchone_data = [
        (3000.0,), # general_expenses
        (1500.0,), # payroll_entries
        (25000.0,), # income_entries
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_tenders_data]
    )

    response = client.get('/api/reports/tender-status?project_id=401')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['tender_id'] == 6
    assert data[0]['project_id'] == 401


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Finance', company_id='5'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_success_status_filter_only(mock_db_conn, mock_user_context, client):
    """Tests successful retrieval with only status filter."""
    mock_tenders_data = [
        {'tender_id': 7, 'status': 'Completed', 'start_date': date(2023, 1, 1), 'end_date': date(2023, 6, 30),
         'project_id': 501, 'project_name': 'Project D', 'project_description': 'Desc D'},
        {'tender_id': 8, 'status': 'Completed', 'start_date': date(2023, 7, 1), 'end_date': date(2023, 12, 31),
         'project_id': 502, 'project_name': 'Project E', 'project_description': 'Desc E'}
    ]

    mock_fetchone_data = [
        # Data for Tender 7 (Project 501)
        (500.0,), # general_expenses
        (200.0,), # payroll_entries
        (10000.0,), # income_entries
        # Data for Tender 8 (Project 502)
        (600.0,), # general_expenses
        (300.0,), # payroll_entries
        (12000.0,), # income_entries
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_tenders_data]
    )

    response = client.get('/api/reports/tender-status?status=Completed')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 2
    assert all(item['status'] == 'Completed' for item in data)


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='6'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_no_tenders_found(mock_db_conn, mock_user_context, client):
    """Tests the case where no tenders are found for the given company/filters."""
    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchall_side_effect=[[]] # Return empty list for tenders
    )

    response = client.get('/api/reports/tender-status?status=NonExistent')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 0 # Expect an empty list


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Finance', company_id='7'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_tender_no_financial_data(mock_db_conn, mock_user_context, client):
    """Tests the case where tenders are found but have no associated financial data."""
    mock_tenders_data = [
        {'tender_id': 9, 'status': 'Open', 'start_date': date(2024, 5, 1), 'end_date': date(2024, 8, 31),
         'project_id': 701, 'project_name': 'Project F', 'project_description': 'Desc F'}
    ]

    mock_fetchone_data = [
        (0.0,), # general_expenses
        (0.0,), # payroll_entries
        (0.0,), # income_entries
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchone_side_effect=mock_fetchone_data,
        fetchall_side_effect=[mock_tenders_data]
    )

    response = client.get('/api/reports/tender-status')

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['tender_id'] == 9
    assert data[0]['project_id'] == 701
    assert data[0]['general_expenses_incurred']['amount'] == 0.0
    assert data[0]['payroll_expenses_incurred']['amount'] == 0.0
    assert data[0]['total_income']['amount'] == 0.0



@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Staff', company_id='1'))
def test_tender_status_report_unauthorized(mock_user_context, client):
    """Tests that a user with an unauthorized role receives a 403."""

    response = client.get('/api/reports/tender-status')

    assert response.status_code == 403
    assert response.get_json() == {"error": "Access denied: insufficient permissions"}


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id=None))
def test_tender_status_report_missing_company_id(mock_user_context, client):
    """Tests that a request with missing company_id in context receives a 400."""

    response = client.get('/api/reports/tender-status')

    assert response.status_code == 400
    assert response.get_json() == {"error": "company_id is required in context"}

@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_invalid_date_format(mock_db_conn, mock_user_context, client):
    """Tests handling of invalid date format in query parameters."""

    # We only need to mock the DB connection setup, the error should happen before DB query
    mock_conn, mock_cursor = setup_mock_db(mock_db_conn)

    response = client.get('/api/reports/tender-status?start_date=not-a-date&end_date=2024-12-31')

    assert response.status_code == 400 # Flask catches the ValueError from date parsing
    assert response.get_json() == {"error": "Invalid date format. Please use YYYY-MM-DD."}

    assert mock_cursor.execute.call_count == 0 # No DB query should be attempted


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_invalid_project_id_format(mock_db_conn, mock_user_context, client):
    """Tests handling of invalid project_id format in query parameters."""
    # The route doesn't explicitly cast project_id to int before passing to DB-API,
    # so the error might occur during DB execution if the driver is strict.
    # However, the test structure should still catch the resulting 500.

    mock_conn, mock_cursor = setup_mock_db(mock_db_conn)
    # Simulate a DB error if the invalid project_id is used in a query expecting integer
    mock_cursor.execute.side_effect = psycopg2.DataError("invalid input syntax for integer")


    response = client.get('/api/reports/tender-status?project_id=not-a-number')

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}

    mock_db_conn.assert_called_once()
    # The first execute call to fetch tenders will happen
    assert mock_cursor.execute.call_count >= 1


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection', side_effect=psycopg2.OperationalError("Database connection failed"))
def test_tender_status_report_db_connection_error(mock_db_conn, mock_user_context, client):
    """Tests handling of a database connection error."""
    response = client.get('/api/reports/tender-status')

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}

    mock_db_conn.assert_called_once()


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_db_query_error_tenders(mock_db_conn, mock_user_context, client):
    """Tests handling of an error during the main tenders database query."""
    mock_conn, mock_cursor = setup_mock_db(mock_db_conn)
    mock_cursor.execute.side_effect = psycopg2.ProgrammingError("Invalid query syntax for tenders")

    response = client.get('/api/reports/tender-status')

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}

    mock_db_conn.assert_called_once()
    mock_cursor.execute.assert_called_once() # Verify the first execute was called


@patch('reporting_module.api.get_user_context', side_effect=lambda: mock_get_user_context(role='Admin', company_id='1'))
@patch('reporting_module.api.get_db_postgres_connection')
def test_tender_status_report_db_query_error_financial(mock_db_conn, mock_user_context, client):
    """Tests handling of an error during one of the financial data queries."""
    mock_tenders_data = [
        {'tender_id': 10, 'status': 'Open', 'start_date': date(2024, 1, 1), 'end_date': date(2024, 3, 31),
         'project_id': 1001, 'project_name': 'Project G', 'project_description': 'Desc G'}
    ]

    mock_conn, mock_cursor = setup_mock_db(
        mock_db_conn,
        fetchall_side_effect=[mock_tenders_data]
    )
    # Make the second execute call (e.g., payroll_entries) raise an error
    mock_cursor.execute.side_effect = [
        None, # First execute for tenders succeeds
        None, # Second execute for general_expenses succeeds
        psycopg2.ProgrammingError("Invalid query syntax for payroll"), # Error here
    ]
    mock_cursor.fetchone.return_value = (0.0,) # Provide a default return for successful fetchone calls


    response = client.get('/api/reports/tender-status')

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}

    mock_db_conn.assert_called_once()
    # Verify execute was called at least up to the point of the error
    assert mock_cursor.execute.call_count >= 3
