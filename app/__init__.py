from pathlib import Path
from typing import Dict, List

import json

from flask import Flask, redirect, render_template, request, url_for, Response, flash

import cv2

HOSTS_FILE = Path("data/hosts.json")
def load_hosts() -> List[Dict]:
    if not HOSTS_FILE.exists():
        HOSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        HOSTS_FILE.write_text("[]", encoding="utf-8")
    try:
        return json.loads(HOSTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_hosts(hosts: List[Dict]) -> None:
    HOSTS_FILE.write_text(json.dumps(hosts, indent=2), encoding="utf-8")


def build_rtsp_url(host: Dict) -> str:
    username = host.get("username", "")
    password = host.get("password", "")
    ip_address = host.get("ip_address", "")
    port = host.get("port", 554)
    channel = str(host.get("channel", "1"))
    stream = str(host.get("stream", "1")).zfill(2)

    auth_part = f"{username}:{password}@" if username or password else ""
    return (
        f"rtsp://{auth_part}{ip_address}:{port}/Streaming/channels/{channel}{stream}"
    )


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "change-me"  # nosec - demo application

    @app.context_processor
    def inject_helpers():
        return {"build_rtsp_url": build_rtsp_url}

    @app.route("/")
    def index():
        return redirect(url_for("viewer"))

    @app.route("/viewer")
    def viewer():
        hosts = load_hosts()
        return render_template("viewer.html", hosts=hosts)

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        hosts = load_hosts()

        if request.method == "POST":
            form_type = request.form.get("form_type")

            def parse_int(value, default):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return default

            if form_type == "single":
                host = {
                    "name": request.form.get("name", ""),
                    "ip_address": request.form.get("ip_address", "").strip(),
                    "username": request.form.get("username", "").strip(),
                    "password": request.form.get("password", "").strip(),
                    "port": parse_int(request.form.get("port", 554) or 554, 554),
                    "channel": parse_int(request.form.get("channel", 1) or 1, 1),
                    "stream": parse_int(request.form.get("stream", 1) or 1, 1),
                }
                if host["ip_address"]:
                    hosts.append(host)
                    save_hosts(hosts)
                    flash("Host added successfully.", "success")
                else:
                    flash("IP address is required to add a host.", "error")

            elif form_type == "bulk":
                raw_hosts = request.form.get("bulk_hosts", "")
                username = request.form.get("bulk_username", "").strip()
                password = request.form.get("bulk_password", "").strip()
                port = parse_int(request.form.get("bulk_port", 554) or 554, 554)
                channel = parse_int(request.form.get("bulk_channel", 1) or 1, 1)
                stream = parse_int(request.form.get("bulk_stream", 1) or 1, 1)

                added = 0
                for line in raw_hosts.splitlines():
                    ip_address = line.strip()
                    if not ip_address:
                        continue
                    host = {
                        "name": "",
                        "ip_address": ip_address,
                        "username": username,
                        "password": password,
                        "port": port,
                        "channel": channel,
                        "stream": stream,
                    }
                    hosts.append(host)
                    added += 1

                if added:
                    save_hosts(hosts)
                    flash(f"Added {added} host(s) successfully.", "success")
                else:
                    flash("No valid IP addresses provided.", "error")

            elif form_type == "delete":
                index = request.form.get("index")
                try:
                    idx = int(index)
                    removed = hosts.pop(idx)
                    save_hosts(hosts)
                    flash(
                        f"Removed host {removed.get('ip_address', 'unknown')}.",
                        "success",
                    )
                except (ValueError, IndexError):
                    flash("Could not remove the selected host.", "error")

            return redirect(url_for("settings"))

        return render_template("settings.html", hosts=hosts)

    def stream_generator(rtsp_url: str):
        cap = None
        try:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                yield from _error_frame("Unable to open stream.")
                return

            while True:
                success, frame = cap.read()
                if not success:
                    yield from _error_frame("Stream interrupted.")
                    break

                ret, buffer = cv2.imencode(".jpg", frame)
                if not ret:
                    continue
                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
        finally:
            if cap is not None:
                cap.release()

    def _error_frame(message: str):
        import numpy as np

        canvas = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(
            canvas,
            message,
            (10, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
        ret, buffer = cv2.imencode(".jpg", canvas)
        if not ret:
            return
        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

    @app.route("/stream/<int:host_id>")
    def stream(host_id: int):
        hosts = load_hosts()
        try:
            host = hosts[host_id]
        except IndexError:
            return Response(status=404)

        rtsp_url = build_rtsp_url(host)
        return Response(
            stream_generator(rtsp_url),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    return app
