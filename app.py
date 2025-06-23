from flask import Flask, request, jsonify
from flask_cors import CORS
import random, smtplib, json
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()
import os
import json
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

CORS(app)

org_email = os.getenv("EMAIL")
org_app_pass = os.getenv("PASS")
creds_json = os.getenv("GOOGLE_CRED")
if not creds_json:
    raise Exception("GOOGLE_CRED not loaded")

service_account_info = json.loads(creds_json)

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
client = gspread.authorize(credentials)

sheet = client.open_by_key('1JtYtzxObTCawJejMX0yxtDjOGiAN3bk2hnv-OA9vDX8').worksheet("Sheet2")

def verify_otp_in_sheet(email, otp):
    email = email.strip().lower()
    otp = otp.strip()

    records = sheet.get_all_records()
    for i, row in enumerate(records):
        sheet_email = str(row["Email"]).strip().lower()
        sheet_otp = str(row["OTP"]).strip()

        if sheet_email == email and sheet_otp == otp:
            sheet.update_cell(i + 2, 3, "Verified")
            return True
    return False

def store_otp(email, otp):
    records = sheet.get_all_records()
    for i, row in enumerate(records):
        if row["Email"] == email:
            sheet.update_cell(i + 2, 2, otp)         
            sheet.update_cell(i + 2, 3, "Not Verified")  
            return
    sheet.append_row([email, otp, "Not Verified"])

def send_otp_email(to_email, otp):
    from_email = org_email
    password = org_app_pass

    email_body = f"""
Dear User,

Your One-Time Password (OTP) for secure verification is:

    {otp}

Please enter this OTP within the next 10 minutes to complete your login.

If you did not request this, please ignore this email or contact our support team immediately.

Thank you for choosing 49funded.

Best regards,  

The 49funded Security Team
"""

    msg = MIMEText(email_body)
    msg["Subject"] = "Your Secure Verification OTP - from 49funded"
    msg["From"] = from_email
    msg["To"] = to_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(from_email, password)
    server.sendmail(from_email, to_email, msg.as_string())
    server.quit()

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"error": "Email is required"}), 400

    otp = str(random.randint(100000, 999999))
    store_otp(email, otp)
    send_otp_email(email, otp)

    return jsonify({"message": "OTP sent successfully"})

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        otp = data.get("otp", "").strip()

        if not email or not otp:
            return jsonify({"error": "Missing email or OTP"}), 400

        if verify_otp_in_sheet(email, otp):
            return jsonify({"message": "OTP verified successfully"})
        else:
            return jsonify({"error": "Invalid OTP"}), 400

    except Exception as e:
        print("Server error:", e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
