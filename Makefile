
help: ## Show help
	@grep -E '^[.a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

test: ## Run tests
	pytest

fast-test: ## Run tests that are not slow
	pytest -m "not slow"

data: ## Download data from kaggle
	mkdir data
	kaggle competitions download -c llm-zoomcamp-2024-competition
	unzip llm-zoomcamp-2024-competition.zip -d data
	rm llm-zoomcamp-2024-competition.zip

pre-commit: ## Install pre commit hooks
	pre-commit install
	pre-commit install-hooks

format: ## Format with pre commit
	pre-commit run --all-files

bump: ## Update requirements
	uv pip compile deployment/requirements.in -o deployment/requirements.txt
	uv pip compile api/requirements.in -o api/requirements.txt
	uv pip compile app/requirements.in -o app/requirements.txt
	uv pip compile tracking/requirements.in -o tracking/requirements.txt

venv: ## Create/Update venv
	uv venv
	. .venv/bin/activate
	uv pip compile pyproject.toml -o requirements.txt
	uv pip install -r requirements.txt
	rm requirements.txt

.PHONY: prefect
prefect: ## Prefect CLI for local server
	docker compose --env-file .env run cli

service-up: ## Start local
	docker compose --env-file .env up --build

service-down: ## Stop local
	docker compose --env-file .env down

localstack-env:
	$(eval export AWS_ACCESS_KEY_ID=test)
	$(eval export AWS_SECRET_ACCESS_KEY=test)
	$(eval export AWS_DEFAULT_REGION=us-east-1)
	$(eval export LOCALSTACK_ENDPOINT=http://localhost:4566)
	$(eval export TF_VAR_aws_endpoint=${LOCALSTACK_ENDPOINT})

localstack-start: localstack-env ## Start LocalStack
	localstack start -d

localstack-stop: ## Stop LocalStack
	localstack stop

localstack-apply: localstack-env ## Apply Terraform configuration to LocalStack
	cd infrastructure && \
	tflocal init && \
	tflocal apply -auto-approve -var-file=localstack.tfvars && \
	echo "ALB DNS Name: $$(tflocal output -raw alb_dns_name)"

localstack-destroy: localstack-env ## Destroy Terraform resources in LocalStack
	cd infrastructure && tflocal destroy -auto-approve

localstack-clean: localstack-destroy localstack-stop ## Clean up local infrastructure and stop LocalStack

aws-apply: ## Apply Terraform configuration to your aws account
	terraform init
	terraform apply -auto-approve -var-file=infrastructure/terraform.tfvars
