import requests
import json
from bs4 import BeautifulSoup as bs

html = requests.get("https://www.wikiart.org/").text
soup = bs(html, features="html.parser")

print(json.loads(soup.find("main", {"class": "wiki-layout-main-page"})["ng-init"].splitlines()[0][28:-1]))