import json
import logging

from playwright.async_api import Page

from src.states import OlimpCodes
from src.utils import get_playwright_no_context

my_log = logging.getLogger(__name__)


def log(s, is_error: bool = False):
    msg = f'[OLIMPBET] -> {s}'
    if not is_error:
        my_log.info(msg)
    else:
        my_log.error(msg)


class OlimpBet:
    def __init__(self, url: str,
                 user_agent: str,
                 timeout: int,
                 xguid_olimpbet: str,
                 user_ukey: str,
                 sport_list: list[str],
                 coeff_name: str,
                 proxy: str | None = None):
        self.url = url

        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,ko;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': 'no-cache',
            # 'cache-control': 'no-cache',
            # 'pragma': 'no-cache',
            # 'referer': 'https://www.olimp.bet/live/1',
            # 'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            # 'sec-ch-ua-mobile': '?0',
            # 'sec-ch-ua-platform': '"Windows"',
            # 'sec-fetch-dest': 'empty',
            # 'sec-fetch-mode': 'cors',
            # 'sec-fetch-site': 'same-origin',
            'User-Agent': user_agent,
            # 'X-Guid': xguid_olimpbet,
        }
        self.cookies = {
            'user_ukey': user_ukey,
            'visitor_id': xguid_olimpbet,
            'visitor_id_version': '2',
        }

        # self.headers = None
        self.cookies = None

        self.timeout = timeout
        self.sport_list = sport_list
        self.coeff_name = coeff_name
        self.proxy = proxy

    def _get_games(self, games: list | str) -> dict | None:
        try:
            if isinstance(games, str):
                games = json.loads(games.strip())
        except Exception as e:
            log(f'Ошибка конвертирования в словарь ответа: {e}')
            return None

        all_games = dict()
        for operation in games:
            payload = operation.get("payload", {})
            if (payload.get("sport", {}).get("name") or '').strip() not in self.sport_list:
                continue
            competitions = payload.get("competitionsWithEvents", [])
            for competition in competitions:
                events = competition.get("events", [])
                for event in events:
                    try:
                        comp_name = event.get("name").strip()
                        comp_id = event.get("id").strip()
                        data_sport_name = event.get("sportName").strip()
                        outcomes = event.get("outcomes")  # для дальнешего получения коэффициентов
                        all_games[comp_name] = {
                            "comp_name": comp_name,
                            "comp_id": comp_id,
                            "data_sport_name": data_sport_name,
                            "outcomes": outcomes,
                            "site": "olimp.bet",
                        }
                    except Exception as e:
                        log(f'Ошибка парсинга:\n{e}')

        return all_games

    @staticmethod
    def _get_raw_response_from_file() -> str:
        """
        Нужен для тестирования - явно задавать в файле готовый ответ содержимого страницы.
        """
        with open(r'Data\raw_response.txt', encoding='utf-8') as file:
            response = json.load(file)
        return response

    @staticmethod
    def _extract_coeff(current_game: dict, coeff_name: str) -> (float | None, str | None):
        outcomes = current_game.get("outcomes", [])
        coeff = None
        short_name = None

        for outcome in outcomes:
            group_name = outcome.get("groupName", "").strip()
            if coeff_name == group_name:
                short_name = outcome.get("shortName", "").strip()
                try:
                    coeff = float(outcome.get("probability"))
                    break
                except:
                    pass

        return coeff, short_name

    async def _get_all_coefficients(self, all_games: dict, coeff_name: str) -> dict | OlimpCodes:
        log('Получение списка коэффициентов...')

        games = dict()
        for game_name, current_game in all_games.items():
            coeff, short_name = self._extract_coeff(current_game, coeff_name)
            games[game_name] = current_game | {"coeff": coeff, "coeff_name": coeff_name, "short_name": short_name}
        return games

    async def get_bets(self, page: Page, is_need_coeffs: bool = False) -> dict:
        log('Получение информации для OlimpBet...')

        # response = self._get_raw_response_from_file()  # для отладки работаем с сохраненным ранее ответом

        response = None
        for try_get in range(5):
            # TODO: в случае ошибки получения ответа от сервера, сделать перебор прокси. вопрос - откуда берете прокси?

            response = await get_playwright_no_context(page=page, url=self.url)

            # response = await fetch_response(url=self.url,
            #                                 headers=self.headers,
            #                                 cookies=self.cookies,
            #                                 proxy=self.proxy,
            #                                 timeout=self.timeout)
            if response:
                break

        if not response:
            return {"result": False, "response": OlimpCodes.error_response}

        all_games = self._get_games(response)
        if not all_games:
            log('Возможно сменилась верстка на сайте...')
            return {"result": False, "response": OlimpCodes.error_games_pars}

        log(f'Количество игр на странице = {len(all_games)}')

        if not is_need_coeffs:
            return {"result": True, "response": all_games}

        games = await self._get_all_coefficients(all_games, coeff_name=self.coeff_name)
        if not games:
            log('Возможно сменилась верстка на сайте...')
            return {"result": False, "response": OlimpCodes.error_get_coeffs}

        return {"result": True, "response": games}
