.PHONY: start-worker test execute

start-worker:
	uv run python src/entrypoints/worker.py

test:
	uv run pytest -v

# Example: make execute workflow=igf-cerveau-daily input='{"batch_size": 3, "dry_run": true}'
execute:
	uv run python -c "import asyncio, json, os, sys; \
	from mistralai.client import Mistral; \
	input=json.loads('$(input)'); \
	client=Mistral(api_key=os.environ['MISTRAL_API_KEY']); \
	e=client.workflows.execute_workflow(workflow_identifier='$(workflow)', input=input); \
	print(e.model_dump_json(indent=2))"
