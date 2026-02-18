from flask import Flask, render_template, redirect, url_for, request, flash, abort, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, User, HealthRecord
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "danger")
            return redirect(url_for("register"))

        role = "admin" if email == "admin@gmail.com" else "user"

        user = User(name=name, email=email, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin_dashboard") if user.role == "admin" else url_for("dashboard"))

        flash("Invalid credentials", "danger")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    records = HealthRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(HealthRecord.date.asc()).all()

    latest = records[-1] if records else None
    alerts = []
    health_score = 100

    if latest:
        if latest.systolic > 140:
            alerts.append("⚠️ High Blood Pressure")
            health_score -= 20

        if latest.sugar > 180:
            alerts.append("⚠️ High Sugar Level")
            health_score -= 20

        if latest.water < 1.5:
            alerts.append("⚠️ Low Water Intake")
            health_score -= 10

        if latest.bmi < 18.5:
            alerts.append("⚠️ Underweight BMI")
            health_score -= 15
        elif latest.bmi >= 25:
            alerts.append("⚠️ Overweight BMI")
            health_score -= 15

    health_score = max(0, health_score)

    return render_template(
        "dashboard.html",
        records=records,
        latest=latest,
        alerts=alerts,
        health_score=health_score
    )


# ---------------- ADD RECORD ----------------
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_record():
    if request.method == "POST":
        weight = float(request.form["weight"])
        height = float(request.form["height"])
        bmi = round(weight / (height * height), 2)

        record = HealthRecord(
            weight=weight,
            height=height,
            bmi=bmi,
            systolic=int(request.form["systolic"]),
            diastolic=int(request.form["diastolic"]),
            sugar=float(request.form["sugar"]),
            water=float(request.form["water"]),
            user_id=current_user.id,
            date=datetime.utcnow()
        )

        db.session.add(record)
        db.session.commit()

        flash("Health record added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_record.html")


# ---------------- EDIT RECORD ----------------
@app.route("/edit/<int:record_id>", methods=["GET", "POST"])
@login_required
def edit_record(record_id):
    record = HealthRecord.query.get_or_404(record_id)

    if record.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        weight = float(request.form["weight"])
        height = float(request.form["height"])
        bmi = round(weight / (height * height), 2)

        record.weight = weight
        record.height = height
        record.bmi = bmi
        record.systolic = int(request.form["systolic"])
        record.diastolic = int(request.form["diastolic"])
        record.sugar = float(request.form["sugar"])
        record.water = float(request.form["water"])

        db.session.commit()

        flash("Record updated successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("edit_record.html", record=record)


# ---------------- DELETE RECORD ----------------
@app.route("/delete/<int:record_id>")
@login_required
def delete_record(record_id):
    record = HealthRecord.query.get_or_404(record_id)

    if record.user_id != current_user.id:
        abort(403)

    db.session.delete(record)
    db.session.commit()

    flash("Record deleted successfully!", "success")
    return redirect(url_for("dashboard"))


# ---------------- DOWNLOAD PDF REPORT ----------------
@app.route("/download-report")
@login_required
def download_report():
    records = HealthRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(HealthRecord.date.desc()).all()

    if not records:
        flash("No records found!", "danger")
        return redirect(url_for("dashboard"))

    latest = records[0]

    # Calculate health score again
    health_score = 100
    if latest.systolic > 140:
        health_score -= 20
    if latest.sugar > 180:
        health_score -= 20
    if latest.water < 1.5:
        health_score -= 10
    if latest.bmi < 18.5 or latest.bmi >= 25:
        health_score -= 15

    health_score = max(0, health_score)

    file_path = "health_report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>Smart Health Monitoring Report</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Name: {current_user.name}", styles["Normal"]))
    elements.append(Paragraph(f"Email: {current_user.email}", styles["Normal"]))
    elements.append(Paragraph(f"Generated On: {latest.date.strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ["Weight (kg)", latest.weight],
        ["Height (m)", latest.height],
        ["BMI", latest.bmi],
        ["Blood Pressure", f"{latest.systolic}/{latest.diastolic}"],
        ["Sugar Level", latest.sugar],
        ["Water Intake (L)", latest.water],
        ["Health Score (%)", health_score],
    ]

    table = Table(data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(file_path, as_attachment=True)


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        abort(403)

    users = User.query.all()
    records = HealthRecord.query.all()

    return render_template("admin_dashboard.html", users=users, records=records)


# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
