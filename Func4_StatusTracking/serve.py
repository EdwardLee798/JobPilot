from flask import Flask, Response, send_from_directory
import csv
import json
import os
import time
import argparse

app = Flask(__name__, static_folder="frontend")

BASE_DIR = os.path.dirname(__file__)
TABLES_DIR = os.path.join(BASE_DIR, "tables")
STATUS_FILE = os.path.join(TABLES_DIR, "Student_application_status.csv")
SUMMARY_FILE = os.path.join(TABLES_DIR, "Student_job_tracking_summary.csv")


def read_csv_to_dicts(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def merged_records():
    """Return a list of merged records by joining summary and status on job_id.
    Each record contains: job_id, company_name, job_title, status_update, event_time
    """
    summary = read_csv_to_dicts(SUMMARY_FILE)
    app_status = read_csv_to_dicts(STATUS_FILE)
    sm = {row.get("job_id"): row for row in summary} if summary else {}
    records = []
    for row in app_status:
        job_id = row.get("job_id")
        summary_row = sm.get(job_id, {})
        rec = {
            "job_id": job_id,
            "company_name": summary_row.get("company_name", ""),
            "job_title": summary_row.get("job_title", ""),
            "status_update": row.get("status_update") or row.get("status") or "",
            "event_time": row.get("event_time") or "",
            "timestamp": row.get("timestamp") or "",
        }
        records.append(rec)
    # try to sort by job_id then event_time
    try:
        records.sort(key=lambda r: (int(r["job_id"]) if r["job_id"] else 0,
                                    float(r["event_time"]) if r["event_time"] else 0))
    except Exception:
        pass
    return records


@app.route("/events")
def events():
    def gen():
        last_mtime = None
        while True:
            try:
                m = os.path.getmtime(STATUS_FILE) if os.path.exists(STATUS_FILE) else None
                if m != last_mtime:
                    last_mtime = m
                    data = merged_records()
                    payload = json.dumps(data, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                time.sleep(1)
            except GeneratorExit:
                break
            except Exception as e:
                # send error message as data event so client can display
                try:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                except Exception:
                    pass
                time.sleep(2)

    return Response(gen(), mimetype="text/event-stream")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    # Use 0.0.0.0 so EventSource works from other hosts if needed
    app.run(host="0.0.0.0", port=args.port, threaded=True)
