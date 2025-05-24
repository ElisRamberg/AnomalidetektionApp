# Database Migrations

This directory contains Alembic database migration files for the anomaly detection backend.

## Setting up Alembic

To initialize Alembic for database migrations:

```bash
# Initialize Alembic (already done)
alembic init migrations

# Generate initial migration
alembic revision --autogenerate -m "Initial database schema"

# Apply migrations
alembic upgrade head
```

## Creating New Migrations

When you modify database models:

```bash
# Generate migration automatically
alembic revision --autogenerate -m "Description of changes"

# Apply new migrations
alembic upgrade head
```

## Migration Commands

```bash
# Show current migration status
alembic current

# Show migration history
alembic history

# Downgrade to previous migration
alembic downgrade -1

# Upgrade to specific migration
alembic upgrade <revision_id>
```

## Note

Migration files will be created here when Alembic is properly configured with our database models. 