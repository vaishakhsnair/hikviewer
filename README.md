# Hik RTSP Viewer

A lightweight Flask application for configuring Hikvision-style RTSP camera streams and viewing them in a browser-friendly grid. Streams are proxied through the server and rendered as MJPEG feeds so you can monitor multiple cameras without a dedicated RTSP client.

## Features

- Settings interface to add individual cameras or bulk import by pasting newline-separated IP addresses.
- Stores camera configuration (IP, credentials, channel/stream numbers, port) in a simple JSON file.
- Generates RTSP URLs in the format `rtsp://<username>:<password>@<ip>:<port>/Streaming/channels/<channel><stream>`.
- Live viewer grid that displays each configured camera and exposes the underlying RTSP URL.
- Ability to remove hosts from the configuration.

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the development server**

   ```bash
   flask --app app:create_app --debug run
   ```

   The application will be available at [http://localhost:5000](http://localhost:5000).

3. **Add cameras**

   - Visit the **Settings** page to add a single camera or bulk import multiple IP addresses with shared credentials.
   - Configurations are stored in `data/hosts.json`. You can edit this file manually if needed.

4. **View streams**

   - Open the **Viewer** page to see the camera grid. Each stream is exposed as an MJPEG feed via `/stream/<id>`.
   - The viewer displays an error frame if the RTSP stream cannot be opened.

## Notes

- This project uses OpenCV to bridge RTSP to MJPEG; ensure the server has enough resources to handle the desired number of streams.
- For production usage, consider running the Flask app behind a WSGI server (e.g., Gunicorn) and tightening secrets/credentials management.
- Replace the default `app.secret_key` with a secure value before deploying.
