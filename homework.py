import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exception

load_dotenv()


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(messsage)s",
    level=logging.INFO,
)

PRACTICUM_TOKEN = os.getenv("TOKEN_YANDEX")
TELEGRAM_TOKEN = os.getenv("TOKEN_TELEGRAM")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot, message):
    """Отправка сообщения в канал."""
    chat_id = TELEGRAM_CHAT_ID
    text = "Письмо пришло!"
    bot.send_message(chat_id, message=text)
    logging.info("Сообщение ушло адресату")


def get_api_answer(current_timestamp):
    """Получаем ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            status_code = response.status_code
            logging.error(f"Ошибка {status_code}")
            raise Exception(f"Ошибка {status_code}")
        else:
            return response.json()
    except Exception as error:
        logging.error(f"Есть ошибки при запросе {error}")
        raise Exception(f"Есть ошибки при запросе {error}")


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) is not dict:
        message = "Ответ от API не словарь!"
        raise TypeError(message)
    elif ["homeworks"][0] not in response:
        message = "Домашки нет в ответе от API"
        raise IndexError(message)
    elif type(response["homeworks"]) is not list:
        message = "Домшка не в списке пришла"
        raise exception.NegativeValueException(message)
    elif response["homeworks"] is None:
        message = "Списсок заданий пуст, ожидай"
        raise exception.NegativeValueException(message)
    homework = response["homeworks"]

    return homework


def parse_status(homework):
    """Чекаем статус домашней работы."""
    homework_name = homework["homework_name"]
    homework_status = homework["status"]
    try:
        if "homework_name" not in homework:
            raise KeyError(
                'У API есть ответ, но в нем нет ключа "homework_name".'
            )
    except KeyError:
        logging.error('У API есть ответ, но в нем нет ключа "homework_name".')
    try:
        if "status" not in homework:
            raise KeyError('В ответе нет "status".')
    except KeyError:
        logging.error('В ответе нет "status".')

    if homework_status not in HOMEWORK_STATUSES:
        logging.debug("Новых статусов домашки в ответе - нет")
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
    for token in all_tokens:
        if token is None:
            logging.critical(f"Ошибка {token}")
            return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logging.debug("У тебя нет новых работ")
            else:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = ...
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message, exc_info=True)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
