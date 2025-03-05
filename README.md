Welcome to TourGuide (aka Guidebook v2)!

Run locally:
0. Install `uv` (https://docs.astral.sh/uv/)
1. Clone the repository
2. Run with `uv run --with gunicorn==23.0.0 --env-file .env.debug gunicorn --workers=2 run:app`