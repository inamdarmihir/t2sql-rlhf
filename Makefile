.PHONY: help build up down logs clean dev-backend dev-frontend

help:
	@echo "Text2SQL Docker Commands"
	@echo "========================"
	@echo "make build        - Build all Docker images"
	@echo "make up           - Start all services"
	@echo "make down         - Stop all services"
	@echo "make logs         - View logs from all services"
	@echo "make clean        - Stop services and remove volumes"
	@echo "make dev-backend  - Run backend in development mode"
	@echo "make dev-frontend - Run frontend in development mode"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"
	@echo "Qdrant: http://localhost:6333"

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	@echo "All services stopped and volumes removed"

dev-backend:
	cd backend && uvicorn api:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev
