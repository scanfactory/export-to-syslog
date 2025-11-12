# Syslog Event Exporter

Экспортер событий из Keycloak и множества приложений на удаленные syslog серверы в формате RFC5424

## Описание

Скрипт собирает события из нескольких источников:

1. **Keycloak** - события аутентификации и администрирования (опционально)
2. **Scanfactory** - события из множества Scanfactory приложений через их API

Все события нормализуются к единому формату и отправляются на один или несколько syslog серверов.

## Установка и настройка

### 1. Установить зависимости

```bash
pip3 install -r requirements.txt
```

### 2. Создать директорию для хранилища

```bash
mkdir -p storage
```

### 3. Настроить параметры в config.py

Смотрите подробный гайд по настройке ниже.

## Конфигурация

### Keycloak настройки

```python
KEYCLOAK_ENABLED = False  # Включить/выключить сбор событий из Keycloak
KEYCLOAK_URL = "https://keycloak.domain"  # URL вашего Keycloak сервера
KEYCLOAK_REALM = "example-realm1"  # Realm для сбора событий
KEYCLOAK_CLIENT_ID = "client-id"  # Client ID для аутентификации
KEYCLOAK_CLIENT_SECRET = ""  # Client secret (оставить пустым если не нужен)
KEYCLOAK_USERNAME = "username"  # Имя пользователя
KEYCLOAK_PASSWORD = "password"  # Пароль пользователя
```

**Параметры:**

- `KEYCLOAK_ENABLED` - установите `True` для включения сбора событий из Keycloak
- `KEYCLOAK_URL` - полный URL вашего Keycloak сервера без trailing slash
- `KEYCLOAK_REALM` - название realm'а, из которого будут собираться события
- `KEYCLOAK_CLIENT_ID` - ID клиента для аутентификации в Keycloak
- `KEYCLOAK_CLIENT_SECRET` - секрет клиента (может быть пустым для public clients)
- `KEYCLOAK_USERNAME/PASSWORD` - учетные данные пользователя с правами на чтение событий

### Настройки приложений

```python
APPLICATIONS = [
    {
        "sources": [
            # (URL API приложения, Имя приложения для логирования)
            ("https://app1.domain/api", "Production App"),
            ("https://app2.domain/api", "Staging App"),
        ],
        "api_token": "Bearer_token_1",  # Токен для группы приложений
    },
    {
        "sources": [
            ("https://app3.domain/api", "Analytics Service"),
        ],
        "api_token": "Bearer_token_2",  # Отдельный токен для другой группы
    },
]
```

**Структура:**

- `APPLICATIONS` - список групп приложений
- Каждая группа содержит:
  - `sources` - список кортежей `(api_url, app_name)`
    - `api_url` - базовый URL API приложения (к нему добавляется `/history/`)
    - `app_name` - читаемое имя приложения для идентификации в логах
  - `api_token` - Bearer токен для аутентификации в API этой группы приложений

**Важно:** Приложения группируются по токену доступа. Если несколько приложений используют один токен (пользователь, которому был выдан токен, имеет доступ к нескольким приложениям), объедините их в одну группу.

### Настройки Syslog серверов

```python
SYSLOG_SERVERS = [
    {"host": "syslog1.domain", "port": 514, , "ssl": False},   # TCP соединение
    {"host": "syslog2.domain", "port": 6514, , "ssl": True},  # TLS соединение
]
```

**Параметры:**

- `host` - адрес syslog сервера (IP или домен)
- `port` - порт сервера:
  - `514` - стандартный TCP порт для syslog
  - `6514` - стандартный порт для syslog через TLS
- `ssl` - использовать ли для подключения к порту SSL контекст. При отсутствии значения содение к порту 6514 будет с SSL

События отправляются на **все** сервера из списка.

### Общие настройки

```python
DEBUG = False              # Включить подробное логирование
EVENT_HOURS = 1            # За сколько последних часов собирать события
KEYCLOAK_DAYS_BACK = 2     # За сколько дней собирать события Keycloak
SHORT_LOGS = True          # Убирать детальную информацию из событий приложений
EVENT_ID_FILE = "storage/events.db"  # Путь к БД для дедупликации
```

**Параметры:**

- `DEBUG` - при `True` выводит детальную информацию о работе экспортера
- `EVENT_HOURS` - окно времени для сбора новых событий (в часах)
- `KEYCLOAK_DAYS_BACK` - собирает события за указанное количество дней для киклока
- `SHORT_LOGS` - при `True` убирает поле `details` из событий для экономии места
- `EVENT_ID_FILE` - путь к SQLite БД для хранения ID обработанных событий для дедупликации

### Использование переменных окружения

Для безопасности рекомендуется использовать переменные окружения для чувствительных данных:

```python
import os

KEYCLOAK_USERNAME = os.getenv("KEYCLOAK_USERNAME", "default_user")
KEYCLOAK_PASSWORD = os.getenv("KEYCLOAK_PASSWORD", "default_pass")

APPLICATIONS = [
    {
        "sources": [("https://app/api", "app")],
        "api_token": os.getenv("APP_API_TOKEN", ""),
    },
]
```

## Запуск

### Ручной запуск

```bash
python3 main.py
```

### Автоматический запуск через cron

Для регулярного экспорта событий добавьте задачу в crontab:

```bash
crontab -e
```

Добавить строку для запуска каждый час:

```bash
0 * * * * cd /path/to/export-to-syslog && /usr/bin/python3 main.py >> /var/log/syslog-exporter.log 2>&1
```

## События

### Формат событий приложения

События получаются через API endpoint `/history/` и имеют структуру:

```json
{
  "project": {
    "id": "uuid",
    "name": "Project Name"
  },
  "by": "username",
  "at": "2025-10-14T12:34:56.123456+00:00",
  "type": "project_created",
  "info": {
    "...": "дополнительная информация"
  }
}
```

## Формат RFC5424

Сообщения отправляются в формате RFC5424:

`<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG`

Пример:

```
<134>1 2025-10-14T12:34:56.123456+00:00 audit-client app-name - project_created - ﻿{"id":"abc123","timestamp":"2025-10-14T12:34:56+00:00","user":"admin","source":"app-name","event_type":"project_created",...}
```

Где:

- `<134>` = PRI (Facility 16 * 8 + Severity 6)
- `1` = VERSION
- `2025-10-14T12:34:56.123456+00:00` = TIMESTAMP
- `audit-client` = HOSTNAME
- `app-name` = APP-NAME (определяется по источнику)
- `-` = PROCID (не используется)
- `project_created` = MSGID (тип события)
- `-` = STRUCTURED-DATA (не используется)
- `{...}` = MSG (JSON с BOM)

## Хранилище событий

События сохраняются в SQLite БД (`storage/events.db`) для предотвращения дублирования.

### Функции

- `load_event_ids()` - загрузка всех ID событий
- `event_exists(event_id)` - быстрая проверка существования события
- `store_event_id(event_id, metadata)` - сохранение события с метаданными
- `cleanup_old_events(days=30)` - удаление событий старше N дней
- `get_stats()` - статистика по хранилищу

### Очистка старых событий

Рекомендуется периодически очищать старые события:

```python
from event_id_store import cleanup_old_events

# Удалить события старше 30 дней
deleted = cleanup_old_events(days=30)
print(f"Удалено {deleted} старых событий")
```

Или через cron (раз в неделю):

```bash
0 0 * * 0 cd /path/to/export-to-syslog && /usr/bin/python3 -c "from event_id_store import cleanup_old_events; cleanup_old_events(30)" 2>&1
```

## Поддерживаемые события Keycloak

Скрипт обрабатывает все типы событий Keycloak, включая описанные события в концигурации с установленными приоритетами и facility.

Полный список событий доступен в [документации Keycloak](https://www.keycloak.org/docs-api/latest/javadocs/org/keycloak/events/EventType.html).
