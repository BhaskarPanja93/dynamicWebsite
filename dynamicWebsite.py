from __future__ import annotations
__version__ = "1.0.2"
__packagename__ = "dynamicWebsite"


def updatePackage():
    from time import sleep
    from json import loads
    import http.client
    print(f"Checking updates for Package {__packagename__}")
    try:
        host = "pypi.org"
        conn = http.client.HTTPSConnection(host, 443)
        conn.request("GET", f"/pypi/{__packagename__}/json")
        data = loads(conn.getresponse().read())
        latest = data['info']['version']
        if latest != __version__:
            try:
                import pip
                pip.main(["install", __packagename__, "--upgrade"])
                print(f"\nUpdated package {__packagename__} v{__version__} to v{latest}\nPlease restart the program for changes to take effect")
                sleep(3)
            except:
                print(f"\nFailed to update package {__packagename__} v{__version__} (Latest: v{latest})\nPlease consider using pip install {__packagename__} --upgrade")
                sleep(3)
        else:
            print(f"Package {__packagename__} already the latest version")
    except:
        print(f"Ignoring version check for {__packagename__} (Failed)")


class Imports:
    from typing import Any
    from flask import Flask, make_response, render_template_string
    from enum import Enum
    from json import dumps, loads
    from threading import Thread
    from time import sleep, time
    from cryptography.fernet import Fernet
    from flask import request, Response
    from flask_sock import Sock
    from randomisedString import Generator as StringGen
    from turbo_flask import Turbo


class Errors:
    """
    Contains all Error classes that will be used by the package
    """
    class ViewerDisconnected(Exception):
        """
        Raised when the visitor has disconnected or has a broken Pipe
        """
        pass
    class InvalidHTMLData(Exception):
        """
        Raised when an invalid object is passed to send to visitor
        """
        pass


class TurboMethods(Imports.Enum):
    """
    All turbo methods of updating content allowed by turbo app
    """
    newDiv = 0
    update = 1
    replace = 2
    remove = 3


class Extras:
    """
    All presets and prebuilt HTML templates will be available here
    """
    @staticmethod
    def baseHTML(head:str, WSRoute:str, title:str, resetOnDisconnect:bool) -> str:
        """
        Minimalistic HTML with no extra functionality
        :param head: (optional) Extra scripts or styles to be added to the head
        :param WSRoute: The route to websocket
        :param title: (optional) The title for the webpage
        :param resetOnDisconnect: (optional) Whether the client body be cleaned upon websocket disconnection
        :return:
        """
        return f"""
        <html>
            <head>
                <script type="module">import * as Turbo from "https://cdn.skypack.dev/pin/@hotwired/turbo@v7.1.0-RBjb2wnkmosSQVoP27jT/min/@hotwired/turbo.js";Turbo.disconnectStreamSource(window.web_sock);window.web_sock = new WebSocket(`ws${{location.protocol.substring(4)}}//${{location.host}}{WSRoute}`); {"window.web_sock.addEventListener('close', function() {document.getElementById('mainDiv').innerHTML = 'DISCONNECTED, REFRESH TO CONTINUE';});" if resetOnDisconnect else ""}Turbo.connectStreamSource(window.web_sock);</script>
                <script>function submit_ws(form){{let form_data = JSON.stringify(Object.fromEntries(new FormData(form)));web_sock.send(form_data);return false;}}</script>
                {head}
                <title>{title}</title>
            </head>
            <body><div id="mainDiv"></div></body>
        </html>
        """


class Cookie:
    """
    Internal DataStructure to hold a visitor's uniquely identifying information and methods to convert to and from cookies
    """
    def __init__(self):
        self.isValid = True
        self.hostURL = ""
        self.remoteAddress = ""
        self.UA = ""
        self.viewerID = ""
        self.delim = Imports.StringGen().AlphaNumeric(20, 20)

    def readDict(self, inputDict: dict) -> Cookie:
        """
        Read from a dictionary into current cookie object and return itself
        :param inputDict: the dictionary to read from
        :return:
        """
        self.delim = inputDict["DELIM"]
        self.remoteAddress = inputDict["REMOTE_ADDRESS"]
        self.UA = inputDict["USER_AGENT"]
        self.viewerID = inputDict["VIEWER_ID"]
        self.hostURL = inputDict["HOST_URL"]
        return self

    def readRequest(self, requestObj: Imports.request) -> Cookie:
        """
        Read from a request context environ object into current cookie object and return itself
        :param requestObj: the request context to read from
        :return:
        """
        self.remoteAddress = requestObj.remote_addr
        self.UA = requestObj.user_agent.string
        self.hostURL = requestObj.host
        self.delim = requestObj.headers.get("DELIM") or self.delim
        return self

    def readAnotherCookie(self, cookie: Cookie) -> Cookie:
        """
        Read from a different cookie object into current cookie object and return itself
        :param cookie: another cookie object of self type
        :return:
        """
        self.hostURL = cookie.hostURL
        self.remoteAddress = cookie.remoteAddress
        self.UA = cookie.UA
        self.viewerID = cookie.viewerID
        self.delim = cookie.delim
        return self

    def attachToResponse(self, response: Imports.Response, fernetKey) -> Imports.Response:
        """
        Attach required cookies and headers into argument response object of Response type and return it
        :param response: the response object to attach cookies and headers to
        :param fernetKey: the fernet string to encrypt the cookie with
        :return:
        """
        response.headers.set("DELIM", self.delim)
        response.set_cookie("DEVICE_INFO", Imports.Fernet(fernetKey).encrypt(str(self).encode()).decode(), expires=Imports.time() + 12 * 30 * 24 * 60 * 60, httponly=True)
        response.set_cookie("DEVICE_INFO_CREATION", str(Imports.time()), expires=Imports.time() + 12 * 30 * 24 * 60 * 60, httponly=True)
        return response

    def decrypt(self, cookieStr: dict, fernetKey) -> Cookie:
        """
        Check if a request.cookie is valid and imports its values into self and return itself
        :param cookieStr: the cookie string received from request object
        :param fernetKey: the fernet string to decrypt the cookie with
        :return:
        """
        try:
            cookieDictBytes = Imports.Fernet(fernetKey).decrypt(cookieStr["DEVICE_INFO"].encode())
            cookieDict = Imports.loads(cookieDictBytes)
            self.readDict(cookieDict)
            return self
        except:
            self.isValid = False
            return self

    def checkValid(self):
        """
        Check if all values of current cookie seem valid, and none empty
        :return:
        """
        valid = False
        if len(self.delim) > 0 and len(self.UA) > 0 and len(self.viewerID) > 0 and len(self.hostURL) > 0 and len(self.remoteAddress) > 0:
            valid = True
        self.isValid = valid
        return valid

    def __eq__(self, other: Cookie):
        """
        Check if 2 cookie objects are same
        :param other: the other cookie object to compare to
        :return:
        """
        return self.delim == other.delim and self.UA == other.UA and self.viewerID == other.viewerID and self.hostURL == other.hostURL and self.remoteAddress == other.remoteAddress and self.isValid == other.isValid

    def __str__(self):
        """
        Convert self to a json dumped string
        :return:
        """
        return Imports.dumps({"HOST_URL": self.hostURL, "REMOTE_ADDRESS": self.remoteAddress, "USER_AGENT": self.UA, "VIEWER_ID": self.viewerID, "DELIM": self.delim})


class BaseViewer:
    """
    Internal (BASE) Datastructure to hold all information regarding individual visitor
    """
    def __init__(self, _id: str, WSList: list, cookie: Cookie, turbo_app: ModifiedTurbo):
        self.__idleSender = True
        self.__sendQueue = []
        self.__turboIdle = True
        self.__activeCSRF: dict[str, dict[str, str]] = {}
        self.turboApp = turbo_app
        self.turboApp.activeViewers.append(self)
        self.purposeToHidden = {}
        self.hiddenToPurpose = {}
        self.clientContentCache = {}
        self.viewerID = _id
        self.WSList = WSList
        self.cookie: Cookie = cookie


    def __startFlaskSender(self) -> None:
        """
        Private method to start executing all pending actions for current visitor. Has to be called everytime there is a new action queued
        :return:
        """
        if self.__idleSender:
            self.__idleSender = False
        else:
            return
        while len(self.__sendQueue)!=0 and self.isActive():
            task = self.__sendQueue.pop(0)
            stream, htmlData, divName = task
            try: self.turboApp.push(stream, to=self.viewerID)
            except: break
            self.clientContentCache[divName] = htmlData
        self.__idleSender = True

    def __stripSecurities(self, form: dict) -> dict|None:
        """
        Upon form submit through websocket CSRF and other security parameters are checked and removed and returns a clean form dictionary with no extra parameters. Returns None if Securities don't match
        :param form: Form dictionary received from client
        :return:
        """
        if self.isActive():
            if "PURPOSE" not in form or "CSRF" not in form: return
            receivedPurpose: str = form.pop("PURPOSE")
            if "." not in receivedPurpose: return
            realPurpose, token = receivedPurpose.split(".")
            if realPurpose in self.__activeCSRF and receivedPurpose in self.__activeCSRF[realPurpose]:
                expectedCSRF = self.__activeCSRF[realPurpose].pop(receivedPurpose)
            else:
                expectedCSRF = None
            receivedCSRF = form.pop("CSRF")
            if not receivedCSRF or receivedCSRF != expectedCSRF: return
            form["PURPOSE"] = self.hiddenToPurpose.get(realPurpose)
            return form

    def isActive(self) -> bool:
        """
        Check if the current viewer's ID is still in owning turbo app active list
        :return:
        """
        try: return sorted(self.turboApp.clients.get(self.viewerID)) == sorted(self.WSList)
        except: return False

    def addCSRF(self, realPurpose: str) -> str:
        """
        Generates hidden tags with CSRF and PURPOSE tags to be used in forms
        :param realPurpose: The purpose of the form submit, must be present in the purposeList when calling the app-create function
        :return:
        """
        if realPurpose not in self.purposeToHidden:
            while True:
                hiddenString = Imports.StringGen().AlphaNumeric(10, 10)
                if hiddenString not in list(self.purposeToHidden.values()): break
            self.purposeToHidden[realPurpose] = hiddenString
            self.hiddenToPurpose[hiddenString] = realPurpose
        hiddenPurpose = self.purposeToHidden[realPurpose]
        while True:  # while needed
            token = Imports.StringGen().AlphaNumeric(_min=5, _max=10)
            csrf = Imports.StringGen().AlphaNumeric(_min=10, _max=20)
            purposeString = f"{hiddenPurpose}.{token}"
            if hiddenPurpose not in self.__activeCSRF:
                self.__activeCSRF[hiddenPurpose] = {}
            if purposeString not in self.__activeCSRF[hiddenPurpose] or not self.__activeCSRF[hiddenPurpose][purposeString]:
                self.__activeCSRF[hiddenPurpose][purposeString] = csrf
                return f"""<input type="hidden" name="PURPOSE" value="{purposeString}"><input type="hidden" name="CSRF" value="{csrf}">"""

    def turboReceive(self, WSObj) -> dict|None:
        """
        Constantly keep watching for data received from websocket, strip the securities and then return the cleaned Dictionary
        :param WSObj:
        :return:
        """
        while True:  # while needed
            try:
                received = WSObj.receive(timeout=5)
                if received:
                    if self.isActive():
                        stripped = self.__stripSecurities(Imports.loads(received))
                        if stripped is not None: return stripped
                    else: raise Errors.ViewerDisconnected
            except: return self.turboApp.activeViewers.remove(self)

    def queueTurboAction(self, htmlData: Imports.Any, divID: str, method: TurboMethods, nonBlockingWait: float = 0, removeAfter: float = 0, blockingWait: float = 0) -> str|None:
        """
        Method to queue live update actions to be executed on current visitor. All actions get queued up and executed sequentially
        :param htmlData: The data to be sent to the client, can be of type str or bytes or any JSON serializable or an object with the __str__ method
        :param divID: The target div ID
        :param method: The kind of action to perform
        :param nonBlockingWait: Duration to wait before executing the action (doesn't block the calling function)
        :param removeAfter: Duration to wait before removing the div entirely. 0 means the div isn't supposed to be removed
        :param blockingWait: Duration to wait before executing the action (blocks the calling function)
        :return:
        """
        if type(htmlData) != str:
            try: htmlData = htmlData.decode()
            except:
                try: htmlData = Imports.dumps(htmlData)
                except:
                    try: htmlData = str(htmlData)
                    except: raise Errors.InvalidHTMLData

        if nonBlockingWait > 0:
            blockingWait = nonBlockingWait
            Imports.Thread(target=self.queueTurboAction, args=(htmlData, divID, method, 0, removeAfter, blockingWait)).start()
            return

        if blockingWait > 0:
            Imports.sleep(0 if blockingWait<0.001 else blockingWait)
            return self.queueTurboAction(htmlData, divID, method, 0, removeAfter)


        if method in [self.turboApp.methods.newDiv, self.turboApp.methods.newDiv.value]:
            readDivID = divID
            while True:  # while needed
                divID = f"{readDivID}_{Imports.StringGen().AlphaNumeric(_min=5, _max=30)}"
                if divID not in self.clientContentCache:
                    self.clientContentCache[divID] = ""
                    self.queueTurboAction(f"""<div id='{divID}'></div><div id='{readDivID}_create'></div>""", f'{readDivID}_create', self.turboApp.methods.replace, 0, 0)
                    break
            self.queueTurboAction(htmlData, divID, self.turboApp.methods.update, nonBlockingWait, removeAfter)

        elif method in [self.turboApp.methods.replace, self.turboApp.methods.replace.value]:
            self.__sendQueue.append([self.turboApp.replace(htmlData, divID), htmlData, divID])
            self.__startFlaskSender()

        elif method in [self.turboApp.methods.remove, self.turboApp.methods.remove.value]:
            self.__sendQueue.append([self.turboApp.remove(divID), "", divID])
            self.__startFlaskSender()

        elif method in [self.turboApp.methods.update, self.turboApp.methods.update.value]:
            if divID not in self.clientContentCache or self.clientContentCache[divID] != htmlData: self.__sendQueue.append([self.turboApp.update(htmlData, divID), htmlData, divID])
            self.__startFlaskSender()
            if removeAfter: self.queueTurboAction("", divID, self.turboApp.methods.remove, removeAfter, 0, removeAfter)

        return divID

class ModifiedTurbo(Imports.Turbo):
    """
    Derived TurboFlask's class with extra functionalities and methods
    """
    def __init__(self, app=None, route=''):
        self.__route = route
        self.__WSWaitViewerIDs: list[str] = []
        self.activeViewers: list[BaseViewer] = []
        self.methods = TurboMethods
        super().__init__(app)

    def init_app(self, app):
        ws_route = app.config.setdefault('TURBO_WEBSOCKET_ROUTE', self.__route)
        if ws_route:
            self.sock = Imports.Sock()
            self.sock.init_app(app)
        app.context_processor(self.context_processor)

    def checkAndWSBlockViewerID(self, viewerID):
        """
        Save viewer ID as pending to connect web socket. Keeps the ViewerID for 60 seconds till the websocket request is made and then freed. No new viewer can get the pending viewer ID
        :param viewerID: String representing the Viewer
        :return:
        """
        def freeViewerID(viewerID):
            Imports.sleep(60)
            if viewerID in self.__WSWaitViewerIDs:
                self.__WSWaitViewerIDs.remove(viewerID)

        if viewerID not in self.__WSWaitViewerIDs:
            self.__WSWaitViewerIDs.append(viewerID)
            Imports.Thread(target=freeViewerID, args=(viewerID,)).start()
            return True
        else:
            return False

    def consumeWSBlockedViewerID(self, viewerID):
        """
        Check if viewer ID has pending websocket connection to be made, if so remove from pending and assign the websocket to the viewer
        :param viewerID: String representing the Viewer
        :return:
        """
        if viewerID not in self.__WSWaitViewerIDs: return False
        else: return not self.__WSWaitViewerIDs.remove(viewerID)

    def generateViewerID(self) -> str:
        """
        Generate a new unique viewerID string
        :return:
        """
        while True:  # while needed
            viewerID = Imports.StringGen().AlphaNumeric(30, 50)
            if viewerID not in self.clients and viewerID not in self.__WSWaitViewerIDs:
                self.checkAndWSBlockViewerID(viewerID)
                return viewerID


def createApps(formCallback, newVisitor, appName:str="Live App", homeRoute:str="/", WSRoute:str="/ws", fernetKey:str=Imports.Fernet.generate_key(), extraHeads:str="", title:str="Live", resetOnDisconnect:bool=True):
    baseApp = Imports.Flask(appName)
    turboApp = ModifiedTurbo(baseApp, WSRoute)

    @baseApp.route(homeRoute, methods=['GET'])
    def _root_url():
        cookieObj = Cookie().decrypt(Imports.request.cookies, fernetKey)
        if not cookieObj.checkValid():
            cookieObj = Cookie().readRequest(Imports.request)
            cookieObj.viewerID = turboApp.generateViewerID()
        else: turboApp.checkAndWSBlockViewerID(cookieObj.viewerID)
        return cookieObj.attachToResponse(Imports.make_response(Imports.render_template_string(Extras.baseHTML(extraHeads, WSRoute, title, resetOnDisconnect))), fernetKey)


    @turboApp.sock.route(WSRoute)
    def _turbo_stream(WSObj):
        cookieObjRequest = Cookie().readRequest(Imports.request)
        cookieObj = Cookie().decrypt(Imports.request.cookies, fernetKey)
        if cookieObjRequest.isValid and cookieObj == (Cookie().decrypt(Imports.request.cookies, fernetKey)):
            if not cookieObj.checkValid() or not turboApp.consumeWSBlockedViewerID(cookieObj.viewerID): return
            turboApp.clients[cookieObj.viewerID] = [WSObj]
            viewerObj = BaseViewer(cookieObj.viewerID, [WSObj], cookieObj, turboApp)
            newVisitor(viewerObj)
            while True:
                received = viewerObj.turboReceive(WSObj)
                Imports.Thread(target=formCallback, args=(viewerObj, received,)).start()
                if received is None:
                    turboApp.clients.pop(cookieObj.viewerID)
                    break


    @baseApp.before_request
    def userBeforeRequest():
        """
        Before any request goes to any route, it passes through this function.
        Applies user remote address correctly (received from proxy)
        :return:
        """
        address = "BANNED"
        if Imports.request.remote_addr == "127.0.0.1":
            if Imports.request.environ.get("HTTP_X_FORWARDED_FOR") == Imports.request.headers.get("X-Forwarded-For"):
                if Imports.request.environ.get("HTTP_X_FORWARDED_FOR") is not None:
                    address = Imports.request.environ.get("HTTP_X_FORWARDED_FOR")
                else: address = "LOCAL"
        else: address = Imports.request.remote_addr
        Imports.request.remote_addr = address

    return baseApp, turboApp
