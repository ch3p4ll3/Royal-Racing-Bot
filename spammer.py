import threading
import time

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
            if time.time() - timer >= 10:
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
                        f"WHERE DATE(creation_date) = CURDATE() AND " \
                        f"(SELECT notify_events FROM bot_users " \
                        f"WHERE tg_id={user} LIMIT 1) IS TRUE AND " \
                        f"id_event NOT IN (SELECT event FROM " \
                        f"bot_event_sended WHERE user={user});"

                for (id_event, event_name, description,
                     start_date, type, image_url, drivers) \
                        in self.db.select(query):

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

                    text = f"**{event_name}**\n\n{description}\n\n" \
                           f"Data di inizio: {start_date}" \
                           f"\nTipologia di evento: {type}" \
                           f"\nNumero di posti: {drivers}"

                    try:
                        if image_url is not None:
                            self.app.send_photo(
                                user,
                                photo=image_url,
                                caption=text,
                                reply_markup=btn
                            )

                        else:
                            self.app.send_message(
                                user,
                                text,
                                reply_markup=btn
                            )

                        self.db.execute(F"INSERT INTO bot_event_sended "
                                        F"VALUES(NULL, {user}, {id_event})")

                    except UserIsBlocked:
                        self.remove_user(user)

    def stop(self):
        self.go = False
