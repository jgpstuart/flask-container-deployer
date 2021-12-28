###############################################################################
#
# A simple flask setup to start and stop docker containers on a VM with a 
# specific time-to-live (TTL).  It is setup to use Jinja2 templating for
# rendering webpages, but you can edit the pages however you like!  
#
# This setup uses a sqlite database to record the ip address of the requester
# to prevent them from starting more containers before their current container
# is destroyed.  A random port is chosen for the user to connect to, and the 
# program makes sure the port is not already in use before using it.  The time
# that the container is created is also stored, and another script runs to
# delete the container after a set number of minutes.  Finally, the container
# ID string is stored and used to destroy the container when the time comes.
#
# There is an accompanying script - killScript.py - that can be added to run as
# a cronjob every minute that will query the database for containers and delete
# containers at the scheduled time.
#
# Prerequisite Packages: python 3, flask, docker
#
###############################################################################
import flask
from datetime import datetime, timedelta
import sqlite3 as sql
import os
import random
import docker


###############################################################################
#
# Customize the amount of time the container runs (TTL), the name of the
# container that you are running, the port number that the container is
# listening on, and the host name/IP address of the machine that the container
# is running on.
#
###############################################################################

# how long the container will run
containerTTL = 10

# name of the container you're going to run
containerName = "overflow3"

# port the container is listening on
containerPort = 8754

# the ip address of the host, the user will use this to connect to the container
hostName = "8.8.8.8"


###############################################################################
#
# Two methods to interact with the database
#
###############################################################################


# to reduce the amount of query code, this method simplifies things
def query_db(query, args=(), one=False):
    con = sql.connect("database.db")
    cur = con.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return(rv[0] if rv else None) if one else rv

# method to insert rows into the database
def insert_db(query, args=()):
    conn = sql.connect("database.db")
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    conn.close()

###############################################################################
#
# The main code starts here
#
###############################################################################

app = flask.Flask(__name__)
app.config["DEBUG"] = True

# the docker client object, used to interact with docker on your system
dockerClient = docker.from_env()

# DEBUG: delete database if exists
if os.path.exists("database.db"):
    os.remove("database.db")

# creates the database file and connects to it
conn = sql.connect("database.db")

# create the table in the database
conn.execute("CREATE TABLE IPS (ip TEXT, port INTEGER, containerID TEXT, time TEXT)")

# gets a port between 49152-65535 and makes sure it's not already in the database
def getPort():
    # bool for when we find a useable port
    found = False

    while found == False:
        # pick a random port between 49152 and 65535
        port = random.randint(49152, 65535)
        print("port is: " + str(port))

        # check to see if port in use in database
        answer = query_db("SELECT * FROM IPS where port = ?", [port])

        # if empty, return the port number
        if not answer:
            return port


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/startContainer", methods=["POST"])
def startContainer():
    
    # get the current time and convert to string
    now = datetime.now()
    timePrint = now.strftime("%H:%M")

    # get the IP address of the requester
    ipAddr = request.access_route[-1]

    # add "containerTTL" minute(s) to current time, this is the destroy time
    deleteTime = now + timedelta(minutes=containerTTL)
    deleteTime = deleteTime.strftime("%H:%M")

    # add the ip and destroy time to the database
    with sql.connect("database.db") as con:

        # check if ip already has a container launched
        ipCheck = query_db("SELECT * FROM IPS WHERE ip = ?", [ipAddr])

        # don't create conatiner if ip has one already
        if ipCheck:
            return flask.render_template("createError.html", ipAddr=ipAddr)
        else:
            # get a port number for the user
            port = getPort()

            # run the container
            container = dockerClient.containers.run(containerName, ports={containerPort:port}, detach=True)

            # get the conatiner ID for the database
            containerID =  container.id

            # insert the user's ip address, port, containerID, time into the DB
            insert_db("INSERT INTO ips (ip, port, containerID, time) VALUES (?,?,?,?)", [ipAddr, port, containerID, deleteTime])

            # return the start page with the 
            return flask.render_template("startContainer.html", deleteTime=deleteTime, hostName=ipAddr, port=port)