# Anomaly Detection Application

A FastAPI-based application for detecting anomalies in financial and transactional data.

## Quick Start

1. **Initial Setup**

   ```bash
   ./setup.sh
   ```

   This will create the necessary directories and configuration files.

2. **Configure Environment**
   Edit the `.env` file with your specific configuration:

   ```bash
   nano .env
   ```

3. **Start the Application**

   ```bash
   docker-compose up --build
   ```

4. **Access the Application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Interactive API: http://localhost:8000/redoc

## Environment Configuration

The application uses environment variables for configuration. Copy `env.template` to `.env` and modify as needed:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection for caching and task queue
- `SECRET_KEY`: Change this in production!
- `CORS_ORIGINS`: Allowed frontend origins

## Development

For detailed development instructions, see:

- `backend/README.md` - Backend development guide
- `frontend/` - Frontend development (if applicable)

## Dependencies

The application requires:

- Docker and Docker Compose
- PostgreSQL (via Docker)
- Redis (via Docker)

All Python dependencies are managed in `requirements.txt`.
