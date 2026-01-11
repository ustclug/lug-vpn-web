# Justfile for LUG VPN Web

set shell := ["zsh", "-c"]

default:
    @just --list

# Deploy the application using Docker Compose (Dev Profile)
deploy:
    docker compose --profile dev up -d --build

# Stop the application
down:
    docker compose --profile dev down

# Initialize/Migrate the database
migrate:
    @echo "Initializing database..."
    docker compose --profile dev exec web env PYTHONPATH=. uv run python scripts/init_db.py

# Run tests
test:
    docker compose --profile dev exec web pytest

# Follow logs
logs:
    docker compose --profile dev logs -f
