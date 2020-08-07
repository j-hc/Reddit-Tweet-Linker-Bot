import sqlite3
from sqlite3 import IntegrityError


class TweetDB:
    db_name = "db/TweetDB.db"

    def __init__(self):
        with sqlite3.connect(self.db_name, check_same_thread=False) as db:
            with db:
                db.cursor().execute("""CREATE TABLE IF NOT EXISTS tws (userid TEXT, twtext TEXT, backuplink TEXT)""")

    def insert_data(self, userid, twtext, backuplink):
        with sqlite3.connect(self.db_name, check_same_thread=False) as db:
            with db:
                try:
                    db.cursor().execute("""INSERT INTO tws VALUES (?,?,?)""", (userid, twtext, backuplink))
                    db.commit()
                except IntegrityError:
                    pass

    def check_data(self, userid, twtext):
        with sqlite3.connect(self.db_name, check_same_thread=False) as db:
            with db:
                cur = db.cursor()
                cur.execute("""SELECT backuplink FROM tws WHERE userid=? AND WHERE INSTR(book_name,?)>0;""", (userid, twtext))
                result = cur.fetchone()
        if result:
            return True
        else:
            return False
