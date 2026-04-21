run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ingest:
	python scripts/ingest.py

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

logs:
	docker-compose logs -f
