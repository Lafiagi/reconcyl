import csv
from io import StringIO
import json
import os
import requests

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@shared_task
def send_reconciliation_report_email(
    email, report_data, report_content, report_format="json"
):
    """
    Sends the reconciliation report via email with the report attached.
    """
    # Define email subject and sender
    email_subject = "Reconciliation Report Completed"
    sender_email = "reconciliation@reconcyl.ng"

    # Define the email body, using an HTML template with context for missing and discrepancies
    email_body = render_to_string(
        "email/reconciliation_report_email.html",
        {
            "email": email,
            "missing_in_target": report_data.get("missing_in_target"),
            "missing_in_source": report_data.get("missing_in_source"),
            "discrepancies": report_data.get("discrepancies"),
        },
    )

    content_type = "application/json"
    filename = "reconciliation_report.json"
    # Prepare the attachment content type based on report_format
    if report_format == "json":
        content_type = "application/json"
        filename = "reconciliation_report.json"
    elif report_format == "csv":
        content_type = "text/csv"
        filename = "reconciliation_report.csv"
    elif report_format == "html":
        content_type = "text/html"
        filename = "reconciliation_report.html"

    # Send email via Mailgun API
    base_url = os.getenv("MAILGUN_BASE_URL")
    api_key = ("api", os.getenv("MAILGUN_API_KEY"))
    response = requests.post(
        base_url,
        auth=api_key,
        files=[("attachment", (filename, report_content, content_type))],
        data={
            "from": sender_email,
            "to": email,
            "subject": email_subject,
            "html": email_body,
        },
    )
    return response.status_code


@shared_task
def process_reconciliation(source_csv, target_csv, email=None, report_format="json"):
    # Read CSVs into Pandas dataframes
    source_df = pd.read_csv(StringIO(source_csv))
    target_df = pd.read_csv(StringIO(target_csv))

    # Normalize data (case insensitive, trimming spaces)
    source_df.columns = source_df.columns.str.strip().str.lower()
    target_df.columns = target_df.columns.str.strip().str.lower()

    source_df = source_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    target_df = target_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    # Reconciliation logic
    missing_in_target = source_df[~source_df.isin(target_df)].dropna()
    missing_in_source = target_df[~target_df.isin(source_df)].dropna()
    discrepancies = pd.merge(source_df, target_df, how="inner", indicator=False)

    report_data = {
        "missing_in_target": missing_in_target.to_dict(orient="records"),
        "missing_in_source": missing_in_source.to_dict(orient="records"),
        "discrepancies": discrepancies.to_dict(orient="records"),
    }

    if report_format == "csv":
        report = generate_csv_report(report_data)
    elif report_format == "html":
        report = generate_html_report(report_data)
    else:
        report = json.dumps(report_data, indent=4)
    # If email is provided, send the report via email
    if email:
        print(f"the rport format is {report_format}\n\n\n")
        send_reconciliation_report_email.delay(
            email, report_data, report, report_format
        )

    return report_data


def generate_csv_report(report_data):
    """
    Converts report_data into CSV format.
    """
    output = StringIO()
    writer = csv.writer(output)

    # Write missing_in_target section
    writer.writerow(["Missing in Target"])
    if report_data["missing_in_target"]:
        headers = report_data["missing_in_target"][0].keys()
        writer.writerow(headers)
        for row in report_data["missing_in_target"]:
            writer.writerow(row.values())
    else:
        writer.writerow(["No missing records in target"])

    # Write missing_in_source section
    writer.writerow([])
    writer.writerow(["Missing in Source"])
    if report_data["missing_in_source"]:
        headers = report_data["missing_in_source"][0].keys()
        writer.writerow(headers)
        for row in report_data["missing_in_source"]:
            writer.writerow(row.values())
    else:
        writer.writerow(["No missing records in source"])

    # Write discrepancies section
    writer.writerow([])
    writer.writerow(["Discrepancies"])
    if report_data["discrepancies"]:
        headers = report_data["discrepancies"][0].keys()
        writer.writerow(headers)
        for row in report_data["discrepancies"]:
            writer.writerow(row.values())
    else:
        writer.writerow(["No discrepancies found"])

    return output.getvalue()


def generate_html_report(report_data):
    """
    Renders the reconciliation report from the template.
    """
    html_report = render_to_string(
        "email/reconciliation_report.html",  # Path to the template
        {
            "missing_in_target": report_data.get("missing_in_target"),
            "missing_in_source": report_data.get("missing_in_source"),
            "discrepancies": report_data.get("discrepancies"),
        }
    )
    return html_report