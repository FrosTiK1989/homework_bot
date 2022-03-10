"""Начало кода Бота-Ассистента."""

import logging
import os
import sys
import time
from http import HTTPStatus
from sqlite3 import DataError

import requests
import telegram
from dotenv import load_dotenv

import exception

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s - %(funcName)s"
)
handler.setFormatter(formatter)


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TOKEN_TELEGRAM")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT")

RETRY_TIME = 20
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot, message):
    """Отправка сообщения в канал."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info("Сообщение ушло клиенту")
    except telegram.TelegramError(message):
        message = "Ошибка при отправке сообщения"
        raise Exception(message)


def get_api_answer(current_timestamp):
    """Получаем ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        logger.info("Проверяем ответ API")
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        if response.status_code != HTTPStatus.OK:
            status_code = response.status_code
            raise Exception(f"Ошибка {status_code}")
    except Exception as error:
        logger.error(f"Есть ошибки при запросе {error}")
        raise Exception(f"Есть ошибки при запросе {error}")


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info("Начало проверки ответа на запрос")
    if not isinstance(response, dict):
        raise TypeError("Ответ от API не словарь!")
    if "homeworks" not in response:
        raise IndexError("Домашки нет в ответе от API")
    if "current_date" not in response:
        raise DataError("Траблы с датой")
    if not isinstance(response["homeworks"], list):
        raise exception.NegativeValueException("Домшка не в списке пришла")
    if response["homeworks"] is None:
        raise exception.NegativeValueException("Список заданий пуст, ожидай")
    homework = response["homeworks"]
    return homework


def parse_status(homework):
    """Чекаем статус домашней работы."""
    if "homework_name" not in homework:
        raise KeyError('У API есть ответ, но в нем нет ключа "homework_name".')
    homework_name = homework["homework_name"]

    if "status" not in homework:
        raise KeyError('В ответе нет "status".')
    homework_status = homework["status"]

    if homework_status not in HOMEWORK_STATUSES:
        raise exception.NegativeValueException("Статуса домашки нет в списке")

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем наличие всех необходимых токенов."""
    all_tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    return all(all_tokens)


def main():
    """Основная логика работы бота."""
    logger.info("Бот стартанул")
    current_report = {}
    prev_report = {}
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
    else:
        logger.critical("Отсутствуют необходимые токены")
        raise SystemExit("Отсутствуют токены!")
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.debug("У тебя нет новых работ")
            else:
                homework = homeworks[0]
                current_report["name"] = homework.get("homework_name")
                message = parse_status(homework)
                current_report["message"] = message
                if current_report != prev_report:
                    send_message(bot, message)
                    prev_report = current_report.copy()
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message, exc_info=True)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        filename="program.log",
        format="%(asctime)s, %(levelname)s, %(message)s, %(lineno)d",
        filemode="w",
    )
    main()
