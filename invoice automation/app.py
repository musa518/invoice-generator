# app.py (fixed & improved demo seeding)
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, abort
from datetime import datetime, timedelta
from collections import defaultdict
import os
import calendar

from sqlalchemy import extract, func

from utils import generate_invoice_pdf
from models import db, Invoice, InvoiceItem  # ensure models.py defines db = SQLAlchemy()

# --- Flask App ---
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///invoices.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def seed_demo_data():
    """
    Create several demo invoices with items across different months and statuses.
    This ensures charts and reports look realistic on a fresh DB.
    """
    # Only seed when empty
    if Invoice.query.count() > 0:
        return

    demo = []

    # Helper to add invoice with items and compute amount
    def make_invoice(client_name, client_email, description, issue_date, days_due, status, items):
        inv = Invoice(
            client_name=client_name,
            client_email=client_email,
            description=description,
            issue_date=issue_date,
            due_date=(issue_date + timedelta(days=days_due)),
            status=status,
            amount=0.0  # will set below
        )
        db.session.add(inv)
        db.session.flush()  # gives inv.id

        total = 0.0
        for itm in items:
            desc = itm.get("description")
            qty = float(itm.get("quantity", 1))
            price = float(itm.get("price", 0))
            tax = float(itm.get("tax", 0))
            subtotal = qty * price * (1 + tax / 100)
            total += subtotal

            inv_item = InvoiceItem(
                invoice_id=inv.id,
                description=desc,
                quantity=qty,
                price=price,
                tax=tax
            )
            db.session.add(inv_item)

        # store computed total
        inv.amount = round(total, 2)
        return inv

    # Create multiple demo invoices across months & clients
    now = datetime.now()
    demo.append(make_invoice(
        client_name="Alpha Corp",
        client_email="alpha@example.com",
        description="Website design + small CMS",
        issue_date=datetime(now.year, max(1, now.month - 4), 12).date(),
        days_due=14,
        status="Paid",
        items=[
            {"description": "Landing page design", "quantity": 1, "price": 600, "tax": 5},
            {"description": "CMS setup", "quantity": 1, "price": 400, "tax": 0},
        ]
    ))

    demo.append(make_invoice(
        client_name="Beta Ltd",
        client_email="beta@example.com",
        description="SEO & content",
        issue_date=datetime(now.year, max(1, now.month - 3), 6).date(),
        days_due=30,
        status="Unpaid",
        items=[
            {"description": "SEO package (3 months)", "quantity": 1, "price": 750, "tax": 0},
        ]
    ))

    demo.append(make_invoice(
        client_name="Gamma Inc",
        client_email="gamma@example.com",
        description="Mobile App MVP",
        issue_date=datetime(now.year, max(1, now.month - 2), 3).date(),
        days_due=30,
        status="Paid",
        items=[
            {"description": "iOS development (hrs)", "quantity": 60, "price": 20, "tax": 10},
            {"description": "Backend API", "quantity": 1, "price": 1200, "tax": 0},
        ]
    ))

    demo.append(make_invoice(
        client_name="Delta Co",
        client_email="delta@example.com",
        description="Branding & logo",
        issue_date=datetime(now.year, max(1, now.month - 1), 18).date(),
        days_due=10,
        status="Paid",
        items=[
            {"description": "Branding package", "quantity": 1, "price": 1500, "tax": 0},
        ]
    ))

    demo.append(make_invoice(
        client_name="Epsilon Partners",
        client_email="eps@partners.com",
        description="Maintenance & support",
        issue_date=datetime(now.year, now.month, min(10, now.day)).date(),
        days_due=7,
        status="Unpaid",
        items=[
            {"description": "Monthly maintenance", "quantity": 1, "price": 199, "tax": 0},
            {"description": "Emergency support (hrs)", "quantity": 2, "price": 50, "tax": 0},
        ]
    ))

    db.session.commit()


# Ensure DB exists and seed demo data if empty
with app.app_context():
    db.create_all()
    seed_demo_data()


# --- Dashboard ---
@app.route("/")
def dashboard():
    invoices = Invoice.query.order_by(Invoice.id.desc()).limit(5).all()

    total_invoices = Invoice.query.count()
    paid_invoices = Invoice.query.filter_by(status="Paid").count()
    unpaid_invoices = Invoice.query.filter_by(status="Unpaid").count()
    total_revenue = db.session.query(func.sum(Invoice.amount)).scalar() or 0

    # Monthly revenue (for paid invoices)
    monthly_data = (
        db.session.query(
            extract('month', Invoice.issue_date).label('month'),
            func.sum(Invoice.amount).label('total')
        )
        .filter(Invoice.status == "Paid", Invoice.issue_date != None)
        .group_by('month')
        .order_by('month')
        .all()
    )

    # build full 12-month array for chart (Jan..Dec)
    monthly_revenue = [0.0] * 12
    for row in monthly_data:
        try:
            m = int(row[0]) - 1
            monthly_revenue[m] = float(row[1] or 0.0)
        except Exception:
            continue

    labels = [calendar.month_abbr[i] for i in range(1, 13)]
    values = monthly_revenue

    return render_template(
        "dashboard.html",
        invoices=invoices,
        total_invoices=total_invoices,
        paid_invoices=paid_invoices,
        unpaid_invoices=unpaid_invoices,
        total_revenue=total_revenue,
        revenue_labels=labels,
        revenue_values=values
    )

# --- Invoice list ---
@app.route("/invoices")
def invoices():
    invoices_q = Invoice.query.order_by(Invoice.issue_date.asc().nulls_last(), Invoice.id.desc()).all() \
        if hasattr(Invoice.issue_date, 'asc') else Invoice.query.order_by(Invoice.issue_date.asc(), Invoice.id.desc()).all()
    return render_template("invoices.html", invoices=invoices_q)


# --- Reports ---
@app.route("/reports")
def reports():
    # monthly revenue for paid invoices (Jan..Dec)
    monthly_revenue = [0.0] * 12
    paid_invoices = Invoice.query.filter(Invoice.status == "Paid", Invoice.issue_date != None).all()
    for inv in paid_invoices:
        try:
            month_idx = inv.issue_date.month - 1
            monthly_revenue[month_idx] += float(inv.amount or 0.0)
        except Exception:
            continue

    paid_count = Invoice.query.filter_by(status="Paid").count()
    unpaid_count = Invoice.query.filter_by(status="Unpaid").count()

    top_clients = defaultdict(float)
    for inv in paid_invoices:
        name = inv.client_name or "Unknown"
        top_clients[name] += float(inv.amount or 0.0)

    # Keep top 8 (or fewer if not available)
    top_clients = dict(sorted(top_clients.items(), key=lambda x: x[1], reverse=True)[:8])

    # Safe defaults if DB somehow empty
    if not any(monthly_revenue):
        monthly_revenue = [0.0] * 12
    if paid_count is None:
        paid_count = 0
    if unpaid_count is None:
        unpaid_count = 0
    if not top_clients:
        top_clients = {"No Data": 0.0}

    return render_template(
        "reports.html",
        monthly_revenue=monthly_revenue,
        paid_vs_unpaid={"Paid": paid_count, "Unpaid": unpaid_count},
        top_clients=top_clients
    )


# --- Create Invoice ---
@app.route("/create", methods=["GET", "POST"])
def create_invoice():
    if request.method == "POST":
        client_name = request.form.get("client_name")
        client_email = request.form.get("client_email")
        due_date_str = request.form.get("due_date")
        status = request.form.get("status") or "Unpaid"

        # parse due_date safely
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                # accept empty or different format by leaving None
                due_date = None

        # set issue_date to today (so dashboard grouping works)
        issue_date = datetime.now().date()

        invoice = Invoice(
            client_name=client_name,
            client_email=client_email,
            due_date=due_date or (issue_date + timedelta(days=7)),
            issue_date=issue_date,
            status=status,
            amount=0.0
        )
        db.session.add(invoice)
        db.session.flush()

        item_names = request.form.getlist("item_name[]")
        item_qtys = request.form.getlist("item_qty[]")
        item_prices = request.form.getlist("item_price[]")
        item_taxes = request.form.getlist("item_tax[]")

        total_amount = 0.0
        for name, qty, price, tax in zip(item_names, item_qtys, item_prices, item_taxes):
            if not name or not name.strip():
                continue
            try:
                qty_val = float(qty or 0)
                price_val = float(price or 0)
                tax_val = float(tax or 0)
            except ValueError:
                qty_val = 0.0
                price_val = 0.0
                tax_val = 0.0

            subtotal = qty_val * price_val * (1 + tax_val / 100)
            total_amount += subtotal

            item = InvoiceItem(
                invoice_id=invoice.id,
                description=name,
                quantity=qty_val,
                price=price_val,
                tax=tax_val
            )
            db.session.add(item)

        invoice.amount = round(total_amount, 2)
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("create_invoice.html")


# --- Invoice Detail ---
@app.route("/invoice/<int:invoice_id>")
def invoice_detail(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template("invoice_detail.html", invoice=invoice, items_list=invoice.items)


# --- Download PDF ---
@app.route("/invoice/<int:invoice_id>/pdf")
def download_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    filename = f"invoice_{invoice_id}.pdf"
    # generate in a temp path inside project folder
    generate_invoice_pdf(invoice, filename)
    return send_file(filename, as_attachment=True)


# --- Delete Invoice ---
@app.route("/invoice/<int:invoice_id>/delete", methods=["POST"])
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    return redirect(url_for("dashboard"))


# --- Mark Paid ---
@app.route("/invoice/<int:invoice_id>/mark_paid", methods=["POST"])
def mark_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = "Paid"
    # optionally set issue_date if missing
    if not getattr(invoice, "issue_date", None):
        invoice.issue_date = datetime.now().date()
    db.session.commit()
    return redirect(url_for("dashboard"))


# --- API: Monthly Revenue (status) ---
@app.route("/api/monthly-revenue-status")
def api_monthly_revenue_status():
    """
    Returns paid/unpaid revenue arrays for Jan..Dec for the current year:
    { labels: ["Jan",...,"Dec"], paid: [0.0,...], unpaid: [0.0,...] }
    """
    labels = [calendar.month_abbr[m] for m in range(1, 13)]
    paid = [0.0] * 12
    unpaid = [0.0] * 12

    rows = (
        db.session.query(
            extract("month", Invoice.issue_date).label("month"),
            Invoice.status,
            func.sum(Invoice.amount).label("total")
        )
        .filter(Invoice.issue_date != None)
        .filter(extract("year", Invoice.issue_date) == datetime.now().year)
        .group_by("month", Invoice.status)
        .all()
    )

    for month, status, total in rows:
        try:
            idx = int(month) - 1
            if status and str(status).strip().lower() == "paid":
                paid[idx] = float(total or 0.0)
            else:
                unpaid[idx] = float(total or 0.0)
        except Exception:
            continue

    return jsonify({"labels": labels, "paid": paid, "unpaid": unpaid})


# --- Edit Invoice ---
@app.route("/invoice/<int:invoice_id>/edit", methods=["GET", "POST"])
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if request.method == "POST":
        try:
            invoice.client_name = request.form.get("client_name")
            invoice.client_email = request.form.get("client_email")
            invoice.description = request.form.get("description")

            issue_date_str = request.form.get("issue_date")
            due_date_str = request.form.get("due_date")
            if issue_date_str:
                try:
                    invoice.issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            if due_date_str:
                try:
                    invoice.due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # Remove old items
            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()

            # Add updated items
            item_names = request.form.getlist("item_name[]")
            item_qtys = request.form.getlist("item_qty[]")
            item_prices = request.form.getlist("item_price[]")
            item_taxes = request.form.getlist("item_tax[]")

            total_amount = 0.0
            for name, qty, price, tax in zip(item_names, item_qtys, item_prices, item_taxes):
                if not name or not name.strip():
                    continue
                try:
                    qty_val = float(qty or 0)
                    price_val = float(price or 0)
                    tax_val = float(tax or 0)
                except ValueError:
                    qty_val = 0.0
                    price_val = 0.0
                    tax_val = 0.0

                subtotal = qty_val * price_val * (1 + tax_val / 100)
                total_amount += subtotal

                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=name,
                    quantity=qty_val,
                    price=price_val,
                    tax=tax_val
                )
                db.session.add(item)

            invoice.amount = round(total_amount, 2)
            db.session.commit()
            return redirect(url_for("invoice_detail", invoice_id=invoice.id))
        except Exception as e:
            db.session.rollback()
            return f"Error updating invoice: {e}", 500

    return render_template("edit_invoice.html", invoice=invoice)
@app.route("/intro")
def intro():
    return render_template("intro.html")



if __name__ == "__main__":
    app.run(debug=True, port=8000)
