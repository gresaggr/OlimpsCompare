import asyncio
import logging.handlers
import sys
import time
from configparser import ConfigParser

from playwright.async_api import async_playwright

from src.logger import set_logger
from src.olimp_bet import OlimpBet
from src.olimp_com import OlimpCom
from src.states import OlimpCodes


def show_only_same_games(olimps: list):
    olimp_bet, olimp_com = olimps
    if len(olimp_bet) > len(olimp_com):
        main_olimp = olimp_bet
        compare_olimp = olimp_com
    else:
        main_olimp = olimp_com
        compare_olimp = olimp_bet
    same_list = []
    for name, game in main_olimp.items():
        game_compare = compare_olimp.get(name)
        if game_compare:
            comp_id = game.get("comp_id")
            site = game.get("site")
            comp_id_compare = game_compare.get("comp_id")
            site_compare = game_compare.get("site")
            same_list.append(f"{site} [{comp_id} {name}] - {site_compare} [{comp_id_compare} {name}]")

    if not same_list:
        logging.info('Не найдены совпадающие игры!')
    else:

        same_message = "\n".join(same_list)
        logging.info(f'Совпадающие игры:\n{same_message}\n\nКоличество совпадений =  {len(same_list)}')


def show_same_games_with_coeffs(olimps: list[dict, dict], sign_list: list):
    """
    Вывод информации о найденных совпадениях.
    :param olimps: список полученных игр для заданных сайтов
    :param sign_list: список допустимых к выводу знаков (если НЕ указано "=", то такие совпадения пропустит)
    """
    olimp_bet, olimp_com = olimps

    # не всегда количество игр одинаковое и проверка по большему идет
    if len(olimp_bet) > len(olimp_com):
        main_olimp = olimp_bet
        compare_olimp = olimp_com
    else:
        main_olimp = olimp_com
        compare_olimp = olimp_bet
    same_list = []
    for name, game in main_olimp.items():
        game_compare = compare_olimp.get(name)
        if game_compare:
            comp_id = game.get("comp_id")
            site = game.get("site")
            comp_id_compare = game_compare.get("comp_id")
            site_compare = game_compare.get("site")

            short_name = game.get("short_name") or game_compare.get("short_name")

            coeff = game.get("coeff")
            coeff_compare = game_compare.get("coeff")
            if not all([coeff, coeff_compare]):
                continue
            if coeff > coeff_compare:
                sign = '>'
            elif coeff < coeff_compare:
                sign = '<'
            else:
                sign = '='

            if sign not in sign_list:
                continue

            same_msg = f"{site} [{comp_id} {name}] - {site_compare} [{comp_id_compare} {name}]"
            same_coeff = f"{short_name} - {site} {coeff} {sign} {coeff_compare} {site_compare}"
            same_list.append(f'{same_msg} ---> {same_coeff}')

    if not same_list:
        logging.info('Не найдены совпадающие игры с заданным знаком!')
    else:

        same_msg = "\n".join(same_list)
        signs_msg = " ".join(sign_list)
        logging.info(
            f'Совпадающие игры для набора знаков "{signs_msg}":\n{same_msg}\n\n'
            f'Количество совпадений =  {len(same_list)}')


def read_settings() -> dict:
    """
    Возвращает словарь конфигурационных данных
    - url_olimpcom: URL for https://www.olimp.com/
    - url_olimpbet: URL for https://www.olimp.bet/
    - user_agent: User agent information
    - xguid_olimpbet: XGUID for https://www.olimp.bet/
    - user_ukey: User UKEY for https://www.olimp.bet/
    """
    config = ConfigParser(interpolation=None)
    config.read('config.ini', encoding='utf-8-sig')
    try:
        url_olimpcom = config['Settings']['URL_OLIMPCOM']
    except KeyError:
        logging.critical('Не задана ссылка для https://www.olimp.com/ Работа не возможна!')
        sys.exit()

    try:
        url_olimpbet = config['Settings']['URL_OLIMPBET']
    except KeyError:
        logging.critical('Не задана ссылка для https://www.olimp.bet/ Работа не возможна!')
        sys.exit()

    try:
        user_agent = config['Settings']['USER_AGENT']
    except KeyError:
        logging.critical('Не задан USER_AGENT. Работа не возможна!')
        sys.exit()

    try:
        xguid_olimpbet = config['Settings']['XGUID_OLIMPBET']
    except KeyError:
        logging.critical('Не задан XGUID_OLIMPBET для https://www.olimp.bet/ Работа не возможна!')
        sys.exit()

    try:
        user_ukey = config['Settings']['USER_UKEY_OLIMPBET']
    except KeyError:
        logging.critical('Не задан USER_UKEY для https://www.olimp.bet/ Работа не возможна!')
        sys.exit()

    return {
        "url_olimpcom": url_olimpcom,
        "url_olimpbet": url_olimpbet,
        "user_agent": user_agent,
        "xguid_olimpbet": xguid_olimpbet,
        "user_ukey": user_ukey,
    }


async def main():
    settings = read_settings()
    olimp_bet = OlimpBet(url=settings.get("url_olimpbet"),
                         user_agent=settings.get("user_agent"),
                         timeout=30,
                         xguid_olimpbet=settings.get("xguid_olimpbet"),
                         user_ukey=settings.get("user_ukey"),
                         sport_list=['Футбол'],
                         coeff_name='Исход матча (основное время)')

    olimp_com = OlimpCom(url=settings.get("url_olimpcom"),
                         user_agent=settings.get("user_agent"),
                         timeout=30,
                         sport_list=['Футбол'],
                         coeff_name='П1')

    # вынес создание браузера сюда, т.к. возможно придется несколько раз получать страницу, и чтобы не пересоздавать
    apw = await async_playwright().start()
    browser = await apw.chromium.launch()
    page = await browser.new_page()

    olimps = await asyncio.gather(olimp_bet.get_bets(page), olimp_com.get_bets())
    if not all([res.get("result") for res in olimps]):
        logging.error('Не удалось получить информацию для сравнения')
        return OlimpCodes.error_get_list
    # show_only_same_games([olimp.get("response") for olimp in olimps])
    show_same_games_with_coeffs([olimp.get("response") for olimp in olimps], sign_list=['>', '<'])
    await browser.close()


if __name__ == "__main__":
    start_time = time.perf_counter()
    set_logger()
    # убрал asyncio.run(main(), т.к. при завершении работы была ошибка.
    # а если задать WindowsSelectorEventLoopPolicy, то не работал Playwright
    # asyncio.run(main())
    asyncio.get_event_loop().run_until_complete(main())
    logging.info(f'Работа завершена. Затраченное время: {round(time.perf_counter() - start_time, 2)} сек')
