from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__, template_folder="templates")

app.secret_key = "leave-management-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///leave_management.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================
# USER TABLE
# =========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    # This will store the numeric User ID entered during registration
    username = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), nullable=False)


# =========================
# LEAVE REQUEST TABLE
# =========================

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    employee_id = db.Column(db.Integer, nullable=False)

    hod_id = db.Column(db.Integer, nullable=False)

    leave_type = db.Column(db.String(50), nullable=False)

    from_date = db.Column(db.String(20), nullable=False)

    to_date = db.Column(db.String(20), nullable=False)

    reason = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), default="Pending")

    hod_comment = db.Column(db.Text)


# =========================
# CREATE DATABASE + DEMO USERS
# =========================

with app.app_context():

    db.create_all()

    # Create demo employee only if it doesn't already exist
    employee = User.query.filter_by(username="1001").first()

    if not employee:
        employee = User(
            name="Employee 1",
            username="1001",
            password=generate_password_hash("1234"),
            role="employee"
        )

        db.session.add(employee)

    # Create demo HOD only if it doesn't already exist
    hod = User.query.filter_by(username="2001").first()

    if not hod:
        hod = User(
            name="HOD 1",
            username="2001",
            password=generate_password_hash("1234"),
            role="hod"
        )

        db.session.add(hod)

    db.session.commit()


# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["role"] = user.role
            session["name"] = user.name

            if user.role == "employee":
                return redirect(url_for("employee_dashboard"))

            elif user.role == "hod":
                return redirect(url_for("hod_dashboard"))

        return render_template(
            "login.html",
            error="Invalid user ID or password"
        )

    return render_template("login.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        # Check that User ID contains numbers only
        if not username.isdigit():

            return render_template(
                "register.html",
                error="User ID must contain numbers only."
            )

        # Check duplicate User ID
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:

            return render_template(
                "register.html",
                error="This User ID already exists."
            )

        # Create new user
        new_user = User(
            name=name,
            username=username,
            password=generate_password_hash(password),
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================
# EMPLOYEE DASHBOARD
# =========================

@app.route("/employee")
def employee_dashboard():

    if session.get("role") != "employee":
        return redirect(url_for("login"))

    employee_id = session["user_id"]

    leaves = LeaveRequest.query.filter_by(
        employee_id=employee_id
    ).order_by(
        LeaveRequest.id.desc()
    ).all()

    hods = User.query.filter_by(role="hod").all()

    employee = User.query.get(employee_id)

    return render_template(
        "employee.html",
        employee=employee,
        leaves=leaves,
        hods=hods
    )


# =========================
# APPLY LEAVE
# =========================

@app.route("/apply-leave", methods=["POST"])
def apply_leave():

    if session.get("role") != "employee":
        return redirect(url_for("login"))

    leave = LeaveRequest(

        employee_id=session["user_id"],

        hod_id=int(request.form.get("hod_id")),

        leave_type=request.form.get("leave_type"),

        from_date=request.form.get("from_date"),

        to_date=request.form.get("to_date"),

        reason=request.form.get("reason"),

        status="Pending"
    )

    db.session.add(leave)

    db.session.commit()

    return redirect(url_for("employee_dashboard"))


# =========================
# HOD DASHBOARD
# =========================

@app.route("/hod")
def hod_dashboard():

    if session.get("role") != "hod":
        return redirect(url_for("login"))

    hod_id = session["user_id"]

    leaves = LeaveRequest.query.filter_by(
        hod_id=hod_id
    ).order_by(
        LeaveRequest.id.desc()
    ).all()

    hod = User.query.get(hod_id)

    return render_template(
        "hod.html",
        hod=hod,
        leaves=leaves,
        User=User
    )


# =========================
# APPROVE / REJECT LEAVE
# =========================

@app.route("/leave/<int:leave_id>/<action>", methods=["POST"])
def update_leave(leave_id, action):

    if session.get("role") != "hod":
        return redirect(url_for("login"))

    leave = LeaveRequest.query.get_or_404(leave_id)

    # Only the assigned HOD can approve/reject
    if leave.hod_id != session["user_id"]:

        return "You are not authorized to approve this leave.", 403

    if action == "approve":

        leave.status = "Approved"

    elif action == "reject":

        leave.status = "Rejected"

    else:

        return "Invalid action", 400

    leave.hod_comment = request.form.get("comment")

    db.session.commit()

    return redirect(url_for("hod_dashboard"))


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)