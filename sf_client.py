import requests
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from config import APPLICATIONS

logger = logging.getLogger(__name__)


def fetch_app_events(hours: int = 1) -> Dict[str, List[Dict[str, Any]]]:
    """
    Получает события из всех приложений, указанных в APPLICATIONS.

    Каждое приложение содержит:
    - sources: список кортежей (API_URL, APP_NAME)
    - api_token: токен для доступа к API

    Функция проходит по всем источникам для каждого токена.

    Возвращает словарь, где ключ - это app_name из конфига, а значение - список событий:
    {
        "appname1": [
            {
                "project": {"id": UUID, "name": str},
                "by": str,  # автор события
                "at": datetime,  # время события
                "type": str,  # тип события
                "info": dict  # дополнительная информация (тело события)
            },
            ...
        ],
        "application 33": [...]
    }
    """
    events_by_source = {}

    for app_idx, app in enumerate(APPLICATIONS, 1):
        sources: list[str] = app.get("sources", [])
        api_token: str = app.get("api_token", "")

        if not api_token:
            logger.warning(f"Приложение #{app_idx}: отсутствует api_token")
            continue

        for source_url, app_name in sources:
            try:
                events = _fetch_from_source(source_url, api_token, hours)
                events_by_source[app_name] = events
                logger.info(f"Получено {len(events)} событий из {app_name}")
            except Exception as ex:
                logger.error(f"Ошибка получения событий из {app_name}: {ex}")
                events_by_source[app_name] = []

    return events_by_source


def _fetch_from_source(
    api_url: str, api_token: str, hours: int = 1
) -> List[Dict[str, Any]]:
    """
    Получает события из конкретного источника (API endpoint).
    """
    now = datetime.now(tz=UTC)
    since = now - timedelta(hours=hours)
    headers = {"Authorization": f"Bearer {api_token}"}

    params = {"$gt-at": since.timestamp(), "$lt-at": now.timestamp(), "all": True}

    response = requests.get(f"{api_url}/history/", headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    return data.get("items", [])
