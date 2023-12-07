import os
import asyncio
import json
from pydantic import BaseModel
from dotenv import load_dotenv

import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot

load_dotenv()

TOKEN = os.environ.get("TOKEN")
GROUP_ID = os.environ.get("GROUP_ID")


async def fetch_html(url):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), timeout=aiohttp.ClientTimeout(total=10)) as session:
        async with session.get(url) as response:
            return await response.text()


async def parse_olx_page(url):
    html = await fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    vacancies = []

    job_elements = soup.find_all("div", class_="offer")

    for job_element in job_elements:
        title = job_element.find("strong").get_text(strip=True)
        description = job_element.find("p", class_="text").get_text(strip=True)
        salary = job_element.find("strong", class_="price").get_text(strip=True)


        vacancy_data = {
            "title": title,
            "description": description,
            "salary": salary,
        }

        vacancies.append(vacancy_data)

    return vacancies


async def send_to_telegram(json_data):
    bot = Bot(token=TOKEN)

    await bot.send_message(chat_id=GROUP_ID, text=json_data, parse_mode="MARKDOWN")


class Vacancy(BaseModel):
    title: str
    description: str
    salary: str


async def validate_and_reformat(results):
    validated_results = [1]
    print(results)
    for item in results:
        try:
            # Використовуємо Pydantic для валідації
            vacancy = Vacancy(**item)
            validated_results.append(vacancy.dict())
        except Exception as e:
            print(f"Validation error: {e}")
            # Обробка помилок валідації

    return validated_results


async def main():
    olx_urls = ["https://www.olx.ua/uk/rabota/q-developer/?currency=UAH", "https://www.olx.ua/uk/list/"]

    tasks = [parse_olx_page(url) for url in olx_urls]
    results = await asyncio.gather(*tasks)

    validated_results = await validate_and_reformat(results)
    json_data = json.dumps(validated_results, ensure_ascii=False, indent=2)

    await send_to_telegram(json_data)


if __name__ == "__main__":

    asyncio.run(main())
