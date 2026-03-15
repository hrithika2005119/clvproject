# app.py  ── CLV (naïve, no dates required)
# ───────────────────────────────────────────────────────
from flask import Flask, request, render_template_string, url_for
import pandas as pd
import io

app = Flask(__name__)

# ─────────────────────────── HTML template ────────────────────────────
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CLV Results </title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; padding: 24px; }
    table { border-collapse: collapse; width: 100%; margin-top: 24px; }
    th, td { padding: 8px 12px; border: 1px solid #ccc; text-align: center; }
    th { background: #007bff; color:#fff; }
    tr:nth-child(even) { background:#f9f9f9; }
  </style>
</head>
<body>

  <h2>Naïve 6‑Month Customer Lifetime Value</h2>
  <p style="margin:0">Assumption: future purchase frequency equals past frequency.</p>

  <table>
    <thead>
      <tr>
        <th>Customer&nbsp;ID</th>
        <th>Past&nbsp;Frequency</th>
        <th>Avg&nbsp;Order&nbsp;Value</th>
        <th>Predicted&nbsp;Purchases<br>(next 6 mo)</th>
        <th>CLV&nbsp;6 mo&nbsp;(₹)</th>
      </tr>
    </thead>
    <tbody>
      {% for r in results %}
      <tr>
        <td>{{ r.id }}</td>
        <td>{{ r.freq }}</td>
        <td>{{ "%.2f"|format(r.aov) }}</td>
        <td>{{ r.pred }}</td>
        <td>{{ "%.2f"|format(r.clv) }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <p style="margin-top:24px">
    <a href="{{ url_for('home') }}">&larr; Upload another file</a>
  </p>
</body>
</html>
"""
# ───────────────────────────────────────────────────────────────────────


# ── upload form ────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home() -> str:
    return """
    <h1>Upload CSV for CLV Prediction (No Dates)</h1>
    <form method="POST" action="/predict-clv" enctype="multipart/form-data">
      <input type="file" name="file" accept=".csv" required>
      <button type="submit">Upload & Predict</button>
    </form>
    """


# ── prediction endpoint ───────────────────────────────────────────────
@app.route("/predict-clv", methods=["POST"])
def predict_clv():
    csv_file = request.files.get("file")
    if not csv_file or csv_file.filename == "":
        return "No file selected", 400
    if not csv_file.filename.lower().endswith(".csv"):
        return "Only .csv files are accepted", 400

    # read file
    try:
        raw = csv_file.stream.read()
        try:
            df = pd.read_csv(io.StringIO(raw.decode("utf-8")))
        except UnicodeDecodeError:
            df = pd.read_csv(io.StringIO(raw.decode("latin1")))
    except Exception as e:
        return f"Could not parse CSV – {e}", 400

    # validate expected columns
    needed = {"CustomerID", "Quantity", "UnitPrice"}
    if not needed.issubset(df.columns):
        return f"CSV must contain columns: {needed}", 400

    df = df.dropna(subset=["CustomerID"])
    df = df[df["Quantity"] > 0]        # filter out negative quantities
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    # group by customer
    grouped = (
        df.groupby("CustomerID")
          .agg(total_spent=("TotalPrice", "sum"),
               freq=("TotalPrice", "size"))   # size = number of rows
          .reset_index()
    )
    grouped["aov"]  = grouped["total_spent"] / grouped["freq"]
    grouped["pred_purchases"] = grouped["freq"]           # naïve assumption
    grouped["clv_6mo"] = grouped["pred_purchases"] * grouped["aov"]

    # build list for template
    results = [
        {
            "id":   r.CustomerID,
            "freq": int(r.freq),
            "aov":  r.aov,
            "pred": int(r.pred_purchases),
            "clv":  r.clv_6mo
        }
        for _, r in grouped.iterrows()
    ]

    return render_template_string(HTML_TEMPLATE, results=results)


# ── run ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # visit http://127.0.0.1:5000/
    app.run(debug=True)
