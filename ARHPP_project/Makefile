.PHONY: help install test run docker prod package clean

help:
	@echo "ARHPP Makefile"
	@echo "  make install    Install dependencies"
	@echo "  make test       Run all tests"
	@echo "  make run        Run API server"
	@echo "  make docker     Build Docker image"
	@echo "  make prod       Run production compose"
	@echo "  make package    Build ZIP"
	@echo "  make clean      Remove caches"

install:
	pip install -r requirements.txt
	pip install scikit-learn reportlab pyinstaller psutil

test:
	pytest tests/ -v

run:
	python -m api.server

docker:
	docker build -t arhpp:2.0.0 .

prod:
	docker compose up -d

stop:
	docker compose down

package:
	python build_arhpp.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build dist .pytest_cache htmlcov ARHPP_v2.0.zip
