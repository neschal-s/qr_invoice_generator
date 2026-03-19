import os, io, base64, json, re
from flask import Flask, request, jsonify, render_template, send_file
import qrcode
from PIL import Image
import fitz  # PyMuPDF
import requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max upload

# ─── FIELD DEFINITIONS ─────────────────────────────────────────────
FIELDS = [
    {"id": "po_number", "n": 1,  "label": "TML PO Number", "max": 10, "type": "int"},
    {"id": "po_item",   "n": 2,  "label": "TML PO Order Item No.", "max": 4, "type": "int", "manual": True},
    {"id": "qty", "n": 3, "label": "Qty", "max": 12, "type": "dec3"},
    {"id": "inv_no", "n": 4, "label": "Invoice No", "max": 16, "type": "alnum"},
    {"id": "inv_date", "n": 5, "label": "Date", "max": 10, "type": "date"},
    {"id": "gross", "n": 6, "label": "Gross", "max": 10, "type": "dec2"},
    {"id": "net", "n": 7, "label": "Net", "max": 10, "type": "dec2"},
    {"id": "vcode", "n": 8, "label": "Vendor Code", "max": 10, "type": "alnum"},
    {"id": "partno", "n": 9, "label": "Part No", "max": 14, "type": "alnum"},
    {"id": "cgst", "n": 10, "label": "CGST", "max": 10, "type": "dec2"},
    {"id": "sgst", "n": 11, "label": "SGST", "max": 10, "type": "dec2"},
    {"id": "igst", "n": 12, "label": "IGST", "max": 10, "type": "dec2"},
    {"id": "ugst", "n": 13, "label": "UGST", "max": 10, "type": "dec2"},
    {"id": "cgst_r", "n": 14, "label": "CGST %", "max": 6, "type": "dec2"},
    {"id": "sgst_r", "n": 15, "label": "SGST %", "max": 6, "type": "dec2"},
    {"id": "igst_r", "n": 16, "label": "IGST %", "max": 6, "type": "dec2"},
    {"id": "ugst_r", "n": 17, "label": "UGST %", "max": 6, "type": "dec2"},
    {"id": "cess", "n": 18, "label": "Cess", "max": 6, "type": "dec2"},
    {"id": "total", "n": 19, "label": "Total", "max": 16, "type": "dec2"},
    {"id": "hsn", "n": 20, "label": "HSN", "max": 10, "type": "int"},
]

# ─── VALIDATION ────────────────────────────────────────────────────
def validate_field(f, val):
    s = str(val or "")
    if not s:
        return False, "Required"
    if "," in s:
        return False, "No commas allowed"
    if len(s) > f["max"]:
        return False, f"Max {f['max']} chars"
    if f["type"] == "int" and not re.match(r"^\d+$", s):
        return False, "Digits only"
    return True, ""

# ─── ROUTES ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", fields=FIELDS)


@app.route("/extract", methods=["POST"])
def extract():
    api_key = request.form.get("api_key", "").strip()
    if not api_key.startswith("sk-or-"):
        return jsonify({"error": "Invalid OpenRouter API key"}), 400

    pdf_file = request.files.get("pdf")
    if not pdf_file:
        return jsonify({"error": "No PDF uploaded"}), 400

    pdf_bytes = pdf_file.read()
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    # 🔹 Extract text from PDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = ""
    for page in doc:
        pdf_text += page.get_text()
    doc.close()

    # Limit text size
    pdf_text = pdf_text[:15000]

    prompt = """Extract invoice data and return ONLY JSON.
If a field is missing, return "" instead of guessing.
Fields: po_number, qty, inv_no, inv_date, gross, net, vcode, partno,
cgst, sgst, igst, ugst, cgst_r, sgst_r, igst_r, ugst_r, cess, total, hsn"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt + "\n\n" + pdf_text
                    }
                ]
            },
            timeout=30
        )

        result = response.json()

        if "choices" not in result:
            return jsonify({"error": result}), 500

        raw = result["choices"][0]["message"]["content"]

        raw = re.sub(r"```json|```", "", raw).strip()
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return jsonify({"error": "Failed to parse AI response"}), 500

        extracted = json.loads(match.group())

        errors = {}
        for f in FIELDS:
            if f.get("manual"):
                continue
            ok, err = validate_field(f, extracted.get(f["id"], ""))
            if not ok:
                errors[f["id"]] = err

        return jsonify({
            "fields": extracted,
            "errors": errors,
            "pdf_b64": pdf_b64,
            "pdf_name": pdf_file.filename
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    fields_data = data["fields"]
    pdf_b64 = data["pdf_b64"]
    pdf_name = data["pdf_name"]

    qr_string = ",".join([fields_data.get(f["id"], "") for f in FIELDS])

    qr = qrcode.make(qr_string)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    pdf_bytes = base64.b64decode(pdf_b64)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page in doc:
        rect = fitz.Rect(page.rect.width - 80, 10, page.rect.width - 10, 80)
        page.insert_image(rect, stream=buf.getvalue())

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    out.seek(0)

    return send_file(out, as_attachment=True, download_name="output.pdf")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)