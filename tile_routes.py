from io import BytesIO

from flask import Blueprint, abort, send_file, request

from db import get_connection
from wsi_reader import extract_roi, wsi_supported

tile_bp = Blueprint("tile_bp", __name__)


@tile_bp.route("/roi/<int:analysis_id>")
def roi_image(analysis_id: int):
    if not wsi_supported():
        abort(503, description="WSI support is not available.")

    x = int(request.args.get("x", 0))
    y = int(request.args.get("y", 0))
    w = int(request.args.get("w", 512))
    h = int(request.args.get("h", 512))
    level = int(request.args.get("level", 0))

    conn = get_connection()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()

    if row is None:
        abort(404)

    if row["filetype"] != "wsi":
        abort(400, description="This case is not a WSI file.")

    image = extract_roi(row["filepath"], x, y, w, h, level)
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return send_file(buf, mimetype="image/jpeg")