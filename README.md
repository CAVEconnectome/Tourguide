Welcome to GuidebookV2!

Run locally:
0. Install `uv` (https://docs.astral.sh/uv/)
1. Clone the repository
2. Run with `uv run --with gunicorn==23.0.0 --env-file .env.debug gunicorn --workers=2 run:app`

Build and run with docker:
1. Build with something like: `docker build --platform linux/amd64 . -t guidebookv2`
2. Run using the docker env file: `./launch_in_docker.sh`