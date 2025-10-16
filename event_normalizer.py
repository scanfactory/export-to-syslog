import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from config import (
    USER_EVENT_PRIORITIES,
    ADMIN_EVENT_PRIORITIES,
    APP_EVENT_PRIORITIES,
    SHORT_LOGS,
)


def normalize_keycloak_event(
    event: Dict[str, Any], is_admin: bool = False
) -> Dict[str, Any]:
    event_type = event.get("type") or event.get("operationType") or "unknown"
    timestamp = event.get("time") or event.get("timestamp")
    user_id = event.get("userId")
    realm_id = event.get("realmId")

    if is_admin:
        resource_path = event.get("resourcePath", "")
        event_id = _generate_event_id(
            str(event_type or ""), timestamp, str(user_id or ""), resource_path
        )
    else:

        session_id = event.get("sessionId", "")
        event_id = _generate_event_id(
            str(event_type or ""), timestamp, str(user_id or ""), session_id
        )

    base = {
        "id": event_id,
        "timestamp": timestamp,
        "user": user_id,
        "realm": realm_id,
        "event_type": event_type,
        "details": event.get("details"),
        "source": "keycloak",
    }

    priority_map = ADMIN_EVENT_PRIORITIES if is_admin else USER_EVENT_PRIORITIES
    priority_facility = priority_map.get(
        event_type, (14, 16)
    )  # default: (Informational, local0)
    base["priority"] = priority_facility[0]
    base["facility"] = priority_facility[1]
    return base


def normalize_app_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Нормализует события приложения к RFC5424-совместимому формату.

    Входной формат (из API /history/):
    {
        "project": {"id": UUID, "name": str},
        "by": str,
        "at": datetime (ISO format),
        "type": str,
        "info": dict
    }

    Выходной формат:
    {
        "id": str,  # уникальный идентификатор события
        "timestamp": str,  # ISO8601 timestamp
        "user": str,  # автор действия
        "project_id": str,  # ID проекта
        "project_name": str,  # название проекта
        "event_type": str,  # тип события
        "details": dict,  # дополнительная информация
        "priority": int,  # приоритет по RFC5424
        "source": "app"  # источник события
    }
    """
    event_type = event.get("type", "unknown")
    project = event.get("project", {})
    timestamp = event.get("at")
    user = event.get("by", "system")

    event_id = _generate_event_id(event_type, timestamp, user, project.get("id"))

    if timestamp:
        if isinstance(timestamp, str):
            normalized_timestamp = timestamp
        else:
            normalized_timestamp = timestamp.isoformat()
    else:
        normalized_timestamp = datetime.now(timezone.utc).isoformat()

    priority_facility = APP_EVENT_PRIORITIES.get(
        event_type, (14, 16)
    )  # default: (Informational, local0)

    normalized = {
        "id": event_id,
        "timestamp": normalized_timestamp,
        "user": user,
        "project_id": str(project.get("id", "")),
        "project_name": project.get("name", ""),
        "event_type": event_type,
        "details": {},
        "priority": priority_facility[0],
        "facility": priority_facility[1],
        "source": "app",
    }

    if not SHORT_LOGS:
        normalized["details"] = event.get("info", {})

    return normalized


def _generate_event_id(
    event_type: str,
    timestamp: Optional[Union[str, datetime]],
    user: str,
    project_id: Optional[Any],
) -> str:
    """
    Генерирует уникальный ID для события.
    Использует хеширование для создания стабильного ID на основе ключевых параметров.
    """
    key_parts = [
        str(event_type),
        str(timestamp),
        str(user),
        str(project_id) if project_id else "",
    ]
    key_string = "|".join(key_parts)

    hash_obj = hashlib.sha256(key_string.encode("utf-8"))
    return hash_obj.hexdigest()[:32]
