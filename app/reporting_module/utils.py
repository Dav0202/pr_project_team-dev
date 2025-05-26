import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from flask import Response, jsonify
import csv
from datetime import datetime

#My solutions

def export_report_data(data, export_format, filename='report'):
    """
    Exports a list of dictionaries to CSV or PDF format.

    Args:
        data (list): A list of dictionaries, where each dictionary is a row.
                     All dictionaries are expected to have the same keys.
        export_format (str): The desired export format ('csv' or 'pdf').
        filename (str): The base name for the exported file (without extension).

    Returns:
        flask.Response: A Flask Response object containing the file data,
                        or a JSON response for unsupported formats.
    """
    if not export_format:
        return jsonify(data)

    # Normalize a single dict into a list
    if isinstance(data, dict):
        data = [data]

    # Now data must be a list of dicts
    if not isinstance(data, list):
        return jsonify({"error": "Data must be a list of dictionaries"}), 400

    if any(not isinstance(row, dict) for row in data):
        return jsonify({"error": "All items in data must be dictionaries"}), 400

    # Extract headers
    headers = list(data[0].keys()) if data else []

    if export_format == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename={filename}.csv'
        return response

    elif export_format == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Add a title
        title_style = styles['h1']
        story.append(Paragraph(filename.replace('_', ' ').title(), title_style))
        story.append(Spacer(1, 0.25 * inch))

        # Prepare data for the table
        # Add headers as the first row
        pdf_data = [headers]
        for row in data:
            # Ensure all values are strings for PDF table
            pdf_data.append([str(row.get(header, '')) for header in headers]) # Use .get for safety
            
        print(pdf_data)

        coll_width = (letter[0] - 2*inch) / len(headers)
        colWidths = [coll_width] * len(headers)
        # Create the table
        table = Table(pdf_data, colWidths=colWidths)

        # Add style to the table
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('WORDWRAP', (0, 1), (-1, -1), True),
        ])

        table.setStyle(style)
        story.append(table)

        try:
            doc.build(story)
        except Exception as e:
            print(f"Error building PDF: {e}")
            return jsonify({"error": "Could not generate PDF"}), 500

        buffer.seek(0)
        return Response(buffer, mimetype='application/pdf',
                        headers={"Content-Disposition": f"attachment;filename={filename}.pdf"})

    else:
        return jsonify(data)
    


def validate_dates(start_date_str, end_date_str):
    """
    Validates if the provided start and end date strings are valid dates.
    Dates are optional, so if they don't exist, the function passes.

    Args:
        start_date_str (str): The start date string, e.g., '2023-01-01'. Can be None.
        end_date_str (str): The end date string, e.g., '2023-12-31'. Can be None.

    Returns:
        tuple: A tuple containing:
            - bool: True if dates are valid or not provided, False otherwise.
            - str: An error message if dates are invalid, None otherwise.
            - str: validated start_date, None otherwise.
            - str: validated end_date, None otherwise.
    """
    start_date = None
    end_date = None

    if start_date_str:
        try:
            #start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date = start_date_str
        except ValueError:
            return False, {"error": "Invalid date format. Please use YYYY-MM-DD."}, None, None

    if end_date_str:
        try:
            #end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date_str
        except ValueError:
            return False, {"error": "Invalid date format. Please use YYYY-MM-DD."}, None, None

    #if start_date and end_date and start_date > end_date:
    #    return False, {"error": "Start date cannot be after end date."}, None, None

    return True, None, start_date, end_date

def build_tender_status_query(company_id, start_date=None, end_date=None, project_id=None, status=None):
            """
            Returns (sql, params) for the tender-status report.
            """
            where = ["t.company_id = %s"]
            params = [company_id]

            if start_date:
                where.append("t.start_date >= %s")
                params.append(start_date)
            if end_date:
                where.append("t.end_date <= %s")
                params.append(end_date)
            if project_id:
                where.append("t.project_id = %s")
                params.append(project_id)
            if status:
                where.append("t.status = %s")
                params.append(status)

            where_sql = " AND ".join(where)

            sql = f"""
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
                WHERE {where_sql}
                ORDER BY t.start_date DESC
            """
            return sql, params