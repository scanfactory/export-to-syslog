# Syslog Event Exporter

Экспортер событий из Keycloak и Scanfactory на удаленный syslog сервер в формате RFC5424

## Описание

Скрипт собирает события из двух источников:

1. **Keycloak** - события аутентификации и администрирования
2. **Scanfactory** - события управления проектами и сканированием

Все события нормализуются к единому формату и отправляются на syslog сервер

## Установка и настройка

1. Установить зависимости:

   ```bash
   pip3 install -r requirements.txt
   ```

2. Настроить параметры в [config.py](config.py):

   - URL и credentials для Keycloak
   - URL и токен для Scanfactory API
   - Адрес syslog сервера (host/port)
   - Приоритеты событий (опционально)

3. Создать директорию для хранилища событий

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

Добавить строку (например, запуск каждый час):

```bash
0 * * * * cd /path/to/export-to-syslog && /usr/bin/python3 main.py >> /var/log/syslog-exporter.log 2>&1
```

## Events

### Формат событий приложения

События приложения получаются через API endpoint `/history/` и имеют следующую структуру:

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
    "...": "дополнительная информация о событии"
  }
}
```

### [Другие события Keycloak](https://www.keycloak.org/docs-api/latest/javadocs/org/keycloak/events/EventType.html)

AUTHREQID_TO_TOKEN  
AUTHREQID_TO_TOKEN_ERROR  
CLIENT_DELETE  
CLIENT_DELETE_ERROR  
CLIENT_INFO  
CLIENT_INFO_ERROR  
CLIENT_INITIATED_ACCOUNT_LINKING  
CLIENT_INITIATED_ACCOUNT_LINKING_ERROR  
CLIENT_LOGIN  
CLIENT_LOGIN_ERROR  
CLIENT_REGISTER  
CLIENT_REGISTER_ERROR  
CLIENT_UPDATE  
CLIENT_UPDATE_ERROR  
CODE_TO_TOKEN  
CODE_TO_TOKEN_ERROR  
CUSTOM_REQUIRED_ACTION  
CUSTOM_REQUIRED_ACTION_ERROR  
DELETE_ACCOUNT  
DELETE_ACCOUNT_ERROR  
EXECUTE_ACTION_TOKEN  
EXECUTE_ACTION_TOKEN_ERROR  
EXECUTE_ACTIONS  
EXECUTE_ACTIONS_ERROR  
FEDERATED_IDENTITY_LINK  
FEDERATED_IDENTITY_LINK_ERROR  
FEDERATED_IDENTITY_OVERRIDE_LINK  
FEDERATED_IDENTITY_OVERRIDE_LINK_ERROR  
GRANT_CONSENT  
GRANT_CONSENT_ERROR  
IDENTITY_PROVIDER_FIRST_LOGIN  
IDENTITY_PROVIDER_FIRST_LOGIN_ERROR  
IDENTITY_PROVIDER_LINK_ACCOUNT  
IDENTITY_PROVIDER_LINK_ACCOUNT_ERROR  
IDENTITY_PROVIDER_LOGIN  
IDENTITY_PROVIDER_LOGIN_ERROR  
IDENTITY_PROVIDER_POST_LOGIN  
IDENTITY_PROVIDER_POST_LOGIN_ERROR  
IDENTITY_PROVIDER_RESPONSE  
IDENTITY_PROVIDER_RESPONSE_ERROR  
IDENTITY_PROVIDER_RETRIEVE_TOKEN  
IDENTITY_PROVIDER_RETRIEVE_TOKEN_ERROR  
IMPERSONATE  
IMPERSONATE_ERROR  
INTROSPECT_TOKEN  
INTROSPECT_TOKEN_ERROR  
INVALID_SIGNATURE  
INVALID_SIGNATURE_ERROR  
INVITE_ORG  
INVITE_ORG_ERROR  
LOGIN  
LOGIN_ERROR  
LOGOUT  
LOGOUT_ERROR  
OAUTH2_DEVICE_AUTH  
OAUTH2_DEVICE_AUTH_ERROR  
OAUTH2_DEVICE_CODE_TO_TOKEN  
OAUTH2_DEVICE_CODE_TO_TOKEN_ERROR  
OAUTH2_DEVICE_VERIFY_USER_CODE  
OAUTH2_DEVICE_VERIFY_USER_CODE_ERROR  
OAUTH2_EXTENSION_GRANT  
OAUTH2_EXTENSION_GRANT_ERROR  
PERMISSION_TOKEN  
PERMISSION_TOKEN_ERROR  
PUSHED_AUTHORIZATION_REQUEST  
PUSHED_AUTHORIZATION_REQUEST_ERROR  
REFRESH_TOKEN  
REFRESH_TOKEN_ERROR  
REGISTER  
REGISTER_ERROR  
REGISTER_NODE  
REGISTER_NODE_ERROR  
REMOVE_CREDENTIAL  
REMOVE_CREDENTIAL_ERROR  
REMOVE_FEDERATED_IDENTITY  
REMOVE_FEDERATED_IDENTITY_ERROR  
REMOVE_TOTP Deprecated.  
REMOVE_TOTP_ERROR Deprecated.  
RESET_PASSWORD  
RESET_PASSWORD_ERROR  
RESTART_AUTHENTICATION  
RESTART_AUTHENTICATION_ERROR  
REVOKE_GRANT  
REVOKE_GRANT_ERROR  
SEND_IDENTITY_PROVIDER_LINK  
SEND_IDENTITY_PROVIDER_LINK_ERROR  
SEND_RESET_PASSWORD  
SEND_RESET_PASSWORD_ERROR  
SEND_VERIFY_EMAIL  
SEND_VERIFY_EMAIL_ERROR  
TOKEN_EXCHANGE  
TOKEN_EXCHANGE_ERROR  
UNREGISTER_NODE  
UNREGISTER_NODE_ERROR  
UPDATE_CONSENT  
UPDATE_CONSENT_ERROR  
UPDATE_CREDENTIAL  
UPDATE_CREDENTIAL_ERROR  
UPDATE_EMAIL  
UPDATE_EMAIL_ERROR  
UPDATE_PASSWORD Deprecated.  
UPDATE_PASSWORD_ERROR Deprecated.  
UPDATE_PROFILE  
UPDATE_PROFILE_ERROR  
UPDATE_TOTP Deprecated.  
UPDATE_TOTP_ERROR Deprecated.  
USER_DISABLED_BY_PERMANENT_LOCKOUT  
USER_DISABLED_BY_PERMANENT_LOCKOUT_ERROR  
USER_DISABLED_BY_TEMPORARY_LOCKOUT  
USER_DISABLED_BY_TEMPORARY_LOCKOUT_ERROR  
USER_INFO_REQUEST  
USER_INFO_REQUEST_ERROR  
VALIDATE_ACCESS_TOKEN Deprecated. see KEYCLOAK-2266  
VALIDATE_ACCESS_TOKEN_ERROR Deprecated.  
VERIFY_EMAIL  
VERIFY_EMAIL_ERROR  
VERIFY_PROFILE  
VERIFY_PROFILE_ERROR  

## Формат [RFC5424](https://www.rfc-editor.org/rfc/rfc5424)

Сообщения отправляются в формате RFC5424:

`<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG`

Пример:

```json
<134>1 2025-10-14T12:34:56.123456+00:00 audit-client factory-app - project_created - ﻿{"id":"abc123","timestamp":"2025-10-14T12:34:56.123456+00:00","user":"admin","project_id":"uuid","project_name":"Test Project","event_type":"project_created","details":{},"priority":6,"source":"app"}
```

Где:

- `<134>` = PRI (Facility 16 * 8 + Severity 6)
- `1` = VERSION
- `2025-10-14T12:34:56.123456+00:00` = TIMESTAMP
- `audit-client` = HOSTNAME
- `factory-app` = APP-NAME
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
