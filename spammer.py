import threading
import time
from datetime import datetime

from pony.orm import db_session, Database
from pyrogram import Client
from pyrogram.errors.exceptions.bad_request_400 import UserIsBlocked
from pyrogram.types import InlineKeyboardMarkup, \
    InlineKeyboardButton

from config import BASE_URL


class Spammer(threading.Thread):
    def __init__(self, app: Client, db: Database):
        threading.Thread.__init__(self)
        self.app = app
        self.db = db
        self.go = True

    def run(self):
        timer = time.time()
        while self.go:
            if time.time() - timer >= 3600:
                self.spammer()
                timer = time.time()

            if not self.go:
                break
            time.sleep(1)

    def remove_user(self, user_id):
        try:
            with db_session:
                self.db.execute(f"DELETE FROM bot_event_sended"
                                f" WHERE user = {user_id}")

                self.db.execute(f"DELETE FROM bot_users WHERE "
                                f"tg_id = {user_id}")
        except Exception:
            pass

    def spammer(self):
        with db_session:
            users = self.db.select("SELECT tg_id FROM bot_users")

            for user in users:

                query = f"SELECT id_event, event_name, descrizione, " \
                        f"start_date, event_type.type, image_url, drivers " \
                        f"FROM events INNER JOIN event_type ON " \
                        f"event_type.id_type=events.type " \
                        f"WHERE DATE(creation_date) > CURDATE() AND " \
                        f"(SELECT notify_events FROM bot_users " \
                        f"WHERE tg_id={user} LIMIT 1) IS TRUE AND " \
                        f"id_event NOT IN (SELECT event FROM " \
                        f"bot_event_sended WHERE user={user});"

                for (id_event, event_name, description,
                     start_date, event_type, image_url, drivers) \
                        in self.db.select(query):

                    cars = ""
                    tracks = ""

                    with db_session:
                        for car_name in self.db.select(
                                f"SELECT car_name FROM cars_in_events "
                                f"INNER JOIN cars ON car=id_car "
                                f"WHERE event={id_event};"):
                            cars += f"• {car_name}"

                    with db_session:
                        for track_name, date in self.db.select(
                                f"SELECT track_name, "
                                f"date FROM calendars "
                                f"INNER JOIN tracks "
                                f"ON track=id_track "
                                f"WHERE event={id_event};"
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

                        self.db.execute(F"INSERT INTO bot_event_sended "
                                        F"VALUES(NULL, {user}, {id_event})")

                    except UserIsBlocked:
                        self.remove_user(int(user))

    def stop(self):
        self.go = False
