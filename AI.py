import aiohttp
import logging
from config import (
    YANDEX_GPT_API_KEY,
    YANDEX_GPT_FOLDER_ID,
    YANDEX_GPT_URL,
    SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)

async def ask_gpt(mood_score: int, trigger: str, thought: str):
    headers = {
        "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
        "x-folder-id": YANDEX_GPT_FOLDER_ID,
        "Content-Type": "application/json"
    }

    user_prompt = f"""Информация о состоянии пользователя: Оценка настроения: {mood_score}/10 Что произошло: {trigger}Мысль по этому поводу: {thought}Пожалуйста, дай краткий психологический совет, исходя из этой информации."""
    payload = {
        "modelUri": f"gpt://{YANDEX_GPT_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": "300"
        },
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": user_prompt}
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(YANDEX_GPT_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()

                    if 'result' in result and 'alternatives' in result['result'] and result['result']['alternatives']:
                        advice = result['result']['alternatives'][0]['message']['text']
                        return advice
                    else:
                        logger.error(f"YandexGPT API returned unexpected structure: {result}")
                        return "Произошла ошибка при обработке ответа от YandexGPT."
                else:
                    error_text = await response.text()
                    logger.error(f"YandexGPT API error {response.status}: {error_text}")
                    return "Произошла ошибка при обращении к YandexGPT. Проверьте ключ API и Folder ID."

        except aiohttp.ClientConnectorError:
            return "Проблема с подключением к сервису YandexGPT. Проверьте интернет-соединение."
        except Exception as e:
            logger.error(f"Unexpected error in ask_gpt: {e}")
            return "Произошла непредвиденная ошибка."