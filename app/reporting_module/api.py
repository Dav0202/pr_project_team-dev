from flask import Blueprint, render_template, request, redirect, url_for, jsonify, Response
import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError
from .utils import export_report_data, validate_dates, build_tender_status_query

report_module_api = Blueprint('api', __name__)

# Mock function to simulate user context
def get_user_context():
    return {
        "company_id": request.headers.get("X-Company-ID"),
        "role": request.headers.get("X-User-Role")
    }
    

def get_db_postgres_connection():
    """
    Establishes a new connection to the PostgreSQL database using specific credentials.
    Replace with your actual database credentials.
    This function is used for the initial connection attempt if no connection exists.
    """
    try:
        conn = psycopg2.connect(
            dbname="your_db",
            user="your_user",
            password="your_password",
            host="your_host"
        )
        return conn
    except OperationalError as e:
        return(f"Error establishing primary database connection: {e}")


@report_module_api.route('/reports/income-summary', methods=['GET'])
def income_summary():
    try:
        user = get_user_context()
        role = user["role"]
        company_id = user["company_id"]

        # Enforce role-based access
        if role not in ('Admin', 'Finance', 'HR'):
            return jsonify({"error": "Access denied: insufficient permissions"}), 403

        if not company_id:
            return jsonify({"error": "company_id is required in context"}), 400

        conn = get_db_postgres_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Optional query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        project_id = request.args.get('project_id')
        export = request.args.get('export')

        # Build WHERE clause dynamically
        where_clauses = ["company_id = %s"]
        params = [company_id]

        if project_id:
            where_clauses.append("project_id = %s")
            params.append(project_id)

        if start_date:
            where_clauses.append("date >= %s")
            params.append(start_date)

        if end_date:
            where_clauses.append("date <= %s")
            params.append(end_date)

        where_sql = " AND ".join(where_clauses)

        # Query total income
        cur.execute(
            f"""
            SELECT COALESCE(SUM(amount), 0) AS total_income
            FROM income_entries
            WHERE {where_sql}
            """,
            params
        )
        total_income = cur.fetchone()["total_income"]

        # Query monthly trend
        cur.execute(
            f"""
            SELECT TO_CHAR(date, 'YYYY-MM') AS month,
                   SUM(amount) AS amount
            FROM income_entries
            WHERE {where_sql}
            GROUP BY month
            ORDER BY month
            """,
            params
        )
        trend_rows = cur.fetchall()
        monthly_trend = [
            {"month": row["month"], "amount": float(row["amount"])} for row in trend_rows
        ]

        cur.close()
        conn.close()

        result = {
            "total_income": float(total_income),
            "monthly_trend": monthly_trend
        }
        return export_report_data(result, export, filename="income_summary")

    except Exception as e:
        print(f"Unhandled error in income_summary: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@report_module_api.route('/reports/expense-summary', methods=['GET'])
def expense_summary():
    try:
        user = get_user_context()
        role = user["role"]
        company_id = user["company_id"]

        # Enforce role-based access
        if role not in ('Admin', 'Finance', 'HR'):
            return jsonify({"error": "Access denied: insufficient permissions"}), 403

        if not company_id:
            return jsonify({"error": "company_id is required in context"}), 400

        conn = get_db_postgres_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Optional query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        project_id = request.args.get('project_id')
        export = request.args.get('export')

        # Build WHERE clause
        where_clauses = ["company_id = %s"]
        params = [company_id]

        if project_id:
            where_clauses.append("project_id = %s")
            params.append(project_id)

        if start_date:
            where_clauses.append("date >= %s")
            params.append(start_date)

        if end_date:
            where_clauses.append("date <= %s")
            params.append(end_date)

        where_sql = " AND ".join(where_clauses)

        # Query total expenses
        cur.execute(
            f"""
            SELECT COALESCE(SUM(amount), 0) AS total_expense
            FROM general_expenses
            WHERE {where_sql}
            """,
            params
        )
        
        total_expense = cur.fetchone()["total_expense"]

        # Query monthly trend
        cur.execute(
            f"""
            SELECT TO_CHAR(date, 'YYYY-MM') AS month,
                   SUM(amount) AS amount
            FROM general_expenses
            WHERE {where_sql}
            GROUP BY month
            ORDER BY month
            """,
            params
        )
        trend_rows = cur.fetchall()
        monthly_trend = [
            {"month": row["month"], "amount": float(row["amount"])} for row in trend_rows
        ]

        cur.close()
        conn.close()

        result = {
            "total_expense": float(total_expense),
            "monthly_trend": monthly_trend
        }

        return export_report_data(result, export, filename="expense_summary")

    except Exception as e:
        print(f"Unhandled error in expense_summary: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@report_module_api.route('/reports/project-finance', methods=['GET'])
def project_finance_summary():
    try:
        user = get_user_context()
        role = user["role"]
        company_id = user["company_id"]

        if role not in ('Admin', 'Finance', 'HR'):
            return jsonify({"error": "Access denied: insufficient permissions"}), 403

        if not company_id:
            return jsonify({"error": "company_id is required in context"}), 400

        conn = get_db_postgres_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        project_id = request.args.get('project_id')
        export = request.args.get('export')

        # Base filter clause
        base_filters = ["company_id = %s"]
        base_params = [company_id]

        if project_id:
            base_filters.append("project_id = %s")
            base_params.append(project_id)

        if start_date:
            base_filters.append("date >= %s")
            base_params.append(start_date)

        if end_date:
            base_filters.append("date <= %s")
            base_params.append(end_date)

        filter_sql = " AND ".join(base_filters)

        # Get projects
        if project_id:
            cur.execute(
                "SELECT id, name FROM projects WHERE id = %s AND company_id = %s",
                (project_id, company_id)
            )
        else:
            cur.execute(
                "SELECT id, name FROM projects WHERE company_id = %s",
                (company_id,)
            )
        projects = cur.fetchall()
        if not projects:
            cur.close()
            conn.close()
            return jsonify([])

        result = []

        for project in projects:
            pid = project["id"]
            pname = project["name"]

            # Income
            income_params = base_params.copy()
            cur.execute(
                f"SELECT COALESCE(SUM(amount), 0) AS total_income "
                f"FROM income_entries WHERE {filter_sql} AND project_id = %s",
                income_params + [pid]
            )
            total_income = float(cur.fetchone()["total_income"])

            # Expenses (general + payroll)
            cur.execute(
                f"SELECT COALESCE(SUM(amount), 0) AS general_expense "
                f"FROM general_expenses WHERE {filter_sql} AND project_id = %s",
                income_params + [pid]
            )
            general_expense = float(cur.fetchone()["general_expense"])

            cur.execute(
                f"SELECT COALESCE(SUM(amount), 0) AS payroll_expense "
                f"FROM payroll_entries WHERE {filter_sql} AND project_id = %s",
                income_params + [pid]
            )
            payroll_expense = float(cur.fetchone()["payroll_expense"])

            total_expense = general_expense + payroll_expense
            net = total_income - total_expense

            result.append({
                "project_id": pid,
                "project_name": pname,
                "income": total_income,
                "expenses": total_expense,
                "net": net
            })

        cur.close()
        conn.close()

        return export_report_data(result, export, filename="finance_summary")

    except Exception as e:
        print(f"Unhandled error in project_finance_summary: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@report_module_api.route('/reports/tender-status', methods=['GET'])
def tender_status_report():
    try:
        user = get_user_context()
        role = user["role"]
        company_id = user["company_id"]

        if role not in ('Admin', 'Finance', 'HR'):
            return jsonify({"error": "Access denied: insufficient permissions"}), 403
        if not company_id:
            return jsonify({"error": "company_id is required in context"}), 400
        

        p_start_date = request.args.get('start_date')
        p_end_date = request.args.get('end_date')
        project_id = request.args.get('project_id')
        status = request.args.get('status')
        export = request.args.get('export')
        
        date_is_valid, error_message, start_date, end_date = validate_dates(p_start_date, p_end_date)
        
        if not date_is_valid:
            return jsonify(error_message), 400
        
        conn = get_db_postgres_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        sql, params = build_tender_status_query(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            status=status,
        )
        cur.execute(sql, params)

        tenders = cur.fetchall()
        results = []
        
        if not tenders:
            cur.close()
            conn.close()
            return jsonify([]), 200

        for tender in tenders:
            # Per-project finance aggregation
            pid = tender['project_id']
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM general_expenses 
                WHERE company_id = %s AND project_id = %s
            """, (company_id, pid))
            general_exp = float(cur.fetchone()[0])

            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM payroll_entries 
                WHERE company_id = %s AND project_id = %s
            """, (company_id, pid))
            payroll_exp = float(cur.fetchone()[0])

            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM income_entries 
                WHERE company_id = %s AND project_id = %s
            """, (company_id, pid))
            income = float(cur.fetchone()[0])

            results.append({
                "tender_id": tender["tender_id"],
                "status": tender["status"],
                "start_date": str(tender["start_date"]),
                "end_date": str(tender["end_date"]),
                "project_id": tender["project_id"],
                "project_name": tender["project_name"],
                "project_description": tender["project_description"],
                "general_expenses_incurred": {
                    "amount": general_exp
                },
                "payroll_expenses_incurred": {
                    "amount": payroll_exp
                },
                "total_income": {
                    "amount": income
                }
            })

        cur.close()
        conn.close()
        return export_report_data(results, export, filename="tender_status")

    except Exception as e:
        print(f"Unhandled error in tender_status_report: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@report_module_api.route('/reports/overall-summary', methods=['GET'])
def overall_summary_report():
    cur = None
    conn = None
    try:
        user = get_user_context()
        role = user["role"]
        company_id = user["company_id"]

        if role not in ('Admin', 'Finance', 'HR'):
            return jsonify({"error": "Access denied: insufficient permissions"}), 403
        if not company_id:
            return jsonify({"error": "company_id is required in context"}), 400

        p_start_date = request.args.get('start_date')
        p_end_date = request.args.get('end_date')
        project_id = request.args.get('project_id')
        status = request.args.get('status')
        export = request.args.get('export')
        date_is_valid, error_message, start_date, end_date = validate_dates(p_start_date, p_end_date)
        
        if not date_is_valid:
            return jsonify(error_message), 400

        filters = ["company_id = %s"]
        params  = [company_id]

        if project_id:
            filters.append("project_id = %s")
            params.append(project_id)
        if start_date:
            filters.append("date >= %s")
            params.append(start_date)
        if end_date:
            filters.append("date <= %s")
            params.append(end_date)

        date_filter_sql = " AND ".join(filters)

        conn = get_db_postgres_connection()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute(
            f"SELECT COALESCE(SUM(amount),0) AS total_income FROM income_entries WHERE {date_filter_sql}",
            params
        )
        total_income = float(cur.fetchone()["total_income"])

        cur.execute(
            f"SELECT COALESCE(SUM(amount),0) AS total_general_expenses FROM general_expenses WHERE {date_filter_sql}",
            params
        )
        total_gen_exp = float(cur.fetchone()["total_general_expenses"])

        cur.execute(
            f"SELECT COALESCE(SUM(amount),0) AS total_payroll_expenses FROM payroll_entries WHERE {date_filter_sql}",
            params
        )
        total_pay_exp = float(cur.fetchone()["total_payroll_expenses"])

        tender_filters = ["t.company_id = %s"]
        tparams = [company_id]
        if project_id:
            tender_filters.append("t.project_id = %s")
            tparams.append(project_id)
        if status:
            tender_filters.append("t.status = %s")
            tparams.append(status)
        if start_date:
            tender_filters.append("t.start_date >= %s")
            tparams.append(start_date)
        if end_date:
            tender_filters.append("t.end_date <= %s")
            tparams.append(end_date)

        tender_where = " AND ".join(tender_filters)
        cur.execute(
        f"""SELECT t.status, COUNT(*) AS count FROM tenders t WHERE {tender_where} GROUP BY t.status ORDER BY t.status""" ,
            tparams)
        
        tender_counts = [{ "status": row["status"], "count": row["count"] } for row in cur.fetchall()]


        proj_filters = ["company_id = %s"]
        pparams = [company_id]
        if project_id:
            proj_filters.append("id = %s")
            pparams.append(project_id)
        cur.execute(
            f"SELECT COUNT(*) AS project_count FROM projects WHERE {' AND '.join(proj_filters)}",
            pparams
        )
        project_count = cur.fetchone()["project_count"]

        cur.close()
        conn.close()
        
        result = {
            "total_income": total_income,
            "total_general_expenses": total_gen_exp,
            "total_payroll_expenses": total_pay_exp,
            "tender_counts": tender_counts,
            "project_count": project_count
        }
        
        return export_report_data(result, export, "overall-summary")

    except Exception as e:
        print(f"Unhandled error in overall_summary_report: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()