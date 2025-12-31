# DocProc

A simple document processing system for uploading, viewing, and searching PDF documents.

## Features

- Upload PDF documents with validation and size limits
- Extract text and page count from PDF documents
- View paginated list of uploaded documents
- Search across document content with pagination
- View individual document details with extracted text
- Delete documents and associated files
- Tag documents with custom labels
- Filter documents by tag

Uploads are validated by content type, magic bytes, and size limits to ensure safe processing.


## Tech Stack

- **Backend:** FastAPI (Python 3.11+), SQLAlchemy 2.0 (async), PostgreSQL
- **Frontend:** React 18, Vite, React Router
- **Infrastructure:** Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Git

### Running the Application

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd docproc
   ```

2. Start all services:
   ```bash
   docker-compose up --build
   ```

3. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development

To run services individually for development:

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Documents

| Method | Endpoint                     | Description                                            |
| ------ | ---------------------------- | ------------------------------------------------------ |
| POST   | `/documents`                 | Upload a PDF document                                  |
| GET    | `/documents`                 | List documents (supports pagination and tag filtering) |
| GET    | `/documents/{id}`            | Get document details                                   |
| DELETE | `/documents/{id}`            | Delete a document                                      |
| POST   | `/documents/{id}/tags`       | Add tags to a document                                 |
| GET    | `/documents/{id}/tags`       | List tags for a document                               |
| DELETE | `/documents/{id}/tags/{tag}` | Remove a tag from a document                           |

### Search

| Method | Endpoint            | Description                                       |
| ------ | ------------------- | ------------------------------------------------- |
| GET    | `/search?q={query}` | Search documents by content (supports pagination) |

### Health

| Method | Endpoint  | Description           |
| ------ | --------- | --------------------- |
| GET    | `/health` | Health check endpoint |



## Common Query Parameters

### Pagination

- `skip`: number of records to skip
- `limit`: maximum number of records to return (max 1000)

Used by:
- GET /documents
- GET /search

Example:
GET /documents?skip=0&limit=50


### Tag Filtering (Documents only)

- `tag`: tag to filter by

Example:
GET /documents?tag=important

## Limits

The application enforces reasonable limits for uploaded files and tags,
such as maximum file size and tag length.

These limits are currently enforced at the application level and can be
promoted to environment configuration if operational requirements evolve.




## Project Structure

```
docproc/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py         # Configuration
│   │   ├── database.py       # Database setup
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── routes/           # API routes
│   │   └── services/         # Business logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── api.js           # API client
│   │   └── App.jsx          # Main application
│   ├── Dockerfile
│   └── package.json
├── scripts/
│   └── seed_data.py         # Test data seeding
├── docker-compose.yml
└── README.md
```

## Environment Variables

### Backend

| Variable       | Description                       |
| -------------- | --------------------------------- |
| `DATABASE_URL` | PostgreSQL connection string      |
| `SECRET_KEY`   | Application secret key (required) |
| `UPLOAD_DIR`   | Directory for uploaded files      |
| `CORS_ORIGINS` | Allowed CORS origins              |


> All backend environment variables must be provided via environment configuration.
> The application fails fast on startup if required variables are missing, avoiding insecure defaults.




### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |
