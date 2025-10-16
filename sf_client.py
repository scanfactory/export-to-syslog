import requests
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from config import APP_API_URL, APP_API_TOKEN


def fetch_app_events(hours: int = 1) -> List[Dict[str, Any]]:
    """
    Получает события приложения через API /history/

    Возвращает список событий в формате:
    {
        "count": int,
        "items": [
            {
                "project": {"id": UUID, "name": str},
                "by": str,  # автор события
                "at": datetime,  # время события
                "type": str,  # тип события
                "info": dict  # дополнительная информация (тело события)
            }
        ]
    }
    """
    now = datetime.now(tz=UTC)
    since = now - timedelta(hours=hours)
    headers = {"Authorization": f"Bearer {APP_API_TOKEN}"}

    params = {"$gt-at": since.timestamp(), "$lt-at": now.timestamp(), "all": True}

    response = requests.get(f"{APP_API_URL}/history/", headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    return data.get("items", [])
