PRETAG ?= danubise
IMAGE_NAME ?= wisper
TAG ?= latest
CONTAINER_NAME ?= $(IMAGE_NAME)_container
CONTAINER_NAME_BASE ?= $(IMAGE_NAME):base
PORT ?= 8000
DOCKERFILE ?= Dockerfile
DOCKERFILE_BASE ?= Dockerfile_base
APP_DIR ?= .
ENV_FILE ?= .env
# Файл, где хранится текущая версия
VERSION_FILE := .version
VERSION := $(shell cat $(VERSION_FILE) 2>/dev/null || echo "0.0.0")
.DEFAULT_GOAL := help

define bump_version
$(eval NEW_VERSION := $(shell echo $(VERSION) | awk -F. '{ $$3+=1; printf("%d.%d.%d", $$1,$$2,$$3) }'))
@echo "Current version: $(VERSION)"
@echo "New version: $(NEW_VERSION)"
@echo $(NEW_VERSION) > $(VERSION_FILE)
endef

.PHONY: help build run stop rm tag logs restart clean version

run_bash: ## Комагда запускает последний собранный контейнер в режиме консоли, подменяет entrypoint=bash, также добавляет все необзодимые переменные окружения. В команду можно добавить монтирование всех необходимые директорий и настроить проброс портов.
	@echo "🚀 Run application $(CONTAINER_NAME)"
	docker rm $(CONTAINER_NAME) || true
	docker run -ti  --rm \
		--name $(CONTAINER_NAME) \
		--entrypoint=bash \
		-p $(PORT):80 \
		--env-file $(ENV_FILE) \
		$(IMAGE_NAME):$(TAG)

build_base: ## Собирает базовый Docker-образ из $(DOCKERFILE_BASE)
	@echo "🔨 Building base docker image $(IMAGE_NAME):$(TAG)"
	docker build -t $(CONTAINER_NAME_BASE) -f $(DOCKERFILE_BASE) $(APP_DIR)

build: stop rm ## Собирает основной Docker-образ из $(DOCKERFILE). Возможно надо в начале собрать базовый образ команды build_base. После успешной сборки эта команды пытается запустить контейнер с переменной окружения TESTRUN=1, ожидается что сервис выполнит тестовый запуск и завершит работу самостоятельно.
	$(call bump_version)
	@echo "🔨 Building app docker image $(IMAGE_NAME):$(NEW_VERSION)"
	docker build -t $(PRETAG)/$(IMAGE_NAME):$(NEW_VERSION) --build-arg APP_VERSION=$(NEW_VERSION) -f $(DOCKERFILE) $(APP_DIR)
	docker tag $(PRETAG)/$(IMAGE_NAME):$(NEW_VERSION)  $(PRETAG)/$(IMAGE_NAME):latest
	docker kill $(CONTAINER_NAME) && docker rm $(CONTAINER_NAME) || echo "Container $(CONTAINER_NAME) is not running"

	docker run --rm -ti -e TESTRUN=1 --env-file=./.env \
				-v ./models:/opt/wisper/models \
				-v ./uploads:/opt/wisper/uploads \
				--entrypoint=python3 \
				-p 8000:8000 \
				--name $(CONTAINER_NAME) $(IMAGE_NAME):latest api_service.py
	@echo "Created a new docker image: $(IMAGE_NAME):$(NEW_VERSION)"
	make tag NEW_VERSION=$(NEW_VERSION)

run: stop rm ## Запускает контейнер из текущего образа с монтированием .env и пробросом порта
	@echo "🚀 Run application $(CONTAINER_NAME) on port $(PORT) "
	docker run --rm -ti \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		--env-file=$(ENV_FILE) \
		 -v ./models:/opt/wisper/models  -v ./uploads:/opt/wisper/uploads \
		$(IMAGE_NAME):$(TAG)

tag:
#	@$(call bump_version)
	@git add .
	@git commit -m "Release v$(NEW_VERSION)"
	@git tag -a "v$(NEW_VERSION)" -m "Release v$(NEW_VERSION)"
	#@git push origin "v$(NEW_VERSION)"
	@echo "Created git-tag: v$(NEW_VERSION)"

version: ## Показывает последнюю собранную версию сервиса и контейнера. Версия сохраняется в файле .version
	@echo "Current version: $(VERSION)"

clean:
	@docker rmi $(IMAGE_NAME):$(VERSION) 2>/dev/null || true
	@echo "Remove image $(IMAGE_NAME):$(VERSION)"


logs:
	docker logs -f $(CONTAINER_NAME)


stop:
	@echo "🛑 Stop application $(CONTAINER_NAME)"
	docker stop $(CONTAINER_NAME) || true


rm: stop
	@echo "🧹 Remove container $(CONTAINER_NAME)"
	docker rm $(CONTAINER_NAME) || true

## build: Собирает основной Docker-образ из $(DOCKERFILE)
restart: rm run
	@echo "♻️ Container $(CONTAINER_NAME) has been restarted"


## help: Показывает список всех доступных команд Makefile с описанием
help:
	@echo "Доступные команды:"
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z0-9_\-]+:.*##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
