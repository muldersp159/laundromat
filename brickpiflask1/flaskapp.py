from flask import Flask, render_template, jsonify, redirect, request, session, flash, url_for
import logging #allow loggings
import time, sys, json
from databaseinterface import DatabaseHelper
from datetime import datetime
import os
from werkzeug.utils import secure_filename

#Create a way to interact with database
database = DatabaseHelper('laundromat.sqlite')

#Global Variables
app = Flask(__name__)
SECRET_KEY = 'my random key can be anything' #this is used for encrypting sessions
app.config.from_object(__name__) #Set app configuration using above SETTINGS
database.set_log(app.logger) #set the logger inside the database
app.config['UPLOAD_FOLDER'] = r"/home/pi/Desktop/laundromat/brickpiflask1/reads"
ALLOWED_EXTENSTIONS = {'csv'}

def allowed_file(filename):
    return "." in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSTIONS

#login
@app.route('/', methods=['GET','POST'])
def index():if 'userid' in session:
        return redirect('./missioncontrol') #no form data is carried across using 'dot/'
    if request.method == "POST":  #if form data has been sent
        email = request.form['email']   #get the form field with the name
        password = request.form['password']
        # TODO - need to make sure only one user is able to login at a time... how, idk
        userdetails = database.ViewQueryHelper("SELECT * FROM users WHERE email = ? AND password = ?",(email,password,))
        if len(userdetails) != 0:  #rows have been found
            row = userdetails[0] #userdetails is a list of dictionaries
            session['userid'] = row['userid']
            session['fullname'] = row['fullname']
            session['permission'] = row['permission']
            session['view'] = "all"
            session['updatetype'] = ""
            session['usersearch'] = ""
            session['searchid'] = ""
            session['custname'] = ""
            session['cid'] = ""
            session['inout'] = ""
            session['itemsearch'] = ""
            return redirect('./missioncontrol')
        else:
            flash("Sorry no user found, password or username incorrect")
    else:
        flash("No data submitted")
    return render_template('index.html')

#main page vvvvvv
#triggered when a user searches for customer they want to view
@app.route('/itemsearch', methods=['GET','POST'])
def itemsearch():
    if 'userid' not in session:
        return redirect('./')
    #putting which user they want to search into session
    session['customerid'] = ""
    name = "%" + request.form['itemsearch'] + "%"
    session['itemsearch'] = name
    return redirect('/missioncontrol')

#selecting a specific customer
@app.route('/dataselection', methods=['GET','POST'])
def dataselection():
    if 'userid' not in session:
        return redirect('./')
    session['view'] = "customer"
    session['itemsearch'] = ""
    session['customerid'] = request.form['customerid']
    return redirect('/missioncontrol')

@app.route('/allcustomers', methods=['GET','POST'])
def allcustomers():
    if 'userid' not in session:
        return redirect('./')
    #updating the session when the user selects that they want to pick form a customer to view data
    session['view'] = "customers"
    session['customerid'] = ""
    session['itemsearch'] = ""
    return redirect('/missioncontrol')

@app.route('/allitems', methods=['GET','POST'])
def allitems():
    if 'userid' not in session:
        return redirect('./')
    #updating the session when the user selects that they want to pick form a customer to view data
    session['view'] = "all"
    return redirect('/missioncontrol')

#home page
@app.route('/missioncontrol', methods=['GET','POST'])
def missioncontrol():
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    customerdetails = ""
    customeritems = ""
    numcustomeritems = ""
    allitems = ""
    countitems = []
    customerinfo = ""
    if session['view'] == "all": #selects all items and breaks them up as to whether they are checked out or not
        allitems = database.ViewQueryHelper("SELECT tags.epc AS EPC, abbreviations.full AS Product FROM tags, abbreviations WHERE abbreviations.abbreviation = tags.type ORDER BY Product ASC;")
        producttotals = database.ViewQueryHelper("SELECT COUNT(tags.epc) AS Amount, abbreviations.full AS Product FROM tags, abbreviations WHERE abbreviations.abbreviation = tags.type GROUP BY Product ORDER BY Product ASC;")
        if len(allitems) == 0:
            allitems = "no items"
        if len(producttotals) != 0: #means that data was returned
            for item in producttotals:
                product = item['Product']
                out = database.ViewQueryHelper("SELECT COUNT(reads.epc) AS Amount, abbreviations.full AS Product FROM reads, abbreviations, tags WHERE reads.epc = tags.epc AND tags.type = abbreviations.abbreviation AND reads.return = 'NA' AND abbreviations.full = ? GROUP BY reads.return, abbreviations.full", (product,))
                if len(out) == 0:
                    out = 0
                else:
                    out = out[0]['Amount']
                count = {}
                count['Out'] = out
                count['In'] = int(item['Amount']) - int(out)
                count['Product'] = product
                count['Total'] = item['Amount']
                countitems.append(count)
    if session['view'] == "customers": #get quick list of customer info to be used in customer selection
        if session['itemsearch'] != "":
            customerdetails = database.ViewQueryHelper("SELECT userid, fullname, phone, email FROM users WHERE permission = 'customer' AND fullname LIKE ?;",(session['itemsearch'],))
            if len(customerdetails) == 0:
                customerdetails = "No Past Customers"
    if session['view'] == "customer": #get details of a specific customer
        customeritems = database.ViewQueryHelper("SELECT reads.epc AS EPC, abbreviations.full AS Product, reads.checkout AS Checkout, reads.return AS Return, reads.orderid AS OrderID FROM reads, abbreviations, orders, users, tags WHERE reads.orderid = orders.orderid AND orders.customerid = users.userid AND reads.epc = tags.epc AND tags.type = abbreviations.abbreviation AND reads.return = 'NA' AND orders.customerid = ? ORDER BY OrderID ASC, Checkout DESC, abbreviations.full ASC;",(session['customerid'],))
        numcustomeritems = database.ViewQueryHelper("SELECT COUNT(reads.epc) AS Amount, abbreviations.full AS Product, reads.return AS Return FROM reads, abbreviations, orders, users, tags WHERE reads.orderid = orders.orderid AND orders.customerid = users.userid AND reads.epc = tags.epc AND tags.type = abbreviations.abbreviation AND reads.return = 'NA' AND orders.customerid = ? GROUP BY Return, Product ORDER BY abbreviations.full ASC, Return;",(session['customerid'],))
        customerinfo = database.ViewQueryHelper("SELECT fullname, phone, email, address FROM users WHERE userid = ?",(session['customerid'],))[0]
        if len(customeritems) == 0:
            customeritems = "Customer Has No Unreturned Items"
    return render_template("missioncontrol.html", customerdetails = customerdetails, customeritems = customeritems, numcustomeritems = numcustomeritems, allitems = allitems, customerinfo = customerinfo, session = session, countitems = countitems)

#main page ^^^^^

'''
@app.route('/checkin', methods=['GET','POST'])
def checkin():
    orderid = database.ViewQueryHelper("SELECT orderid from reads WHERE epc = ? ORDER BY readid DESC",(epc,))[0]
    database.ModifyQueryHelper("UPDATE reads SET return = ? WHERE epc = ? AND orderid = ?;",(datetime.datetime.now(), epc, orderid))

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    database.ModifyQueryHelper("INSERT INTO reads (epc, orderid, checkout, rfidstrength) VALUES (?,?,?,?);",(epc, orderid, datetime.datetime.now(), rfidstrength))
'''



#update users code vvvvvvv

@app.route('/new', methods=['GET','POST'])
def new():
    session['updatetype'] = "new"
    session['usersearch'] = ""
    session['searchid'] = ""
    return redirect('/updateusers')

@app.route('/select', methods=['GET','POST'])
def select():
    session['updatetype'] = "select"
    session['usersearch'] = ""
    return redirect('/updateusers')

@app.route('/update', methods=['GET','POST'])
def update():
    session['updatetype'] = "update"
    return redirect('/updateusers')

@app.route('/updateusers', methods=['GET','POST'])
def updateusers():
    if 'userid' not in session:
        return redirect('./')
    if session['permission'] != "admin":
        return redirect('./')
    users = ""
    update = ""
    if session['usersearch'] != "":
        name = "%" + session['usersearch'] + "%"
        users = database.ViewQueryHelper("SELECT userid, fullname, phone, permission, email, password FROM users WHERE fullname LIKE ?",(name,))
    if session['searchid'] != "":
        update = database.ViewQueryHelper("SELECT userid, fullname, phone, permission, email, password, address FROM users WHERE userid = ?",(session['searchid'],))[0]
    return render_template("updateusers.html", session = session, users = users, update = update)

@app.route('/usersearch', methods=['GET','POST'])
def usersearch():
    if 'userid' not in session:
        return redirect('./')
    session['searchid'] = ""
    name = request.form['username']
    session['usersearch'] = name.strip()
    return redirect('/updateusers')

@app.route('/userupdate', methods=['GET','POST'])
def userupdate():
    session['usersearch'] = ""
    session['searchid'] = request.form['id']
    return redirect('/updateusers')

@app.route('/newuser', methods=['GET','POST'])
def newuser():
    name = request.form['name'].strip()
    ph = request.form['ph']
    email = request.form['email']
    pword = request.form['pwd']
    role = request.form['role']
    address = request.form['address']
    database.ModifyQueryHelper("INSERT INTO users (fullname, email, password, permission, phone, address) VALUES (?,?,?,?,?,?);",(name, email, pword, role, ph, address))
    flash("New user added")
    return redirect('/updateusers')
    
@app.route('/userdata', methods=['GET','POST'])
def userdata():
    name = request.form['name'].strip()
    ph = request.form['ph']
    email = request.form['email']
    pword = request.form['pwd']
    role = request.form['role']
    uid = request.form['id']
    address = request.form['address']
    database.ModifyQueryHelper("UPDATE users SET fullname = ?, email = ?, password = ?, permission = ?, phone = ?, address = ? WHERE userid = ?;",(name, email, pword, role, ph, uid, address))
    flash("User data updated")
    return redirect('/updateusers')

#update users code ^^^^^^^


#logging item reads vvvv
@app.route('/checkinout', methods=['GET','POST'])
def checkinout():
    if session['inout'] == "in":
        session['cid'] = "in"
    if 'userid' not in session:
        return redirect('./') #no form data is carried across using 'dot/'
    customers = ""
    selected = ""
    if session['custname'] != "":
        name = "%" + session['custname'] + "%"
        customers = database.ViewQueryHelper("SELECT userid, fullname, phone, email FROM users WHERE permission = 'customer' AND fullname LIKE ?",(name,))
    if session['cid'] != "":
        if session['cid'] != "in":
            selected = database.ViewQueryHelper("SELECT userid, fullname, phone, email, address FROM users WHERE permission = 'customer' AND userid = ?",(session['cid'],))[0]
        else:
            selected = "in"
    return render_template('checkinout.html', customers = customers, selected = selected, session = session)

@app.route('/inout', methods=['GET','POST'])
def inout():
    session['cid'] = ""
    session['custname'] = ""
    session['inout'] = request.form['inout']
    return redirect('/checkinout')

@app.route('/custsearch', methods=['GET','POST'])
def custsearch():
    session['cid'] = ""
    name = request.form['custname']
    session['custname'] = name
    return redirect('/checkinout')

@app.route('/custsel', methods=['GET','POST'])
def custsel():
    session['custname'] = ""
    cid = request.form['cid']
    session['cid'] = cid
    return redirect('/checkinout')

@app.route('/order', methods=['GET','POST'])
def order():
    file = request.files['file']
    cid = session['cid']
    inout = session['inout']
    filename = ""
    file_location = ""
    #checking not an emppty file submitted
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "":
        flash("No Selected File")
        return redirect('/checkinout')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_location)
    #extracting data from file
    f = open(file_location, "r").read()
    lines = f.split('\n')
    print(lines)
    data = {}
    headings = []
    line_count = 0
    if "," in lines[0]:
        headings = lines[0].split(",")
        for heading in headings:
            data[heading] = []
        for line in lines:
            if line_count != 0:
                pos = 0
                for column in line:
                    data[headings[pos]].append(column)
                    pos += 1
            line_count += 0
    else:
        data["EPC"] = []
        for line in lines:
            if line_count != 0:
                data["EPC"].append(line)
            line_count += 1
            
    if inout == "in" or inout == "inout":
        for epc in data['EPC']:
            orderid = database.ViewQueryHelper("SELECT orderid from reads WHERE epc = ? ORDER BY readid DESC",(epc,))
            if len(orderid) != 0:
                row = orderid[0]
                database.ModifyQueryHelper("UPDATE reads SET return = ? WHERE epc = ? AND orderid = ?;",(datetime.now(), epc, row['orderid']))
    
    #performing different process depending on in our out allows for scans in to be of mixed orders
    if inout == "out" or inout == "inout":
        orderid = request.form['order']
        #checking if order already in db, if not then make it
        test = database.ViewQueryHelper("SELECT * FROM orders WHERE orderid = ?;",(orderid,))
        if len(test) == 0:
            database.ModifyQueryHelper("INSERT INTO orders (orderid, customerid, commisioned) VALUES (?, ?, ?);",(orderid, cid, datetime.now()))
        for epc in data['EPC']:
            if epc != "":
                #ensuring not double read occur
                check = database.ViewQueryHelper("SELECT * FROM reads WHERE epc = ? AND orderid = ?;", (epc, orderid))
                if len(check) != 0: #rows have been found, therefore that tag has already been logged to that order
                    pass
                else:
                    database.ModifyQueryHelper("INSERT INTO reads (epc, orderid, checkout, return) VALUES (?,?,?,'NA');",(epc, orderid, datetime.now()))
    session['custname'] = ""
    session['inout'] = ""
    session['cid'] = ""
    if file_location != "":
        os.remove(file_location) # deleting temp file now that data saved
        flash("read saved")
    return redirect('/checkinout')

#loggin item reads ^^^^^

@app.route('/newtags', methods=['GET','POST'])
def newtags():
    if 'userid' not in session:
        return redirect('./')
    if session['permission'] != "admin":
        return redirect('./')
    items = database.ViewQueryHelper("SELECT * FROM abbreviations")
    return render_template('newtags.html', items = items)

@app.route('/uploadtags', methods=['GET','POST'])
def uploadtags():
    if 'userid' not in session:
        return redirect('./')
    if session['permission'] != "admin":
        return redirect('./')
    file = request.files['file']
    itemtype = request.form['type']
    filename = ""
    file_location = ""
    #checking not an emppty file submitted
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "":
        flash("No Selected File")
        return redirect('/newtags')
    filename = file.filename
    if " " in filename:
        filenameparts = file.filename.split(" ")
        filename = ""
        for part in filenameparts:
            filename = filename + part
        print(filename)
    
    if file and allowed_file(filename):
        print("test2")
        filename = secure_filename(filename)
        file_location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_location)
    else:
        flash("invalid file name")
        return redirect('/newtags')
    #extracting data from file
    f = open(file_location, "r").read()
    f.strip("\n")
    lines = f.split('\n')
    data = {}
    headings = []
    line_count = 0
    if "," in lines[0]:
        headings = lines[0].split(",")
        for heading in headings:
            data[heading] = []
        for line in lines:
            if line_count != 0:
                pos = 0
                for column in line:
                    data[headings[pos]].append(column)
                    pos += 1
            line_count += 0
    else:
        heading = lines[0]
        print("heading" + heading)
        data[heading] = []
        for line in lines:
            if line_count != 0:
                data[heading].append(line)
            line_count += 1
    
    for epc in data['EPC']:
        if epc != "":
            database.ModifyQueryHelper("INSERT INTO tags (epc, purchasedate, type) VALUES (?,?,?);",(epc, datetime.now(), itemtype))
    #file.remove(file_location) check syntax --------------
    flash(str(line_count) + " New tags uploaded to database")
    return redirect('/newtags')
    

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
