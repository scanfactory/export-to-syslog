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
    event: Dict[str, Any], realm: str, is_admin: bool = False
) -> Dict[str, Any]:
    event_type = event.get("type") or event.get("operationType") or "unknown"
    timestamp = event.get("time") or event.get("timestamp")
    user_id = event.get("userId")
    realm_id = event.get("realmId")

    normalized_timestamp = _normalize_timestamp(timestamp)

    if is_admin:
        resource_path = event.get("resourcePath", "")
        event_id = _generate_event_id(
            str(event_type or ""),
            normalized_timestamp,
            str(user_id or ""),
            resource_path,
        )
    else:
        session_id = event.get("sessionId", "")
        event_id = _generate_event_id(
            str(event_type or ""), normalized_timestamp, str(user_id or ""), session_id
        )

    base = {
        "id": event_id,
        "timestamp": normalized_timestamp,
        "user": user_id,
        "realm_id": realm_id,
        "realm_name": realm,
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
        normalized_timestamp = _normalize_timestamp(timestamp)
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


def _normalize_timestamp(timestamp: Optional[Union[int, float, str]]) -> str:
    """
    Универсальная функция преобразования timestamp в ISO 8601 формат.

    Обрабатывает различные форматы:
    - int/float в миллисекундах (например, 1731254400589)
    - int/float в секундах (например, 1731254400)
    - строка с числом в миллисекундах (например, "1731254400589")
    - строка с числом в секундах (например, "1731254400")
    - строка в ISO формате (например, "2025-11-10T14:53:01+00:00")

    Args:
        timestamp: Временная метка в различных форматах

    Returns:
        ISO 8601 строка
    """
    if not timestamp:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(timestamp, str):
        try:
            if "T" in timestamp or "-" in timestamp[:10]:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return dt.isoformat()
        except (ValueError, AttributeError):
            pass

        try:
            timestamp_num = float(timestamp)
            return _convert_numeric_timestamp(timestamp_num)
        except (ValueError, TypeError):
            return datetime.now(timezone.utc).isoformat()

    elif isinstance(timestamp, (int, float)):
        return _convert_numeric_timestamp(timestamp)

    else:
        return datetime.now(timezone.utc).isoformat()


def _convert_numeric_timestamp(timestamp_num: float) -> str:
    """
    Преобразует числовой timestamp (в секундах или миллисекундах) в ISO формат.

    Автоматически определяет, в секундах или миллисекундах передан timestamp.
    если timestamp > 10^10, то это миллисекунды

    Args:
        timestamp_num: Числовой timestamp

    Returns:
        ISO 8601 строка
    """

    if timestamp_num > 100_000_000_000:
        dt = datetime.fromtimestamp(timestamp_num / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromtimestamp(timestamp_num, tz=timezone.utc)

    return dt.isoformat()


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
