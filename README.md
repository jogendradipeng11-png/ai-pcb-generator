# AI PCB Generator

## Run locally

```bash
source .venv/bin/activate
pip install -r requirements.txt
npm install --legacy-peer-deps
export GROQ_API_KEY="your_groq_api_key"
python server.py
```

Open `http://localhost:5000`.

## Deploy to Render

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint** and select the repository.
3. Render reads `render.yaml` and builds the Docker service.
4. In the Render dashboard, set the `GROQ_API_KEY` secret for the service.

The service starts with Gunicorn and listens on Render's `PORT` environment variable.
