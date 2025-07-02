# Health Report FastAPI Microservice

This is the backend microservice for the Lab Report Analyzer project. It provides OCR and AI-powered extraction of health parameters from uploaded PDF and image lab reports.

## Related Repositories

- **Frontend:** [Health Report Next.js App](https://github.com/vivekbopaliya/lab-report-analyzer)


## Features

- Accepts file uploads (PDF, JPG, PNG) from the Next.js frontend
- Extracts text using OCR (Tesseract, PyMuPDF, or similar)
- Parses and returns structured health parameters for further analysis
- Designed to be stateless and easy to deploy

## Usage

1. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at [http://localhost:8000](http://localhost:8000)

## Environment Variables

The FastAPI microservice uses a `.env` file for configuration. Here are the variables and what they control:

- `API_HOST` — The host address for the FastAPI server (default: `0.0.0.0` to listen on all interfaces).
- `API_PORT` — The port the FastAPI server runs on (default: `8000`).
- `LOG_LEVEL` — Logging level for the server (e.g., `INFO`, `DEBUG`).
- `ALLOWED_ORIGINS` — List of allowed origins for CORS, e.g., `["http://localhost:3000", "http://127.0.0.1:3000"]` to allow requests from your Next.js frontend.

## API Endpoints

- `GET /` — Root endpoint. Returns a welcome message and version.
- `GET /health` — Health check endpoint. Returns service status.
- `POST /extract-text/image` — Upload an image file to extract text using OCR.
- `POST /extract-text/pdf` — Upload a PDF file to extract text.
- `POST /parse-parameters` — Send extracted text to parse and return health parameters.
- `POST /process-document` — Upload a PDF or image file and get extracted health parameters in one step.

