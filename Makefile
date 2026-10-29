.PHONY: install train eval test run

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

train:
	python scripts/train_production_clinicalbert.py --epochs 3 --synthetic 160 --trainable-last-n 2

eval:
	python scripts/evaluate_baselines.py

test:
	pytest tests/

run:
	python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
