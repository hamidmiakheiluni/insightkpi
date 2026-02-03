from datetime import date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class KPIEntry(db.Model):
    __tablename__ = "kpi_entries"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    kpi_name = db.Column(db.String(120), nullable=False, index=True)
    kpi_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    value = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(500), nullable=True)

    # ✅ NEW: Evaluation fields (minimal approach)
    target_value = db.Column(db.Float, nullable=True)  # can be blank if not set
    direction = db.Column(db.String(10), nullable=False, default="higher")  # higher | lower
    tolerance_pct = db.Column(db.Float, nullable=False, default=5.0)  # % tolerance for amber
