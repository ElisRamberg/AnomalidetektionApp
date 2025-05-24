# Backend Architecture Plan for Anomaly Detection System

## Executive Summary

This document outlines the backend architecture for an anomaly detection system following ETL (Extract, Transform, Load) principles. The backend will support file uploads, data preprocessing, modular anomaly detection algorithms, and flexible storage for analysis results.

## System Overview

### Architecture Pattern: ETL (Extract, Transform, Load)
- **Extract**: File upload and validation system
- **Transform**: Data preprocessing and anomaly detection algorithms
- **Load**: Database storage for raw data, features, and analysis results

### Design Principles
- **Modularity**: Easy to add/modify detection algorithms
- **Testability**: Clear separation of concerns with comprehensive testing
- **Scalability**: Async processing for large datasets
- **Flexibility**: Algorithm results stored as scores, not binary classifications

## Technology Stack

### Core Framework: FastAPI + Python 3.11+
**Why chosen:**
- **Performance**: Async support, excellent for I/O operations
- **Documentation**: Auto-generated OpenAPI/Swagger docs
- **Type Safety**: Built-in Pydantic models for data validation
- **AI/ML Integration**: Seamless integration with pandas, scikit-learn, etc.
- **Testing**: Great testing ecosystem with pytest

### Database: PostgreSQL + SQLAlchemy
**Why chosen:**
- **ACID Compliance**: Critical for financial data integrity
- **JSON Support**: Native JSON columns for flexible metadata storage
- **Performance**: Excellent indexing and query optimization
- **Ecosystem**: Strong Python integration with SQLAlchemy ORM

### Additional Libraries
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **scikit-learn**: Machine learning algorithms
- **Celery + Redis**: Async task processing for large files
- **Pydantic**: Data validation and serialization
- **pytest**: Testing framework
- **Alembic**: Database migrations

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── database.py            # Database connection setup
│   │
│   ├── api/                   # API routes
│   │   ├── __init__.py
│   │   ├── upload.py          # File upload endpoints
│   │   ├── analysis.py        # Analysis trigger endpoints
│   │   ├── transactions.py    # Transaction data endpoints
│   │   ├── strategies.py      # Strategy management endpoints
│   │   └── health.py          # Health check endpoints
│   │
│   ├── models/                # Database models
│   │   ├── __init__.py
│   │   ├── upload.py          # File upload models
│   │   ├── transaction.py     # Transaction data models
│   │   ├── analysis.py        # Analysis result models
│   │   └── strategy.py        # Strategy configuration models
│   │
│   ├── schemas/               # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── upload.py          # Upload request/response schemas
│   │   ├── transaction.py     # Transaction schemas
│   │   ├── analysis.py        # Analysis schemas
│   │   └── strategy.py        # Strategy schemas
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── file_processor.py  # File parsing and validation
│   │   ├── data_transformer.py # Data preprocessing
│   │   ├── analysis_engine.py # Coordinate anomaly detection
│   │   └── strategy_manager.py # Strategy execution
│   │
│   ├── algorithms/            # Anomaly detection algorithms
│   │   ├── __init__.py
│   │   ├── base.py           # Base algorithm interface
│   │   ├── statistical/      # Statistical methods
│   │   │   ├── __init__.py
│   │   │   ├── zscore.py
│   │   │   ├── correlation.py
│   │   │   └── timeseries.py
│   │   ├── rule_based/       # Domain-specific rules
│   │   │   ├── __init__.py
│   │   │   ├── weekend_threshold.py
│   │   │   └── periodization.py
│   │   └── ml_based/         # Machine learning methods
│   │       ├── __init__.py
│   │       ├── isolation_forest.py
│   │       ├── autoencoder.py
│   │       └── clustering.py
│   │
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   ├── file_validators.py # File format validation
│   │   ├── data_validators.py # Data quality checks
│   │   └── exceptions.py     # Custom exceptions
│   │
│   └── tasks/               # Async tasks (Celery)
│       ├── __init__.py
│       ├── file_processing.py
│       └── analysis_tasks.py
│
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Test configuration
│   ├── test_api/           # API endpoint tests
│   ├── test_services/      # Service layer tests
│   ├── test_algorithms/    # Algorithm tests
│   └── test_utils/         # Utility tests
│
├── migrations/             # Database migrations
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Development environment
└── README.md              # Setup instructions
```

## Database Schema Design

### Core Tables

#### 1. file_uploads
```sql
CREATE TABLE file_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    error_message TEXT,
    metadata JSONB,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2. transactions
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID REFERENCES file_uploads(id),
    external_transaction_id VARCHAR(255),
    amount DECIMAL(15,2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    raw_data JSONB NOT NULL,
    processed_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for performance
    CREATE INDEX idx_transactions_upload_id ON transactions(upload_id);
    CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);
    CREATE INDEX idx_transactions_account_id ON transactions(account_id);
    CREATE INDEX idx_transactions_external_id ON transactions(external_transaction_id);
);
```

#### 3. analysis_runs
```sql
CREATE TABLE analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID REFERENCES file_uploads(id),
    strategy_id UUID REFERENCES strategies(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB,
    
    CREATE INDEX idx_analysis_runs_upload_id ON analysis_runs(upload_id);
    CREATE INDEX idx_analysis_runs_strategy_id ON analysis_runs(strategy_id);
);
```

#### 4. anomaly_scores
```sql
CREATE TABLE anomaly_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id),
    analysis_run_id UUID REFERENCES analysis_runs(id),
    algorithm_type VARCHAR(100) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL,
    score DECIMAL(10,6) NOT NULL,
    confidence DECIMAL(5,4),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Composite index for efficient queries
    CREATE INDEX idx_anomaly_scores_transaction_analysis ON anomaly_scores(transaction_id, analysis_run_id);
    CREATE INDEX idx_anomaly_scores_algorithm ON anomaly_scores(algorithm_type, algorithm_name);
);
```

#### 5. strategies
```sql
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    configuration JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 6. rule_flags
```sql
CREATE TABLE rule_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id),
    analysis_run_id UUID REFERENCES analysis_runs(id),
    rule_name VARCHAR(100) NOT NULL,
    triggered BOOLEAN NOT NULL,
    flag_value TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CREATE INDEX idx_rule_flags_transaction_analysis ON rule_flags(transaction_id, analysis_run_id);
    CREATE INDEX idx_rule_flags_rule_name ON rule_flags(rule_name);
);
```

## ETL Implementation Details

### Extract Phase

#### File Upload Process
1. **Validation**: File type, size, and basic structure validation
2. **Storage**: Temporary file storage with unique identifiers
3. **Parsing**: Format-specific parsers (CSV, JSON, Excel, SIE4, XML)
4. **Error Handling**: Detailed error messages for file format issues

#### Supported File Formats
- **CSV**: Standard comma-separated values
- **JSON**: Structured JSON with transaction arrays
- **Excel**: .xlsx and .xls formats
- **SIE4**: Swedish standard for accounting data
- **XML**: Custom XML schemas for transaction data

### Transform Phase

#### Data Preprocessing
1. **ID Generation**: Create unique transaction IDs if not present
2. **Data Cleaning**: Handle missing values, normalize formats
3. **Validation**: Ensure required fields are present and valid
4. **Enrichment**: Add derived fields (day of week, time period, etc.)

#### Algorithm Framework

```python
# Base Algorithm Interface
class AnomalyDetectionAlgorithm(ABC):
    """Base class for all anomaly detection algorithms"""
    
    @abstractmethod
    def name(self) -> str:
        """Return algorithm name"""
        pass
    
    @abstractmethod
    def algorithm_type(self) -> str:
        """Return algorithm type (statistical, rule_based, ml_based)"""
        pass
    
    @abstractmethod
    def detect(self, transactions: pd.DataFrame, config: dict) -> pd.DataFrame:
        """
        Run anomaly detection
        
        Args:
            transactions: DataFrame with transaction data
            config: Algorithm-specific configuration
            
        Returns:
            DataFrame with columns: transaction_id, score, confidence, metadata
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """Validate algorithm configuration"""
        pass
```

#### Algorithm Types

1. **Statistical Methods**
   - Z-Score analysis with configurable thresholds
   - Correlation analysis for related transactions
   - Time series anomaly detection
   - Moving average deviations

2. **Rule-Based Methods**
   - Weekend transaction thresholds
   - Unusual periodization patterns
   - Account-specific rules
   - Time-based patterns

3. **ML-Based Methods**
   - Isolation Forest for outlier detection
   - Autoencoders for pattern recognition
   - Clustering-based anomaly detection
   - Ensemble methods

### Load Phase

#### Data Storage Strategy
- **Raw Data**: Original transaction data preserved
- **Processed Data**: Cleaned and enriched transaction data
- **Feature Scores**: Algorithm outputs as numerical scores
- **Rule Flags**: Boolean flags from rule-based algorithms
- **Strategy Results**: Aggregated results from strategy configurations

## API Design

### REST API Endpoints

#### File Upload
```
POST /api/v1/upload
- Multipart file upload
- Real-time validation
- Async processing initiation

GET /api/v1/upload/{upload_id}/status
- Check processing status
- Get error details if failed

GET /api/v1/upload/history
- List recent uploads
- Pagination support
```

#### Analysis Management
```
POST /api/v1/analysis/run
- Trigger analysis with strategy
- Async processing

GET /api/v1/analysis/{run_id}/status
- Check analysis progress
- Get partial results

GET /api/v1/analysis/{run_id}/results
- Get complete analysis results
- Support for filtering and pagination
```

#### Transaction Data
```
GET /api/v1/transactions
- List transactions with filtering
- Pagination and sorting
- Include anomaly scores if available

GET /api/v1/transactions/{transaction_id}
- Get detailed transaction info
- Include all algorithm scores and flags

GET /api/v1/transactions/anomalies
- Get only flagged transactions
- Support strategy-based filtering
```

#### Strategy Management
```
GET /api/v1/strategies
- List available strategies
- Include presets and custom strategies

POST /api/v1/strategies
- Create custom strategy
- Validate configuration

PUT /api/v1/strategies/{strategy_id}
- Update strategy configuration
- Re-run validation

GET /api/v1/strategies/{strategy_id}/preview
- Preview strategy impact without running
- Use sample data for estimation
```

## Async Processing with Celery

### Task Types
1. **File Processing**: Parse and validate uploaded files
2. **Data Transformation**: Clean and enrich transaction data
3. **Algorithm Execution**: Run anomaly detection algorithms
4. **Strategy Evaluation**: Apply strategies and calculate results

### Task Architecture
```python
@celery.task(bind=True, max_retries=3)
def process_uploaded_file(self, upload_id: str):
    """Process uploaded file asynchronously"""
    try:
        # File parsing and validation
        # Data cleaning and transformation
        # Store processed data
        # Trigger analysis if requested
    except Exception as exc:
        # Handle errors and retry logic
        pass

@celery.task(bind=True)
def run_anomaly_detection(self, upload_id: str, strategy_id: str):
    """Run anomaly detection algorithms"""
    try:
        # Load strategy configuration
        # Execute configured algorithms
        # Store results
        # Send completion notification
    except Exception as exc:
        # Error handling
        pass
```

## Testing Strategy

### Test Coverage Areas
1. **API Tests**: Endpoint functionality and error handling
2. **Service Tests**: Business logic validation
3. **Algorithm Tests**: Algorithm accuracy and performance
4. **Integration Tests**: End-to-end workflow testing
5. **Performance Tests**: Load testing for large datasets

### Test Data Strategy
- **Sample Files**: Representative test files for each supported format
- **Edge Cases**: Invalid data, missing fields, large files
- **Performance Data**: Large datasets for stress testing

## Security Considerations

### Data Protection
- **File Validation**: Strict validation to prevent malicious uploads
- **Data Sanitization**: Clean all input data
- **Access Control**: Role-based access to sensitive operations
- **Audit Logging**: Track all data access and modifications

### Infrastructure Security
- **Environment Variables**: Secure configuration management
- **Database Security**: Encrypted connections and secure credentials
- **API Security**: Rate limiting and input validation
- **Container Security**: Minimal base images and security scanning

## Deployment Strategy

### Development Environment
- **Docker Compose**: Local development with all services
- **Hot Reloading**: FastAPI development server
- **Test Database**: Isolated PostgreSQL instance

### Production Considerations
- **Container Orchestration**: Kubernetes or Docker Swarm
- **Database**: Managed PostgreSQL service
- **Caching**: Redis for Celery and API caching
- **Monitoring**: Logging, metrics, and alerting
- **Backup Strategy**: Regular database backups

## Future Enhancements

### Performance Optimizations
- **Database Indexing**: Query optimization for large datasets
- **Caching Layer**: Redis caching for frequently accessed data
- **Parallel Processing**: Multi-threaded algorithm execution

### Algorithm Improvements
- **Model Training**: Custom ML models based on historical data
- **Ensemble Methods**: Combine multiple algorithms for better accuracy
- **Real-time Processing**: Stream processing for live transaction data

### User Experience
- **Real-time Updates**: WebSocket connections for live progress
- **Advanced Filtering**: Complex query builder for transaction analysis
- **Export Features**: PDF reports and data export functionality

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- Set up FastAPI application structure
- Implement database models and migrations
- Create basic file upload functionality
- Set up testing framework

### Phase 2: ETL Pipeline (Week 3-4)
- File parsing for all supported formats
- Data transformation and validation
- Basic algorithm framework
- Simple statistical algorithms

### Phase 3: Advanced Algorithms (Week 5-6)
- Rule-based algorithm framework
- ML-based algorithms
- Strategy management system
- Algorithm result storage

### Phase 4: API Completion (Week 7-8)
- Complete all API endpoints
- Async processing with Celery
- Error handling and validation
- Performance optimization

### Phase 5: Testing & Documentation (Week 9-10)
- Comprehensive test suite
- API documentation
- Deployment configuration
- Performance testing

This architecture provides a solid foundation for the anomaly detection system while maintaining flexibility for future enhancements and algorithm improvements.
