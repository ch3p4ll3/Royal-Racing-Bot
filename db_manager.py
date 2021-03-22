import pymysql
from config import DB_HOST, DB_DB, DB_PSW, DB_USER


def connect() -> pymysql.Connection:
    bd_connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PSW,
        database=DB_DB,
        autocommit=True
    )
    return bd_connection


def disconnect(cursor, connection) -> None:
    cursor.close()
    connection.close()


def select(query, values=None):
    bd_connection = connect()
    cursor = bd_connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute(query=query, args=values)

    for i in cursor.fetchall():
        yield i.values()

    disconnect(cursor, bd_connection)


def delete(query, values=None) -> None:
    bd_connection = connect()
    cursor = bd_connection.cursor(pymysql.cursors.DictCursor)

    cursor.execute(query=query, args=values)

    disconnect(cursor, bd_connection)


def update(query, values=None) -> None:
    delete(query, values)


def insert(query, values=None) -> None:
    delete(query, values)
