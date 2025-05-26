#!/bin/bash

# Anomaly Detection App Setup Script
echo "Setting up Anomaly Detection Application..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.template .env
    echo "✓ .env file created. Please review and modify the values as needed."
else
    echo "✓ .env file already exists."
fi

# Create uploads directory if it doesn't exist
if [ ! -d uploads ]; then
    echo "Creating uploads directory..."
    mkdir -p uploads
    echo "✓ uploads directory created."
else
    echo "✓ uploads directory already exists."
fi

# Create backend uploads directory if it doesn't exist
if [ ! -d backend/uploads ]; then
    echo "Creating backend uploads directory..."
    mkdir -p backend/uploads
    echo "✓ backend/uploads directory created."
else
    echo "✓ backend/uploads directory already exists."
fi

echo ""
echo "Setup complete! Next steps:"
echo "1. Review and modify .env file with your configuration"
echo "2. Run 'docker-compose up --build' to start the application"
echo "3. The API will be available at http://localhost:8000"
echo "4. API documentation will be at http://localhost:8000/docs" 