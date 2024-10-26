import requests
from datetime import datetime
from nextcord import Embed, Color
import re
import json
import locale
from bs4 import BeautifulSoup as bs
from .settings import *
from .saints import SAINTS


def citation():
    try:
        soup = bs(requests.get("http://www.unjourunpoeme.fr").text, features="html.parser")
        bloc = soup.find("div", {"class": "poemedujour"})
        title = bloc.find("h3", {"class": "posttitle"}).text.strip()
        author = bloc.find("a", {"class": "poemehasardauteur"}).text.strip()
        poem = "\n\n".join(s for c in bloc.find("blockquote").contents if (s := c.text.strip()))

        return f"# {title}\n\n**{author}**\n\n{poem}"
    except Exception:
        return "Impossible de trouver la citation du jour. Bouuuh !"


def saint():
    return SAINTS[datetime.now().strftime("%m/%d")]


def weather_emoji(_id):
    emojis = {re.compile(r"2.."): ":thunder_cloud_rain:",
              re.compile(r"3.."): ":white_sun_rain_cloud:",
              re.compile(r"5.."): ":cloud_rain:",
              re.compile(r"6.."): ":snowflake:",
              re.compile(r"7.."): ":interrobang:",
              re.compile(r"800"): ":sunny:",
              re.compile(r"801"): ":white_sun_small_cloud:",
              re.compile(r"80[23]"): ":white_sun_cloud:",
              re.compile(r"804"): ":cloud:"}
    try:
        code = next(emoji[1] for emoji in emojis.items() if emoji[0].match(str(_id)))
    except StopIteration:
        code = ":negative_squared_cross_mark:"
    return code


def weather(lat, lon):
    r = requests.get(f"https://api.openweathermap.org/data/2.5/"
                     f"forecast?lat={lat}&lon={lon}&appid={OWM_KEY}&lang=fr&units=metric")
    j = json.loads(r.text)

    next_hours = []
    for i in (2, 8, 14):
        hourly = j["list"][i]
        next_hours.append({"time": datetime.fromtimestamp(hourly["dt"]).strftime("%H:%M"),
                           "emoji": weather_emoji(hourly["weather"][0]["id"]),
                           "description": hourly["weather"][0]["description"],
                           "temp": round(hourly["main"]["temp"]),
                           "wind_speed": round(hourly["wind"]["speed"] * 3.6)
                           })

    return next_hours


def digest():
    try:
        locale.setlocale(locale.LC_ALL, "fr_CH.utf-8")
    except locale.Error:
        pass
    now = datetime.now()

    embed = Embed(color=[Color.red(), Color.gold(), Color.orange(), Color.blue(), Color.green(), Color.magenta(), Color.purple()][now.weekday()])
    embed.title = "Bonjour !"
    embed.description = f"Nous sommes le {now.strftime('%A %-d %B')} ({saint()})"

    if EPHEMERIS_INCLUDE_CITATION:
        embed.description += f"\n\n{citation()}\n\u200B"

    if EPHEMERIS_INCLUDE_WEATHER:
        w_strings = []
        for w in weather(46.5196661, 6.6325467):
            w_strings.append(f"{w['emoji']} {w['description']} ({w['temp']}°C, {w['wind_speed']} km/h)")
        embed.add_field(name="Matin", value=w_strings[0])
        embed.add_field(name="Après-midi", value=w_strings[1])
        embed.add_field(name="Soir", value=w_strings[2])

    if EPHEMERIS_INCLUDE_ARTWORK:
        soup = bs(requests.get("https://www.wikiart.org/").text, features="html.parser")

        j = json.loads(soup.find("main", {"class": "wiki-layout-main-page"})["ng-init"].splitlines()[0][28:-1])

        images = [
            {
                "url": j["ImageDescription"]["Url"],
                "width": j["ImageDescription"]["Width"],
                "height": j["ImageDescription"]["Height"],
            },
            {
                "url": j["PaintingJson"]["image"],
                "width": j["PaintingJson"]["width"],
                "height": j["PaintingJson"]["height"],
            },
        ]

        if isinstance(j["PaintingJson"]["images"], list):
            for image in j["PaintingJson"]["images"]:
                images.append({
                    "url": image["image"],
                    "width": image["width"],
                    "height": image["height"],
                })

        embed.set_image(max(images, key=lambda x: x["width"] * x["height"])["url"])
        embed.set_footer(text=f"{j['ArtistName']} - {j['Title']} ({j['CompletitionYear']})")

    return embed


if __name__ == "__main__":
    print(citation())
