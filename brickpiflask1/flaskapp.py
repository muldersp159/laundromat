from flask import Flask, render_template, jsonify, redirect, request, session, flash, Response
import logging #allow loggings
import time, sys, json
import yourrobot #import in your own robot functionality
from interfaces.databaseinterface import DatabaseHelper
import datetime
from time import sleep
from camera_pi import Camera #a picam extension

database = DatabaseHelper('Fire Robot.sqlite')#Create the database
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

def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/', methods=['GET','POST']) #login page
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
        if len(userdetails) != 0:
            #saving info to session for login validation on other pages
            row = userdetails[0]
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
    #updating the current fire in the session to being complete
    database.ModifyQueryHelper('UPDATE FireTbl SET Complete=? WHERE FireID=?',("True",int(session['fireid'])))
    userid = session['userid']
    session.clear()
    session['userid'] = userid
    session['FoundVictim'] = False
    return redirect('/missioncontrol')

def startfire():
    #creating a new fire at the locaiton passed in
    starttime = datetime.datetime.now()
    starttime = str(starttime)[:19]
    database.ModifyQueryHelper('INSERT INTO FireTbl (LocationID, UserID, StartTime) VALUES (?,?,?)',(session['locationid'],session['userid'],starttime))
    firedetails = database.ViewQueryHelper("SELECT FireID FROM FireTbl WHERE LocationID=? AND UserID=? AND StartTime=?",(session['locationid'],session['userid'],starttime))
    row = firedetails[0]
    session['fireid'] = row['FireID']

def saveevent(elapsedtime):
    #only saving data if location selected
    if 'locationid' in session and 'fireid' in session:
        heading = robot.get_orientation_IMU()[0]
        temp = robot.get_thermal_sensor()
        database.ModifyQueryHelper('INSERT INTO EventsTbl (FireID, EventType, Temp, ElapsedTime, Heading) VALUES (?,?,?,?,?)',(int(session['fireid']),str(robot.CurrentCommand),float(temp),float(elapsedtime),float(heading)))
        #saving current command info into db
        #rather than having a save for each function, just have the one
    return

@app.route('/locationform', methods=['GET','POST'])
def locationform():
    state = request.form['state']
    suburb = request.form['suburb']
    street = request.form['street']
    number = request.form['number']
    #validate that no fields are empty
    if state != "" and suburb != "" and street != "" and number != "":
        #checking not creating a location that already exists
        locationidreturn = database.ViewQueryHelper("SELECT LocationID FROM LocationTbl WHERE Number=? AND Street=? AND Suburb=? AND State=?",(number,street,suburb,state))
        if len(locationidreturn) != 0:
            return redirect('/missioncontrol')
        else:
            database.ModifyQueryHelper('INSERT INTO LocationTbl (State, Suburb, Street, Number) VALUES (?,?,?,?)',(state,suburb,street,number))
            locationidreturn = database.ViewQueryHelper("SELECT LocationID FROM LocationTbl WHERE Number=? AND Street=? AND Suburb=? AND State=?",(number,street,suburb,state))
            row = locationidreturn[0]
            session['locationid'] = row['LocationID']
            startfire()
            return redirect('/missioncontrol')
    else: 
        return redirect('/missioncontrol')

@app.route('/pastlocation', methods=['GET','POST'])
def pastlocation():
    #where user has selected a previous location
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
        return redirect('./') #no form data is carried across using './'
    locationdetails = database.ViewQueryHelper("SELECT LocationID, State, Suburb, Street, Number FROM LocationTbl")
    locations = []
    #getting all past llocations for drop-down
    if len(locationdetails) != 0:
        #only creates the dropdown if there are past locations
        for location in locationdetails:
            locations.append({"location":str(location['Number']) + " " + str(location['Street']) + " " +  str(location['Suburb']) + " " + str(location['State']),"id":location['LocationID']})
    else:
        locations = "No Past Locations"
    return render_template("missioncontrol.html", configured = robot.Configured, voltage = robot.get_battery(), locations = locations, session = session)

#dashboard
@app.route('/sensorview', methods=['GET','POST'])
def sensorview():
    if not robot.Configured: #make sure robot is functioning
        return redirect('./')
    if 'userid' not in session:
        return redirect('./')
    return render_template("sensorview.html", configured = robot.Configured)

#get all stats and return through JSON
@app.route('/getallstats', methods=['GET','POST'])
def getallstats():
    if 'userid' not in session:
        return redirect('./')
    robot.CurrentCommand = "getting all stats"
    results = robot.get_all_sensors()
    return jsonify(results) #passing sensor values to page

@app.route('/getevents', methods=['GET','POST'])
def getevents():
    #called from webpage when it loads up
    events = "no events" #placeholder in case reviewed fire not in session
    if "reviewedfire" in session:
        returnedevents = database.ViewQueryHelper("SELECT EventType, ElapsedTime, Temp, Heading FROM EventsTbl WHERE FireID = ? ORDER BY EventID ASC", (session['reviewedfire'],))
        if len(returnedevents) == 0:
            events = "no events"
        else:
            events = []
            for event in returnedevents:
                #used for drawing past paths
                events.append(event['EventType'])
                events.append(event['Heading'])
                events.append(event['ElapsedTime'])
    return jsonify({"events":events})

@app.route('/reviewedfireform', methods=['GET','POST'])
def reviewedlocationform():
    #putting the past fire user selected into session
    session['reviewedfire'] = request.form['reviewedfire']
    return redirect('/pastfires')

#map or table of fire and path data
@app.route('/pastfires')
def pastfires():
    if not robot.Configured: #make sure robot is configured
        return redirect('./')
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    events = [] #what events the robot went through
    reviewedlocationdetails = [] #where and when fire happened
    username = ""
    if 'reviewedfire' in session:
        events = database.ViewQueryHelper("SELECT EventType, ElapsedTime, Temp, Heading FROM EventsTbl WHERE FireID = ? ORDER BY EventID ASC", (session['reviewedfire'],))
        reviewedlocationdetailsreturned = database.ViewQueryHelper("SELECT LocationTbl.State, LocationTbl.Suburb, LocationTbl.Street, LocationTbl.Number, UserTbl.FullName, FireTbl.StartTime FROM LocationTbl, FireTbl, UserTbl WHERE FireTbl.LocationID = LocationTbl.LocationID AND FireTbl.FireID=? AND FireTbl.UserID = UserTBl.UserID;",(session['reviewedfire'],))
        reviewedlocationdetails = reviewedlocationdetailsreturned[0]#selecting the dictionary returned to save having to do this step in js
        if len(events) == 0:
            events = "no events"
    #getting all past fires for user to select
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
        #drop-down wont be created if no past fires
    return render_template('map.html', fires = fires, configured = robot.Configured, session = session, events = events, details = reviewedlocationdetails)

#start robot moving
@app.route('/forward', methods=['GET','POST'])
def forward():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "moving forward"
    heading = robot.get_orientation_IMU()[0]
    duration = None #placeholder in case nothing returned
    robot.sound.play_music()
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 25)
    robot.sound.pause()
    robot.CurrentCommand = "Moving Forward"
    saveevent(duration) #saving the event the robot executed
    robot.CurrentCommand = "stop" #signifying robot has stopped
    return jsonify({ "message":"moving forward", "duration":duration, "heading":heading}) #jsonify take any type and makes a JSON
    
#start robot moving backwards
@app.route('/reverse', methods=['GET','POST'])
def reverse():
    if not robot.Configured: #make sure robot is
        return jsonify({ "message":"robot not yet configured"})
    robot.CurrentCommand = "Reversed"
    robot.sound.say("Turning around")
    duration = None
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
    robot.sound.say("Turning Right")
    duration = None
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
    robot.sound.say("Turning Left")
    duration = None
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
    robot.sound.say("Closing Claw")
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
    robot.sound.say("Opening Claw")
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
    robot.sound.say("Help is on the way")
    duration = None
    duration = robot.move_power_untildistanceto(RPOWER, LPOWER, 20)
    saveevent(duration)
    jsonify({ "message":"Auto Moving Forward", "duration":duration }) #jsonify take any type and makes a JSON
    if robot.CurrentCommand != "stop":
        identifyjunction()
    return 

def identifyjunction():
    #working out why the robot has stopped
    #fire, wall, junction, victim?
    #robot has different actions for each
    robot.CurrentCommand = "Identifying Junction"
    if robot.CurrentCommand != "stop":
        distancemeasured = robot.get_ultra_sensor()
        if distancemeasured > 20 and distancemeasured != 0.0:
            #no object in front of object
            duration = 0
            robot.CurrentCommand = "Junction Detected"
            saveevent(duration)
            if session['DetectingIntersections'] == True:
                log("entering junction")
                robot.move_power_time(RPOWER, LPOWER, 1.9)
                #log("moved off red tape (entering)")
                #making sure detected red tape
                session['DetectingIntersections'] = False
                navigateintersection("intersection")
                #told the navigation function what intersection at
            elif session['DetectingIntersections'] == False:
                log("exiting junciton")
                robot.move_power_time(RPOWER, LPOWER, 0.5)
                #to get off red tape when exiting junction
                #log("moved off red tape (exiting)")
                session['DetectingIntersections'] = True
                movetojunction()
        else:
            #object in front
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
                #not fire, not vic, therefor wall
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
    #turning robot around to go back way came
    saveevent(duration)
    movetojunction()

def navigateintersection(collisiontype):   
    robot.CurrentCommand = "Navigating Intersection"
    starttime = time.time()
    if session['VictimFound'] == False:
        #robot hasn't found victim yet
        #hug left wall
        robot.rotate_power_degrees_IMU(20, -90)
        log("check left")
        if robot.CurrentCommand != "stop":
            distancemeasured = robot.get_ultra_sensor()
            #reading ultrasonic to see if there is a wall infront
            if distancemeasured >= 30 and distancemeasured != 0.0:
                elapsedtime = time.time() - starttime
                saveevent(elapsedtime)
                robot.CurrentCommand = "Turned Left"
                duration = 0
                saveevent(duration)
                movetojunction() #start moving forward again
            else:
                if collisiontype == "intersection":
                    robot.rotate_power_degrees_IMU(20, 90)
                    log("check forward")
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 30 and distancemeasured != 0.0:
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Went Straight"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
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
                        else:
                            robot.rotate_power_degrees_IMU(20, 90)
                            elapsedtime = time.time() - starttime
                            saveevent(elapsedtime)
                            robot.CurrentCommand = "Reversed"
                            duration = 0
                            saveevent(duration)
                            movetojunction()
                elif collisiontype == "wall" or collisiontype == "fire":
                    #treat the fire as if its a wall, but save fire detected
                    robot.rotate_power_degrees_IMU(20, 180)
                    distancemeasured = robot.get_ultra_sensor()
                    if distancemeasured >= 30 and distancemeasured != 0.0:
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Turned Right"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
                    else:
                        robot.rotate_power_degrees_IMU(20, 90)
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Reversed"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
    elif session['VictimFound'] == True:
        #robot has collected the victim
        #hug the right wall back
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
                            robot.rotate_power_degrees_IMU(20, -90)
                            elapsedtime = time.time() - starttime
                            saveevent(elapsedtime)
                            robot.CurrentCommand = "Reversed"
                            duration = 0
                            saveevent(duration)
                            movetojunction()
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
                    else:
                        robot.rotate_power_degrees_IMU(20, -90)
                        elapsedtime = time.time() - starttime
                        saveevent(elapsedtime)
                        robot.CurrentCommand = "Reversed"
                        duration = 0
                        saveevent(duration)
                        movetojunction()
    return jsonify({ "message":"Navigating Intersection"})

#creates a route to get all the user data
@app.route('/getallusers', methods=['GET','POST'])
def getallusers():
    results = database.ViewQueryHelper("SELECT * FROM users")
    return jsonify([dict(row) for row in results]) #jsonify doesnt work with an SQLite.Row

#Get the robot's current command
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

#See if IMU calibrated
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
    if 'fireid' in session:
        endfire()
        #ending the current fire running
    session.clear()
    #clearing all info in session
    #(ie. user details, fire details, etc.)
    robot.safe_exit()
    #shuts down the robot's sensors and motors
    func = request.environ.get('werkzeug.server.shutdown')
    func()
    #closing the port
    return jsonify({ "message":"shutting down" })

#Log a message
def log(message):
    app.logger.info(message)
    return

#---------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
#Threaded mode is important if using shared resources e.g. sensor
#each user request launches a thread.
#However, with Threaded Mode on, errors can occur if resources are not locked down
#e.g trying to access live readings - conflicts can occur due to processor lock. Use carefully..
