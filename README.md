# Onwa — Community Book Circulation Platform

A community-powered platform where physical books travel reader-to-reader, each carrying a digital Book Passport tracking its journey.

## Stack
- **Backend:** Python Flask + SQLite
- **Frontend:** HTML, CSS, Vanilla JS
- **Maps:** Leaflet.js | **Charts:** Chart.js

## Run Locally

```bash
pip install flask
python app.py
```

Visit → http://localhost:5000

## Login Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@onwa.com | admin123 | Admin |
| shalem@onwa.com | password | Member |

## Features
- Book Passport journey tracking
- Queue system with notifications
- Live search (debounced AJAX)
- Reading log (want / reading / finished)
- UK map view (Leaflet.js)
- Impact dashboard (CO2, miles)
- Admin panel (add/delete books, charts)

## Files
| File | Description |
|------|-------------|
| `app.py` | Flask backend + DB schema |
| `TECHNICAL_REPORT.md` | Full technical documentation |
| `desc.html` | Platform description |
| `templates/` | Jinja2 HTML templates |
| `static/css/animations.css` | 15+ keyframe animations |
