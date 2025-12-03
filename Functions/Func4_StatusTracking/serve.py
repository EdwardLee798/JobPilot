from flask import Flask, Response, send_from_directory, request, jsonify
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

# try import agent from status_tracking package; fall back gracefully if unavailable
try:
    from status_tracking import agent, config
except Exception as e:
    agent = None
    config = None
    print(f"Warning: could not import status_tracking.agent: {e}")


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
            "job_desc": summary_row.get("job_desc", ""),
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


# @app.route('/api/chat', methods=['POST'])
# def chat_api():
#     """Simple endpoint that forwards a user's message to the `status_tracking.agent` and
#     returns the assistant reply as JSON. Expects JSON: {"message": "..."}.
#     """
#     if agent is None:
#         return jsonify({"error": "Agent not available on server"}), 500

#     try:
#         payload = request.get_json(silent=True) or {}
#         message = payload.get('message', '')
#         if not message:
#             return jsonify({"error": "Empty message"}), 400

#         # invoke the agent
#         resp = agent.invoke(
#             input={"messages": [("user", message)]},
#             config=config
#         )

#         print("===================================================")
#         print(resp)
#         print("===================================================")

        
#         # extract reply text robustly
#         reply_text = ''
#         try:
#             if isinstance(resp, dict):
#                 msgs = resp.get('messages') or resp.get('output')
#             else:
#                 msgs = getattr(resp, 'messages', None)

#             if msgs:
#                 last = msgs[-1]
#                 if isinstance(last, dict):
#                     reply_text = last.get('content') or last.get('text') or str(last)
#                 else:
#                     reply_text = getattr(last, 'content', None) or str(last)
#             else:
#                 reply_text = str(resp)
#         except Exception:
#             reply_text = str(resp)

#         return jsonify({"reply": reply_text})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@app.route('/api/chat_stream', methods=['GET', 'POST'])
def chat_stream():
    """Stream responses from `status_tracking.agent.stream` to the client using SSE.
    Clients should POST JSON {"message": "..."} and receive Server-Sent Events
    with payloads of the form: {"type": "delta", "content": "partial text"}
    and a final {"type": "done"} event when streaming completes.
    """
    if agent is None:
        return jsonify({"error": "Agent not available on server"}), 500

    # support GET (EventSource) and POST (fetch)
    if request.method == 'GET':
        message = request.args.get('message', '')
    else:
        payload = request.get_json(silent=True) or {}
        message = payload.get('message', '')
    if not message:
        return jsonify({"error": "Empty message"}), 400

    def gen():
        try:
            # stream from agent
            prev_content = ""
            for chunk in agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                stream_mode="values",
                config=config
            ):
                # each chunk contains state; pick latest message
                try:
                    latest = chunk["messages"][-1]
                except Exception:
                    latest = None

                # try attribute access then mapping access
                content = None
                tool_calls = None
                if latest is not None:
                    content = getattr(latest, 'content', None)
                    if content is None and isinstance(latest, dict):
                        content = latest.get('content') or latest.get('text')
                    tool_calls = getattr(latest, 'tool_calls', None)
                    if tool_calls is None and isinstance(latest, dict):
                        tool_calls = latest.get('tool_calls') or latest.get('toolCalls')

                if content:
                    # compute the longest common prefix (LCP) between prev_content and content
                    try:
                        s1 = str(prev_content or '')
                        s2 = str(content or '')
                        # find lcp length
                        lcp = 0
                        max_l = min(len(s1), len(s2))
                        while lcp < max_l and s1[lcp] == s2[lcp]:
                            lcp += 1
                        # send only the suffix of s2 beyond lcp
                        suffix = s2[lcp:]
                        if suffix:
                            payload = json.dumps({"type": "delta", "content": suffix}, ensure_ascii=False)
                            yield f"data: {payload}\n\n"
                        # update previous content
                        prev_content = s2
                    except Exception:
                        # fallback: send whole content
                        try:
                            payload = json.dumps({"type": "delta", "content": str(content)}, ensure_ascii=False)
                            yield f"data: {payload}\n\n"
                        except Exception:
                            try:
                                payload = json.dumps({"type": "delta", "content": str(content)}, ensure_ascii=False)
                                yield f"data: {payload}\n\n"
                            except Exception:
                                # last resort: send minimal JSON-safe message
                                yield f"data: {{\"type\":\"delta\",\"content\":\"{str(content)}\"}}\n\n"
                elif tool_calls:
                    # notify client about tool calls (names)
                    try:
                        names = [tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None) for tc in tool_calls]
                        payload = json.dumps({"type": "tool_calls", "calls": names}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                    except Exception:
                        yield f"data: {{\"type\":\"tool_calls\"}}\n\n"

            # done
            data = json.dumps({"type": "done"})
            yield f"data: {data}\n\n"

        except GeneratorExit:
            # client disconnected
            return
        except Exception as e:
            try:
                data = json.dumps({"type": "error", "error": str(e)})
                yield f"data: {data}\n\n"
            except Exception:
                pass

    return Response(gen(), mimetype='text/event-stream')


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/assets/<path:path>")
def assets_files(path):
    assets_dir = os.path.join(BASE_DIR, "assets")
    return send_from_directory(assets_dir, path)


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    # Use 0.0.0.0 so EventSource works from other hosts if needed
    app.run(host="0.0.0.0", port=args.port, threaded=True)
