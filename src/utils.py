import asyncio
import logging

import aiohttp
from playwright.async_api import async_playwright, Page

my_log = logging.getLogger(__name__)


async def fetch_response(url: str,
                         headers: dict,
                         cookies: dict | None = None,
                         max_tries=1,
                         pause_next=1,
                         proxy: str | None = None,
                         timeout: int = 30) -> str | None:
    proxies = None
    if proxy:
        ip = proxy.split(':')[0]
        port = proxy.split(':')[1]
        login = proxy.split(':')[2]
        password = proxy.split(':')[3]
        proxies = f"https://{login}:{password}@{ip}:{port}"

    for try_num in range(1, max_tries + 1):
        if try_num > 1:
            await asyncio.sleep(pause_next)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url,
                                       headers=headers,
                                       cookies=cookies,
                                       proxy=proxies,
                                       timeout=timeout) as resp:
                    response = await resp.text()
                    return response
        except Exception as e:
            my_log.error(f'Ошибка получения ответа при запросе "{url}": {e}')

    my_log.info('Не удалось получить ответ!')
    return None


async def get_playwright_no_context(page: Page, url: str):
    await page.goto(url)
    response = await page.content()
    response = response.split('<body><pre>')[-1].split('</pre>')[0]
    return response


async def just_check_playwright():
    test_url = 'https://www.olimp.bet/api/v4/0/live/sports-with-competitions-with-events?vids%5B%5D=1%3A'
    apw = await async_playwright().start()
    browser = await apw.chromium.launch()
    page = await browser.new_page()
    response = await get_playwright_no_context(page=page, url=test_url)
    await browser.close()
    print(response)


if __name__ == '__main__':
    asyncio.run(just_check_playwright())
