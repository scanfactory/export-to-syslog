import requests
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from config import (
    KEYCLOAK_URL,
    KEYCLOAK_ADMIN_REALM,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_USERNAME,
    KEYCLOAK_PASSWORD,
)

logger = logging.getLogger(__name__)


def get_admin_token() -> str:
    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_ADMIN_REALM}/protocol/openid-connect/token"
    data = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "username": KEYCLOAK_USERNAME,
        "password": KEYCLOAK_PASSWORD,
        "grant_type": "password",
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения токена Keycloak: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Статус: {e.response.status_code}, Ответ: {e.response.text}")
        raise
    except KeyError:
        logger.error(f"Токен не найден в ответе Keycloak: {response.text}")
        raise


def fetch_keycloak_events(
    event_type: str, access_token: str, hours: int = 1
) -> List[Dict[str, Any]]:
    now = datetime.now(tz=UTC)
    since = now - timedelta(hours=hours)

    # по формату киклок поддерживает дни при запросе ивентов
    yesterday = since - timedelta(days=1)
    date_from = yesterday.strftime("%Y-%m-%d")
    date_to = now.strftime("%Y-%m-%d")

    url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_ADMIN_REALM}/{event_type}"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        events = response.json()

        filtered_events = []
        since_timestamp = since.timestamp()
        for event in events:

            event_time = event.get("time") or event.get("timestamp")
            if event_time:
                if isinstance(event_time, int):
                    event_timestamp = event_time / 1000
                else:
                    try:
                        event_dt = datetime.fromisoformat(
                            event_time.replace("Z", "+00:00")
                        )
                        event_timestamp = event_dt.timestamp()
                    except:
                        filtered_events.append(event)
                        continue

                if event_timestamp >= since_timestamp:
                    filtered_events.append(event)
            else:
                filtered_events.append(event)

        logger.info(
            f"Получено {len(filtered_events)}/{len(events)} событий типа {event_type} за последний {hours} час(а)"
        )
        return filtered_events
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка получения событий Keycloak ({event_type}): {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Статус: {e.response.status_code}, Ответ: {e.response.text}")
        raise
