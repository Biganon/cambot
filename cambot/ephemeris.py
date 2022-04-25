import os
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
        ts = datetime.now().strftime("%s")
        req = requests.get(f"https://fr.wikiquote.org/wiki/Wikiquote:Accueil?r={ts}")
        soup = bs(req.text, features="html.parser")
        citation = soup.find(lambda tag:tag.name=="i" and "Lumière sur" in tag.text).parent.parent.parent.findAll("div")[1].text.strip()
        return f"*{citation}*"
    except Exception:
        return "Impossible de trouver la citation du jour. Bouuuh !"

def saint():
    today = datetime.now().strftime("%m/%d")
    saint = SAINTS[today]
    return saint

def weather_emoji(_id):
    emojis = {re.compile(r"2.."):":thunder_cloud_rain:",
              re.compile(r"3.."):":white_sun_rain_cloud:",
              re.compile(r"5.."):":cloud_rain:",
              re.compile(r"6.."):":snowflake:",
              re.compile(r"7.."):":interrobang:",
              re.compile(r"800"):":sunny:",
              re.compile(r"801"):":white_sun_small_cloud:",
              re.compile(r"80[23]"):":white_sun_cloud:",
              re.compile(r"804"):":cloud:"}
    try:
        code = next(emoji[1] for emoji in emojis.items() if emoji[0].match(str(_id)))
    except StopIteration:
        code = ":negative_squared_cross_mark:"
    return code

def weather(lat, lon):
    r = requests.get(f"https://api.openweathermap.org/data/2.5/"
                     f"onecall?lat={lat}&lon={lon}&appid={OWM_KEY}&lang=fr&units=metric")
    j = json.loads(r.text)

    next_hours = []
    for i in (2, 8, 14):
        hourly = j["hourly"][i]
        time = datetime.fromtimestamp(hourly["dt"]).strftime("%H:%M")
        temp = round(hourly["temp"])
        feels_like = hourly["feels_like"]
        humidity = hourly["humidity"]
        wind_speed = round(hourly["wind_speed"] * 3.6)
        description = hourly["weather"][0]["description"]
        emoji = weather_emoji(hourly["weather"][0]["id"])
        next_hours.append({"time":time,
                           "emoji":emoji,
                           "description":description,
                           "temp":temp,
                           "wind_speed":wind_speed
                           })

    return next_hours

def digest():
    try:
        locale.setlocale(locale.LC_ALL, "fr_CH.utf-8")
    except locale.Error:
        pass
    now = datetime.now()
    d = now.strftime("%A %-d %B")
    c = citation()
    s = saint()
    w_strings = []
    for w in weather(46.5196661, 6.6325467):
        w_strings.append(f"{w['emoji']} {w['description']} ({w['temp']}°C, {w['wind_speed']} km/h)")

    embed = Embed()
    embed.title = "Bonjour !"
    embed.description = f"Nous sommes le {d} ({s})\n\n{c}\n\u200B"
    colors = [Color.red(), Color.gold(), Color.orange(), Color.blue(), Color.green(), Color.magenta(), Color.purple()]
    embed.color = colors[now.weekday()]
    embed.add_field(name="Matin", value=w_strings[0])
    embed.add_field(name="Après-midi", value=w_strings[1])
    embed.add_field(name="Soir", value=w_strings[2])

    return embed

if __name__ == "__main__":
    print(citation())
