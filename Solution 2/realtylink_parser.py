import re
from typing import Iterable
from dataclasses import dataclass

from requests import Session
from bs4 import BeautifulSoup

BASE_URL = "https://realtylink.org"
RESIDENTIAL_FOR_RENT_URL = f"{BASE_URL}/en/properties~for-rent"
PAGE_API_URL = f"{BASE_URL}/Property/GetInscriptions"
PHOTO_API_URL = f"{BASE_URL}/Property/PhotoViewerDataListing"
PHOTO_URL_TEMPALTE = "https://mediaserver.realtylink.org/media.ashx?id={}&t=pi&f=I"

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


@dataclass
class Apartment:
    url: str
    title: str
    region: str
    address: str
    description: str
    photo_urls: list[str]
    price: int
    bedroom_count: int
    bathroom_count: int
    area: int


class RealtyLinkParser:
    def __init__(self):
        self.parsed_offset = 0
        self.parsing_session = Session()
        self.page_load_session = Session()

    def parse(self) -> Iterable[Apartment]:
        for page_html in self._get_page_htmls():
            for apartment_url in self._parse_apartment_urls(page_html):
                print(f"Parsing: {apartment_url}")
                yield self._parse_apartment(apartment_url)

    def _parse_apartment(self, apartment_url: str) -> Apartment:
        r = self.parsing_session.get(apartment_url, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")

        full_adress = self._parse_apartment_full_adress(soup).split(", ")

        return Apartment(
            url=apartment_url,
            title=self._parse_apartment_title(soup),
            region=", ".join(full_adress[1:]),
            address=", ".join(full_adress[:2]),
            description=self._parse_apartment_description(soup),
            photo_urls=list(self._parse_apartment_photo_urls(apartment_url)),
            price=self._parse_apartment_price(soup),
            bedroom_count=self._parse_apartment_bedroom_count(soup),
            bathroom_count=self._parse_apartment_bathroom_count(soup),
            area=self._parse_apartment_area(soup),
        )

    @staticmethod
    def _parse_apartment_title(soup: BeautifulSoup) -> str:
        if title_tag := soup.find("span", attrs={"data-id": "PageTitle"}):
            return title_tag.text.strip()
        return ""

    @staticmethod
    def _parse_apartment_full_adress(soup: BeautifulSoup) -> str:
        if apartment_full_tag := soup.find("h2", attrs={"itemprop": "address"}):
            return apartment_full_tag.text.strip()
        return ""

    @staticmethod
    def _parse_apartment_description(soup: BeautifulSoup) -> str:
        if description_tag := soup.find("div",
                                        attrs={"itemprop": "description"}):
            return description_tag.text.strip()
        return ""

    @staticmethod
    def _parse_apartment_price(soup: BeautifulSoup) -> int:
        if price_tag := soup.find("meta", attrs={"itemprop": "price"}):
            return int(price_tag.get("content"))
        return 0

    @staticmethod
    def _parse_apartment_bedroom_count(soup: BeautifulSoup) -> int:
        if bedroom_count_tag := soup.find(
                "div", attrs={"class", "col-lg-3 col-sm-6 cac"}
        ):
            return int(bedroom_count_tag.text.strip().split(" ")[0])
        return 0

    @staticmethod
    def _parse_apartment_bathroom_count(soup: BeautifulSoup) -> int:
        if bathroom_count_tag := soup.find(
                "div", attrs={"class", "col-lg-3 col-sm-6 sdb"}
        ):
            return int(bathroom_count_tag.text.strip().split(" ")[0])
        return 0

    @staticmethod
    def _parse_apartment_area(soup: BeautifulSoup) -> int:
        if area_tag := soup.find("div", attrs={"class", "carac-value"}):
            return int(area_tag.text.strip().split(" ")[0].replace(",", ""))
        return 0

    def _parse_apartment_photo_urls(self, apartment_url: str) -> Iterable[str]:
        r = self.parsing_session.post(
            PHOTO_API_URL,
            json=self._make_photo_json_body(apartment_url),
            headers=HEADERS,
        )
        response_json_body = r.json()
        for photo_obj in response_json_body["PhotoList"]:
            yield self._make_photo_url(photo_obj["Id"])

    @staticmethod
    def _make_photo_url(photo_id: str) -> str:
        return PHOTO_URL_TEMPALTE.format(photo_id)

    @staticmethod
    def _make_photo_json_body(apartment_url: str) -> dict[str, str]:
        centris_no = re.findall(r"\d+", apartment_url)[0]
        return {
            "lang": "en",
            "centrisNo": centris_no,
            "track": "true",
            "authorizationMediaCode": "995",
        }

    def _parse_apartment_urls(self, page_html: str) -> Iterable[str]:
        soup = BeautifulSoup(page_html, "html.parser")
        url_tags = soup.find_all("a", class_="property-thumbnail-summary-link")
        for url_tag in url_tags:
            yield f"{BASE_URL}{url_tag.get('href')}"

    def _get_page_htmls(self) -> Iterable[str]:
        self._load_cookies()
        while True:
            r = self.page_load_session.post(
                PAGE_API_URL, json=self._make_page_json_body(), headers=HEADERS
            )
            if r.status_code != 200:
                break

            result = r.json()["d"]["Result"]
            if self.parsed_offset >= result["count"]:
                break
            self.parsed_offset += result["inscNumberPerPage"]

            yield result["html"]

    def _make_page_json_body(self) -> dict[str, int]:
        return {"startPosition": self.parsed_offset}

    def _load_cookies(self):
        self.page_load_session.get(RESIDENTIAL_FOR_RENT_URL, headers=HEADERS)
