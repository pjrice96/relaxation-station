import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
from tornado.escape import *

import csv
import json
import os
import os.path
import sys
import datetime
import time
import uuid

# ******************************************************************************
# Setting up some globals ******************************************************

#Some can be read from Environmental variables (or not as they have a default)
BASE_PATH = os.getenv("BASE_PATH", ".")
print("BASE_PATH: " + BASE_PATH)

# path to store uploaded files
# make sure to modify permissions on uploaded files
__UPLOADS__ = "uploads/"

# These control how quickly websockets refresh
WEBSOCKET_REFRESH_RATE_MS = 10000
OPT_WEBSOCKET_REFRESH_RATE_MS = 500

# Logging function good for debugging and recording events of importance.
# In a real system these might point to some thing besides printing the stdout
def applog(str):
    print str


# ******************************************************************************
# **** empty functions *********************************************************

def storeWeatherInfo(store_object):
    pass

# ******************************************************************************
# **** WEB STUFF BELOW *********************************************************

# ******************************************************************************
# **** Base Handler ************************************************************

class BaseHandler(tornado.web.RequestHandler):
    # This base handler is an extension of the orginal request handler to add
    # some features
    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_current_role(self):
        return self.get_secure_cookie("role")

    def isWriteAllowed(self):
        writeAllowed = ('"ADMIN"' in self.get_current_role()) or ('"WRITE"' in self.get_current_role())
        return(writeAllowed)

    def isAdminAllowed(self):
        adminAllowed = ('"ADMIN"' in self.get_current_role())
        return(adminAllowed)

    def returnError(self,error,write):
        # Create a JSON object
        resp_obj = {}
        resp_obj['rmessage'] = error
        resp_obj['status'] = error
        applog(error)
        # Send object back as response
        write(json.dumps(resp_obj))

# ******************************************************************************
# ******************************************************************************
# GET Examples
class Get_Render_Plain_Page_Handler(BaseHandler):
    # Renders no matter if the user is signed in or not
    # Not autheticated
    def get(self):
        # Doesn't add anyhing to the page through templating.
        # Might use this if the page is doing everything on the client side or
        # you expect to pull all the information to customize the page through
        # and Ajax call or by opening a web socket (see examples below).
        self.render("getrenderplain.html")

class Get_Auth_Render_Templated_Page_Handler(BaseHandler):
    # Will redirect to login page if user isn't signed in
    @tornado.web.authenticated
    def get(self):
        # Get user name from cookie
        username = tornado.escape.xhtml_escape(self.current_user)
        # Create object that will be injected into user page if using templating
        dataOut = {"try this":1}
        dataOut['TEMP_SUFFIX'] = "TEMP_SUFFIX"
        dataOut['s7_output_html'] = "monitor_PeakMWh_lookup_output()"

        # Add to the response header of the get request
        #self.set_header("Cache-control", "public, max-age=0")

        # Render a page means to do some preprocessing on it. In this case
        # The information is in three pieces username, an object (dataOut) and
        # the base_url are used to fill in the template of the
        # getrenderexample.html page
        self.render("getrendertemplate.html",
                    username = username,
                    dataOut = dataOut,
                    base_url = BASE_PATH)

class Get_Export_CSV_File_Handler(BaseHandler):
    # Example of returning a file other then a html in this case exporting a
    # comma seperated values (CSV) file.
    @tornado.web.authenticated
    def get(self):
        # Export csv file will be downloaded
        filename=self.get_argument("csv", None, True)
        if filename != None:
            # The developer would need to make sure the file exsisted before the
            # code below is allowed to run
            ifile  = open("./public/output/" + filename+".csv", "r")
            self.set_header ('Content-Type', 'text/csv')
            self.set_header ('Content-Disposition', 'attachment; filename='+filename+'.csv')
            self.write (ifile.read())
            self.finish()
            ifile.close()

class Admin_Only_Page_Handler(BaseHandler):
    # Example of checking to see what role a user has before giving them a page.
    # In this case if they ask for this page and they aren't an authenticated
    # admin we send them back an error that makes it look like the page doesn't
    # exist.
    @tornado.web.authenticated
    def get(self):
        if not self.isAdminAllowed():
            raise tornado.web.HTTPError(404)
        else:
            username = tornado.escape.xhtml_escape(self.current_user)
            self.render("getrenderplain.html", username = username)

# ******************************************************************************
# ******************************************************************************
# POST Examples

# The POST has two purposes.
# First, its used when the client wants to send information to the
# server/backend. Think you filled out a form.
# Second, the Post is used when the client wants to request more from the server
# then just what it could get (GET). This is usaully on some new information the
# client has. Think you filled out a form that causes some information to be
# retrieved and you want to tell the client so it can be presented it to the
# user.
# The thing that the server returns to the client could be a new page or just
# the information.
# You could think of them as additional services that the backend offers.
# There are genrally two parts to a post - the data the client sent and the data
# the server returns to the client.

class Post_Ignores_Request_Data_Handler(BaseHandler):
    # Example always sends a response to the client, ignores an request
    # data sent
    # No authentication
    def post(self):
        # Response could be static like this example or could be running a
        # a function that dynamically creates the data from external inputs,
        # a database just about anything
        resp_obj = {'status':'Need to upload bid',
                    'rmessage':'Bid entry needed for tomorrow'}
        # Send object back as response
        self.write(json.dumps(resp_obj))



class Post_Based_On_JSON_Request_Handler(BaseHandler):
    # Not autheticated
    def post(self):
        applog("INFO: posted something make note in log")
        try:
            # We are first going to "try" and process the clients request of the
            # server. In this case the server is expecting that the client
            # has sent it a request that is serialized (encoded,loads) as a json
            # object. The server will try and convert the request into a python
            # object so it can access the data in the python object.
            object = json.loads(self.request.body)
        except:
            # If our try at converting from a json object to a python object
            # fails we have some things to do.
            applog("ERROR: Converting to JSON Object in Post_Based_On_JSON_Request_Handler. Body next->\n")
            applog(self.request.body)
        else:
            # If the JSON->Python object conversion was sucessfull the server
            # can access the objects data and return something to the client
            if 'CPL_plan' in object:
                applog("INFO: Sending accepted plan to system\n")
                # Create a response object to send to the client
                resp_obj={}
                resp_obj['gmessage'] = "Day Ahead CPL plan saved!"
                # Send object to client as response
                self.write(json.dumps(resp_obj))
                return

class Post_Accept_JSON_Data_Based_On_Role_Handler(BaseHandler):
    # This example shows how to change what you do with the request data based
    # on the users privelages.
    @tornado.web.authenticated
    def post(self):
        if not self.isWriteAllowed():
            # Because the user doesn't have write privaliges the server just
            # responds the an appology. THe client will present this to the user
            resp_obj={}
            resp_obj['rmessage'] = "Sorry you don't have permission to modify this"
            applog("SECURITY: Post_Accept_JSON_Data_Based_On_Role_Handler - attempt to write without permissions\n")
            # Send object back as response
            self.write(json.dumps(resp_obj))
            return
        # user is autherized or has write privalges
        applog("INFO: POSTED Post_Accept_JSON_Data_Based_On_Role_Handler DATA")
        try:
            object = json.loads(self.request.body)
        except:
            applog("ERROR: Converting to JSON Object in Post_Accept_JSON_Data_Based_On_Role_Handler. Body next->\n")
            applog(self.request.body)
        else:
            if 'CPL_plan' in object:
                applog("INFO: Sending accepted plan to system\n")
                resp_obj={}
                resp_obj['gmessage'] = "Day Ahead CPL plan saved!"
                # Send object back as response
                self.write(json.dumps(resp_obj))
                return

class Post_Data_From_Form_Based_On_Role_Handler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        if not self.isAdminAllowed():
            resp_obj={}
            resp_obj['rmessage'] = "Sorry you don't have permission to modify this"
            # Send object back as response
            applog("SECURITY: Post_Data_From_Form_Based_On_Role_Handler - attempt to write without permissions")
            self.write(json.dumps(resp_obj))
            return

        # Get data from form (in request header instead of body)
        dayaheadcap = int(self.get_argument('dayaheadcap', 0))
        dayaheadbid = int(self.get_argument('dayaheadbid', 0))
        dayaheadplantoday = int(self.get_argument('dayaheadplantoday', 0))
        dayaheadplantomm = int(self.get_argument('dayaheadplantomm', 0))
        optimizationflag = int(self.get_argument('optimizationflag', 0))
        monitorhistory = int(self.get_argument('monitorhistory', 0))
        setdemoflag = int(self.get_argument('setdemoflag', 0))

        applog("INFO: Post_Data_From_Form_Based_On_Role_Handler Updated")
        # Create response object
        resp_obj = {}
        resp_obj['demostate'] = 1
        resp_obj['gmessage'] = 'Applied'

        # Send object back as response
        self.write(json.dumps(resp_obj))

class Post_Data_From_Form_Handler(BaseHandler):
    # No Authentication
    def post(self):
        # Get data from form (in request header instead of body)
        dayaheadcap = int(self.get_argument('dayaheadcap', 0))
        dayaheadbid = int(self.get_argument('dayaheadbid', 0))
        dayaheadplantoday = int(self.get_argument('dayaheadplantoday', 0))
        dayaheadplantomm = int(self.get_argument('dayaheadplantomm', 0))
        optimizationflag = int(self.get_argument('optimizationflag', 0))
        monitorhistory = int(self.get_argument('monitorhistory', 0))
        setdemoflag = int(self.get_argument('setdemoflag', 0))

        applog("INFO: Post_Data_From_Form_Handler Updated")
        # Create response object
        resp_obj = {}
        resp_obj['demostate'] = 1
        resp_obj['gmessage'] = 'Applied'

        # Send object back as response
        self.write(json.dumps(resp_obj))

class Post_Data_From_Form_Return_Page_Handler(BaseHandler):
    # No Authentication
    def post(self):
        # Get data from form (in request header instead of body)
        dayaheadcap = int(self.get_argument('dayaheadcap', 0))
        dayaheadbid = int(self.get_argument('dayaheadbid', 0))
        dayaheadplantoday = int(self.get_argument('dayaheadplantoday', 0))
        dayaheadplantomm = int(self.get_argument('dayaheadplantomm', 0))
        optimizationflag = int(self.get_argument('optimizationflag', 0))
        monitorhistory = int(self.get_argument('monitorhistory', 0))
        setdemoflag = int(self.get_argument('setdemoflag', 0))

        applog("INFO: Post_Data_From_Form_Return_Page_Handler Updated")
        # Create response object
        resp_obj = {}
        resp_obj['demostate'] = 1
        resp_obj['gmessage'] = 'Applied'

        self.render("getrendertemplate.html",
                     username = username,
                     dataOut = resp_obj,
                     base_url = BASE_PATH)

class Post_Data_And_Store_It_Handler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        #print self.request.body
        if not self.isWriteAllowed():
            resp_obj={}
            resp_obj['rmessage'] = "Sorry you don't have permission to modify this"
            # Send object back as response
            self.write(json.dumps(resp_obj))
            return

        try:
            storeobject = json.loads(self.request.body)
        except:
            applog("ERROR: Converting to JSON Object in Post_Data_And_Store_It_Handler. Body next ->\n")
            applog(self.request.body)
        else:
            storeWeatherInfo(storeobject)

class Post_And_Upload_A_File_Handler(BaseHandler):
    # No authentication
    def post(self):
        # This actually uploads two files
        # Get data information from form
        fuelcost = float(self.get_argument('fuelcost', 0.0))

        # A CSV file has been uploaded
        if "tambfile" in self.request.files:
            amb_csvfilename = os.path.join(__UPLOADS__,self.request.files["tambfile"][0].filename)
            amb_csvfilename = amb_csvfilename.encode('ascii', errors='ignore')

            try:
                f = open(amb_csvfilename,"wb")
                f.write(self.request.files["tambfile"][0].body)
                f.flush()
                f.close()
            except:
                self.returnError("ERROR: Couldn't create/write file >%s< during upload" % amb_csvfilename,self.write)

        else:
            self.returnError("ERROR: Couldn't find the field 'tambfile' in POST values upload from Bid Enter. Probably field was left blank.",self.write)


        if "mwfile" in self.request.files:
            # A CSV file has been uploaded
            mw_elecp_gton_csvfilename = os.path.join(__UPLOADS__,self.request.files["mwfile"][0].filename)
            mw_elecp_gton_csvfilename = mw_elecp_gton_csvfilename.encode('ascii', errors='ignore')

            try:
                f = open(mw_elecp_gton_csvfilename,"wb")
                f.write(self.request.files["mwfile"][0].body)
                f.flush()
                f.close()
            except:
                self.returnError("ERROR: Couldn't create/write file >%s< during upload" % mw_elecp_gton_csvfilename, self.write)
                return
        else:
            self.returnError("ERROR: Couldn't find the field 'mwfile' in POST values upload from Bid Enter. Probably field was left blank.", self.write)
            return

        resp_obj = {}

        resp_obj['gmessage'] = 'Bid saved. Goto Day Ahead Planning!'

        # Send object back as response
        self.write(json.dumps(resp_obj))

# ******************************************************************************
# ******************************************************************************
# WebSocket Examples

class WebSocket_Example_Handler(tornado.websocket.WebSocketHandler):
    # def check_origin(self, origin):
    #     # Not clear what this does but might be important so keeping it around
    #     applog('WARNING: WebSocket origin: {0} (host: {1})\n'.format(origin, self.request.headers.get('Host')))
    #     return super(MBOC_optimizer_finished_Handler, self).check_origin(origin)

    def open(self):
        # Read data from a sub system at regular intervals
        dataOut = {"try this":1}
        # Becuase the connection was just activated write out the data to the
        # websocket connected to a client
        self.write_message(json.dumps(dataOut))
        # setup a future call back of this routine so that data can be
        # refreshed on the client side
        tornado.ioloop.IOLoop.instance().add_timeout(
            datetime.timedelta(microseconds = WEBSOCKET_REFRESH_RATE_MS * 1000),
            self.update)
        # Set this flag so that the websocket can be inform of its closing
        # if this in't done the socket might try transmitting on a close
        # connection and cause an error
        self.open = True

    def on_close(self):
        # Tell the possible future call back to update that the connection is
        # been closed.  If not done will result in errors.
        self.open = False

    def on_message(self, message):
        # Recieve messages from the client here
        applog("WARNING: Message in MBOC_ExecutionAction_Handler not expected> %s\n" % message)

    def update(self):
        # Read data from a sub system at regular intervals
        dataOut = {"try this":1}

        if self.open:
            # If the connection is still active write out the data to the
            # websocket connected to a client
            self.write_message(json.dumps(dataOut))
            # setup a future call back of this routine so that data can be
            # refreshed on the client side
            tornado.ioloop.IOLoop.instance().add_timeout(
                datetime.timedelta(microseconds = WEBSOCKET_REFRESH_RATE_MS * 1000),
                self.update)


# ******************************************************************************
# *** Login/Logout *************************************************************
class AuthProxyHandler(BaseHandler):
    def get(self):
        if not self.current_user:
	    self.set_status(401)
        return

class AuthLoginHandler(BaseHandler):
    def get(self):
        applog("Login screen requested\n")
        errormessage = self.get_argument("error", "")
        next_url = self.get_argument("next", "")
        self.render("login.html", errormessage=errormessage, next_url=next_url, base_url=BASE_PATH)

    def check_permission(self, password, username):
        # Yes, this needs to be fixed
        #TODO: Tie into Predix Authentication and Authorization or
        # into customers AAA system.
        # No point in making this any more complex than this.
        # Not meant to be production quality at this point.

        adminUserName = os.getenv('ADMIN_USERNAME', 'admin')
        operatorUserName = os.getenv('OPERATOR_USERNAME', 'operator')
        guestUserName = os.getenv('GUEST_USERNAME', 'guest')

        adminPassword = os.getenv('ADMIN_PASSWORD', 'admin')
        operatorPassword = os.getenv('OPERATOR_PASSWORD', 'operator')
        guestPassword = os.getenv('GUEST_PASSWORD', 'guest')

        if username == adminUserName and password == adminPassword :
            return ([True,"ADMIN"])
        if username == operatorUserName and password == operatorPassword:
            return ([True,"WRITE"])
        if username == guestUserName and password == guestPassword:
            return ([True,"GUEST"])
        return ([False,None])


    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        applog("SECURITY: Attempt to login by username %s\n" % username)

        (auth,role) = self.check_permission(password, username)
        if auth:
            #print "Auth"
            applog("SECURITY: Login by username %s role %s\n" % (username,role))
            next_url = self.get_argument("next", u"/")
            self.set_current_user(username)
            self.set_current_role(role)
            self.redirect(next_url)

        else:
            error_msg = u"?error=" + tornado.escape.url_escape("Login incorrect")
            applog("SECURITY: Failed login by username %s\n" % (username))
            self.redirect(u"/auth/login/" + error_msg)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user), expires_days = None)
        else:
            self.clear_cookie("user")

    def set_current_role(self, role):
        if role:
            self.set_secure_cookie("role", tornado.escape.json_encode(role), expires_days = None)
        else:
            self.clear_cookie("role")

class AuthLogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))

# *** Login/Logout *************************************************************
# ******************************************************************************

class Main_Bootstrap_Page_Handler(BaseHandler):
    def get(self):
        # Hand back from a get request with no fancy stuff
        self.render("index.html")

# Setup pointer between url S path and handlers

def prefix_with_base(url):
    if url:
        composed = "{0}/{1}".format(BASE_PATH, url)
    else:
        composed = BASE_PATH or "/"
    applog('Composed URL: ' + composed + '\n')
    return composed

p = prefix_with_base

# *** Settings, app setup and execution
settings = {
    "template_path": './public',
    "static_path":'./public',
    "debug":True,
    "cookie_secret": "A secret shared is not a secret",
    "login_url": "/auth/login/"
}

application = tornado.web.Application([
    #
    # If you are using authentication you will need these
    ('/auth/login/', AuthLoginHandler),
    ('/auth/logout/', AuthLogoutHandler),
    ('/auth/login', AuthLoginHandler),
    ('/auth/logout', AuthLogoutHandler),
    ('/auth-proxy', AuthProxyHandler),
    #
    # For access to local bootstrap site
    (p(''), Main_Bootstrap_Page_Handler),
    (p('bootstrap'), Main_Bootstrap_Page_Handler),
    #
    # Examples of other ways of handing back something from a GET request
    (p('get_plain_page_example'),Get_Render_Plain_Page_Handler),
    (p('get_auth_render_templated_example'),Get_Auth_Render_Templated_Page_Handler),
    (p('exportcsvfile'),Get_Export_CSV_File_Handler),
    # Example of handing back something only if they are signed in as a special
    # user
    (p('adminonly'),Admin_Only_Page_Handler),
    #
    # Examples of POST requests
    (p('services/give_data_and_get_data'),Post_Based_On_JSON_Request_Handler),
    (p('services/give_data_if_allowed'),Post_Accept_JSON_Data_Based_On_Role_Handler),
    (p('services/give_data_from_form_if_allowed'),Post_Data_From_Form_Based_On_Role_Handler),
    (p('services/give_data_from_form'),Post_Data_From_Form_Handler),
    (p('services/give_data_from_form_return_page'),Post_Data_From_Form_Return_Page_Handler),
    (p('services/give_data_and_store_it'),Post_Data_And_Store_It_Handler),
    (p('services/give_data_from_file'),Post_And_Upload_A_File_Handler),
    #
    # Example of Websocket handlers
    # this don't have any authentication (be warned)
    (p('services/open_socket_example'),WebSocket_Example_Handler),
    #
    # Anything not handled above and static in nature (in a file) handled here
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": "./public", "default_filename": "index.html"})
    ], **settings)


if __name__ == "__main__":
    # Start it all up
    # If WEB_SITE_PORT not redefined as an Environmental Variable us 9001
    WEB_SITE_PORT = int(os.getenv('WEB_SITE_PORT', '8080'))

    application.listen(WEB_SITE_PORT)
    tornado.ioloop.IOLoop.current().start()
