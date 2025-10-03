# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    issue_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)

    amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="Unpaid")

    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan")

    def total_amount(self):
        """Recalculate invoice total from items"""
        total = 0.0
        for item in self.items:
            subtotal = item.quantity * item.price
            subtotal += subtotal * (item.tax or 0) / 100
            total += subtotal
        return total


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)

    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float, default=1)
    price = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)  # in percent (e.g., 15 = 15%)

    def subtotal(self):
        subtotal = self.quantity * self.price
        subtotal += subtotal * (self.tax or 0) / 100
        return subtotal
