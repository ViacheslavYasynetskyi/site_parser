import os
import asyncio
import json
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot

from search_parametrs import citi, vacation

load_dotenv()

TOKEN = os.environ.get("TOKEN")
GROUP_ID = os.environ.get("GROUP_ID")


async def fetch_html(url):
    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            timeout=aiohttp.ClientTimeout(total=20)
    ) as session:
        async with session.get(url) as response:
            return await response.text()


async def parse_olx_page(url):
    try:
        html = await fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        vacancies = []

        job_elements = soup.find_all("div", class_="css-oukcj3")

        for job_element in job_elements:
            title_element = job_element.find("div", class_="css-b7dwkg")
            description_element = job_element.find("div", class_="css-re1w99")

            # Перевірка, чи елементи знайдено перед викликом get_text()
            title = title_element.get_text(strip=True) if title_element else "No title"
            description = description_element.get_text(strip=True) if description_element else "No description"

            vacancy_data = {
                    "title": title,
                    "description": description,
                }

            vacancies.append(vacancy_data)

        return vacancies

    except Exception as e:
        print(f"Error parsing page: {e}")
        return []


async def send_to_telegram(json_data):
    bot = Bot(token=TOKEN)
    formatted_text = format_telegram_message(json_data)
    await bot.send_message(chat_id=GROUP_ID, text=formatted_text, parse_mode="MARKDOWN")


def format_telegram_message(json_data):
    try:
        vacancies = json.loads(json_data)
        if not vacancies:
            return "No vacancies found."

        formatted_text = "Here are the latest vacancies:\n"
        for vacancy in vacancies:
            formatted_text += f"\n*Title:* {vacancy['title']}\n"
            formatted_text += f"*Description:* {vacancy['description']}\n"
            formatted_text += "------------------------"

        return formatted_text
    except json.JSONDecodeError:
        return "Error decoding JSON data."


class Vacancy(BaseModel):
    title: str
    description: str


async def validate_and_reformat(results):
    validated_results = []
    print(results)
    for item in results:
        try:
            # Використовуємо Pydantic для валідації
            vacancy = Vacancy(**item)
            validated_results.append(vacancy.model_dump())
        except ValidationError as e:
            print(f"Validation error: {e}")
            # Обробка помилок валідації

    return validated_results


async def main():
    olx_base_url = f"https://www.olx.ua/uk/{citi}/q-{vacation}/?currency=UAH&page="
    num_vacation = 20

    tasks = [parse_olx_page(f"{olx_base_url}{page}") for page in range(1, num_vacation + 1)]

    results_list = await asyncio.gather(*tasks)
    results = [item for sublist in results_list for item in sublist]

    validated_results = await validate_and_reformat(results)
    json_data = json.dumps(validated_results, ensure_ascii=False, indent=2)

    await send_to_telegram(json_data)


if __name__ == "__main__":

    asyncio.run(main())
