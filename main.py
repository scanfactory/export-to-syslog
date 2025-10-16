#!/usr/bin/env python3
"""
Экспортер событий из Keycloak и Scanfactory на syslog сервер.

Собирает события из нескольких источников, нормализует их к RFC5424 формату
и отправляет на удаленный syslog сервер через TLS.
"""

import json
import sys
import logging
from datetime import datetime
from typing import Any, Dict

from keycloak_client import get_admin_token, fetch_keycloak_events
from sf_client import fetch_app_events
from event_normalizer import normalize_keycloak_event, normalize_app_event
from event_id_store import load_event_ids, store_event_id
from syslog_sender import send_syslog_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _extract_metadata(event: Dict[str, Any]) -> Dict[str, Any]:
    """Извлекает только ключевые метаданные для хранения в БД."""
    return {
        "id": event.get("id", ""),
        "timestamp": event.get("timestamp", ""),
        "user": event.get("user", ""),
        "event_type": event.get("event_type", ""),
        "source": event.get("source", ""),
        "priority": event.get("priority", 0),
        "facility": event.get("facility", 0),
    }


def main() -> int:
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Запуск экспорта событий на syslog")
    logger.info("=" * 60)

    try:
        event_ids = load_event_ids()
        logger.info(f"Загружено {len(event_ids)} обработанных событий из кеша")

        normalized_events = []
        stats = {
            "keycloak_user": 0,
            "keycloak_admin": 0,
            "app": 0,
            "sent": 0,
            "errors": 0,
            "duplicates_keycloak_user": 0,
            "duplicates_keycloak_admin": 0,
            "duplicates_app": 0,
        }

        logger.info("Получение событий из Keycloak...")
        try:
            token = get_admin_token()
            kc_user_events = fetch_keycloak_events("events", token)
            kc_admin_events = fetch_keycloak_events("admin-events", token)

            for e in kc_user_events:
                try:
                    ne = normalize_keycloak_event(e, is_admin=False)
                    if ne["id"] not in event_ids:
                        normalized_events.append(ne)
                        store_event_id(ne["id"], _extract_metadata(ne))
                        stats["keycloak_user"] += 1
                    else:
                        stats["duplicates_keycloak_user"] += 1
                except Exception as ex:
                    logger.error(f"Ошибка нормализации Keycloak user event: {ex}")
                    stats["errors"] += 1

            for e in kc_admin_events:
                try:
                    ne = normalize_keycloak_event(e, is_admin=True)
                    if ne["id"] not in event_ids:
                        normalized_events.append(ne)
                        store_event_id(ne["id"], _extract_metadata(ne))
                        stats["keycloak_admin"] += 1
                    else:
                        stats["duplicates_keycloak_admin"] += 1
                except Exception as ex:
                    logger.error(f"Ошибка нормализации Keycloak admin event: {ex}")
                    stats["errors"] += 1

            logger.info(
                f"Получено новых событий Keycloak: user={stats['keycloak_user']}, admin={stats['keycloak_admin']}"
            )

        except Exception as ex:
            logger.error(f"Ошибка при получении событий Keycloak: {ex}")
            stats["errors"] += 1

        logger.info("Получение событий из Scanfactory...")
        try:
            app_events = fetch_app_events()

            for e in app_events:
                try:
                    ne = normalize_app_event(e)
                    if ne["id"] not in event_ids:
                        normalized_events.append(ne)
                        store_event_id(ne["id"], _extract_metadata(ne))
                        stats["app"] += 1
                    else:
                        stats["duplicates_app"] += 1
                except Exception as ex:
                    logger.error(f"Ошибка нормализации app event: {ex}")
                    stats["errors"] += 1

            logger.info(f"Получено новых событий из приложения: {stats['app']}")

        except Exception as ex:
            logger.error(f"Ошибка при получении событий приложения: {ex}")
            stats["errors"] += 1

        total_events = len(normalized_events)
        logger.info(f"Начинаем отправку {total_events} событий на syslog сервер...")

        for i, event in enumerate(normalized_events, 1):
            try:
                send_syslog_event(event, event["priority"], event.get("facility"))
                stats["sent"] += 1

                if i % 10 == 0:
                    logger.info(f"Отправлено {i}/{total_events} событий...")

            except Exception as ex:
                logger.error(
                    f"Ошибка отправки события {event.get('id', 'unknown')}: {ex}"
                )
                stats["errors"] += 1

        elapsed_time = (datetime.now() - start_time).total_seconds()
        total_duplicates = (
            stats["duplicates_keycloak_user"]
            + stats["duplicates_keycloak_admin"]
            + stats["duplicates_app"]
        )
        logger.info("=" * 60)
        logger.info("Экспорт завершен")
        logger.info(f"Время выполнения: {elapsed_time:.2f} сек")
        logger.info(f"Статистика:")
        logger.info(f"  - Keycloak user events: {stats['keycloak_user']}")
        logger.info(f"  - Keycloak admin events: {stats['keycloak_admin']}")
        logger.info(f"  - App events: {stats['app']}")
        logger.info(f"  - Всего отправлено: {stats['sent']}")
        logger.info(
            f"  - Отфильтровано дубликатов: {total_duplicates} (KC user: {stats['duplicates_keycloak_user']}, KC admin: {stats['duplicates_keycloak_admin']}, App: {stats['duplicates_app']})"
        )
        logger.info(f"  - Ошибок: {stats['errors']}")
        logger.info("=" * 60)

        return 1 if stats["errors"] > 0 else 0

    except Exception as ex:
        logger.critical(f"Критическая ошибка: {ex}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
