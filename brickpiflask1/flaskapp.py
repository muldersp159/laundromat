from flask import Flask, render_template, jsonify, redirect, request, session, flash
import logging #allow loggings
import time, sys, json
from databaseinterface import DatabaseHelper
from datetime import datetime

#Create a way to interact with database
database = DatabaseHelper('laundromat.sqlite')

#Global Variables
app = Flask(__name__)
SECRET_KEY = 'my random key can be anything' #this is used for encrypting sessions
app.config.from_object(__name__) #Set app configuration using above SETTINGS
database.set_log(app.logger) #set the logger inside the database


#Request Handlers ---------------------------------------------
#login
@app.route('/', methods=['GET','POST'])
def index():
    if 'userid' in session:
        return redirect('./missioncontrol') #no form data is carried across using 'dot/'
    if request.method == "POST":  #if form data has been sent
        email = request.form['email']   #get the form field with the name 
        password = request.form['password']
        # TODO - need to make sure only one user is able to login at a time...
        userdetails = database.ViewQueryHelper("SELECT * FROM users WHERE email = ? AND password = ?",(email,password,))
        if len(userdetails) != 0:  #rows have been found
            row = userdetails[0] #userdetails is a list of dictionaries
            session['userid'] = row['userid']
            session['fullname'] = row['fullname']
            session['view'] = "all"
            return redirect('./missioncontrol')
        else:
            flash("Sorry no user found, password or username incorrect")
    else:
        flash("No data submitted")
    return render_template('index.html')

#triggered when a user selects which customer they want to view
@app.route('/dataselection', methods=['GET','POST'])
def dataselection():
    #putting type of data user wants to see into session
    session['customerid'] = request.form['customerselect']
    print("customer " + str(session['customerid']) + " seleced")
    return redirect('/missioncontrol')

@app.route('/allcustomers', methods=['GET','POST'])
def allcustomers():
    #updating the session when the user selects that they want to pick form a customer to view data
    session['view'] = "customers"
    return redirect('/missioncontrol')

@app.route('/allitems', methods=['GET','POST'])
def allitems():
    #updating the session when the user selects that they want to pick form a customer to view data
    session['view'] = "all"
    return redirect('/missioncontrol')

#home page
@app.route('/missioncontrol', methods=['GET','POST'])
def missioncontrol():
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    print(session['view'])
    customerdetails = ""
    customeritems = ""
    numcustomeritems = ""
    allitems = ""
    customerinfo = ""
    if session['view'] == "all": #selects all items and breaks them up as to whether they are checked out or not
        allitems = database.ViewQueryHelper("SELECT reads.epc AS EPC, abbreviations.full AS Product, reads.checkout AS Checkout, reads.return AS Return FROM reads, abbreviations, orders, users, tags WHERE reads.epc = tags.epc AND tags.type = abbreviations.abbreviation ORDER BY reads.return DESC, abbreviations.full ASC, reads.epc;") 
        countitmes = database.ViewQueryHelper("SELECT COUNT(reads.epc) AS Amount, abbreviations.full AS Product FROM reads, abbreviations, orders, users, tags WHERE reads.epc = tags.epc AND tags.type = abbreviations.abbreviation GROUP BY abbreviations.full ORDER BY abbreviations.full ASC;") 
        if len(allitems) == 0:
            allitems = "no items"
    elif session['view'] == "customers": #get quick list of customer info to be used in customer selection
        customerdetails = database.ViewQueryHelper("SELECT userid, fullname FROM users WHERE permission = 'customer';")
        if len(customerdetails) == 0:
            customerdetails = "No Past Customers"
    elif session['view'] == "customer": #get details of a specific customer
        customeritems = database.ViewQueryHelper("SELECT reads.epc AS EPC, abbreviations.full AS Product, reads.checkout AS Checkout FROM reads, abbreviations, orders, users, tags WHERE reads.orderid = orders.orderid AND orders.customerid = users.userid AND reads.epc = tags.epc AND tags.type = abbreviations.abbreviation AND reads.return = 'NA' AND users.userid = ? ORDER BY abbreviations.full ASC, reads.epc;",(session['customerid'],))
        numcustomeritems = database.ViewQueryHelper("SELECT COUNT(reads.epc) AS Amount, abbreviations.full AS Product FROM reads, abbreviations, orders, users, tags WHERE reads.orderid = orders.orderid AND orders.customerid = users.userid AND reads.epc = tags.epc AND tags.type = abbreviations.abbreviation AND reads.return = 'NA' AND users.userid = ? GROUP BY abbreviations.full ORDER BY abbreviations.full ASC;",(session['customerid'],))
        customerinfo = database.ViewQueryHelper("SELECT fullname, phone, address, email FROM users WHERE userid = ?",(session['customerid'],))
        if len(customeritems) == 0:
            customeritems = "Customer Has No Unreturned Items"
    print("checking if refreshing page")
    return render_template("missioncontrol.html", customerdetails = customerdetails, customeritems = customeritems, numcustomeritems = numcustomeritems, allitems = allitems, customerinfo = customerinfo, session = session, countitems = countitmes)

'''
@app.route('/checkin', methods=['GET','POST'])
def checkin():
    orderid = database.ViewQueryHelper("SELECT orderid from reads WHERE epc = ? ORDER BY readid DESC",(epc,))[0]
    database.ModifyQueryHelper("UPDATE reads SET return = ? WHERE epc = ? AND orderid = ?;",(datetime.datetime.now(), epc, orderid))

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    database.ModifyQueryHelper("INSERT INTO reads (epc, orderid, checkout, rfidstrength) VALUES (?,?,?,?);",(epc, orderid, datetime.datetime.now(), rfidstrength))
'''

@app.route('/updateusers', methods=['GET','POST'])
def updateusers():
    if 'userid' not in session or session['permission'] != "admin":
        return redirect('./')
    return render_template("updateusers.html")

#dashboard
@app.route('/sensorview', methods=['GET','POST'])
def sensorview():
    if 'userid' not in session:
        return redirect('./')
    return render_template("sensorview.html")

#map or table of fire and path data
@app.route('/checkinout', methods=['GET','POST'])
def map():
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    return render_template('checkinout.html')

#creates a route to get all the event data
@app.route('/getallusers', methods=['GET','POST'])
def getallusers():
    results = database.ViewQueryHelper("SELECT * FROM users")
    return jsonify([dict(row) for row in results]) #jsonify doesnt work with an SQLite.Row

#Shutdown the web server
@app.route('/shutdown', methods=['GET','POST'])
def shutdown():
    log("shutting down")
    session.clear()
    func = request.environ.get('werkzeug.server.shutdown')
    func()
    return jsonify({ "message":"shutting down" })

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('./')

#Log a message
def log(message):
    app.logger.info(message)
    return

#---------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

#Threaded mode is important if using shared resources e.g. sensor, each user request launches a thread.. However, with Threaded Mode on errors can occur if resources are not locked down e.g trying to access live readings - conflicts can occur due to processor lock. Use carefully..
