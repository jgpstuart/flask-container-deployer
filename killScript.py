import sys
from datetime import datetime
import sqlite3 as sql
import docker

def query_db(query, args=(), one=False):
    con = sql.connect("/home/jer/Documents/flaskTest/database.db")
    cur = con.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return(rv[0] if rv else None) if one else rv

def edit_db(query, args=()):
    conn = sql.connect("/home/jer/Documents/flaskTest/database.db")
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    conn.close()


# get the current time and convert to string
now = datetime.now()
timePrint = now.strftime("%H:%M")
print("Current time is: " + str(timePrint))

# query the database for times that match
toKill = query_db("SELECT * FROM IPS WHERE time = ?", [timePrint])

# if there is nothing that needs to be deleted now, exit
if not toKill:
    sys.exit()
else:
    dockerClient = docker.from_env()
    # loop through and kill the containers
    for entry in toKill:
        containerToKill = entry[2]
        tempContainer = dockerClient.containers.get(containerToKill)
        tempContainer.stop()

        # delete the entry with this containerID in the database
        edit_db("DELETE FROM IPS WHERE containerID = ?", [containerToKill])
