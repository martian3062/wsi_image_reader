from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    send_file,
)
from werkzeug.utils import secure_filename

from analysis import allowed_file, analyze_image, analyze_pil_image
from db import get_connection, init_db
from report_export import build_pdf_report
from tile_routes import tile_bp
from wsi_reader import wsi_supported, get_wsi_info, generate_wsi_thumbnail, extract_roi

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
REPORT_FOLDER = BASE_DIR / "generated_reports"

UPLOAD_FOLDER.mkdir(exist_ok=True)
REPORT_FOLDER.mkdir(exist_ok=True)


def create_app():
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    init_db()
    app.register_blueprint(tile_bp)

    @app.route("/")
    def index():
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, filename, filetype, risk_score, pattern_label, created_at "
            "FROM analyses ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()
        return render_template("index.html", recent=rows)

    @app.route("/upload", methods=["POST"])
    def upload():
        file = request.files.get("image")
        if not file or not file.filename:
            return redirect(url_for("index"))

        if not allowed_file(file.filename):
            return redirect(url_for("index"))

        original_name = secure_filename(file.filename)
        ext = original_name.rsplit(".", 1)[1].lower()
        saved_name = f"{uuid4().hex}.{ext}"
        save_path = UPLOAD_FOLDER / saved_name
        file.save(save_path)

        thumb_rel = None

        if ext == "svs":
            if not wsi_supported():
                abort(503, description="OpenSlide is not installed or not supported here.")

            info = get_wsi_info(str(save_path))
            thumb_name = f"{uuid4().hex}_thumb.jpg"
            thumb_path = UPLOAD_FOLDER / thumb_name
            generate_wsi_thumbnail(str(save_path), str(thumb_path))

            roi_img = extract_roi(str(save_path), 0, 0, 1024, 1024, 0)
            result = analyze_pil_image(roi_img)
            result["width"] = info["width"]
            result["height"] = info["height"]

            filetype = "wsi"
            thumb_rel = thumb_name
        else:
            result = analyze_image(str(save_path))
            filetype = "image"

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO analyses (
                filename, filepath, filetype, width, height, avg_intensity, intensity_std,
                edge_density, redness_score, saturation_score, tissue_ratio,
                risk_score, pattern_label, summary, roi_json, thumbnail_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                original_name,
                str(save_path),
                filetype,
                result["width"],
                result["height"],
                result["avg_intensity"],
                result["intensity_std"],
                result["edge_density"],
                result["redness_score"],
                result["saturation_score"],
                result["tissue_ratio"],
                result["risk_score"],
                result["pattern_label"],
                result["summary"],
                json.dumps({"x": 0, "y": 0, "w": 1024, "h": 1024}),
                thumb_rel,
            ),
        )
        analysis_id = cur.lastrowid
        conn.commit()
        conn.close()

        return redirect(url_for("result", analysis_id=analysis_id))

    @app.route("/result/<int:analysis_id>")
    def result(analysis_id: int):
        conn = get_connection()
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        conn.close()

        if row is None:
            abort(404)

        return render_template("result.html", row=row)

    @app.route("/case/<int:analysis_id>")
    def case_detail(analysis_id: int):
        conn = get_connection()
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        saved = conn.execute(
            "SELECT * FROM saved_cases WHERE analysis_id = ? ORDER BY id DESC",
            (analysis_id,),
        ).fetchall()
        conn.close()

        if row is None:
            abort(404)

        return render_template("case_detail.html", row=row, saved=saved)

    @app.route("/save-case/<int:analysis_id>", methods=["POST"])
    def save_case(analysis_id: int):
        title = request.form.get("title", "").strip() or f"Case {analysis_id}"
        notes = request.form.get("notes", "").strip()

        conn = get_connection()
        conn.execute(
            "INSERT INTO saved_cases (analysis_id, title, notes) VALUES (?, ?, ?)",
            (analysis_id, title, notes),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("case_detail", analysis_id=analysis_id))

    @app.route("/saved-cases")
    def saved_cases():
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT s.id as saved_id, s.title, s.notes, s.created_at, a.id as analysis_id,
                   a.filename, a.pattern_label, a.risk_score
            FROM saved_cases s
            JOIN analyses a ON s.analysis_id = a.id
            ORDER BY s.id DESC
            """
        ).fetchall()
        conn.close()
        return render_template("saved_cases.html", rows=rows)

    @app.route("/dashboard")
    def dashboard():
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, filename, risk_score, pattern_label, created_at FROM analyses ORDER BY id DESC LIMIT 20"
        ).fetchall()
        conn.close()
        return render_template("dashboard.html", rows=rows)

    @app.route("/partials/score-cards/<int:analysis_id>")
    def partial_score_cards(analysis_id: int):
        conn = get_connection()
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        conn.close()
        if row is None:
            abort(404)
        return render_template("partials/score_cards.html", row=row)

    @app.route("/partials/roi-panel/<int:analysis_id>")
    def partial_roi_panel(analysis_id: int):
        conn = get_connection()
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        conn.close()
        if row is None:
            abort(404)
        return render_template("partials/roi_panel.html", row=row)

    @app.route("/export-pdf/<int:analysis_id>")
    def export_pdf(analysis_id: int):
        conn = get_connection()
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        conn.close()
        if row is None:
            abort(404)

        output_path = REPORT_FOLDER / f"analysis_{analysis_id}.pdf"
        build_pdf_report(row, str(output_path))
        return send_file(output_path, as_attachment=True)

    @app.route("/health")
    def health():
        return {"status": "ok", "wsi_supported": wsi_supported()}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)