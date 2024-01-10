import json
import re
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager



BASE_URL = "https://realtylink.org/en/properties~for-rent"
HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"}
PHOTO_API_URL = "https://realtylink.org/Property/PhotoViewerDataListing"
PHOTO_URL_TEMPALTE = "https://mediaserver.realtylink.org/media.ashx?id={}&t=pi&f=I"
NUM_PAGES = 3


@dataclass
class Apartment:
    url: str
    title: str
    region: str
    address: str
    description: str
    photos: list
    price: int
    amount_of_rooms: int
    estate_area: int


def check_is_bedrooms_exist(soup: BeautifulSoup) -> int:
    amount_of_bedrooms = soup.select_one(".teaser > .cac")

    if amount_of_bedrooms is not None:
        return int(amount_of_bedrooms.text.strip().split(" ")[0])

    else:
        return 0


def _make_photo_url(photo_id: str) -> str:
    return PHOTO_URL_TEMPALTE.format(photo_id)


def _make_photo_json_body(apartment_url: str) -> dict[str, str]:
    centris_no = re.findall(r"\d+", apartment_url)[0]
    return {
        "lang": "en",
        "centrisNo": centris_no,
        "track": "true",
        "authorizationMediaCode": "995",
    }


def parse_photo_urls(apartment_url: str) -> [str]:
    r = requests.post(PHOTO_API_URL, headers=HEADERS,
                      json=_make_photo_json_body(apartment_url))

    response_json_body = r.json()

    for photo_obj in response_json_body["PhotoList"]:
        yield _make_photo_url(photo_obj["Id"])


def parse_single_apartment(apps_soup: BeautifulSoup):
    detailed_url = f'https://realtylink.org{apps_soup.select_one(".property-thumbnail-item > .shell > a").get("href")}'
    apartment_url_soup = BeautifulSoup(
        requests.get(detailed_url, headers=HEADERS).content, "html.parser")

    apartment = Apartment(
        url=detailed_url,
        title=apartment_url_soup.find(
            attrs={"data-id": "PageTitle"}).text.strip(),
        region=", ".join(
            apartment_url_soup.select_one(".pt-1").text.strip().split(", ")[
            1:]),
        address=apartment_url_soup.select_one(".pt-1").text.strip().split(", ")[
            0],
        description=apartment_url_soup.select_one("[itemprop]").text.strip(),
        photos=list(parse_photo_urls(apartment_url=detailed_url)),
        price=int(
            apartment_url_soup.find("meta", attrs={"itemprop": "price"}).get(
                "content")),
        amount_of_rooms=check_is_bedrooms_exist(apartment_url_soup),
        estate_area=int(
            apartment_url_soup.select_one(".carac-value").text.strip().split(
                " ")[
                0].replace(",", ""))
    )
    print("done")

    return apartment


def parse_one_page_apartments() -> [Apartment]:
    page = requests.get(BASE_URL, headers=HEADERS).content
    soup = BeautifulSoup(page, "html.parser")

    apps = soup.select(".property-thumbnail-item")

    return [parse_single_apartment(apps_soup) for apps_soup in apps]


_driver: WebDriver | None = None


def get_driver() -> WebDriver:
    return _driver


def set_driver(new_driver: WebDriver) -> None:
    global _driver
    _driver = new_driver


def parse_all_apartments():
    all_apartments = []
    driver = get_driver()
    driver.get(url=BASE_URL)

    for page in range(NUM_PAGES):
        all_apartments += parse_one_page_apartments()
        next_button = driver.find_element(By.CLASS_NAME, "next")

        next_button.click()

    return all_apartments


def convert_to_json(data):
    with open("apps.json", "w") as f:
        json.dump(data, f, indent=4)


def main():
    with webdriver.Chrome(service=Service(ChromeDriverManager().install())) as new_driver:
        set_driver(new_driver)
        result = list(map(asdict, parse_all_apartments()))
        convert_to_json(result)


if __name__ == "__main__":
    main()