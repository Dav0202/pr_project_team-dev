import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import os
import google.generativeai as genai
import functools
from reporting_module import api

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
def gemini_request(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error using gemini api: {e}")
        return "There was an error while processing your request."
    

load_dotenv()   

app = Flask(__name__)

app.register_blueprint(api.report_module_api, url_prefix= '/api')

def get_db_connection():
    conn = sqlite3.connect('app/projects.db')
    conn.row_factory = sqlite3.Row
    return conn

# Add this cache to avoid repeated API calls
exchange_rate_cache = {}

@functools.lru_cache(maxsize=32)
def get_exchange_rate_cached(from_currency, to_currency='PLN'):
    """Cached version of get_exchange_rate to reduce API calls"""
    cache_key = f"{from_currency}_{to_currency}"
    
    # Check if we have a cached value less than 1 day old
    if cache_key in exchange_rate_cache:
        cached_time, rate = exchange_rate_cache[cache_key]
        if datetime.now() - cached_time < timedelta(days=1):
            return rate
    
    # If not in cache or too old, get a fresh rate
    try:
        if from_currency == to_currency:
            rate = 1.0
        else:
            response = requests.get(f'https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}', 
                                   timeout=5)  # Add timeout
            response.raise_for_status()
            data = response.json()
            rate = data['rates'][to_currency]
        
        # Cache the result
        exchange_rate_cache[cache_key] = (datetime.now(), rate)
        return rate
    except requests.exceptions.RequestException as e:
        print(f"Error fetching exchange rate: {e}")
        # Return last cached value if available
        if cache_key in exchange_rate_cache:
            print(f"Using cached exchange rate for {cache_key}")
            return exchange_rate_cache[cache_key][1]
        return 1.0  # Default fallback

def get_exchange_rate(from_currency, to_currency='PLN'):
    if from_currency == to_currency:
        return 1.0
    try:
         response = requests.get(f'https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}')
         response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
         data = response.json()
         return data['rates'][to_currency]
    except requests.exceptions.RequestException as e:
         print(f"Error fetching exchange rate: {e}")
         return 1.0 # Return a default rate of 1 if API fails

def convert_to_pln(amount, currency):
    return float(amount) * get_exchange_rate_cached(currency)


def check_and_update_schema():
    conn = get_db_connection()
    
    # Check if the role column exists in the users table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'role' not in columns:
        print("Adding 'role' column to users table")
        try:
            # Add the role column to the users table
            conn.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "User"')
            conn.commit()
            print("Role column added successfully")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Error: {e}")
    
    conn.close()


@app.route('/api/project-dashboard-data')
def project_dashboard_data():
    try:
        conn = get_db_connection()
        
        # Check if we can access the database
        try:
            # Fetch projects data
            projects = conn.execute('SELECT * FROM projects').fetchall()
        except sqlite3.Error as e:
            print(f"Database error when fetching projects: {e}")
            return jsonify({"error": "Database error when fetching projects"}), 500
        
        # Prepare response data
        dashboard_data = []
        
        for project in projects:
            try:
                # Get project incomes
                incomes = conn.execute('SELECT SUM(amount) as total FROM income WHERE project_id = ?', 
                                     (project['id'],)).fetchone()
                total_income = incomes['total'] if incomes['total'] else 0
                
                # Get project expenses
                expenses = conn.execute('SELECT SUM(amount) as total FROM expenses WHERE project_id = ?', 
                                      (project['id'],)).fetchone()
                total_expenses = expenses['total'] if expenses['total'] else 0
                
                # Get project tasks for completion calculation
                tasks = conn.execute('SELECT COUNT(*) as total, SUM(CASE WHEN status = "Completed" THEN 1 ELSE 0 END) as completed FROM tasks WHERE project_id = ?',
                                   (project['id'],)).fetchone()
                
                # Calculate completion percentage
                completion_percentage = 0
                if tasks['total'] and tasks['total'] > 0:
                    completion_percentage = round((tasks['completed'] / tasks['total']) * 100)
                
                # Determine status based on dates and completion
                status = "Not Started"
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                if completion_percentage == 100:
                    status = "Completed"
                elif current_date >= project['start_date']:
                    status = "In Progress"
                
                # Use the cached version for better performance
                income_pln = float(total_income) * get_exchange_rate_cached('USD')
                expenses_pln = float(total_expenses) * get_exchange_rate_cached('USD')
                
                # Add project to dashboard data
                dashboard_data.append({
                    'project_id': project['id'],
                    'name': project['name'],
                    'description': project['description'],
                    'start_date': project['start_date'],
                    'end_date': project['end_date'],
                    'status': status,
                    'income': income_pln,
                    'expenses': expenses_pln,
                    'profit': income_pln - expenses_pln,
                    'completion': completion_percentage
                })
                
            except Exception as e:
                print(f"Error processing project {project['id']}: {e}")
                # Continue to next project instead of failing completely
                continue
        
        conn.close()
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        print(f"Unhandled error in project_dashboard_data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/dashboard-data')
def dashboard_data():
    conn = get_db_connection()
    
    # Get projects data
    projects = conn.execute('SELECT * FROM projects').fetchall()
    total_income = 0
    total_expenses = 0
    monthly_data = {}
    upcoming_payments = []
    
    for project in projects:
        # Calculate income
        incomes = conn.execute('SELECT * FROM income WHERE project_id = ?', 
                             (project['id'],)).fetchall()
        for income in incomes:
            amount_pln = convert_to_pln(income['amount'], income['currency'])
            total_income += amount_pln
            month_key = datetime.strptime(income['date'], '%Y-%m-%d').strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'income': 0, 'expenses': 0}
            monthly_data[month_key]['income'] += amount_pln
            upcoming_payments.append({
                'type': 'income',
                'project_name': project['name'],
                'date': income['date'],
                'amount': amount_pln,
                'currency': 'PLN'
            })

        # Calculate expenses
        expenses = conn.execute('SELECT * FROM expenses WHERE project_id = ?',
                              (project['id'],)).fetchall()
        for expense in expenses:
            amount_pln = convert_to_pln(expense['amount'], expense['currency'])
            total_expenses += amount_pln
            month_key = datetime.strptime(expense['date'], '%Y-%m-%d').strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'income': 0, 'expenses': 0}
            monthly_data[month_key]['expenses'] += amount_pln
            upcoming_payments.append({
                'type': 'expense',
                'project_name': project['name'],
                'date': expense['date'],
                'amount': amount_pln,
                'currency': 'PLN'
            })

    # Format monthly data for charts
    monthly_chart_data = [
        {
            'month': k,
            'income': round(v['income'], 2),
            'expenses': round(v['expenses'], 2),
            'profit': round(v['income'] - v['expenses'], 2)
        }
        for k, v in sorted(monthly_data.items())
    ]
    
    # Sort upcoming payments by date
    upcoming_payments.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))


    conn.close()

    return jsonify({
        'total_income': round(total_income, 2),
        'total_expenses': round(total_expenses, 2),
        'profit_loss': round(total_income - total_expenses, 2),
        'monthly_data': monthly_chart_data,
        'upcoming_payments': upcoming_payments,
    })

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/reporting_api')
def reporting_api():
    return render_template('reporting-api.html')

@app.route('/projects')
def projects():
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects').fetchall()
    conn.close()
    return render_template('projects.html', projects=projects)


@app.route('/project/<int:project_id>')
def project(project_id):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', 
                         (project_id,)).fetchone()
    incomes = conn.execute('SELECT * FROM income WHERE project_id = ?',
                          (project_id,)).fetchall()
    expenses = conn.execute('SELECT * FROM expenses WHERE project_id = ?',
                          (project_id,)).fetchall()
    conn.close()
    
    total_income = sum(convert_to_pln(i['amount'], i['currency']) 
                      for i in incomes)
    total_expenses = sum(convert_to_pln(e['amount'], e['currency'])
                        for e in expenses)
    
    return render_template('project.html',
                         project=project,
                         incomes=incomes,
                         expenses=expenses,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         profit_loss=total_income - total_expenses)

@app.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO projects (name, description, start_date, end_date) '
                    'VALUES (?, ?, ?, ?)',
                    (name, description, start_date, end_date))
        conn.commit()
        conn.close()
        
        return redirect(url_for('projects'))
    
    return render_template('add_project.html')



@app.route('/project/<int:project_id>/add_income', methods=['GET', 'POST'])
def add_income(project_id):
    if request.method == 'POST':
        type_ = request.form['type']
        date = request.form['date']
        amount = request.form['amount']
        currency = request.form['currency']
        invoice_link = request.form['invoice_link']

        # Generate invoice_id as YYYYMMDD_N
        today = date.replace("-", "")
        conn = get_db_connection()
        result = conn.execute(
            'SELECT COUNT(*) FROM income WHERE date = ? AND project_id = ?',
            (date, project_id)
        ).fetchone()
        invoice_count = result[0] + 1
        invoice_id = f"{today}_{project_id}_{invoice_count}"

        # Insert into the database
        conn.execute(
            'INSERT INTO income (project_id, type, date, amount, currency, invoice_id, invoice_link) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (project_id, type_, date, amount, currency, invoice_id, invoice_link)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('project', project_id=project_id))

    return render_template('add_income_expense.html', action="Income", project_id=project_id)









@app.route('/project/<int:project_id>/delete_income/<int:income_id>', methods=['POST', 'GET'])
def delete_income(project_id, income_id):
    # Connect to the database
    conn = get_db_connection()
    
    
    # Delete the income by its ID
    conn.execute('DELETE FROM income WHERE id = ? AND project_id = ?', (income_id, project_id))
    conn.commit()
    conn.close()
    
    # Redirect back to the project page
    return redirect(url_for('project', project_id=project_id))




@app.route('/project/<int:project_id>/add_expense', methods=['GET', 'POST'])
def add_expense(project_id):
    if request.method == 'POST':
        type_ = request.form['type']
        date = request.form['date']
        amount = request.form['amount']
        currency = request.form['currency']
        invoice_link = request.form['invoice_link']

        # Generate invoice_id as YYYYMMDD_N
        today = date.replace("-", "")
        conn = get_db_connection()
        result = conn.execute(
            'SELECT COUNT(*) FROM expenses WHERE date = ? AND project_id = ?',
            (date, project_id)
        ).fetchone()
        invoice_count = result[0] + 1
        invoice_id = f"{today}_{project_id}_{invoice_count}"

        # Insert into the database
        conn.execute(
            'INSERT INTO expenses (project_id, type, date, amount, currency, invoice_id, invoice_link) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (project_id, type_, date, amount, currency, invoice_id, invoice_link)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('project', project_id=project_id))

    return render_template('add_income_expense.html', action="Expense", project_id=project_id)


@app.route('/project/<int:project_id>/delete_expense/<int:expense_id>', methods=['POST', 'GET'])
def delete_expense_for_project(project_id, expense_id):
    # Connect to the database
    conn = get_db_connection()
    
    # Delete the expense by its ID and project ID
    conn.execute('DELETE FROM expenses WHERE id = ? AND project_id = ?', (expense_id, project_id))
    conn.commit()
    conn.close()
    
    # Redirect back to the project page
    return redirect(url_for('project', project_id=project_id))


@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    conn = get_db_connection()
    
    if request.method == 'POST':
        type_ = request.form['type']
        date = request.form['date']
        amount = request.form['amount']
        currency = request.form['currency']
        
        conn.execute('INSERT INTO general_expenses (type, date, amount, currency) '
                     'VALUES (?, ?, ?, ?)',
                    (type_, date, amount, currency))
        conn.commit()

    expenses = conn.execute('SELECT * FROM general_expenses').fetchall()
    total_expenses = sum(convert_to_pln(expense['amount'], expense['currency'])
                            for expense in expenses)

    conn.close()
    
    return render_template('expenses.html', expenses=expenses, total_expenses=total_expenses)


@app.route('/api/unified-data')
def unified_data():
    conn = get_db_connection()
    
    # Fetch all project data
    projects = conn.execute('SELECT id, name FROM projects').fetchall()
    project_map = {project['id']: project['name'] for project in projects}

    # Fetch all income data
    income_data = conn.execute('SELECT id, project_id, type, date, amount, currency FROM income').fetchall()
    formatted_income = [{
        'id': i['id'],
        'date': i['date'],
        'project_name': project_map.get(i['project_id'], 'N/A'),
        'type': i['type'],
        'amount': convert_to_pln(i['amount'], i['currency']),
        'currency': 'PLN',
         'source': 'income'
    } for i in income_data]

    # Fetch all expenses data
    expense_data = conn.execute('SELECT id, project_id, type, date, amount, currency FROM expenses').fetchall()
    formatted_expenses = [{
        'id': e['id'],
        'date': e['date'],
        'project_name': project_map.get(e['project_id'], 'N/A'),
        'type': e['type'],
         'amount': convert_to_pln(e['amount'], e['currency']),
         'currency': 'PLN',
          'source': 'expense'
    } for e in expense_data]

    # Fetch all general expenses data
    general_expense_data = conn.execute('SELECT id, type, date, amount, currency FROM general_expenses').fetchall()
    formatted_general_expenses = [{
        'id': ge['id'],
        'date': ge['date'],
        'project_name': 'General Expense',
        'type': ge['type'],
       'amount': convert_to_pln(ge['amount'], ge['currency']),
       'currency': 'PLN',
        'source': 'general_expense'
    } for ge in general_expense_data]

    combined_data = formatted_income + formatted_expenses + formatted_general_expenses
    
    # Sort by date
    combined_data.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
    
    conn.close()
    
    return jsonify(combined_data)

@app.route('/unified')
def unified():
    return render_template('unified_income_expense.html')
    
@app.route('/api/report-data')
def report_data():
    conn = get_db_connection()

    # Fetch all income data
    income_data = conn.execute('SELECT date, amount, currency, project_id FROM income').fetchall()
    formatted_income = [{
        'date': i['date'],
        'amount': convert_to_pln(i['amount'], i['currency']),
        'project_id': i['project_id'],
    } for i in income_data]
    
    # Fetch all expense data - store as positive numbers
    expense_data = conn.execute('SELECT date, amount, currency, project_id FROM expenses').fetchall()
    formatted_expenses = [{
        'date': e['date'],
        'amount': abs(convert_to_pln(e['amount'], e['currency'])),  # Use abs() to ensure positive
        'project_id': e['project_id'],
    } for e in expense_data]
    
    # Fetch all general expense data - store as positive numbers
    general_expense_data = conn.execute('SELECT date, amount, currency FROM general_expenses').fetchall()
    formatted_general_expenses = [{
        'date': ge['date'],
        'amount': abs(convert_to_pln(ge['amount'], ge['currency'])),  # Use abs() to ensure positive
    } for ge in general_expense_data]
     
    combined_data = formatted_income + formatted_expenses + formatted_general_expenses

    monthly_data = {}
    yearly_data = {}
    
    for item in combined_data:
        date_obj = datetime.strptime(item['date'], '%Y-%m-%d')
        month_key = date_obj.strftime('%Y-%m')
        year_key = date_obj.strftime('%Y')

        amount = item['amount']
        if month_key not in monthly_data:
            monthly_data[month_key] = {'income': 0, 'expenses': 0}
        if year_key not in yearly_data:
            yearly_data[year_key] = {'income': 0, 'expenses': 0}

        # Check if this item is from income or expenses based on the original lists
        is_income = item in formatted_income
        if is_income:
            monthly_data[month_key]['income'] += amount
            yearly_data[year_key]['income'] += amount
        else:
            monthly_data[month_key]['expenses'] += amount
            yearly_data[year_key]['expenses'] += amount

    project_based_data = {}
    for item in formatted_income + formatted_expenses:
        project_id = item['project_id'] if 'project_id' in item else None
        if project_id not in project_based_data:
            project_based_data[project_id] = {'income': 0, 'expenses': 0}
        
        # Check if this item is from income or expenses
        is_income = item in formatted_income
        if is_income:
            project_based_data[project_id]['income'] += item['amount']
        else:
            project_based_data[project_id]['expenses'] += item['amount']

    # Format monthly data for charts
    monthly_chart_data = [
        {
            'month': k,
            'income': round(v['income'], 2),
            'expenses': round(v['expenses'], 2),
            'profit': round(v['income'] - v['expenses'], 2)  # Changed to subtraction
        }
        for k, v in sorted(monthly_data.items())
    ]

    # Format yearly data for charts
    yearly_chart_data = [
        {
            'year': k,
            'income': round(v['income'], 2),
            'expenses': round(v['expenses'], 2),
            'profit': round(v['income'] - v['expenses'], 2)  # Changed to subtraction
        }
        for k, v in sorted(yearly_data.items())
    ]

    project_based_report_data = []
    for k, v in project_based_data.items():
        if k is not None:
            project = conn.execute('SELECT name FROM projects WHERE id = ?', (k,)).fetchone()
            if project:
                project_based_report_data.append({
                    'project_name': project['name'],
                    'income': round(v['income'], 2),
                    'expenses': round(v['expenses'], 2),
                    'profit': round(v['income'] - v['expenses'], 2)  # Changed to subtraction
                })

    # forecasting report data
    today = datetime.today()
    next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    forecasting_data = {}
    for item in combined_data:
        date_obj = datetime.strptime(item['date'], '%Y-%m-%d')
        if date_obj >= today and date_obj < next_month:
            month_key = date_obj.strftime('%Y-%m')
            if month_key not in forecasting_data:
                forecasting_data[month_key] = {'income': 0, 'expenses': 0}
            
            # Check if this item is from income or expenses
            is_income = item in formatted_income
            if is_income:
                forecasting_data[month_key]['income'] += item['amount']
            else:
                forecasting_data[month_key]['expenses'] += item['amount']

    forecast_report = [
        {
            'month': k,
            'income': round(v['income'], 2),
            'expenses': round(v['expenses'], 2),
            'profit': round(v['income'] - v['expenses'], 2)  # Changed to subtraction
        }
        for k, v in sorted(forecasting_data.items())
    ]

    conn.close()

    return jsonify({
        'monthly_data': monthly_chart_data,
        'yearly_data': yearly_chart_data,
        'project_based_data': project_based_report_data,
        'forecast_report': forecast_report,
    })

@app.route('/reporting')
def reporting():
    return render_template('reporting.html')


@app.route('/projects/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('projects'))


@app.route('/expense/<int:expense_id>/delete', methods=['POST'])
def delete_expense(expense_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM general_expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('expenses'))

@app.route('/expense/<int:expense_id>/edit', methods=['GET', 'POST'])
def edit_expense(expense_id):
        conn = get_db_connection()
        expense = conn.execute('SELECT * FROM general_expenses WHERE id = ?', (expense_id,)).fetchone()
        if request.method == 'POST':
            type_ = request.form['type']
            date = request.form['date']
            amount = request.form['amount']
            currency = request.form['currency']
            conn.execute('UPDATE general_expenses SET type = ?, date = ?, amount = ?, currency = ? WHERE id = ?',
                         (type_, date, amount, currency, expense_id))
            conn.commit()
            conn.close()
            return redirect(url_for('expenses'))
        conn.close()
        return render_template('edit_expense.html', expense=expense)


@app.route('/project/<int:project_id>/add_task', methods=['POST'])
def add_task(project_id):
    title = request.form['title']
    description = request.form['description']
    due_date = request.form['due_date']
    assigned_user = request.form['assigned_user']

    conn = get_db_connection()
    conn.execute('INSERT INTO tasks (project_id, title, description, due_date, assigned_user) '
                'VALUES (?, ?, ?, ?, ?)',
                (project_id, title, description, due_date, assigned_user))
    conn.commit()
    conn.close()
    return redirect(url_for('project', project_id=project_id))

@app.route('/task/<int:task_id>/update_status', methods=['POST'])
def update_task_status(task_id):
    status = request.form['status']
    conn = get_db_connection()
    conn.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
    conn.commit()
    task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    conn.close()
    return redirect(url_for('project', project_id=task['project_id']))

@app.route('/api/project-tasks/<int:project_id>')
def get_project_tasks(project_id):
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()
    
    formatted_tasks = [{
        'id': task['id'],
        'title': task['title'],
        'description': task['description'],
        'due_date': task['due_date'],
        'status': task['status'],
        'assigned_user': task['assigned_user'],
    } for task in tasks]
    
    return jsonify(formatted_tasks)


@app.route('/task/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    
    if task: # Check if task is not None
         return redirect(url_for('project', project_id=task['project_id']))
    else:
        return redirect(url_for('projects')) # if no task is found, go to the projects page


@app.route('/users')
def users():
    # First, check and update the schema if needed
    check_and_update_schema()
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('users.html', users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    # First, check and update the schema if needed
    check_and_update_schema()
    
    username = request.form['username']
    role = request.form.get('role', 'User')  # Default to 'User' if not provided
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, role) VALUES (?, ?)', (username, role))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # or handle the duplicate username
    conn.close()
    
    return redirect(url_for('users'))


@app.route('/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('users'))

# New route to get user data for editing
@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT id, username, role FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'role': user['role'] if user['role'] else 'User'
        })
    else:
        return jsonify({'error': 'User not found'}), 404

# New route to update user information
@app.route('/user/<int:user_id>/edit', methods=['POST'])
def edit_user(user_id):
    username = request.form['username']
    role = request.form.get('role', 'User')  # Default to 'User' if not provided
    
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET username = ?, role = ? WHERE id = ?', 
                    (username, role, user_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Username already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users')
def get_users():
    # First, check and update the schema if needed
    check_and_update_schema()
    
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role FROM users').fetchall()
    conn.close()
    
    formatted_users = [{
        'id': user['id'],
        'username': user['username'],
        'role': user['role'] if user['role'] else 'User'  # Provide default role if NULL
    } for user in users]
    
    return jsonify(formatted_users)


@app.route('/tender-analysis')
def tender_analysis():
    return render_template('tender_analysis.html')

@app.route('/api/analyze-tender', methods=['POST'])
def analyze_tender():
    if request.method == 'POST':
      tender_text = request.form['tender_text']
      if not tender_text:
           return jsonify({"error": "Tender text is required"}), 400
      prompt = f"Analyze the following tender document: {tender_text}"
      analysis = gemini_request(prompt)
      return jsonify({'analysis': analysis})
    return jsonify({'error': 'Invalid method'}), 405

@app.route('/invoices')
def invoices():
    conn = get_db_connection()

    # Query all income and expenses across all projects
    incomes = conn.execute('SELECT * FROM income').fetchall()
    expenses = conn.execute('SELECT * FROM expenses').fetchall()

    # Combine both income and expense data
    all_invoices = []

    for income in incomes:
        # Safely fetch the project name, checking if a project exists for the given project_id
        project = conn.execute('SELECT name FROM projects WHERE id = ?', (income['project_id'],)).fetchone()
        project_name = project['name'] if project else 'Unknown Project'

        # Skip this invoice if project name is "Unknown Project"
        if project_name != 'Unknown Project':
            all_invoices.append({
                'invoice_id': income['invoice_id'],
                'invoice_link': income['invoice_link'],
                'type': 'Income',
                'project_name': project_name,
                'amount': income['amount'],
                'currency': income['currency'],
                'date': income['date']
            })

    for expense in expenses:
        # Safely fetch the project name for expenses
        project = conn.execute('SELECT name FROM projects WHERE id = ?', (expense['project_id'],)).fetchone()
        project_name = project['name'] if project else 'Unknown Project'

        # Skip this invoice if project name is "Unknown Project"
        if project_name != 'Unknown Project':
            all_invoices.append({
                'invoice_id': expense['invoice_id'],
                'invoice_link': expense['invoice_link'],
                'type': 'Expense',
                'project_name': project_name,
                'amount': expense['amount'],
                'currency': expense['currency'],
                'date': expense['date']
            })

    # Sort all invoices by date
    all_invoices.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
    conn.close()

    return render_template('invoices.html', all_invoices=all_invoices)


if __name__ == '__main__':
    app.run(debug=True)