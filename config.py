# МОЖНО ИСПОЛЬЗОВАТЬ ТАК
# import os
# os.getenv("ENV_VAR_NAME", "default_value")

KEYCLOAK_URL = "https://keycloak.domain"
KEYCLOAK_ADMIN_REALM = "master"
KEYCLOAK_CLIENT_ID = "admin-cli"
KEYCLOAK_USERNAME = "your_admin_user"  # os.getenv("KEYCLOAK_USERNAME", None)
KEYCLOAK_PASSWORD = "your_admin_password"  # os.getenv("KEYCLOAK_PASSWORD", None)

APP_API_URL = "https://sf.app.url/api"
APP_API_TOKEN = "eyJhbGc..."

SYSLOG_HOST = "localhost"
SYSLOG_PORT = 514  # или 6514 с ssl context

# --------------------------------------------------
SHORT_LOGS = True  # Если True, из события приложения убирает детали (поле details)
# Например, убирает список добавленных 20000 хостов или 
# информацию о 20 новых шаблонах

EVENT_ID_FILE = "storage/events.db"

# RFC5424 Facility codes:
# 4/10 - security/authorization messages
# 13 - log audit
# 16 - local use 0 (local0)

# Keycloak User Events: (priority, facility)
USER_EVENT_PRIORITIES = {
    "CODE_TO_TOKEN": (14, 4),      # security/authorization
    "CODE_TO_TOKEN_ERROR": (14, 4),      # security/authorization
    "LOGIN": (14, 4),            # security/authorization
    "LOGIN_ERROR": (14, 4),            # security/authorization
    "LOGOUT": (14, 4),           # security/authorization
    "LOGOUT_ERROR": (14, 4),           # security/authorization
}

# Keycloak Admin Events: (priority, facility)
ADMIN_EVENT_PRIORITIES = {
    "UPDATE": (4, 13),               # audit
    "CREATE": (4, 13),
    "DELETE": (4, 13),               # audit
    "ACTION": (5, 13),               # audit
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
