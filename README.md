# Cheapest Grocery Finder 🛒

> **⚠️ Work in Progress**: This project is currently under active development. Features and documentation may be incomplete or subject to change.

A microservices-based application that helps users find the best grocery prices across different stores. The system aggregates pricing data, provides price comparisons, and offers predictive insights using machine learning.

## Project Overview

The Cheapest Grocery Finder consists of several microservices:

- **API Gateway**: Routes and manages all incoming requests
- **Auth Service**: Handles user authentication and authorization
- **User Service**: Manages user profiles and preferences
- **Price Service**: Processes and analyzes grocery price data
- **ML Service**: Provides price predictions and trends

## Tech Stack

- FastAPI
- PostgreSQL
- MongoDB
- Docker
- Terraform
- Redis
- React (Frontend)

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Node.js 16+ (for frontend)
- Terraform (for infrastructure)

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/josuejero/grocery-finder.git
cd grocery-finder
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Unix/macOS
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start the services:
```bash
cd infrastructure
docker-compose up -d
```

## Project Structure

```
├── frontend/               # React frontend application
├── infrastructure/         # Docker and Terraform configurations
│   ├── docker-compose.yml
│   └── terraform/
└── services/              # Backend microservices
    ├── api_gateway/
    ├── auth_service/
    ├── price_service/
    └── user_service/
```

## Contributing

This project is still in development. Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
