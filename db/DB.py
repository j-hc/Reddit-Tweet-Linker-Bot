import sqlite3
from sqlite3 import IntegrityError


class TweetDB:
    db_name = "db/TweetDB.db"

    def __init__(self):
        self.db = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute("""CREATE TABLE IF NOT EXISTS tws (userid TEXT, twtext TEXT, backuplink TEXT, UNIQUE(backuplink))""")

    def insert_data(self, userid, twtext, backuplink):
        try:
            self.cur.execute("""INSERT INTO tws VALUES (?,?,?)""", (userid, twtext, backuplink))
            self.db.commit()
        except IntegrityError:
            pass

    def a_query(self, userid, twtext):
        self.cur.execute("""SELECT backuplink FROM tws WHERE userid=? AND INSTR(twtext,?)>0;""", (userid, twtext))
        result = self.cur.fetchone()
        return result
