#!/usr/bin/env python2.7

"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
import json
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from sqlalchemy import exc
from flask import Flask, request, render_template, g, redirect, Response, jsonify
from random import randint

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@w4111a.eastus.cloudapp.azure.com/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@w4111a.eastus.cloudapp.azure.com/proj1part2"
#
DATABASEURI = "postgresql://ac3877:verbose@w4111a.eastus.cloudapp.azure.com/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """
  user_id = request.args.get('id')
  script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
  rel_path = "queries/vehicle_class.sql"
  abs_file_path = os.path.join(script_dir, rel_path)
  f = open(abs_file_path, 'r')
  query = f.read()
  f.close()
  cursor = g.conn.execute(query.rstrip())
  rates = []
  for row in cursor:
    rates.append(list(row))
  if(user_id != None):
    query = "SELECT * FROM Addresses A WHERE A.uid={}".format(user_id)
    cursor = g.conn.execute(query)
    address = []
    address.append([0,'null','Select a saved address'])
    for row in cursor:
      addr = list(row)
      final_addr = [addr[0],addr[1]+' '+addr[3]+' '+addr[4], addr[5]+ ' - '+addr[1]+' '+addr[3]+' '+addr[4]]
      address.append(final_addr)
    data = {'rates':rates, 'id': user_id, 'addresses': address}
  else:
    data = {'rates':rates, 'id': user_id}
  return render_template("index.html", data=data)




@app.route('/reservations')
def reservations():
  user_id = request.args.get('id')
  data = {'id':user_id}
  return render_template("reservations.html", data=data)

@app.route('/confirm-user')
def confirm_user():
  user_id = request.args.get('id')
  # passengers only below:
  # query = "SELECT U.uid FROM Passengers U WHERE U.uid={}".format(user_id)
  # passengers and drivers below:
  query = "SELECT Users.uid FROM (SELECT uid FROM Passengers UNION SELECT uid FROM Drivers) AS Users WHERE Users.uid={}".format(user_id)
  cursor = g.conn.execute(query)
  record = cursor.fetchone()
  if record != None:
    results = list(record)
  else:
    results = []
  return jsonify(data= results)

@app.route('/get-current')
def pass_current_reservations():
  user_id = request.args.get('id')
  query = "SELECT to_char(T.date, \'YYYY-MM-DD\') AS date, to_char(T.time, \'HH:MI:SS\') AS time, T.type, T.distance, T.pick_addr, T.drop_addr, " + \
    "T.est_amount, T.tid, D.name, D.phone FROM Trips T,Drivers D WHERE T.passenger={} AND T.driver=D.uid AND T.status=\'reserved\' ORDER BY T.date, T.time".format(user_id)
  cursor = g.conn.execute(query)
  reservations = []
  for row in cursor: 
    reservations.append(list(row))
  data = {'reservations':reservations, 'id':user_id}
  return jsonify(data= data)  

@app.route('/get-past')
def pass_past_reservations():
  user_id = request.args.get('id')
  query = "SELECT to_char(T.date, \'YYYY-MM-DD\') AS date, to_char(T.time, \'HH:MI:SS\') AS time, T.type, T.distance, T.pick_addr, T.drop_addr, " + \
    "T.est_amount, T.tid, T.drating FROM Trips T WHERE T.passenger={} AND T.status=\'completed\' ORDER BY T.date, T.time".format(user_id)
  cursor = g.conn.execute(query)
  reservations = []
  for row in cursor: 
    reservations.append(list(row))
  data = {'reservations':reservations, 'id':user_id}
  return jsonify(data= data)

@app.route('/search-drivers')
def search_drivers():
  date = request.args.get('date')
  time1 = request.args.get('time1')
  time2 = request.args.get('time2')
  vclass = request.args.get('class')
  query = "SELECT D.uid, D.name,D.rating,V.make,V.model,V.capacity FROM drivers D, vehicles V WHERE D.uid=V.uid AND V.cname=\'"+ vclass+"\' AND D.uid NOT IN (SELECT T.driver FROM Trips T WHERE T.date=\'"+date+"\' AND T.time>=\'"+time1+"\' AND T.time<=\'"+time2+"\');"
  cursor = g.conn.execute(query)
  results = []
  for row in cursor:
    results.append(list(row))
  return jsonify(data= results)


@app.route('/create-user')
def create_user():
  name = request.args.get('name')
  email = request.args.get('email')
  phone = request.args.get('phone')
  query = "INSERT INTO Passengers (name, email, phone) VALUES (\'"+ name +"\', \'"+ email +"\', \'"+ phone +"\') RETURNING uid;"
  try: 
      cursor = g.conn.execute(query)
      record = cursor.fetchone()
      results = list(record)
      data = {'error': 0, 'data': results}
      return jsonify(data= data)
  except exc.SQLAlchemyError as e:
      data = {'error':1, 'message':str(e)}
      return jsonify(data= data)

@app.route('/assign-rating')
def assign_rating():
  user = request.args.get('userid')
  trip = request.args.get('tripid')
  rating = request.args.get('rating')
  stmt2 = "UPDATE Trips SET (drating) = ({}) WHERE tid={}".format(rating, trip)
  try: 
      cursor = g.conn.execute(stmt2)
      data = {'error': 0, 'data': None}
      return jsonify(data= data)
  except exc.SQLAlchemyError as e:
      data = {'error':1, 'message':str(e)}
      return jsonify(data= data)

@app.route('/cancel-trip')
def cancel_trip():
  trip = request.args.get('tripid')
  stmt2 = "DELETE FROM Trips T WHERE T.tid="+trip+";" 
  try: 
      cursor = g.conn.execute(stmt2)
      data = {'error': 0, 'data': None}
      return jsonify(data= data)
  except exc.SQLAlchemyError as e:
      data = {'error':1, 'message':str(e)}
      return jsonify(data= data)

@app.route('/save-address')
def save_address():
  user = request.args.get('id')
  label = request.args.get('label').strip()
  addr = request.args.get('addr').strip()
  city = request.args.get('city').strip()
  state = request.args.get('state').strip()
  query = "INSERT INTO Addresses (uid, street1, city, state, label) VALUES ("+user+", \'"+ addr +"\', \'"+ city +"\', \'"+ state +"\', \'"+ label +"\') RETURNING uid;"
  try: 
      cursor = g.conn.execute(query)
      record = cursor.fetchone()
      results = list(record)
      data = {'error': 0, 'data': results}
      return jsonify(data= data)
  except exc.SQLAlchemyError as e:
      data = {'error':1, 'message':str(e)}
      return jsonify(data= data)


@app.route('/create-trip')
def craete_trip():
  user = request.args.get('pid')
  driver = request.args.get('did')
  paddr = request.args.get('paddr')
  daddr = request.args.get('daddr').strip()
  dist = request.args.get('dist')
  amt = request.args.get('amt')
  date = request.args.get('date')
  time = request.args.get('time')
  ftype = request.args.get('type')
  status = 'reserved'
  query = "INSERT INTO Trips (date,time,distance,status,type,est_amount,pick_addr,drop_addr,driver,passenger)"
  query = query+" VALUES (\'"+date+"\',\'"+ time +"\', "+ dist +", \'"+ status +"\', \'"+ ftype +"\', "+ amt
  query = query+", \'"+ paddr +"\',\'"+ daddr +"\',"+ driver +","+ user +") RETURNING tid;"
  try: 
      cursor = g.conn.execute(query)
      record = cursor.fetchone()
      results = list(record)
      data = {'error': 0, 'data': results}
      return jsonify(data= data)
  except exc.SQLAlchemyError as e:
      data = {'error':1, 'message':str(e)}
      return jsonify(data= data)


#drivers page
@app.route('/drivers')
def drivers():
  user_id = request.args.get('id')
  data = {'id':user_id}
  return render_template("drivers.html", data=data)

#get driver's current reservations
@app.route('/get-current-reservations') 
def get_current_reservations():
  user_id = request.args.get('id')
  # for reference, column indices are: 0=name, 1=phone, 2=date, 3=time, 4=type, 5=distance, 6=pick_addr, 7=drop_add, 8=est_amount, 9=tid
  query = "SELECT P.name, P.phone, to_char(T.date, \'YYYY-MM-DD\') AS date, to_char(T.time, \'HH:MI:SS\') AS time, T.type, T.distance, T.pick_addr, T.drop_addr, " + \
    "T.est_amount, T.tid FROM Trips T, Passengers P WHERE T.driver={} AND T.passenger = P.uid AND T.status!=\'completed\' ORDER BY T.date, T.time".format(user_id)
  cursor = g.conn.execute(query)
  reservations = []
  for row in cursor: 
    reservations.append(list(row))
  data = {'reservations':reservations, 'id':user_id}
  return jsonify(data= data)  
  
# driver entering completed trip information
@app.route('/complete-trip') 
def complete_trip():
  user_id = request.args.get('id')
  # get values from form
  tid = request.args.get('comptid').rstrip()
  amount = request.args.get('tamtcharged').rstrip()
  paytype = request.args.get('tpaytype').rstrip()
  prating = request.args.get('tpassrating').rstrip()
  # require paytype be CASH, AMEX, VISA, or MC
  if (paytype.lower() not in ['cash', 'amex', 'visa', 'mc']):
    message = "Invalid payment type; must be CASH, MC, VISA, or AMEX."
    data = {'error':1, 'message':message, 'id':user_id}
    return jsonify(data=data)
  if (paytype=='AMEX' or paytype=='VISA' or paytype=='MC'):
    # generating random number for auth_id, since we don't have an actual credit card processing system...
    auth = randint(1,2147483647)
    stmt = "INSERT INTO Transactions (pay_type, auth_id, amt_charged, tid) VALUES (\'{}\', {}, {}, {})".format(paytype, auth, amount, tid)
  else:
    stmt = "INSERT INTO Transactions (pay_type, amt_charged, tid) VALUES (\'{}\', {}, {})".format(paytype, amount, tid)
  try: 
    cursor = g.conn.execute(stmt)
    data = {'error':0, 'id':user_id}
    # if insert was successful, set corresponding trip status to completed
    stmt2 = "UPDATE Trips SET (status, prating) = (\'completed\', {}) WHERE tid={}".format(prating, tid)
    cursor = g.conn.execute(stmt2)
    return jsonify(data=data)
  except exc.SQLAlchemyError as e:
    print str(e)
    message = "Error entering trip information, check form entries."
    data = {'error':1, 'message':message, 'id':user_id}
    return jsonify(data=data)

# driver getting completed trip info
@app.route('/get-past-trips') 
def get_past_trips():
  user_id = request.args.get('id')
  # get values from form
  start = request.args.get('start').rstrip()
  end = request.args.get('end').rstrip()
  # treat empty entries as open interval
  if (start == '' and end == ''):
    query = "SELECT P.name, to_char(T.date, \'YYYY-MM-DD\') AS date, to_char(T.time, \'HH:MI:SS\') AS time, T.est_amount, TR.amt_charged, T.drating, T.prating, T.tid FROM " + \
      "Trips T, Transactions TR, Passengers P WHERE T.status='completed' AND T.tid=TR.tid AND T.driver={} AND T.passenger=P.uid".format(user_id)
  elif (start == ''):
    query = "SELECT P.name, to_char(T.date, \'YYYY-MM-DD\') AS date, to_char(T.time, \'HH:MI:SS\') AS time, T.est_amount, TR.amt_charged, T.drating, T.prating, T.tid FROM " + \
      "Trips T, Transactions TR, Passengers P WHERE T.status='completed' AND t.tid=TR.tid AND T.passenger=P.uid AND " + \
      "T.driver={} AND T.date <= \'{}\'".format(user_id, end)
  elif (end == ''):
    query = "SELECT P.name, to_char(T.date, \'YYYY-MM-DD\') AS date, to_char(T.time, \'HH:MI:SS\') AS time, T.est_amount, TR.amt_charged, T.drating, T.prating, T.tid FROM " + \
      "Trips T, Transactions TR, Passengers P WHERE T.status='completed' AND t.tid=TR.tid AND T.passenger=P.uid AND " + \
      "T.driver={} AND T.date >= \'{}\'".format(user_id, start)
  else:
    query = "SELECT P.name, to_char(T.date, \'YYYY-MM-DD\') AS date, to_char(T.time, \'HH:MI:SS\') AS time, T.est_amount, TR.amt_charged, T.drating, T.prating, T.tid FROM " + \
      "Trips T, Transactions TR, Passengers P WHERE T.status='completed' AND t.tid=TR.tid AND T.passenger=P.uid AND " + \
      "T.driver={} AND T.date >= \'{}\' AND T.date <= \'{}\'".format(user_id, start, end)
  try: 
    cursor = g.conn.execute(query)
    trips = []
    for row in cursor: 
      trips.append(list(row))
    data = {'error':0, 'id':user_id, 'trips':trips}
    # if insert was successful, set corresponding trip status to completed
    return jsonify(data=data)
  except exc.SQLAlchemyError as e:
    print str(e)
    message = "Error retrieving past trips, check date range formats."
    data = {'error':1, 'message':message, 'id':user_id}
    return jsonify(data=data)

# show driver's vehicles
@app.route('/show-vehicles')
def show_vehicles():
  user_id = request.args.get('id')
  # retrieve driver's vehicles
  query = "SELECT V.plate_no, V.make, V.model, V.capacity, V.cname FROM Vehicles V WHERE V.uid={}".format(user_id)
  cursor = g.conn.execute(query)
  vehicles = []
  for row in cursor:
    vehicles.append(list(row))
  data = {'id':user_id, 'vehicles':vehicles}
  return jsonify(data=data)

# add a vehicle
@app.route('/add-vehicle')
def add_vehicle():
  user_id = request.args.get('id')
  # get values from form
  vplate = request.args.get('vplate').rstrip()
  vmake = request.args.get('vmake').rstrip()
  vmodel = request.args.get('vmodel').rstrip()
  vcapacity = request.args.get('vcapacity').rstrip()
  vclass = request.args.get('vclass').rstrip().lower()
  # require vclass be suplux, econ, lux, or suv
  if (vclass not in ['suplux', 'econ', 'lux', 'suv']):
    message = "Invalid vehicle class; must be econ, lux, suplux, or suv."
    data = {'error':1, 'message':message, 'id':user_id}
    return jsonify(data=data)
  else:
    stmt = "INSERT INTO Vehicles (plate_no, make, model, capacity, cname, uid) " + \
      "VALUES (\'{}\', \'{}\', \'{}\', {}, \'{}\', {})".format(vplate, vmake, vmodel, vcapacity, vclass, user_id)
  try: 
    cursor = g.conn.execute(stmt)
    data = {'error':0, 'id':user_id}
    return jsonify(data=data)
  except exc.SQLAlchemyError as e:
    print str(e)
    message = "Error entering vehicle, check form entries.  Note that drivers cannot share cars per company policy."
    data = {'error':1, 'message':message, 'id':user_id}
    return jsonify(data=data)

# delete a vehicle
@app.route('/delete-vehicle')
def delete_vehicle():
  user_id = request.args.get('id')
  # get plate from form
  vplate = request.args.get('vplate').rstrip()
  # check whether car exists and belongs to user
  stmt = "SELECT uid FROM Vehicles V WHERE V.plate_no=\'{}\'".format(vplate)
  try: 
    cursor=g.conn.execute(stmt)
    record = cursor.fetchone()
    if (record == None):
      message = "Error: no vehicle matches entered license plate."
      data = {'error':1, 'message':message, 'id':user_id}
      return jsonify(data=data)
    elif (str(record[0]) != str(user_id)):
      message = "Error: you can't delete a vehicle that doesn't belong to you!"
      data = {'error':1, 'message':message, 'id':user_id}
      return jsonify(data=data)
    else: 
      stmt = "DELETE FROM Vehicles V WHERE V.plate_no=\'{}\'".format(vplate)
      cursor = g.conn.execute(stmt)
      data = {'error':0, 'id':user_id}
      return jsonify(data=data)
  except exc.SQLAlchemyError as e:
    print str(e)
    message = "Error deleting vehicle, check form entry."
    data = {'error':1, 'message':message, 'id':user_id}
    return jsonify(data=data)

# show most frequent driver/passenger info and top/bottom rated driver info 
@app.route('/admins')
def admins(): 
  user_id = request.args.get('id')
  query1 = "SELECT P.uid, P.name, P.email, COUNT(P.uid), SUM(TR.amt_charged) FROM Passengers P, Trips T, Transactions TR WHERE " + \
    "P.uid = T.passenger AND T.tid = TR.tid GROUP BY P.uid, P.name, P.email ORDER BY COUNT(P.uid) DESC LIMIT 5"
  query2 = "SELECT D.uid, D.name, D.email, COUNT(D.uid), SUM(TR.amt_charged) FROM Drivers D, Trips T, Transactions TR WHERE " + \
    "D.uid = T.driver AND T.tid = TR.tid GROUP BY D.uid, D.name, D.email ORDER BY COUNT(D.uid) DESC LIMIT 5"
  query3 = "SELECT D.uid, D.name, D.email, D.rating, SUM(TR.amt_charged) FROM Drivers D, Trips T, Transactions TR WHERE " + \
    "D.uid = T.driver AND T.tid = TR.tid GROUP BY D.uid, D.name, D.email, D.rating ORDER BY D.rating DESC LIMIT 5"
  query4 = "SELECT D.uid, D.name, D.email, D.rating, SUM(TR.amt_charged) FROM Drivers D, Trips T, Transactions TR WHERE " + \
    "D.uid = T.driver AND T.tid = TR.tid GROUP BY D.uid, D.name, D.email, D.rating ORDER BY D.rating ASC LIMIT 5"
  cursor = g.conn.execute(query1)
  topfc = []
  for row in cursor:
    topfc.append(list(row))
  cursor = g.conn.execute(query2)
  topfd = []
  for row in cursor:
    topfd.append(list(row))
  cursor = g.conn.execute(query3)
  toprd = []
  for row in cursor:
    toprd.append(list(row))
  cursor = g.conn.execute(query4)
  lowrd = []
  for row in cursor:
    lowrd.append(list(row))
  data = {'topfc':topfc, 'topfd':topfd, 'toprd':toprd, 'lowrd':lowrd, 'id':user_id}
  return render_template("admins.html", data=data)

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
