IMAGE_NAME ?= wisper
TAG ?= latest
CONTAINER_NAME ?= $(IMAGE_NAME)_container
CONTAINER_NAME_BASE ?= $(IMAGE_NAME):base
PORT ?= 7000
DOCKERFILE ?= Dockerfile
DOCKERFILE_BASE ?= Dockerfile_base
APP_DIR ?= .
ENV_FILE ?= .env
# Файл, где хранится текущая версия
VERSION_FILE := .version
VERSION := $(shell cat $(VERSION_FILE) 2>/dev/null || echo "0.0.0")


define bump_version
$(eval NEW_VERSION := $(shell echo $(VERSION) | awk -F. '{ $$3+=1; printf("%d.%d.%d", $$1,$$2,$$3) }'))
@echo "Current version: $(VERSION)"
@echo "New version: $(NEW_VERSION)"
@echo $(NEW_VERSION) > $(VERSION_FILE)
endef

.PHONY: build run stop rm tag logs restart clean version
run_bash:
	@echo "🚀 Run application $(CONTAINER_NAME)"
	docker rm $(CONTAINER_NAME) || true
	docker run -ti  --rm \
		--name $(CONTAINER_NAME) \
		--entrypoint=bash \
		-p $(PORT):80 \
		--env-file $(ENV_FILE) \
		$(IMAGE_NAME):$(TAG)

build_base:
	@echo "🔨 Building base docker image $(IMAGE_NAME):$(TAG)"
	docker build -t $(CONTAINER_NAME_BASE) -f $(DOCKERFILE_BASE) $(APP_DIR)

build:
	$(call bump_version)
	@echo "🔨 Building app docker image $(IMAGE_NAME):$(NEW_VERSION)"
	docker build -t $(IMAGE_NAME):$(NEW_VERSION) --build-arg APP_VERSION=$(NEW_VERSION) -f $(DOCKERFILE) $(APP_DIR)
	docker tag $(IMAGE_NAME):$(NEW_VERSION) $(IMAGE_NAME):latest
	docker kill $(CONTAINER_NAME) && docker rm $(CONTAINER_NAME) || echo "Container $(CONTAINER_NAME) is not running"

	docker run --rm -ti -e TESTRUN=1 --env-file=./.env \
				-v ./models:/opt/wisper/models \
				-v ./uploads:/opt/wisper/uploads \
				-p 8000:8000
				--name $(CONTAINER_NAME) $(IMAGE_NAME):latest
	@echo "Created a new docker image: $(IMAGE_NAME):$(NEW_VERSION)"
	make tag NEW_VERSION=$(NEW_VERSION)

tag:
#	@$(call bump_version)
	@git add .
	@git commit -m "Release v$(NEW_VERSION)"
	@git tag -a "v$(NEW_VERSION)" -m "Release v$(NEW_VERSION)"
	#@git push origin "v$(NEW_VERSION)"
	@echo "Created git-tag: v$(NEW_VERSION)"

version:
	@echo "Current version: $(VERSION)"

clean:
	@docker rmi $(IMAGE_NAME):$(VERSION) 2>/dev/null || true
	@echo "Remove image $(IMAGE_NAME):$(VERSION)"

run:
	@echo "🚀 Run application $(CONTAINER_NAME) on port $(PORT) "
	docker run --rm -ti \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		--env-file=$(ENV_FILE) \
		 -v ./models:/opt/wisper/models  -v ./uploads:/opt/wisper/uploads \
		$(IMAGE_NAME):$(TAG)

logs:
	docker logs -f $(CONTAINER_NAME)


stop:
	@echo "🛑 Stop application $(CONTAINER_NAME)"
	docker stop $(CONTAINER_NAME) || true


rm: stop
	@echo "🧹 Remove container $(CONTAINER_NAME)"
	docker rm $(CONTAINER_NAME) || true


restart: rm run
	@echo "♻️ Container $(CONTAINER_NAME) has been restarted"
