from flask import Flask, render_template, jsonify, redirect, request, session, flash
import logging #allow loggings
import time, sys, json
import yourrobot #import in your own robot functionality
from interfaces.databaseinterface import DatabaseHelper
import datetime

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
    session['DetectingIntersections'] = True
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

@app.route('/endfire', methods=['GET','POST'])
def endfire():
    database.ModifyQueryHelper('UPDATE FireTbl SET Complete=? WHERE FireID=?',("True",int(session['fireid'])))
    userid = session['userid']
    session.clear()
    session['userid'] = userid
    session['FoundVictim'] = False
    return redirect('/missioncontrol')

def saveevent(elapsedtime):
    if 'locationid' in session and 'fireid' in session:
        heading = robot.get_orientation_IMU()[0]
        temp = robot.get_thermal_sensor()
        database.ModifyQueryHelper('INSERT INTO EventsTbl (FireID, EventType, Temp, ElapsedTime, Heading) VALUES (?,?,?,?,?)',(int(session['fireid']),str(robot.CurrentCommand),float(temp),float(elapsedtime),float(heading)))
    return

def startfire():
    starttime = datetime.datetime.now()
    starttime = str(starttime)[:19]
    database.ModifyQueryHelper('INSERT INTO FireTbl (LocationID, UserID, StartTime) VALUES (?,?,?)',(session['locationid'],session['userid'],starttime))
    firedetails = database.ViewQueryHelper("SELECT FireID FROM FireTbl WHERE LocationID=? AND UserID=? AND StartTime=?",(session['locationid'],session['userid'],starttime))
    row = firedetails[0]
    session['fireid'] = row['FireID']

@app.route('/locationform', methods=['GET','POST'])
def locationform():
    state = request.form['state']
    suburb = request.form['suburb']
    street = request.form['street']
    number = request.form['number']
    
    if state != "" and suburb != "" and street != "" and number != "":
        locationidreturn = database.ViewQueryHelper("SELECT LocationID FROM LocationTbl WHERE Number=? AND Street=? AND Suburb=? AND State=?",(number,street,suburb,state))
        if len(locationidreturn) != 0:
            return redirect('/missioncontrol')
        else:
            database.ModifyQueryHelper('INSERT INTO LocationTbl (State, Suburb, Street, Number) VALUES (?,?,?,?)',(state,suburb,street,number))
            locationidreturn = database.ViewQueryHelper("SELECT LocationID FROM LocationTbl WHERE Number=? AND Street=? AND Suburb=? AND State=?",(number,street,suburb,state))
            row = locationidreturn[0]
            session['locationid'] = row['LocationID']
            startfire(state,suburb,street,number)
            return redirect('/missioncontrol')

@app.route('/pastlocation', methods=['GET','POST'])
def pastlocation():
    location = request.form.get('pastlocation')
    if location != "No Past Locations": 
        session['locationid'] = location
        startfire()
        return redirect('/missioncontrol')
    else:
        return redirect('/missioncontrol')

#home page
@app.route('/missioncontrol')
def missioncontrol():
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    locationdetails = database.ViewQueryHelper("SELECT LocationID, State, Suburb, Street, Number FROM LocationTbl")
    locations = []
    if len(locationdetails) != 0:
        for location in locationdetails:
            locations.append({"location":str(location['Number']) + " " + str(location['Street']) + " " +  str(location['Suburb']) + " " + str(location['State']),"id":location['LocationID']})
    else:
        locations = "No Past Locations"
    return render_template("missioncontrol.html", configured = robot.Configured, voltage = robot.get_battery(), locations = locations, session = session)

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

@app.route('/getevents', methods=['GET','POST'])
def getevents():
    events = "no events"
    if "reviewedfire" in session:
        returnedevents = database.ViewQueryHelper("SELECT EventType, ElapsedTime, Temp, Heading FROM EventsTbl WHERE FireID = ? ORDER BY EventID ASC", (session['reviewedfire'],))
        if len(returnedevents) == 0:
            events = "no events"
        else:
            events = []
            for event in returnedevents:
                events.append(event['EventType'])
                events.append(event['Heading'])
                events.append(event['ElapsedTime'])
    return jsonify({"events":events})

@app.route('/reviewedfireform', methods=['GET','POST'])
def reviewedlocationform():
    session['reviewedfire'] = request.form['reviewedfire']
    return redirect('/pastfires')

#map or table of fire and path data
@app.route('/pastfires')
def pastfires():
    if not robot.Configured: #make sure robot is
        return redirect('./')
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    events = []
    reviewedlocationdetails = []
    reviewedfirestart = []
    username = ""
    if 'reviewedfire' in session:
        events = database.ViewQueryHelper("SELECT EventType, ElapsedTime, Temp, Heading FROM EventsTbl WHERE FireID = ? ORDER BY EventID ASC", (session['reviewedfire'],))
        reviewedlocationdetailsreturned = database.ViewQueryHelper("SELECT LocationTbl.State, LocationTbl.Suburb, LocationTbl.Street, LocationTbl.Number, UserTbl.FullName, FireTbl.StartTime FROM LocationTbl, FireTbl, UserTbl WHERE FireTbl.LocationID = LocationTbl.LocationID AND FireTbl.FireID=? AND FireTbl.UserID = UserTBl.UserID;",(session['reviewedfire'],))
        reviewedlocationdetails = reviewedlocationdetailsreturned[0]
        if len(events) == 0:
            events = "no events"
    firedetails = database.ViewQueryHelper("SELECT FireID, LocationID, StartTime FROM FireTbl WHERE Complete = ?",("True",))
    fires = []
    if len(firedetails) != 0:
        for fire in firedetails:
            locationdetails = database.ViewQueryHelper("SELECT State, Suburb, Street, Number FROM LocationTbl WHERE LocationID = ?",(fire['LocationID'],))
            location = locationdetails[0]
            datetimeparts = fire['StartTime'].split()
            date = datetimeparts[0]
            time = datetimeparts[1]
            fires.append({"details":str(location['Number']) + " " + str(location['Street']) + " " +  str(location['Suburb']) + " " + str(location['State']) + " on " + str(date) + " at " + str(time),"id":fire['FireID']})
    else:
        locations = "No Past Fires"
    return render_template('map.html', fires = fires, configured = robot.Configured, session = session, events = events, details = reviewedlocationdetails)

#start robot moving
@app.route('/forward', methods=['GET','POST'])
def forward():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "moving forward"
    heading = robot.get_orientation_IMU()
    duration = None
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 25)
    robot.CurrentCommand = "Moving Forward"
    saveevent(duration)
    robot.CurrentCommand = "stop"
    return jsonify({ "message":"moving forward", "duration":duration, "heading":heading[0]}) #jsonify take any type and makes a JSON
    
#start robot moving backwards
@app.route('/reverse', methods=['GET','POST'])
def reverse():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "Reversed"
    duration = robot.rotate_power_degrees_IMU(20, 180)
    saveevent(duration)
    robot.CurrentCommand = "stop"
    #save data to the databas
    return jsonify({ "message":"Reversed", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/turnright', methods=['GET','POST'])
def turnright():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "Turned Right"
    duration = robot.rotate_power_degrees_IMU(20, 90)
    saveevent(duration)
    robot.CurrentCommand = "stop"
    #save data to the databas
    return jsonify({ "message":"Turned Right", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/turnleft', methods=['GET','POST'])
def turnleft():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "Turned Left"
    duration = robot.rotate_power_degrees_IMU(20, -90)
    saveevent(duration)
    robot.CurrentCommand = 'stop'
    #save data to the databas
    return jsonify({ "message":"Turned Left", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/closeclaw', methods=['GET','POST'])
def closeclaw():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "Closed Claw"
    duration = None
    while robot.CurrentCommand != "stop":
        duration = robot.close_claw()
        saveevent(duration)
        robot.CurrentCommand = 'stop'
    #save data to the databas
    return jsonify({ "message":"Closed Claw", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/openclaw', methods=['GET','POST'])
def openclaw():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "Opened Claw"
    duration = None
    while robot.CurrentCommand != "stop":
        duration = robot.open_claw()
        saveevent(duration)
        robot.CurrentCommand = 'stop'
    #save data to the databas
    return jsonify({ "message":"Opened Claw", "duration":duration }) #jsonify take any type and makes a JSON

@app.route('/tojunction', methods=['GET','POST'])
def movetojunction():
    if not robot.Configured: #make sure robot is configured
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "Auto Moving Forward"
    duration = None
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 20)
    saveevent(duration)
    jsonify({ "message":"Auto Moving Forward", "duration":duration }) #jsonify take any type and makes a JSON
    if robot.CurrentCommand != "stop":
        identifyjunction()
    return 

def identifyjunction():
    robot.CurrentCommand = "Identifying Junction"
    if robot.CurrentCommand != "stop":
        distancemeasured = robot.get_ultra_sensor()
        if distancemeasured > 20 and distancemeasured != 0.0:
            duration = 0
            robot.CurrentCommand = "Junction Detected"
            saveevent(duration)
            if session['DetectingIntersections'] == True
                navigateintersection("intersection")
            else:
                session['DetectingIntersections'] = True
                #robot.move_power_time(RPOWER, LPOWER, time) to get of the red tape when you know that you are exiting a junction
                movetojunction()
        else:   
            tempmeasured = robot.get_thermal_sensor()
            if tempmeasured > 40:
                duration = 0
                robot.CurrentCommand = "Fire Detected"
                saveevent(duration)
                navigateintersection("fire")
                #a fire was detected, so the robot treats it as a wall but logs it
            elif tempmeasured < 20:
                #using an icepack or cold can of soft drint for victim
                duration = 0
                robot.CurrentCommand = "Victim Found"
                saveevent(duration)
                session['VictimFound'] = True
                collectvictim()
            else:
                duration = 0
                robot.CurrentComman = "Wall Detected"
                saveevent(duration)
                navigateintersection("wall")
    return jsonify({ "message":"identifying junction"})

def collectvictim():
    robot.CurrentCommand = "Colleting Victim"
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 5)
    while robot.CurrentCommand != "stop":
        duration += robot.close_claw()
        robot.CurrentCommand = 'stop'
    duration += robot.rotate_power_degrees_IMU(20, 180)
    saveevent(duration)
    movetojunction()

def navigateintersection(collisiontype):
    if session['DetectingIntersections'] == True:
        #robot.move_power_time(RPOWER, LPOWER, time)
        session['DetectingIntersections'in] = False
    robot.CurrentCommand = "Navigating Intersection"
    starttime = time.time()
    if session['VictimFound'] == False:
        robot.rotate_power_degrees_IMU(20, -90)
        if robot.CurrentCommand != "stop":
            distancemeasured = robot.get_ultra_sensor() #reading ultrasonic to see if there is a wall infront
            if distancemeasured >= 40 and distancemeasured != 0.0:
                elapsedtime = time.time() - starttime
                saveevent(elapsedtime)
                robot.CurrentCommand = "Turned Left"
                duration = 0
                saveevent(duration)
                movetojunction()
                #turned left
            else:
                if collisiontype == "intersection":
                    robot.rotate_power_degrees_IMU(20, 90)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 30 and distancemeasured != 0.0:
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Went Straight"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
                        #went straight
                    else:
                        duration = robot.rotate_power_degrees_IMU(20, 90)
                        distancemeasured = robot.get_ultra_sensor()
                        if distancemeasured >= 30 and distancemeasured != 0.0:
                            elapsedtime = time.time() - starttime
                            saveevent(elapsedtime)
                            robot.CurrentCommand = "Turned Right"
                            duration = 0
                            saveevent(duration)
                            movetojunction()
                            #turned right
                        else:
                            robot.rotate_power_degrees_IMU(20, 90)
                            elapsedtime = time.time() - starttime
                            saveevent(elapsedtime)
                            robot.CurrentCommand = "Reversed"
                            duration = 0
                            saveevent(duration)
                            movetojunction()
                            #reversed
                elif collisiontype == "wall" or collisiontype == "fire":
                    robot.rotate_power_degrees_IMU(20, 180)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 30 and distancemeasured != 0.0:
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Turned Right"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
                        #turned right
                    else:
                        robot.rotate_power_degrees_IMU(20, 90)
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Reversed"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
                        #reversed
    elif session['VictimFound'] == True:
        duration = robot.rotate_power_degrees_IMU(20, 90)
        if robot.CurrentCommand != "stop":
            distancemeasured = robot.get_ultra_sensor() #reading ultrasonic to see if there is a wall infront
            if distancemeasured >= 30 and distancemeasured != 0.0:
                elapsedtime = time.time() - starttime
                saveevent(elapsedtime)
                robot.CurrentCommand = "Turned Right"
                duration = 0
                saveevent(duration)
                movetojunction()
                #turned left
            else:
                if collisiontype == "intersection":
                    duration = robot.rotate_power_degrees_IMU(20, -90)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 30 and distancemeasured != 0.0:
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Went Straight"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
                        #went straight
                    else:
                        duration = robot.rotate_power_degrees_IMU(20, -90)
                        distancemeasured = robot.get_ultra_sensor()
                        if distancemeasured >= 30 and distancemeasured != 0.0:
                            elapsedtime = time.time() - starttime
                            saveevent(elapsedtime)
                            robot.CurrentCommand = "Turned Left"
                            duration = 0
                            saveevent(duration)
                            movetojunction()
                        else:
                            obot.rotate_power_degrees_IMU(20, -90)
                            elapsedtime = time.time() - starttime
                            saveevent(elapsedtime)
                            robot.CurrentCommand = "Reversed"
                            duration = 0
                            saveevent(duration)
                            movetojunction()
                            #reversed
                elif collisiontype == "wall" or collisiontype == "fire":
                    duration = robot.rotate_power_degrees_IMU(20, 180)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 30 and distancemeasured != 0.0:
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Turned Left"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
                        #turned right
                    else:
                        robot.rotate_power_degrees_IMU(20, -90)
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Reversed"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
                        #reversed
    return jsonify({ "message":"Navigating Intersection"})

'''def navigatewall():
    robot.CurrentCommand = "navigating wall"
    robot.CurrentCommand = "Turned Left"
    duration = robot.rotate_power_degrees_IMU(20, -90)
    if robot.CurrentCommand != "stop":
        distancemeasured = robot.get_ultra_sensor() #reading ultrasonic to see if there is a wall infront
        if distancemeasured < 40 and distancemeasured != 0:
            robot.CurrentCommand = "Reversed"
            duration = robot.rotate_power_degrees_IMU(20, 180)
            distancemeasured = robot.get_ultra_sensor()
            if distancemeasured < 40 and distancemeasured != 0:
                robot.CurrentCommand = "Turned Right"
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
    session.clear()
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
