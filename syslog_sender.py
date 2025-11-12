import socket
import ssl
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from config import SYSLOG_SERVERS

logger = logging.getLogger(__name__)


# https://www.rfc-editor.org/rfc/rfc5424


class SyslogSender:
    """
    Менеджер соединений для отправки событий на syslog серверы.
    """

    def __init__(self):
        self.connections: List[Tuple[str, int, Any]] = []  # (host, port, socket)
        self._connected = False

    def __enter__(self):
        """Context manager entry - устанавливает соединения со всеми серверами."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - закрывает все соединения."""
        self.close()

    def connect(self) -> None:
        """Устанавливает соединения со всеми syslog серверами из конфига."""
        if self._connected:
            logger.warning("Соединения уже установлены")
            return

        for server in SYSLOG_SERVERS:
            host = server["host"]
            port = server["port"]
            ssl_enabled = server.get("ssl", port == 6514)

            try:
                sock = socket.create_connection((host, port), timeout=10)

                if ssl_enabled:
                    context = ssl.create_default_context()
                    sock = context.wrap_socket(sock, server_hostname=host)

                self.connections.append((host, port, sock))
                logger.info(f"Установлено соединение с {host}:{port}")

            except Exception as ex:
                logger.error(f"Не удалось подключиться к {host}:{port}: {ex}")

        self._connected = True

        if not self.connections:
            raise Exception(
                f"Не удалось установить соединение ни с одним из {len(SYSLOG_SERVERS)} серверов"
            )

    def close(self) -> None:
        """Закрывает все открытые соединения."""
        for host, port, sock in self.connections:
            try:
                sock.close()
                logger.debug(f"Соединение с {host}:{port} закрыто")
            except Exception as ex:
                logger.warning(f"Ошибка при закрытии соединения с {host}:{port}: {ex}")

        self.connections.clear()
        self._connected = False

    def send_event(
        self, event: Dict[str, Any], priority: int, facility: Optional[int] = None
    ) -> None:
        """
        Отправляет событие на все подключенные syslog серверы в формате RFC5424.

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
        if not self._connected:
            raise Exception(
                "Соединения не установлены. Используйте connect() или context manager"
            )

        # Формируем RFC5424 сообщение
        rfc5424_msg = self._format_rfc5424_message(event, priority, facility)

        # Отправляем на все активные соединения
        errors = []
        for host, port, sock in self.connections:
            try:
                sock.sendall(rfc5424_msg.encode("utf-8"))
                logger.debug(f"Событие отправлено на {host}:{port}")
            except Exception as ex:
                error_msg = f"Ошибка отправки на {host}:{port}: {ex}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Если все серверы вернули ошибку, выбрасываем исключение
        if errors and len(errors) == len(self.connections):
            raise Exception(
                f"Не удалось отправить событие ни на один из {len(self.connections)} серверов: {'; '.join(errors)}"
            )

    def _format_rfc5424_message(
        self, event: Dict[str, Any], priority: int, facility: Optional[int] = None
    ) -> str:
        """Форматирует событие в RFC5424 сообщение."""
        msg = json.dumps(event, ensure_ascii=False)

        hostname = "audit-client"

        app_name = event.get("source", "unknown")
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
        return f"<{pri}>1 {timestamp} {hostname} {app_name} {procid} {msgid} {structured_data} {bom}{msg}\n"


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
