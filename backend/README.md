# Anomaly Detection Backend

A FastAPI-based backend for anomaly detection in financial transaction data using ETL (Extract, Transform, Load) architecture.

## Features

- **File Upload & Processing**: Support for CSV, JSON, Excel, SIE4, and XML formats
- **Modular Algorithm Framework**: Statistical, rule-based, and ML-based anomaly detection
- **Strategy Management**: Configurable detection strategies with preset options
- **Async Processing**: Celery-based background task processing
- **RESTful API**: Comprehensive API with automatic OpenAPI documentation
- **Database Storage**: PostgreSQL with optimized indexing for large datasets

## Architecture

### ETL Pipeline

- **Extract**: File upload, validation, and parsing
- **Transform**: Data preprocessing and anomaly detection algorithms
- **Load**: Storage of raw data, processed data, and analysis results

### Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **PostgreSQL**: Robust database with JSON support
- **Redis**: Caching and Celery message broker
- **Celery**: Distributed task queue for async processing
- **SQLAlchemy**: ORM with async support
- **Pandas/NumPy**: Data processing and analysis
- **Scikit-learn**: Machine learning algorithms

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Development Setup

1. **Clone the repository and navigate to backend:**

   ```bash
   cd backend
   ```

2. **Start services with Docker Compose:**

   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Celery Flower (task monitoring): http://localhost:5555

### Local Development (without Docker)

1. **Create virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start PostgreSQL and Redis:**

   ```bash
   # Using Docker for services only
   docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

5. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Health Checks

- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with service status
- `GET /api/v1/health/readiness` - Kubernetes readiness probe
- `GET /api/v1/health/liveness` - Kubernetes liveness probe

### File Upload (Coming Soon)

- `POST /api/v1/upload` - Upload transaction data files
- `GET /api/v1/upload/{upload_id}/status` - Check upload processing status
- `GET /api/v1/upload/history` - List recent uploads

### Analysis Management (Coming Soon)

- `POST /api/v1/analysis/run` - Trigger anomaly detection analysis
- `GET /api/v1/analysis/{run_id}/status` - Check analysis progress
- `GET /api/v1/analysis/{run_id}/results` - Get analysis results

### Transaction Data (Coming Soon)

- `GET /api/v1/transactions` - List transactions with filtering
- `GET /api/v1/transactions/{transaction_id}` - Get transaction details
- `GET /api/v1/transactions/anomalies` - Get flagged transactions

### Strategy Management (Coming Soon)

- `GET /api/v1/strategies` - List available strategies
- `POST /api/v1/strategies` - Create custom strategy
- `PUT /api/v1/strategies/{strategy_id}` - Update strategy
- `GET /api/v1/strategies/{strategy_id}/preview` - Preview strategy impact

## Database Schema

### Core Tables

- **file_uploads**: Track uploaded files and processing status
- **transactions**: Store raw and processed transaction data
- **strategies**: Store anomaly detection strategy configurations
- **analysis_runs**: Track analysis execution and progress
- **anomaly_scores**: Store algorithm-generated anomaly scores
- **rule_flags**: Store rule-based detection flags

## Algorithm Framework

### Statistical Methods

- Z-Score analysis with configurable thresholds
- Correlation analysis for related transactions
- Time series anomaly detection
- Moving average deviations

### Rule-Based Methods

- Weekend transaction threshold rules
- Unusual periodization patterns
- Account-specific rules
- Time-based pattern detection

### ML-Based Methods

- Isolation Forest for outlier detection
- Autoencoders for pattern recognition
- Clustering-based anomaly detection
- Ensemble methods

## Configuration

### Environment Variables

```bash
# Application
APP_NAME=Anomaly Detection API
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/anomaly_detection

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# File Upload
MAX_FILE_SIZE=104857600  # 100MB
UPLOAD_DIR=./uploads
ALLOWED_FILE_TYPES=["csv","json","xlsx","xls","xml","sie4"]

# API
CORS_ORIGINS=["http://localhost:3000"]
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_api/test_health.py
```

## Development

### Adding New Algorithms

1. Create algorithm class inheriting from `AnomalyDetectionAlgorithm`
2. Implement required methods: `name()`, `algorithm_type()`, `detect()`, `validate_config()`
3. Register algorithm in the appropriate module
4. Add configuration schema and tests

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## Deployment

### Production Considerations

- Use managed PostgreSQL service
- Configure Redis cluster for high availability
- Set up proper logging and monitoring
- Use environment-specific configuration
- Implement proper backup strategies

### Docker Production Build

```bash
docker build -t anomaly-detection-backend .
docker run -p 8000:8000 anomaly-detection-backend
```

## Contributing

1. Follow the existing code structure and patterns
2. Write tests for new features
3. Update documentation
4. Follow Python PEP 8 style guidelines
5. Use type hints throughout the codebase

## License

[Add your license information here]
