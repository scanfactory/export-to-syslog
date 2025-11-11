import requests
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from config import (
    KEYCLOAK_URL,
    KEYCLOAK_REALM,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_USERNAME,
    KEYCLOAK_PASSWORD,
)

logger = logging.getLogger(__name__)


def get_admin_token() -> str:
    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    data = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "username": KEYCLOAK_USERNAME,
        "password": KEYCLOAK_PASSWORD,
        "grant_type": "password",
    }
    if KEYCLOAK_CLIENT_SECRET:
        data["client_secret"] = KEYCLOAK_CLIENT_SECRET

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        token = response.json()["access_token"]
        logger.info("Успешная авторизация в Keycloak")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения токена Keycloak: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Статус: {e.response.status_code}, Ответ: {e.response.text}")
        raise
    except KeyError:
        logger.error(f"Токен не найден в ответе Keycloak: {response.text}")
        raise


def fetch_keycloak_events(
    event_type: str, access_token: str, hours: int = 1, fetch_days_back: int = 1
) -> List[Dict[str, Any]]:
    now = datetime.now(tz=UTC)
    since = now - timedelta(hours=hours)

    # Keycloak API позволяет получать события только за сутки (YYYY-MM-DD)
    date_from = (now - timedelta(days=fetch_days_back)).strftime("%Y-%m-%d")

    url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/{event_type}"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "dateFrom": date_from,
    }

    logger.debug(f"Запрашиваем {event_type} с {date_from}")
    logger.debug(f"Полный URL: {url}")
    logger.debug(f"Параметры запроса: {params}")
    logger.debug(f"Будут отфильтрованы события начиная с: {since.isoformat()}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        events = response.json()

        logger.debug(f"API вернул {len(events)} событий типа {event_type}")
        if events and len(events) > 0:
            logger.debug(f"Пример первого события: {events[0]}")

        filtered_events = []
        since_timestamp = since.timestamp()
        logger.debug(
            f"Фильтруем события новее чем: {since.isoformat()} (timestamp: {since_timestamp})"
        )

        for i, event in enumerate(events):
            event_time = event.get("time") or event.get("timestamp")
            if event_time:
                if isinstance(event_time, int):
                    event_timestamp = event_time / 1000
                    if i == 0:
                        logger.debug(
                            f"Временная метка события (мс->с): {event_time} -> {event_timestamp}"
                        )
                else:
                    try:
                        event_dt = datetime.fromisoformat(
                            event_time.replace("Z", "+00:00")
                        )
                        event_timestamp = event_dt.timestamp()
                        if i == 0:
                            logger.debug(
                                f"Дата/время события: {event_time} -> {event_timestamp}"
                            )
                    except Exception as e:
                        logger.debug(
                            f"Не удалось распарсить временную метку '{event_time}': {e}"
                        )
                        filtered_events.append(event)
                        continue

                if event_timestamp >= since_timestamp:
                    filtered_events.append(event)
                elif i < 3:
                    logger.debug(
                        f"Событие отфильтровано: {event_timestamp} < {since_timestamp}"
                    )
            else:
                logger.debug(f"У события нет поля time/timestamp: {event}")
                filtered_events.append(event)

        logger.info(
            f"Получено {len(filtered_events)}/{len(events)} (подходящих/всего) событий типа {event_type} за {hours} час(ов)"
        )
        return filtered_events
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения событий Keycloak ({event_type}): {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Статус: {e.response.status_code}, Ответ: {e.response.text}")
        raise
