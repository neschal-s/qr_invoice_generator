# TML Invoice QR Generator

Upload any vendor invoice PDF → Claude AI extracts all 20 fields → Generates TML-compliant QR → Returns original invoice with QR embedded.

---

## Run Locally (Test First)

### Step 1 — Install Python dependencies
```bash
pip install flask anthropic "qrcode[pil]" PyMuPDF Pillow
```

### Step 2 — Start the server
```bash
python app.py
```

### Step 3 — Open in browser
```
http://localhost:5000
```

### Step 4 — Use it
1. Enter your Claude API key (get free $5 credit at console.anthropic.com)
2. Enter TML PO Order Item No. (field #2 — from your ASN)
3. Upload your invoice PDF
4. Click "Extract with Claude AI"
5. Review the 20 extracted fields, edit if needed
6. Click "Generate QR & Download PDF"
7. Your original invoice PDF is returned with TML QR code in the top-right corner

---

## Deploy to Render (Host Online)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "TML QR Generator"
git remote add origin https://github.com/YOUR_USERNAME/tml-qr-app.git
git push -u origin main
```

### Step 2 — Deploy on Render
1. Go to https://render.com and sign up (free)
2. Click "New" → "Web Service"
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` and deploys
5. Your site is live at `https://tml-qr-generator.onrender.com`

---

## How it works

```
Browser → POST /extract  → Flask → Claude API → returns 20 fields
Browser → POST /download → Flask → Python qrcode → PyMuPDF → returns PDF
```

- Claude API key is used per-request and never stored
- QR generated using Python `qrcode` library (ISO 18004 compliant)
- Original invoice PDF preserved exactly using PyMuPDF
- QR placed top-right corner, 76.5pt (~2.7cm) — above TML 2cm minimum

---

## Field Spec (TML QR Code Implementation v1.0)

| # | Field | Format |
|---|-------|--------|
| 1 | TML PO Number | Digits only |
| 2 | TML PO Order Item No. | Digits only (manual entry) |
| 3 | Vendor Invoice Part Qty | Decimal up to 3 places |
| 4 | Vendor GST Invoice No. | Alphanumeric, no special chars |
| 5 | Vendor Invoice Date | DD.MM.YYYY |
| 6 | Invoice Basic/Gross Rate | Decimal 2 places |
| 7 | Vendor Invoice Net Rate | Decimal 2 places |
| 8 | Vendor Code | Alphanumeric |
| 9 | Invoice Part Number | Alphanumeric |
| 10-13 | Tax Values CGST/SGST/IGST/UGST | Decimal 2 places |
| 14-17 | Tax Rates CGST/SGST/IGST/UGST % | Decimal 2 places, no % sign |
| 18 | Cess | Decimal 2 places |
| 19 | Total Invoice Value | Decimal 2 places |
| 20 | HSN / SAC Code | Digits only |

All fields comma-separated, no spaces within fields.
