import asyncio
import logging

from bs4 import BeautifulSoup

from src.states import OlimpCodes
from src.utils import fetch_response

my_log = logging.getLogger(__name__)

COEFF_NAME = 'П1'
# в коде страницы на сайте
DATA_SPORT = {
    "Футбол": "1",
    "Хоккей": "2",
    "Теннис": "3",
    "Баскетбол": "5",
    "Настольный теннис": "40",
    "Киберспорт": "112",
    "Волейбол": "10",
    # и т.д.
}


def log(s, is_error: bool = False):
    msg = f'[OLIMPCOM] -> {s}'
    if not is_error:
        my_log.info(msg)
    else:
        my_log.error(msg)


class OlimpCom:
    def __init__(self, url: str,
                 user_agent: str,
                 timeout: int,
                 sport_list: list[str],
                 coeff_name: str,
                 proxy: str | None = None):
        self.url = url
        self.headers = {
            'accept': '*/*',
            'accept-language': 'ru,ru-RU;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': url,
            'pragma': 'no-cache',
            'referer': url,
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Opera";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': user_agent,
            'x-requested-with': 'XMLHttpRequest',
        }
        self.timeout = timeout
        self.sport_list = sport_list
        self.coeff_name = coeff_name
        self.proxy = proxy

    def _get_games(self, response) -> dict:
        soup = BeautifulSoup(response, 'lxml')

        all_games = dict()
        for data_sport in self.sport_list:
            data_sport_code = DATA_SPORT.get(data_sport, '')
            trs = soup.find_all("tr", {"data-sport": data_sport_code})
            for tr in trs:
                try:
                    td = tr.find_all("td")[-1]
                    comp_name = td.find("a").text
                    comp_url = f'{self.url}/{td.find("a").get("href")}'
                    comp_url = comp_url.replace('/betting', '')
                    comp_id = td.find("a").get("id").split("_")[-1]
                    data_sport = data_sport
                    all_games[comp_name] = {
                        "comp_name": comp_name,
                        "comp_url": comp_url,
                        "comp_id": comp_id,
                        "data_sport": data_sport,
                        "site": "olimp.com",
                    }
                except Exception as e:
                    log(f'Ошибка парсинга для блока\n{tr}:\n{e}')

        return all_games

    @staticmethod
    def _extract_coeff(response: str, coeff_name: str) -> float | None:
        soup = BeautifulSoup(response, 'lxml')
        try:
            coeff = float(soup.find("span",
                                    {"class", "googleStatIssueName"},
                                    string=coeff_name).parent.find_all("span")[1].get("data-v1"))
        except:
            coeff = None
        return coeff

    async def _get_all_coefficients(self, all_games: dict, coeff_name: str) -> dict | OlimpCodes:
        # TODO: здесь, скорее всего, нужно будет использовать пул прокси, чтобы каждый запрос был с разного IP
        # другой вариант - последовательно делать запросы. теряем в скорости,
        # но меньше потребление памяти и меньше нагрузка на сервер донор

        log('Получение списка коэффициентов...')
        tasks = [fetch_response(game.get("comp_url"), headers=self.headers) for game_name, game in all_games.items()]
        results = await asyncio.gather(*tasks)
        if not results:
            return OlimpCodes.error_get_coeffs
        games = dict()

        # здесь все упирается в счетные задачи. можно попробовать распараллелить именно через процессы
        for current_game, response in zip(all_games.items(), results):
            coeff = self._extract_coeff(response, coeff_name)
            games[current_game[0]] = current_game[1] | {"coeff": coeff, "coeff_name": coeff_name}
        return games

    async def get_bets(self):
        log('Получение информации для OlimpCom...')
        response = await fetch_response(url=f'{self.url}', headers=self.headers, proxy=self.proxy,
                                        timeout=self.timeout)
        if not response:
            # не знаю как у вас принято обрабатывать такого рода ошибки:
            # вызывать кастомное исключение и ловить его выше, или что-то такого плана
            log('Возможно требуется заменить ссылку через бота https://t.me/olimpbet_bot и дальше в разделе "Лайв"')
            return {"result": False, "response": OlimpCodes.error_response}

        all_games = self._get_games(response)
        if not all_games:
            log('Возможно сменилась верстка на сайте...')
            return {"result": False, "response": OlimpCodes.error_games_pars}

        log(f'Количество игр на странице = {len(all_games)}')
        games = await self._get_all_coefficients(all_games, coeff_name=self.coeff_name)
        if not games:
            log('Возможно сменилась верстка на сайте...')
            return {"result": False, "response": OlimpCodes.error_get_coeffs}

        return {"result": True, "response": games}
