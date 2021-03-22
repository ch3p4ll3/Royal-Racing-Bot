from datetime import datetime
from db_manager import select, insert, update, delete

from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import UserIsBlocked
from pyrogram.types import InlineKeyboardMarkup, \
    InlineKeyboardButton, CallbackQuery, Message

from config import BASE_URL, SESSION_STRING, API_HASH, API_ID, TG_KEY
from spammer import Spammer

app = Client(
    SESSION_STRING,
    api_hash=API_HASH,
    api_id=API_ID,
    bot_token=TG_KEY,
    parse_mode="markdown"
)

eventi_nuovi = Spammer(app)
eventi_nuovi.start()


def add_user(user_id, name):
    try:
        insert("INSERT IGNORE INTO bot_users(tg_id, tg_name)"
               " VALUES(%s, %s);", (user_id, name,))
    except Exception as e:
        print(e)


def remove_user(user_id):
    try:
        delete("DELETE FROM bot_event_sended WHERE user = %s", (user_id,))

        delete("DELETE FROM bot_users WHERE tg_id = %s", (user_id,))
    except Exception:
        pass


@app.on_message(filters=filters.command("start"))
def start_command(client: Client, message: Message):
    add_user(message.from_user.id, message.from_user.first_name)

    incorso = InlineKeyboardButton("Visualizza eventi in corso", "evento#0")
    passati = InlineKeyboardButton("Visualizza eventi passati", "evento#1")
    programma = InlineKeyboardButton("Visualizza eventi in programma",
                                     "evento#2")
    impostazioni = InlineKeyboardButton("Impostazioni", "impostazioni")

    btn = InlineKeyboardMarkup(
        [[incorso],
         [passati],
         [programma],
         [impostazioni]]
    )

    try:
        message.reply_text("Benvenuto nel bot di Royal Racing."
                           " Resta aggiornato con i nuovi eventi "
                           "organizzati!", reply_markup=btn)
    except UserIsBlocked:
        remove_user(message.from_user.id)


@app.on_callback_query(filters=filters.regex("change_notify"))
def change_notify(client: Client, callback_query: CallbackQuery):
    update("UPDATE bot_users SET notify_events = !notify_events "
           "WHERE tg_id = %s;", (callback_query.from_user.id,))

    settings_callback(client, callback_query)


@app.on_callback_query(filters=filters.regex("impostazioni"))
def settings_callback(client: Client, callback_query: CallbackQuery):
    result = select("SELECT notify_events "
                    "FROM bot_users WHERE "
                    "tg_id = %s;", (callback_query.from_user.id,))
    notify = list(next(result))[0]

    txt = "attivata"
    txt = "disattivata" if not notify else txt

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"Notifiche nuovi eventi {txt}",
                "change_notify"
            )
        ],
        [
            InlineKeyboardButton("Back", "home")
        ]
    ])

    app.edit_message_text(
        callback_query.from_user.id,
        callback_query.message.message_id,
        text="Impostazioni",
        reply_markup=btn
    )


@app.on_callback_query(filters=filters.regex("home"))
def home_callback(client: Client, callback_query: CallbackQuery):
    incorso = InlineKeyboardButton("Visualizza eventi in corso", "evento#0")
    passati = InlineKeyboardButton("Visualizza eventi passati", "evento#1")
    programma = InlineKeyboardButton("Visualizza eventi in programma",
                                     "evento#2")
    impostazioni = InlineKeyboardButton("Impostazioni", "impostazioni")

    btn = InlineKeyboardMarkup(
        [[incorso],
         [passati],
         [programma],
         [impostazioni]]
    )

    try:
        if callback_query.message.photo:
            app.send_message(
                callback_query.from_user.id,
                text="Benvenuto nel bot di Royal Racing."
                     " Resta aggiornato con i nuovi eventi "
                     "organizzati!",
                reply_markup=btn
            )

        else:
            app.edit_message_text(
                callback_query.from_user.id,
                callback_query.message.message_id,
                text="Benvenuto nel bot di Royal Racing."
                     " Resta aggiornato con i nuovi eventi "
                     "organizzati!",
                reply_markup=btn
            )

    except UserIsBlocked:
        remove_user(callback_query.from_user.id)


@app.on_callback_query(filters=filters.regex("dettagliEvento"))
def dettagli_evento(client: Client, callback_query: CallbackQuery):
    event_id = callback_query.data.split("#")[1]
    query = "SELECT id_event, event_name, descrizione, start_date, " \
            "event_type.type, image_url, drivers, COUNT(driver) AS 'subs'" \
            "FROM events INNER JOIN event_type ON " \
            "event_type.id_type=events.type " \
            "INNER JOIN users_with_teams ON " \
            "events.id_event = users_with_teams.event " \
            "WHERE id_event = %s"

    for (id_event, event_name, description,
         start_date, event_type, image_url,
         drivers, subs) in select(query, (event_id,)):

        cars = ""
        tracks = ""

        for car_name in select("SELECT car_name FROM "
                               "cars_in_events INNER "
                               "JOIN cars ON car=id_car "
                               "WHERE event=%s;", (id_event,)):
            cars += f"• {car_name}"

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

        btn = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    event_name,
                    url=f"{BASE_URL}/event-detail/{id_event}"
                )
            ],
            [
                InlineKeyboardButton("Back", "home")
            ]
        ])

        text = f"**{event_name}**\n\n{description}\n" \
               f"\nData di inizio: {start_date}" \
               f"\nTipologia di evento: {event_type}" \
               f"\nNumero di posti: {subs}/{drivers}\n" \
               f"\nAuto:\n{cars}\n\n" \
               f"Tracciati: \n{tracks}"

        try:
            if image_url is not None:
                app.send_photo(
                    callback_query.from_user.id,
                    photo=image_url,
                    caption=text,
                    reply_markup=btn
                )

            else:
                app.edit_message_text(
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    text=text,
                    reply_markup=btn
                )

        except UserIsBlocked:
            remove_user(callback_query.from_user.id)


@app.on_callback_query(filters=filters.regex("evento"))
def evento_callback(client: Client, callback_query: CallbackQuery):
    choice = callback_query.data.split("#")[1]
    btns = []

    if choice == "1":
        query = "SELECT event_name, id_event" \
                " FROM events WHERE CURDATE() > start_date"

        for i, j in select(query):
            btns.append([InlineKeyboardButton(
                i,
                callback_data=f"dettagliEvento#{j}"
            )])

    elif choice == "2":
        query = "SELECT event_name, id_event " \
                "FROM events WHERE CURDATE() < finish_date"

        for i, j in select(query):
            btns.append([InlineKeyboardButton(
                i,
                callback_data=f"dettagliEvento#{j}"
            )])

    else:
        query = "SELECT event_name, id_event " \
                "FROM events WHERE CURDATE() " \
                "BETWEEN start_date AND finish_date"

        for i, j in select(query):
            btns.append([InlineKeyboardButton(
                i,
                callback_data=f"dettagliEvento#{j}"
            )])

    btns.append([InlineKeyboardButton("Back", "home")])

    try:
        app.edit_message_reply_markup(
            callback_query.from_user.id,
            callback_query.message.message_id,
            reply_markup=InlineKeyboardMarkup(btns)
        )

    except UserIsBlocked:
        remove_user(callback_query.from_user.id)


@app.on_message(filters=filters.regex(r"(?i)trello"))
def trello_easter_egg(client: Client, message: Message):
    try:
        message.reply_text(
            """
d888888b
`~~88~~'
      88
      88
      88
      YP\n\n
d8888b.
88  `8D
88oobY'
88`8b
88 `88.
88   YD\n\n
d88888b
88'
88ooooo
88~~~~~
88.
Y88888P\n\n
db
88
88
88
88booo.
Y88888P\n\n
db
88
88
88
88booo.
Y88888P\n\n
  .d88b.
 .8P  Y8.
 88    88
 88    88
`8b  d8'
 `Y88P'
 """, parse_mode=None)

    except UserIsBlocked:
        remove_user(message.from_user.id)
