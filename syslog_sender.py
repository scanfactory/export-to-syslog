import socket
import ssl
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from config import SYSLOG_HOST, SYSLOG_PORT


# https://www.rfc-editor.org/rfc/rfc5424


def send_syslog_event(
    event: Dict[str, Any], priority: int, facility: Optional[int] = None
) -> None:
    """
    Отправляет событие на syslog сервер в формате RFC5424.

    RFC5424 формат:
    <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG

    Где:
    - PRI = приоритет (Facility * 8 + Severity)
    - VERSION = 1
    - TIMESTAMP = ISO8601 с timezone
    - HOSTNAME = имя хоста источника
    - APP-NAME = имя приложения
    - PROCID = ID процесса (используем "-" если не применимо)
    - MSGID = ID типа сообщения (используем "-" если не применимо)
    - STRUCTURED-DATA = структурированные данные (используем "-" если нет)
    - MSG = само сообщение в JSON

    Facility codes (RFC5424):
    - 4/10: security/authorization messages
    - 13: log audit
    - 16: local use 0 (local0)
    """

    msg = json.dumps(event, ensure_ascii=False)

    hostname = "audit-client"

    source = event.get("source", "unknown")
    if source == "app":
        app_name = "scanfactory-app"
    elif source == "keycloak":
        app_name = "keycloak"
    else:
        app_name = "unknown"

    timestamp = _normalize_timestamp(event.get("timestamp"))

    if facility is None:
        facility = event.get("facility", 16)  # default: local0

    facility_int = facility if isinstance(facility, int) else 16

    # PRI: Facility * 8 + Severity
    severity = priority if priority <= 7 else 7  # Severity должен быть 0-7
    pri = facility_int * 8 + severity

    procid = "-"
    msgid = event.get("event_type", "-")
    structured_data = "-"

    bom = "\ufeff"  # UTF-8 Byte Order Mark перед MSG если есть не-ASCII символы
    rfc5424_msg = f"<{pri}>1 {timestamp} {hostname} {app_name} {procid} {msgid} {structured_data} {bom}{msg}\n"

    with socket.create_connection((SYSLOG_HOST, SYSLOG_PORT)) as sock:
        if SYSLOG_PORT == 6514:
            context = ssl.create_default_context()
            with context.wrap_socket(sock, server_hostname=SYSLOG_HOST) as ssock:
                ssock.sendall(rfc5424_msg.encode("utf-8"))
        else:
            sock.sendall(rfc5424_msg.encode("utf-8"))


def _normalize_timestamp(timestamp: Optional[str]) -> str:
    """
    Нормализует timestamp к формату RFC5424 (ISO8601 с timezone).

    RFC5424 требует формат: YYYY-MM-DDTHH:MM:SS.ssssss+TZ
    Пример: 2025-10-14T12:34:56.123456+00:00
    """
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    if isinstance(timestamp, str):
        if not (
            timestamp.endswith("Z") or "+" in timestamp or timestamp.count("-") > 2
        ):
            timestamp = timestamp + "Z"
        if timestamp.endswith("Z"):
            timestamp = timestamp[:-1] + "+00:00"

    return timestamp
