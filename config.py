# МОЖНО ИСПОЛЬЗОВАТЬ ТАК
# import os
# os.getenv("ENV_VAR_NAME", "default_value")

# --------------------------------------------------
# KEYCLOAK SETTINGS

KEYCLOAK_ENABLED = False
KEYCLOAK_URL = "https://keycloak.domain"

# realm в котором будут собраны события
KEYCLOAK_REALM = "example-realm1"
KEYCLOAK_CLIENT_ID = "client-id-example"

# можно оставить пустым "", если не требуется для аутентификации
KEYCLOAK_CLIENT_SECRET = ""

KEYCLOAK_USERNAME = "your_username"  # os.getenv("KEYCLOAK_USERNAME", None)
KEYCLOAK_PASSWORD = "your_password"  # os.getenv("KEYCLOAK_PASSWORD", None)

# --------------------------------------------------
# APPLICATION SETTINGS

APPLICATIONS = [
    {
        "sources": [
            ## (Ссылка на API приложения, имя приложения)
            ("https://sf.app.url/api", "appname1"),
            ("https://2nd.app/api", "appname 2"),
        ],
        "api_token": "1eyJhbGc...",
    },
    {
        "sources": [
            ("https://another.app/api", "appname 33"),
        ],
        "api_token": "2eyJhbGc...",
    },
]

# --------------------------------------------------
# SYSLOG SETTINGS

SYSLOG_SERVERS = [
    {"host": "localhost", "port": 514, "ssl": False},
    # {"host": "localhost", "port": 6514, "ssl": True},
]

# --------------------------------------------------
# ОБЩИЕ НАСТРОЙКИ

# Если True, включает подробное логирование для отладки
DEBUG = False

# К-во последних часов, за которые надо фильтровать события (по умолчанию 1 час) >= 1
EVENT_HOURS = 1

# За какое к-во дней собирать события Keycloak >= 0
KEYCLOAK_DAYS_BACK = 2

# Если True, из события приложения убирает детали (поле details)
SHORT_LOGS = True
# Например, убирает список добавленных 20000 хостов или
# информацию о 20 новых шаблонах

EVENT_ID_FILE = "storage/events.db"

# RFC5424 Facility codes:
# 4/10 - security/authorization messages
# 13 - log audit
# 16 - local use 0 (local0)

# Keycloak User Events: (priority, facility)
USER_EVENT_PRIORITIES = {
    "CODE_TO_TOKEN": (14, 4),  # security/authorization
    "CODE_TO_TOKEN_ERROR": (14, 4),
    "LOGIN": (14, 4),
    "LOGIN_ERROR": (14, 4),
    "LOGOUT": (14, 4),
    "LOGOUT_ERROR": (14, 4),
}

# Keycloak Admin Events: (priority, facility)
ADMIN_EVENT_PRIORITIES = {
    "UPDATE": (4, 13),  # audit
    "CREATE": (4, 13),
    "DELETE": (4, 13),  # audit
    "ACTION": (5, 13),  # audit
}

# События приложения: (priority, facility)
APP_EVENT_PRIORITIES = {
    # Критичные события безопасности (audit)
    "proj-del": (4, 13),
    "user-created": (4, 13),
    "user-deleted": (4, 13),
    "user-updated": (5, 13),
    # Важные изменения конфигурации (local0)
    "proj-new": (6, 16),
    "kube-release-rollout": (6, 16),
    # Управление состоянием (local0)
    "proj-upd": (7, 16),
    "project-upd-floodwatch": (7, 16),
    "email-tmpl-new": (7, 16),
    "email-tmpl-del": (7, 16),
}


# --------------------------------------------------
# ВАЛИДАЦИЯ КОНФИГУРАЦИИ


def validate_config():
    """
    Валидирует конфигурацию на корректность.

    Проверки:
    - Уникальность имён приложений в APPLICATIONS
    - Наличие обязательных полей
    """
    errors = []

    app_names = []
    for idx, app in enumerate(APPLICATIONS, 1):
        sources = app.get("sources", [])
        if not app.get("api_token", ""):
            errors.append(f"APPLICATIONS[{idx}]: отсутствует 'api_token'")

        for source_url, app_name in sources:
            if not app_name or not app_name.strip():
                errors.append(
                    f"Источники #{idx}: пустое имя для источника '{source_url}'"
                )
            elif app_name in app_names:
                errors.append(
                    f"Источники #{idx}: дубликат имени '{app_name}' "
                    f"(уже используется другим источником)"
                )
            else:
                app_names.append(app_name)

    if not SYSLOG_SERVERS:
        errors.append("SYSLOG_SERVERS: список серверов пуст")

    for idx, server in enumerate(SYSLOG_SERVERS, 1):
        if "host" not in server:
            errors.append(f"SYSLOG_SERVERS[{idx}]: отсутствует поле 'host'")
        if "port" not in server:
            errors.append(f"SYSLOG_SERVERS[{idx}]: отсутствует поле 'port'")

    if errors:
        error_msg = "Ошибки в конфигурации:\n" + "\n".join(
            f"  - {err}" for err in errors
        )
        raise ValueError(error_msg)


validate_config()
