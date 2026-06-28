import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()  # must run before signals.py initializes the Groq client

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database import get_entry, init_db, log_submission, read_log
from scoring import classify, compute_final_score, generate_label
from signals import classify_with_llm, compute_stylo_score

app = Flask(__name__)
init_db()

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/submit", methods=["POST"])
@limiter.limit("5 per minute;50 per hour")
def submit():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    content = (data.get("content") or data.get("text") or "").strip()
    if not content:
        return jsonify({"error": "content field is required and must not be empty"}), 400

    creator_id = data.get("creator_id")
    content_id = str(uuid.uuid4())
    short_text = len(content.split()) < 10

    llm_score   = 0.5 if short_text else classify_with_llm(content)[0]
    stylo_score = compute_stylo_score(content)
    final_score = compute_final_score(llm_score, stylo_score)
    classification, confidence_level = classify(final_score)
    label_text  = generate_label(final_score)

    log_submission({
        "content_id":       content_id,
        "creator_id":       creator_id,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "content_preview":  content[:200],
        "llm_score":        llm_score,
        "stylo_score":      stylo_score,
        "final_score":      round(final_score, 4),
        "classification":   classification,
        "confidence_level": confidence_level,
        "label_text":       label_text,
        "short_text_flag":  int(short_text),
        "status":           "classified",
    })

    return jsonify({
        "content_id":       content_id,
        "classification":   classification,
        "confidence_score": round(final_score, 4),
        "confidence_level": confidence_level,
        "label_text":       label_text,
        "signals": {
            "llm_score":   round(llm_score, 4),
            "stylo_score": round(stylo_score, 4),
        },
        "short_text_warning": short_text,
        "status":             "classified",
        "appeal_url":         f"/appeal/{content_id}",
    })


@app.route("/appeal/<content_id>", methods=["POST"])
def appeal(content_id):
    data = request.get_json(silent=True)
    if not data or not data.get("reasoning", "").strip():
        return jsonify({"error": "reasoning field is required"}), 400

    entry = get_entry(content_id)
    if entry is None:
        return jsonify({"error": "content_id not found"}), 404
    if entry["status"] == "under_review":
        return jsonify({"error": "appeal already submitted for this content"}), 409

    from database import log_appeal
    log_appeal(content_id, data["reasoning"].strip())

    return jsonify({
        "appeal_id":  str(uuid.uuid4()),
        "content_id": content_id,
        "status":     "under_review",
        "message":    "Your appeal has been received and the content is now under review.",
    })


@app.route("/log", methods=["GET"])
def view_log():
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 100))
    except ValueError:
        limit = 20
    entries = read_log(limit)
    return jsonify({"entries": entries, "total": len(entries)})


if __name__ == "__main__":
    app.run(port=5001, debug=True)
