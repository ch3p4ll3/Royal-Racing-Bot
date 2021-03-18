from os import getenv

from pony.orm import Database, db_session
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import UserIsBlocked
from pyrogram.types import InlineKeyboardMarkup, \
    InlineKeyboardButton, CallbackQuery, Message

from config import BASE_URL, DB_DB, DB_PSW, DB_USER, \
    DB_HOST, SESSION_STRING, API_HASH, API_ID
from spammer import Spammer

db = Database()

app = Client(
    SESSION_STRING,
    api_hash=API_HASH,
    api_id=API_ID,
    bot_token=getenv("TG-KEY"),
    parse_mode="markdown"
)

db.bind(
    provider='mysql',
    host=DB_HOST,
    user=DB_USER,
    passwd=DB_PSW,
    db=DB_DB
)


def add_user(user_id, name):
    try:
        with db_session:
            db.execute(f"INSERT IGNORE INTO bot_users(tg_id, tg_name) "
                       f"VALUES('{user_id}', '{name}');")
    except Exception as e:
        print(e)


def remove_user(user_id):
    try:
        with db_session:
            db.execute(f"DELETE FROM bot_event_sended WHERE user = {user_id}")

            db.execute(f"DELETE FROM bot_users WHERE tg_id = {user_id}")
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
    with db_session:
        db.execute(f"UPDATE bot_users SET notify_events = !notify_events "
                   f"WHERE tg_id={callback_query.from_user.id};")

    settings_callback(client, callback_query)


@app.on_callback_query(filters=filters.regex("impostazioni"))
def settings_callback(client: Client, callback_query: CallbackQuery):
    with db_session:
        notify = db.select(f"SELECT notify_events FROM bot_users "
                           f"WHERE tg_id = {callback_query.from_user.id}")[0]

    txt = " attivata"
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
    query = f"SELECT id_event, event_name, descrizione, start_date, " \
            f"event_type.type, image_url, drivers, COUNT(driver) AS 'subs'" \
            f"FROM events INNER JOIN event_type ON " \
            f"event_type.id_type=events.type " \
            f"INNER JOIN users_with_teams ON " \
            f"events.id_event = users_with_teams.event " \
            f"WHERE id_event = {event_id}"

    with db_session:
        for (id_event, event_name, description,
             start_date, event_type, image_url,
             drivers, subs) in db.execute(query):

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
                   f"Data di inizio: {start_date}" \
                   f"\nTipologia di evento: {event_type}" \
                   f"\nNumero di posti: {subs}/{drivers}"

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
        with db_session:
            query = "SELECT event_name, id_event" \
                    " FROM events WHERE CURDATE() > start_date"

            for i, j in db.execute(query):
                btns.append([InlineKeyboardButton(
                    i,
                    callback_data=f"dettagliEvento#{j}"
                )])

    elif choice == "2":
        with db_session:
            query = "SELECT event_name, id_event " \
                    "FROM events WHERE CURDATE() < finish_date"

            for i, j in db.execute(query):
                btns.append([InlineKeyboardButton(
                    i,
                    callback_data=f"dettagliEvento#{j}"
                )])

    else:
        with db_session:
            query = "SELECT event_name, id_event " \
                    "FROM events WHERE CURDATE() " \
                    "BETWEEN start_date AND finish_date"

            for i, j in db.execute(query):
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
        message.reply_text("""
d888888b 
`~~88~~' 
   88    
   88    
   88    
   YP    
         
         
d8888b.  
88  `8D  
88oobY'  
88`8b    
88 `88.  
88   YD  
         
         
d88888b  
88'      
88ooooo  
88~~~~~  
88.      
Y88888P  
         
         
db       
88       
88       
88       
88booo.  
Y88888P  
         
         
db       
88       
88       
88       
88booo.  
Y88888P  
         
         
 .d88b.  
.8P  Y8. 
88    88 
88    88 
`8b  d8' 
 `Y88P'  
 """)

    except UserIsBlocked:
        remove_user(message.from_user.id)


eventi_nuovi = Spammer(app, db)
eventi_nuovi.start()


@app.on_disconnect()
async def stop_spammer(client: Client):
    await eventi_nuovi.stop()
