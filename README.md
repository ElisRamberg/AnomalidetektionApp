# Anomaly Detection App

A full-stack application for detecting anomalies in financial data with ETL capabilities.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Setup & Run

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd AnomalidetektionApp
   ```

2. **Start all services**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Celery Monitor: http://localhost:5555

## 🏗️ Architecture

### Services
- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Backend**: FastAPI with async support
- **Database**: PostgreSQL for data storage
- **Cache/Queue**: Redis for caching and Celery task queue
- **Worker**: Celery for background processing
- **Monitor**: Flower for task monitoring

### Tech Stack
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Processing**: Pandas, NumPy, Scikit-learn
- **Database**: PostgreSQL with AsyncPG
- **Queue**: Celery with Redis
- **Containerization**: Docker & Docker Compose

## 📁 Project Structure

```
├── frontend/           # Next.js frontend application
├── backend/           # FastAPI backend application
│   ├── app/          # Main application code
│   ├── tests/        # Test files
│   └── migrations/   # Database migrations
├── uploads/          # File upload directory
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 🛠️ Development

### Local Development (without Docker)

1. **Backend Setup**
   ```bash
   cd backend
   pip install -r ../requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Start Services**
   ```bash
   # PostgreSQL and Redis
   docker-compose up postgres redis
   ```

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/anomaly_detection

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# API
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]

# Security
SECRET_KEY=your-secret-key-change-in-production
```

## 📊 Features

- **File Upload**: Support for CSV, Excel, JSON, XML, and SIE4 formats
- **Data Processing**: ETL pipeline with data validation
- **Anomaly Detection**: Multiple algorithms for detecting outliers
- **Real-time Processing**: Background tasks with Celery
- **Interactive Dashboard**: Modern UI with charts and visualizations
- **API Documentation**: Auto-generated with FastAPI

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests (if configured)
cd frontend
npm test
```

## 📝 API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 Troubleshooting

### Common Issues

1. **Port conflicts**: Make sure ports 3000, 8000, 5432, 6379, 5555 are available
2. **Docker issues**: Try `docker-compose down` and `docker-compose up --build`
3. **Database connection**: Ensure PostgreSQL is healthy before backend starts

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend
```

## 🚀 Deployment

For production deployment, update environment variables and use:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📄 License

[Your License Here]
