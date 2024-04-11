from __future__ import annotations


class Imports:
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
    class ViewerDisconnected(Exception):
        pass


class TurboMethods(Imports.Enum):
    newDiv = "new"
    update = "update"
    replace = "replace"
    remove = "remove"


class Extras:

    @staticmethod
    def HTML(extraHeads: str, WSRoute):
        return f"""
        <html>
            <head>
                <script type="module">
                import * as Turbo from "https://cdn.skypack.dev/pin/@hotwired/turbo@v7.1.0-RBjb2wnkmosSQVoP27jT/min/@hotwired/turbo.js";
                Turbo.disconnectStreamSource(window.web_sock)
                window.web_sock = new WebSocket(`ws${{location.protocol.substring(4)}}//${{location.host}}{WSRoute}`);
                window.web_sock.addEventListener('close', function() {{document.getElementById("mainDiv").innerHTML = "DISCONNECTED, REFRESH TO CONTINUE";}});
                Turbo.connectStreamSource(window.web_sock);
            </script>
            <script>
                function submit_ws(form) 
                {{
                    let form_data = JSON.stringify(Object.fromEntries(new FormData(form)));
                    web_sock.send(form_data);
                    return false;
                }}
                </script>
            {extraHeads}
            <title>Main Page</title>
            </head>
            <body>
                <div id="mainDiv"></div>
            </body>
        </html>
    """

class Cookie:
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
        self.delim = requestObj.headers.get("DELIM")
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
    def __init__(self, _id: str, WSList: list, cookie: Cookie, turbo_app: ModifiedTurbo, purposeList: list[str]):
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
        self.__generateHidden(purposeList)

    def __generateHidden(self, purposeList: list[str]):
        for purposeName in purposeList:
            while True:
                hiddenString = Imports.StringGen().AlphaNumeric(10, 10)
                if hiddenString not in list(self.purposeToHidden.values()): break
            self.purposeToHidden[purposeName] = hiddenString
            self.hiddenToPurpose[hiddenString] = purposeName

    def __startFlaskSender(self):
        if self.__idleSender:
            self.__idleSender = False
        else:
            return
        while self.__sendQueue and self.isActive():
            task = self.__sendQueue[0]
            stream, htmlData, divName = task
            try:
                self.turboApp.push(stream, to=self.viewerID)
            except:
                break
            self.clientContentCache[divName] = htmlData
            self.__sendQueue.pop(0)
        self.__idleSender = True

    def __stripSecurities(self, form: dict):
        print(form)
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

    def isActive(self):
        try:
            return sorted(self.turboApp.clients.get(self.viewerID)) == sorted(self.WSList)
        except:
            return False

    def addCSRF(self, realPurpose: str):
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

    def turboReceive(self, WSObj):
        while True:  # while needed
            try:
                received = WSObj.receive(timeout=5)
                if self.isActive():
                    if received:
                        stripped = self.__stripSecurities(Imports.loads(received))
                        if stripped is not None: return stripped
                else:
                    raise Errors.ViewerDisconnected
            except:
                break
        self.turboApp.activeViewers.remove(self)

    def queueTurboAction(self, htmlData: str, divName: str, method: TurboMethods, nonBlockingWait: float = 0, removeAfter: float = 0, blockingWait: float = 0):
        if type(htmlData) != str:
            htmlData = str(htmlData)

        if nonBlockingWait > 0:
            blockingWait = nonBlockingWait
            Imports.Thread(target=self.queueTurboAction, args=(htmlData, divName, method, 0, removeAfter, blockingWait)).start()
            return

        if blockingWait > 0:
            Imports.sleep(blockingWait)
            self.queueTurboAction(htmlData, divName, method, 0, removeAfter)
            return

        if method in [self.turboApp.methods.newDiv, self.turboApp.methods.newDiv.value]:
            readDivName = divName
            while True:  # while needed
                divName = f"{readDivName}_{Imports.StringGen().AlphaNumeric(_min=5, _max=30)}"
                if divName not in self.clientContentCache:
                    self.clientContentCache[divName] = ""
                    self.queueTurboAction(f"""<div id='{divName}'></div><div id='{readDivName}_create'></div>""", f'{readDivName}_create', self.turboApp.methods.replace, 0, 0)
                    break
            self.queueTurboAction(htmlData, divName, self.turboApp.methods.update, nonBlockingWait, removeAfter)
        elif method in [self.turboApp.methods.replace, self.turboApp.methods.replace.value]:
            self.__sendQueue.append([self.turboApp.replace(htmlData, divName), htmlData, divName])
            self.__startFlaskSender()
        elif method in [self.turboApp.methods.remove, self.turboApp.methods.remove.value]:
            self.__sendQueue.append([self.turboApp.remove(divName), "", divName])
            self.__startFlaskSender()
        elif method in [self.turboApp.methods.update, self.turboApp.methods.update.value]:
            if divName not in self.clientContentCache or self.clientContentCache[divName] != htmlData: self.__sendQueue.append([self.turboApp.update(htmlData, divName), htmlData, divName])
            self.__startFlaskSender()
            if removeAfter: self.queueTurboAction('', divName, self.turboApp.methods.remove, removeAfter, 0, removeAfter)
        return divName

class ModifiedTurbo(Imports.Turbo):
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
        if viewerID not in self.__WSWaitViewerIDs:
            return False
        else:
            self.__WSWaitViewerIDs.remove(viewerID)
            return True

    def generateViewerID(self):
        while True:  # while needed
            viewerID = Imports.StringGen().AlphaNumeric(30, 50)
            if viewerID not in self.clients and viewerID not in self.__WSWaitViewerIDs:
                self.checkAndWSBlockViewerID(viewerID)
                return viewerID

def createApps(formCallback, newVisitor, appName, homeRoute, WSRoute, fernetKey, formPurposeList, extraHeads):
    baseApp = Imports.Flask(appName)
    turboApp = ModifiedTurbo(baseApp, WSRoute)

    @baseApp.route(homeRoute, methods=['GET'])
    def _root_url():
        cookieObj = Cookie().decrypt(Imports.request.cookies, fernetKey)
        if not cookieObj.checkValid():
            cookieObj = Cookie().readRequest(Imports.request)
            viewerID = turboApp.generateViewerID()
            cookieObj.viewerID = viewerID
            cookieObj.delim = Imports.StringGen().AlphaNumeric(10, 10)
        else: turboApp.checkAndWSBlockViewerID(cookieObj.viewerID)
        response = Imports.make_response(Imports.render_template_string(Extras.HTML(extraHeads, WSRoute)))
        return cookieObj.attachToResponse(response, fernetKey)


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
                else:
                    address = "LOCAL"
        else:
            address = Imports.request.remote_addr
        Imports.request.remote_addr = address


    @turboApp.sock.route(WSRoute)
    def _turbo_stream(WSObj):
        cookieObjRequest = Cookie().readRequest(Imports.request)
        cookieObj = Cookie().decrypt(Imports.request.cookies, fernetKey)
        if cookieObjRequest.isValid and cookieObj == (Cookie().decrypt(Imports.request.cookies, fernetKey)):
            if not cookieObj.checkValid() or not turboApp.consumeWSBlockedViewerID(cookieObj.viewerID): return
            turboApp.clients[cookieObj.viewerID] = [WSObj]
            viewerObj = BaseViewer(cookieObj.viewerID, [WSObj], cookieObj, turboApp, formPurposeList)
            newVisitor(viewerObj)
            while True:
                received = viewerObj.turboReceive(WSObj)
                Imports.Thread(target=formCallback, args=(viewerObj, received,)).start()
                if received is None:
                    turboApp.clients.pop(cookieObj.viewerID)
                    break
    return baseApp, turboApp
