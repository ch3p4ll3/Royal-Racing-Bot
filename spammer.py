import threading
import time
from datetime import datetime

from pyrogram import Client
from pyrogram.errors.exceptions.bad_request_400 import UserIsBlocked
from pyrogram.types import InlineKeyboardMarkup, \
    InlineKeyboardButton

from config import BASE_URL
from db_manager import select, delete, insert


def remove_user(user_id):
    try:
        delete("DELETE FROM bot_event_sended"
               " WHERE user = %s", (user_id,))

        delete("DELETE FROM bot_users "
               "WHERE tg_id = %s", (user_id,))
    except Exception:
        pass


class Spammer(threading.Thread):
    """spammer class, with this you
    can stay updated with new events"""
    def __init__(self, app: Client):
        threading.Thread.__init__(self)
        self.app = app
        self.go = True

    def run(self):
        timer = time.time()
        while self.go:
            if time.time() - timer >= 10:
                self.spammer()
                timer = time.time()

            if not self.go:
                break
            time.sleep(1)

    def spammer(self):
        users = select("SELECT tg_id FROM bot_users")

        for user in users:
            user = list(user)[0]

            query = "SELECT id_event, event_name, descrizione, " \
                    "start_date, event_type.type, image_url, drivers " \
                    "FROM events INNER JOIN event_type ON " \
                    "event_type.id_type=events.type " \
                    "WHERE DATE(creation_date) > CURDATE() AND " \
                    "(SELECT notify_events FROM bot_users " \
                    "WHERE tg_id=%s LIMIT 1) IS TRUE AND " \
                    "id_event NOT IN (SELECT event FROM " \
                    "bot_event_sended WHERE user=%s);"

            for (id_event, event_name, description,
                 start_date, event_type, image_url,
                 drivers) in select(query, (user, user)):

                cars = ""
                tracks = ""

                for car_name in select("SELECT car_name FROM cars_in_events "
                                       "INNER JOIN cars ON car=id_car "
                                       "WHERE event=%s;", (id_event,)):
                    cars += f"• {list(car_name)[0]}"

                for track_name, date in select(
                        "SELECT track_name, "
                        "date FROM calendars "
                        "INNER JOIN tracks "
                        "ON track=id_track "
                        "WHERE event=%s;", (id_event,)
                ):

                    if date < datetime.now():
                        tracks += f"~~• {track_name} - {date}~~\n"
                    else:
                        tracks += f"• {track_name} - {date}\n"

                btn = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                event_name,
                                url=f"{BASE_URL}/event-detail/{id_event}"
                            )
                        ]
                    ]
                )

                text = f"**{event_name}**\n\n{description}\n" \
                       f"\nData di inizio: {start_date}" \
                       f"\nTipologia di evento: {event_type}" \
                       f"\nNumero di posti: {drivers}\n" \
                       f"\nAuto:\n{cars}\n\n" \
                       f"Tracciati: \n{tracks}"

                try:
                    if image_url is not None:
                        self.app.send_photo(
                            int(user),
                            photo=image_url,
                            caption=text,
                            reply_markup=btn
                        )

                    else:
                        self.app.send_message(
                            int(user),
                            text,
                            reply_markup=btn
                        )

                    insert("INSERT INTO bot_event_sended "
                           "VALUES(NULL, %s, %s)", (user, id_event,))

                except UserIsBlocked:
                    remove_user(user)

    def stop(self):
        self.go = False
