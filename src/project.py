from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Folder, Event, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

#Connect to Database and create database session
engine = create_engine('sqlite:///event_manager.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID=json.loads(open('client_secrets.json','r').read())['web']['client_id']
APPLICATION_NAME = "Event Manager Application"

#Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                       for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html',STATE=state)

@app.route('/gconnect',methods=['POST'])
def gconnect():
    if request.args.get('state')!=login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'),401)
        response.headers['Content-Type']='application/json'
        return response
    code = request.data

    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json',scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'),401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'% access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url,'GET')[1])
    print 'result'
    
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')),500)
        response.headers['Content-Type'] = 'application/json'
        print 'error'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id']!= gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."),401)
        response.headers['Content-Type'] = 'application/json'
        print 'user ID do not match'
        return response

    if result['issued_to']!= CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."),401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        print 'client ID do not match'
        return reponse
    
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),200)
        response.headers['Content-Type'] = 'application/json'
        print 'connected'
        return response

    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id
    login_session['provider'] = 'google'
    print "add login_session"
    
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token':access_token,'alt':'json'}
    answer = requests.get(userinfo_url,params = params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
   
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width:300px;height:300px;border-radius:150px;-webkit-border-radius: 150px; -moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

def createUser(login_session):
    newUser = User(name=login_session['username'],email=login_session['email'],picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s'%access_token
    h = httplib2.Http()
    result = h.request(url,'GET')[0]

    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'),200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.',400))
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state')!= login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s" % access_token
    
    app_id = json.loads(open('fb_client_secrets.json','r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json','r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' %(
        app_id,app_secret,access_token)
    h= httplib2.Http()
    result = h.request(url,'GET')[1]
    
    #Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    #strip expire tag from access token
    token = result.split("&")[0]
    
    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url,'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]
    
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token
    
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url,'GET')[1]
    data = json.loads(result)
    
    login_session['picture'] = data["data"]["url"]
    
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    
    output = ''
    output += '<h1>Welcome, '
    output += login_session['picture']
    output += ' "style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    
    flash("Now logged in as %s" % login_session['username'])
    return output
    
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url,'DELETE')[1]
    return "you have been logged out"
    

#JSON APIs to view Folder Information
@app.route('/folder/<int:folder_id>/event/JSON')
def folderJSON(folder_id):
    folder = session.query(Folder).filter_by(id = folder_id).one()
    events = session.query(Event).filter_by(folder_id = folder_id).all()
    return jsonify(eventItems=[i.serialize for i in events])


@app.route('/folder/<int:folder_id>/event/<int:event_id>/JSON')
def eventJSON(folder_id, event_id):
    event = session.query(Event).filter_by(id = event_id).one()
    return jsonify(eventItem = event.serialize)

@app.route('/folders/JSON')
def foldersJSON():
    folders = session.query(Folder).all()
    return jsonify(folders= [r.serialize for r in folders])


#Show all folders
@app.route('/')
@app.route('/folders/')
def showFolders():  
  if 'provider' not in login_session:
      return render_template('publicfolders.html')
  else:
      user_id = login_session['user_id']
      folders = session.query(Folder).filter_by(user_id=user_id).order_by(asc(Folder.name))
      return render_template('folders.html',folders=folders)

#Create a new folder
@app.route('/folder/new/', methods=['GET','POST'])
def newFolder():
  if 'provider' not in login_session:
      return redirect('/login')
  if request.method == 'POST':
      newFolder = Folder(name = request.form['name'],user_id=login_session['user_id'])
      session.add(newFolder)
      flash('New Folder %s Successfully Created' % newFolder.name)
      session.commit()
      return redirect(url_for('showFolders'))
  else:
      return render_template('newFolder.html')

#Edit a folder
@app.route('/folder/<int:folder_id>/edit/', methods = ['GET', 'POST'])
def editFolder(folder_id):
  if 'provider' not in login_session:
      return redirect('/login')
  editedFolder = session.query(Folder).filter_by(id = folder_id).one()
  if editedFolder.user_id!=login_session['user_id']:
      return "<script>function myFunction() {alert('You are not authorized to edit this folder. Please create your own folder in order to edit.');}</script><body onload='myFunction()''>"
  if request.method == 'POST':
      if request.form['name']:
        editedFolder.name = request.form['name']
        flash('Folder Successfully Edited %s' % editedFolder.name)
        return redirect(url_for('showFolders'))
  else:
      return render_template('editFolder.html', folder = editedFolder)


#Delete a Folder
@app.route('/folder/<int:folder_id>/delete/', methods = ['GET','POST'])
def deleteFolder(folder_id):
  if 'provider' not in login_session:
      return redirect('/login')
  folderToDelete = session.query(Folder).filter_by(id = folder_id).one()
  if folderToDelete.user_id != login_session['user_id']:
      return "<script>function myFunction() {alert('You are not authorized to delete this folder,Please create your own folder in order to delete.');}</script><body onload='myFunction()''>"
  if request.method == 'POST':
    session.delete(folderToDelete)
    flash('%s Successfully Deleted' % folderToDelete.name)
    session.commit()
    return redirect(url_for('showFolders'))
  else:
    return render_template('deleteFolder.html',folder = folderToDelete)

#Show a restaurant menu
@app.route('/folder/<int:folder_id>/')
@app.route('/folder/<int:folder_id>/event/')
def showEvent(folder_id):
    folder = session.query(Folder).filter_by(id = folder_id).one()
    creator = getUserInfo(folder.user_id)
    events = session.query(Event).filter_by(folder_id = folder_id).all()
    if 'provider' not in login_session or creator.id!= login_session['user_id']:
        print "not logged in"
        flash('Please log in to see detailed events')
        return render_template('publicevent.html',folder=folder,creator=creator)
    else:
        return render_template('event.html', events = events, folder = folder,creator=creator)
     
#Create a new event
@app.route('/folder/<int:folder_id>/event/new/',methods=['GET','POST'])
def newEvent(folder_id):
  if 'provider' not in login_session:
      return redirect('/login')
  folder = session.query(Folder).filter_by(id = folder_id).one()
  if login_session['user_id']!=folder.user_id:
      return "<script>function myFunction() {alert('You are not authorized to add events to this folder. Please create your own folder in order to add items.');}</script><body onload='myFunction()''>"
  if request.method == 'POST':
      newEvent = Event(name = request.form['name'], description = request.form['description'], time = request.form['time'], location = request.form['location'], folder_id = folder_id,user_id=folder.user_id)
      session.add(newEvent)
      session.commit()
      flash('New Event %s Successfully Created' % (newEvent.name))
      return redirect(url_for('showEvent', folder_id = folder_id))
  else:
      return render_template('newEvent.html', folder_id = folder_id)

#Edit a event
@app.route('/folder/<int:folder_id>/event/<int:event_id>/edit', methods=['GET','POST'])
def editEvent(folder_id, event_id):
    if 'provider' not in login_session:
        return redirect('/login')
    editedEvent = session.query(Event).filter_by(id = event_id).one()
    folder = session.query(Folder).filter_by(id = folder_id).one()
    if login_session['user_id']!= folder.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit the event to this folder.Please create your own folder in order to edit them.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedEvent.name = request.form['name']
        if request.form['description']:
            editedEvent.description = request.form['description']
        if request.form['time']:
            editedEvent.time = request.form['time']
        if request.form['location']:
            editedEvent.location = request.form['location']
        session.add(editedEvent)
        session.commit() 
        flash('Event Successfully Edited')
        return redirect(url_for('showEvent', folder_id = folder_id))
    else:
        return render_template('editEvent.html', folder_id = folder_id, event_id = event_id, event = editedEvent)


#Delete an event item
@app.route('/folder/<int:folder_id>/event/<int:event_id>/delete', methods = ['GET','POST'])
def deleteEvent(folder_id,event_id):
    if 'provider' not in login_session:
        return redirect('/login')
    folder = session.query(Folder).filter_by(id = folder_id).one()
    eventToDelete = session.query(Event).filter_by(id = event_id).one() 
    if login_session['user_id']!=folder.user_id:
        return "<script>function myFunction(){alert('You are not authorized to delete the event to this folder.Please create your own folder in order to delete items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(eventToDelete)
        session.commit()
        flash('Event Successfully Deleted')
        return redirect(url_for('showEvent', folder_id = folder_id))
    else:
        return render_template('deleteEvent.html', event = eventToDelete)

@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']    
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showFolders'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showFolders'))


if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
