#FROM python:3.10.13-slim-bullseye  AS poetry
#ARG APP_USER=vkuser
#ARG APP_UID=4285
#ARG APP_HOME=/opt/${APP_USER}/app
## Creating spitch userd with predefined id
#RUN apt-get update && apt-get install -y ffmpeg  && rm -fr /var/lib/apt/lists/*
#RUN useradd -u ${APP_UID} -m ${APP_USER} && mkdir /opt/poetry
#USER ${APP_USER}
## Configuring working directory
#WORKDIR $APP_HOME
#
## Coping files
#COPY poetry.lock pyproject.toml README.md ./
#
#ENV POETRY_HOME=/opt/poetry
#ENV POETRY_VIRTUALENVS_IN_PROJECT=true
#ENV PATH="$POETRY_HOME/bin:/home/${APP_USER}/.local/bin:$PATH"
#
#RUN pip3 install --no-cache-dir poetry==2.1.3 && \
#    poetry install --no-interaction --no-ansi -vvv --no-root && \
#    rm -fr poetry.lock pyproject.toml README.md && mkdir -p /opt/${APP_USER}/app/wisper_app

FROM python:3.10.13-slim-bullseye AS runtime
ARG APP_USER=wisper
ARG APP_UID=1000
ARG APP_HOME=/opt/${APP_USER}
ARG POETRY_VERSION=2.2.1
ARG APP_VERSION=0.0.0
ARG maintainer="Vyacheslav <you@example.com>"
ARG description="Telegram Exporter Bot"
ARG PROJECT_NAME=tgexporter
ENV APP_HOME=${APP_HOME} \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/opt/poetry/bin:${APP_HOME}/.venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION}

# Копируем виртуальное окружение и зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -u ${APP_UID} -m -s /usr/sbin/nologin ${APP_USER}  \
    && mkdir -p ${POETRY_HOME}  \
    && chown ${APP_USER}:${APP_USER} ${POETRY_HOME} -R
WORKDIR ${APP_HOME}

FROM runtime AS runtime2

COPY --from=wisper:base --chown=${APP_USER}:${APP_USER} ${APP_HOME} ${APP_HOME}
# Копируем только исходники приложения (не ломая кэш зависимостей)
#COPY --chown=${APP_USER}:${APP_USER} ${PROJECT_NAME} ${APP_HOME}/${PROJECT_NAME}
COPY --chown=${APP_USER}:${APP_USER} api_service.py ${APP_HOME}/

RUN chown ${APP_USER}:${APP_USER} ${POETRY_HOME} -R
USER ${APP_USER}

# Метаданные (полезно для CI/CD)
LABEL maintainer=${maintainer} \
      version=${APP_VERSION} \
      description=${description}



# Runing gen-cloud-audio-uploading script
CMD ["uvicorn" ,"api_service:app" ,"--reload", "--host", "0.0.0.0","--port", "8000" ]