from flask import Flask, render_template, jsonify, redirect, request, session, flash
import logging #allow loggings
import time, sys, json
import yourrobot #import in your own robot functionality
from interfaces.databaseinterface import DatabaseHelper
from datetime import datetime

#Create the database
database = DatabaseHelper('Fire Robot.sqlite')
#Create Robot first. It take 4 seconds to initialise the robot, sensor view wont work until robot is created...
robot = yourrobot.Robot()
if robot.get_battery() < 6: #the robot motors will disable at 6 volts
    robot.safe_exit()

#Global Variables
app = Flask(__name__)
SECRET_KEY = 'my random key can be anything' #this is used for encrypting sessions
app.config.from_object(__name__) #Set app configuration using above SETTINGS
robot.set_log(app.logger) #set the logger inside the robot
database.set_log(app.logger) #set the logger inside the database
LPOWER = 32 #constant power/speed
RPOWER = 30 #to account for an inconsistancy in the output of the two motors
junctionColour = "Red"

#Request Handlers ---------------------------------------------
#home page and login
@app.route('/', methods=['GET','POST'])
def index():
    session['VictimFound'] = False
    if 'userid' in session:
        return redirect('./missioncontrol') #no form data is carried across using 'dot/'
    if request.method == "POST":  #if form data has been sent
        email = request.form['email']   #get the form field with the name 
        password = request.form['password']
        # TODO - need to make sure only one user is able to login at a time...
        userdetails = database.ViewQueryHelper("SELECT * FROM UserTbl WHERE Email=? AND Password=?",(email,password))
        if len(userdetails) != 0:  #rows have been found
            row = userdetails[0] #userdetails is a list of dictionaries
            session['userid'] = row['UserID']
            session['username'] = row['FullName']
            return redirect('./missioncontrol')
        else:
            flash("Sorry no user found, password or username incorrect")
    else:
        flash("No data submitted")
    return render_template('index.html')

def startfire(state,suburb,street,number):
    locationdetails = database.ViewQueryHelper("SELECT LocationID FROM LocationTbl WHERE Number=? AND Street=? AND Suburb=? AND State=?",(number,street,suburb,state))
    row = locationdetails[0]
    locationid = row['LocationID']
    starttime = time.time()
    database.ModifyQueryHelper('INSERT INTO FireTbl (LocationID, UserID, StartTime) VALUES (?,?,?)',(locationid,session['userid'],starttime))

@app.route('/locationform', methods=['GET','POST'])
def locationform():
    state = request.form['state']
    suburb = request.form['suburb']
    street = request.form['street']
    number = request.form['number']
    print(street, number, suburb, state)
    if state != "" and suburb != "" and street != "" and number != "":
        locationid = database.ViewQueryHelper("SELECT LocationID FROM LocationTbl WHERE Number=? AND Street=? AND Suburb=? AND State=?",(number,street,suburb,state))
        if len(locationid) != 0:
            return
        else:
            database.ModifyQueryHelper('INSERT INTO LocationTbl (State, Suburb, Street, Number) VALUES (?,?,?,?)',(state,suburb,street,number))
            startfire(state,suburb,street,number)
            return

@app.route('/pastlocation', methods=['GET','POST'])
def pastlocation():
    location = request.form['pastlocation']
    if location != "No Past Locations":
        locationparts = location.split(" ")
        number = locationparts[0]
        street = locationparts[1]
        suburb = locationparts[2]
        state = locationparts[3]
        startfire(state,suburb,street,number)
        return
    else:
        return

#home page
@app.route('/missioncontrol')
def missioncontrol():
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    locationdetails = database.ViewQueryHelper("SELECT State, Suburb, Street, Number FROM LocationTbl")
    locations = []
    print(locationdetails)
    if len(locationdetails) != 0:
        for location in locationdetails:
            locations.append(str(location['Number']) + " " + str(location['Street']) + " " +  str(location['Suburb']) + " " + str(location['State']))
    else:
        locations = "No Past Locations"
    return render_template("missioncontrol.html", configured = robot.Configured, voltage = robot.get_battery(), locations = locations)

#dashboard
@app.route('/sensorview', methods=['GET','POST'])
def sensorview():
    if not robot.Configured: #make sure robot is funcitoning
        return redirect('./')
    if 'userid' not in session:
        return redirect('./')
    return render_template("sensorview.html", configured = robot.Configured)

#get all stats and return through JSON
@app.route('/getallstats', methods=['GET','POST'])
def getallstats():
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    robot.CurrentCommand = "getting all stats"
    results = robot.get_all_sensors()
    return jsonify(results)

#map or table of fire and path data
@app.route('/map')
def map():
    if not robot.Configured: #make sure robot is
        return redirect('./')
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    results = None
    return render_template('map.html', results=results, configured = robot.Configured)

#start robot moving
@app.route('/forward', methods=['GET','POST'])
def forward():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "moving forward"
    heading = robot.get_orientation_IMU()
    duration = None
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 25)
    robot.CurrentCommand = "stop"
    return jsonify({ "message":"moving forward", "duration":duration, "heading":heading[0]}) #jsonify take any type and makes a JSON
    
#start robot moving backwards
@app.route('/reverse', methods=['GET','POST'])
def reverse():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "reversing"
    duration = robot.rotate_power_degrees_IMU(20, 180)
    robot.CurrentCommand = "stop"
    #save data to the databas
    return jsonify({ "message":"reversing", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/turnright', methods=['GET','POST'])
def turnright():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "turning right"
    duration = robot.rotate_power_degrees_IMU(20, 90)
    robot.CurrentCommand = "stop"
    #save data to the databas
    return jsonify({ "message":"turning right", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/turnleft', methods=['GET','POST'])
def turnleft():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "turning left"
    duration = robot.rotate_power_degrees_IMU(20, -90)
    robot.CurrentCommand = 'stop'
    #save data to the databas
    return jsonify({ "message":"turning left", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/closeclaw', methods=['GET','POST'])
def closeclaw():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "closing claw"
    duration = None
    while robot.CurrentCommand != "stop":
        duration = robot.close_claw()
        robot.CurrentCommand = 'stop'
    #save data to the databas
    return jsonify({ "message":"closing claw", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/openclaw', methods=['GET','POST'])
def openclaw():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "opening claw"
    duration = None
    while robot.CurrentCommand != "stop":
        duration = robot.open_claw()
        robot.CurrentCommand = 'stop'
    #save data to the databas
    return jsonify({ "message":"opening claw", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/tojunction', methods=['GET','POST'])
def movetojunction():
    if not robot.Configured: #make sure robot is configured
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "auto moving forward"
    duration = None
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 20)
    jsonify({ "message":"moving until junction", "duration":duration }) #jsonify take any type and makes a JSON
    if robot.CurrentCommand != "stop":
        identifyjunction()
    return 

def identifyjunction():
    robot.CurrentCommand = "identifying junction"
    if robot.CurrentCommand != "stop":
        distancemeasured = robot.get_ultra_sensor()
        if distancemeasured >= 20 and distancemeasured != 0.0:
            navigateintersection("intersection")
        else:   
            tempmeasured = robot.get_thermal_sensor()
            if tempmeasured > 40:
                jsonify({ "message":"fire detected"})
                navigateintersection("fire")
                #a fire was detected, so the robot treats it as a wall but logs it
            elif tempmeasured < 20:
                #using an icepack or cold can of soft drint for victim
                jsonify({ "message":"victim found"})
                session['VictimFound'] = True
                collectvictim()
            else:
                navigateintersection("wall")
    return jsonify({ "message":"identifying junction"})

def collectvictim():
    robot.CurrentCommand = "moving towards victim"
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 5)
    robot.CurrentCommand = "closing claw"
    duration = None
    while robot.CurrentCommand != "stop":
        duration = robot.close_claw()
        robot.CurrentCommand = 'stop'
    reverse()
    movetojunction()

def navigateintersection(collisiontype):
    robot.CurrentCommand = "navigating intersection"
    if session['VictimFound'] == False:
        robot.CurrentCommand = "Turning Left"
        duration = robot.rotate_power_degrees_IMU(20, -90)
        if robot.CurrentCommand != "stop":
            distancemeasured = robot.get_ultra_sensor() #reading ultrasonic to see if there is a wall infront
            if distancemeasured >= 40 and distancemeasured != 0.0:
                movetojunction()
                #turned left
            else:
                if collisiontype == "intersection":
                    robot.CurrentCommand = "Turning Right"
                    duration = robot.rotate_power_degrees_IMU(20, 90)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 40 and distancemeasured != 0.0:
                        movetojunction()
                        #went straight
                    else:
                        robot.CurrentCommand = "Turning Right"
                        duration = robot.rotate_power_degrees_IMU(20, 90)
                        distancemeasured = robot.get_ultra_sensor()
                        if distancemeasured >= 40 and distancemeasured != 0.0:
                            movetojunction()
                            #turned right
                        else:
                            robot.CurrentCommand = "Turning Right"
                            duration = robot.rotate_power_degrees_IMU(20, 90)
                            movetojunction()
                            #reversed
                elif collisiontype == "wall" or collisiontype == "fire":
                    robot.CurrentCommand = "Reversing"
                    duration = robot.rotate_power_degrees_IMU(20, 180)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 40 and distancemeasured != 0.0:
                        movetojunction()
                        #turned right
                    else:
                        robot.CurrentCommand = "Turning Right"
                        duration = robot.rotate_power_degrees_IMU(20, 90)
                        movetojunction()
                        #reversed
    elif session['VictimFound'] == True:
        robot.CurrentCommand = "Turning Right"
        duration = robot.rotate_power_degrees_IMU(20, 90)
        if robot.CurrentCommand != "stop":
            distancemeasured = robot.get_ultra_sensor() #reading ultrasonic to see if there is a wall infront
            if distancemeasured >= 40 and distancemeasured != 0.0:
                movetojunction()
                #turned left
            else:
                if collisiontype == "intersection":
                    robot.CurrentCommand = "Turning Left"
                    duration = robot.rotate_power_degrees_IMU(20, -90)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 40 and distancemeasured != 0.0:
                        movetojunction()
                        #went straight
                    else:
                        robot.CurrentCommand = "Turning Left"
                        duration = robot.rotate_power_degrees_IMU(20, -90)
                        distancemeasured = robot.get_ultra_sensor()
                        if distancemeasured >= 40 and distancemeasured != 0.0:
                            movetojunction()
                            #turned right
                        else:
                            robot.CurrentCommand = "Turning Left"
                            duration = robot.rotate_power_degrees_IMU(20, -90)
                            movetojunction()
                            #reversed
                elif collisiontype == "wall" or collisiontype == "fire":
                    robot.CurrentCommand = "Reversing"
                    duration = robot.rotate_power_degrees_IMU(20, 180)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 40 and distancemeasured != 0.0:
                        movetojunction()
                        #turned right
                    else:
                        robot.CurrentCommand = "Turning Left"
                        duration = robot.rotate_power_degrees_IMU(20, -90)
                        movetojunction()
                        #reversed
    return jsonify({ "message":"navigating intersection"})

'''def navigatewall():
    robot.CurrentCommand = "navigating wall"
    robot.CurrentCommand = "Turning Left"
    duration = robot.rotate_power_degrees_IMU(20, -90)
    if robot.CurrentCommand != "stop":
        distancemeasured = robot.get_ultra_sensor() #reading ultrasonic to see if there is a wall infront
        if distancemeasured < 40 and distancemeasured != 0:
            robot.CurrentCommand = "Reversing"
            duration = robot.rotate_power_degrees_IMU(20, 180)
            distancemeasured = robot.get_ultra_sensor()
            if distancemeasured < 40 and distancemeasured != 0:
                robot.CurrentCommand = "Turning Right"
                duration = robot.rotate_power_degrees_IMU(20, 90)
                movetojunction()
                #reversed
            else:
                movetojunction()
                #went right
        else:
            movetojunction()
            #turned left
    return jsonify({ "message":"navigating path obstruction"})'''

#creates a route to get all the event data
@app.route('/getallusers', methods=['GET','POST'])
def getallusers():
    results = database.ViewQueryHelper("SELECT * FROM users")
    return jsonify([dict(row) for row in results]) #jsonify doesnt work with an SQLite.Row

#Get the current command from brickpiinterface.py
@app.route('/getcurrentcommand', methods=['GET','POST'])
def getcurrentcommand():
    return jsonify({"currentcommand":robot.CurrentCommand})

@app.route('/getheading', methods=['GET','POST'])
def getheading():
    heading = robot.get_orientation_IMU()[0]
    return jsonify({'heading':heading})

@app.route('/getmovement', methods=['GET','POST'])
def getmovement():
    heading = robot.get_orientation_IMU()[0]
    command = robot.CurrentCommand
    return jsonify({'heading':heading, 'command':command})

#get the current routine from robot.py
@app.route('/getcurrentroutine', methods=['GET','POST'])
def getcurrentroutine():
    return jsonify({"currentroutine":robot.CurrentRoutine})

#get the configuration status from brickpiinterface
@app.route('/getconfigured', methods=['GET','POST'])
def getconfigured():
    return jsonify({"configured":robot.Configured})

#Start callibration of the IMU sensor
@app.route('/getcalibration', methods=['GET','POST'])
def getcalibration():
    calibration = "Not Calibrated"
    if robot.calibrate_imu():
        calibration = "Calibrated"
    return jsonify({"calibration":calibration})

#Start callibration of the IMU sensor
@app.route('/reconfigIMU', methods=['GET','POST'])
def reconfigIMU():
    robot.reconfig_IMU()
    return jsonify({"reconfigure":"reconfiguring_IMU"})

#Stop current process
@app.route('/stop', methods=['GET','POST'])
def stop():
    robot.stop_all()
    return jsonify({ "message":"stopping" })

#Shutdown the web server
@app.route('/shutdown', methods=['GET','POST'])
def shutdown():
    session['FoundVictim'] = False
    robot.safe_exit()
    func = request.environ.get('werkzeug.server.shutdown')
    func()
    return jsonify({ "message":"shutting down" })

#Log a message
def log(message):
    app.logger.info(message)
    return

#---------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

#Threaded mode is important if using shared resources e.g. sensor, each user request launches a thread.. However, with Threaded Mode on errors can occur if resources are not locked down e.g trying to access live readings - conflicts can occur due to processor lock. Use carefully..
