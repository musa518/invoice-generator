# utils.py
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

def generate_invoice_pdf(invoice, filename):
    """
    invoice: SQLAlchemy Invoice object with .items relationship
    """
    brand_color = colors.HexColor("#2E86C1")

    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=36, leftMargin=36,
                            topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Right", alignment=2))
    styles.add(ParagraphStyle(name="Center", alignment=1))
    styles.add(ParagraphStyle(name="SmallGrey", fontSize=9, textColor=colors.grey))

    # --- Header ---
    header_data = []
    if getattr(invoice, "company_logo", None):
        try:
            logo = Image(invoice.company_logo, width=80, height=40)
            header_data.append([logo,
                Paragraph("<b style='font-size:20px;color:#2E86C1;'>INVOICE</b>", styles["Right"])
            ])
        except:
            header_data.append([
                Paragraph("<b style='font-size:16px;'>InvoicePro</b>", styles["Normal"]),
                Paragraph("<b style='font-size:20px;color:#2E86C1;'>INVOICE</b>", styles["Right"])
            ])
    else:
        header_data.append([
            Paragraph("<b style='font-size:16px;'>InvoicePro</b>", styles["Normal"]),
            Paragraph("<b style='font-size:20px;color:#2E86C1;'>INVOICE</b>", styles["Right"])
        ])

    header_table = Table(header_data, colWidths=[300, 220])
    header_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # --- Company Info ---
    elements.append(Paragraph("123 Business Street, City, Country", styles["Normal"]))
    elements.append(Paragraph("Email: you@company.com | Phone: +123456789", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # --- Invoice Metadata ---
    meta = [
        ["Date:", invoice.issue_date.strftime("%Y-%m-%d") if invoice.issue_date else ""],
        ["Due:", invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else ""],
        ["Status:", invoice.status],
    ]
    meta_table = Table(meta, colWidths=[80, 200])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (0,0), (0,-1), brand_color),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 16))

    # --- Bill To ---
    elements.append(Paragraph("<b style='color:#2E86C1;'>Bill To:</b>", styles["Normal"]))
    elements.append(Paragraph(invoice.client_name or "", styles["Normal"]))
    if getattr(invoice, "client_email", None):
        elements.append(Paragraph(f"Email: {invoice.client_email}", styles["Normal"]))
    elements.append(Spacer(1, 16))

    # --- Items Table ---
    data = [["Description", "Qty", "Unit Price", "Line Total"]]
    subtotal = 0

    if hasattr(invoice, "items") and invoice.items:
        for i, item in enumerate(invoice.items, start=1):
            line_total = (item.quantity or 0) * (item.price or 0)
            subtotal += line_total
            data.append([
                item.description,
                str(item.quantity),
                f"${item.price:.2f}",
                f"${line_total:.2f}",
            ])
    else:
        subtotal = float(invoice.amount or 0)
        data.append([
            getattr(invoice, "description", "Services Rendered"),
            "1",
            f"${subtotal:.2f}",
            f"${subtotal:.2f}",
        ])

    table = Table(data, colWidths=[260, 60, 80, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # --- Totals ---
    tax = subtotal * 0.1
    total = subtotal + tax
    totals = [
        ["Subtotal", f"${subtotal:.2f}"],
        ["Tax (10%)", f"${tax:.2f}"],
        ["Total", f"${total:.2f}"],
    ]
    totals_table = Table(totals, colWidths=[360, 120])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("LINEABOVE", (0, -1), (-1, -1), 1, brand_color),
        ("TEXTCOLOR", (0, -1), (-1, -1), brand_color),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 20))

    # --- Payment Instructions ---
    elements.append(Paragraph("<b style='color:#2E86C1;'>Payment Instructions</b>", styles["Normal"]))
    elements.append(Paragraph("Bank: Bank Name, Account #: 123456789, IBAN: PK00BANK000000", styles["Normal"]))
    elements.append(Spacer(1, 16))

    # --- Notes ---
    if getattr(invoice, "description", None):
        elements.append(Paragraph("<b style='color:#2E86C1;'>Notes</b>", styles["Normal"]))
        elements.append(Paragraph(invoice.description, styles["Normal"]))
        elements.append(Spacer(1, 16))

    # --- Footer ---
    footer_bar = Table([[Paragraph("Thank you for your business!", styles["Center"])]],
                       colWidths=[540], rowHeights=[20])
    footer_bar.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), brand_color),
        ("TEXTCOLOR", (0,0), (-1,-1), colors.white),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE")
    ]))
    elements.append(Spacer(1, 30))
    elements.append(footer_bar)
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
        styles["SmallGrey"]
    ))

    doc.build(elements)
