# Установить основной пакет (попадет в main)
poetry add fastapi

# Установить пакет для тестов
poetry add --group test pytest

# Установить пакет только для разработки
poetry add --group dev notebook

# Ещё пакет для отладки
poetry add --group debug debugpy


[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.111.0"

[tool.poetry.group.test.dependencies]
pytest = "^8.2.0"

[tool.poetry.group.dev.dependencies]
notebook = "^7.2.0"

[tool.poetry.group.debug.dependencies]
debugpy = "^1.8.1"
