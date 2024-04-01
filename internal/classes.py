from __future__ import annotations

from enum import Enum
from json import dumps, loads
from threading import Thread
from time import sleep, time

from cryptography.fernet import Fernet
from flask import request, Response
from flask_sock import Sock
from randomisedString import Generator as StringGen
from turbo_flask import Turbo

class Error:
    class InvalidOrModifiedCookieError(Exception):
        pass
    class ViewerDisconnected(Exception):
        pass


class ModifiedTurbo(Turbo):
    class TurboMethods(Enum):
        newDiv = "new"
        update = "update"
        replace = "replace"
        remove = "remove"

    def __init__(self, app=None, route=''):
        self.route = route
        self.WSWaitViewerIDs:list[str] = []
        self.methods = ModifiedTurbo.TurboMethods
        super().__init__(app)


    def init_app(self, app):
        ws_route = app.config.setdefault('TURBO_WEBSOCKET_ROUTE', self.route)
        if ws_route:
            self.sock = Sock()
            self.sock.init_app(app)
        app.context_processor(self.context_processor)

    def checkAndWSBlockViewerID(self, viewerID):
        def freeViewerID(viewerID):
            sleep(60)
            if viewerID in self.WSWaitViewerIDs:
                self.WSWaitViewerIDs.remove(viewerID)
        if viewerID not in self.WSWaitViewerIDs:
            self.WSWaitViewerIDs.append(viewerID)
            Thread(target=freeViewerID, args=(viewerID,)).start()
            return True
        else:
            return False

    def generateViewerID(self):
        while True:  # while needed
            viewerID = StringGen().AlphaNumeric(30, 50)
            if viewerID not in self.clients and viewerID not in self.WSWaitViewerIDs:
                self.checkAndWSBlockViewerID(viewerID)
                return viewerID


class Cookie:
    def __init__(self):
        self.isValid = True
        self.hostURL = ""
        self.remoteAddress = ""
        self.UA = ""
        self.viewerID = ""
        self.delim = StringGen().AlphaNumeric(20,20)

    def readDict(self, inputDict:dict) -> Cookie:
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

    def readRequest(self, requestObj:request) -> Cookie:
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

    def readAnotherCookie(self, cookie:Cookie) -> Cookie:
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

    def attachToResponse(self, response:Response, fernetKey) -> Response:
        """
        Attach required cookies and headers into argument response object of Response type and return it
        :param response: the response object to attach cookies and headers to
        :param fernetKey: the fernet string to encrypt the cookie with
        :return:
        """
        response.headers.set("DELIM", self.delim)
        response.set_cookie("DEVICE_INFO", Fernet(fernetKey).encrypt(str(self).encode()).decode(), expires=time() + 12 * 30 * 24 * 60 * 60, httponly=True)
        response.set_cookie("DEVICE_INFO_CREATION", str(time()), expires=time() + 12 * 30 * 24 * 60 * 60, httponly=True)
        return response

    def decrypt(self, cookieStr:dict, fernetKey) -> Cookie:
        """
        Check if a request.cookie is valid and imports its values into self and return itself
        :param cookieStr: the cookie string received from request object
        :param fernetKey: the fernet string to decrypt the cookie with
        :return:
        """
        try:
            cookieDictBytes = Fernet(fernetKey).decrypt(cookieStr["DEVICE_INFO"].encode())
            cookieDict = loads(cookieDictBytes)
            self.readDict(cookieDict)
            return self
        except:
            self.isValid = False
            return self

    def checkValid(self):
        valid = False
        if len(self.delim)>0 and len(self.UA)>0 and len(self.viewerID)>0 and len(self.hostURL)>0 and len(self.remoteAddress)>0:
            valid = True
        self.isValid = valid
        return valid

    def __eq__(self, other:Cookie):
        """
        Check if 2 cookie objects are same
        :param other: the other cookie object to compare to
        :return:
        """
        return self.delim==other.delim and self.UA==other.UA and self.viewerID==other.viewerID and self.hostURL==other.hostURL and self.remoteAddress==other.remoteAddress and self.isValid==other.isValid

    def __str__(self):
        """
        Convert self to a json dumped string
        :return:
        """
        return dumps({"HOST_URL": self.hostURL, "REMOTE_ADDRESS": self.remoteAddress, "USER_AGENT": self.UA, "VIEWER_ID": self.viewerID, "DELIM":self.delim})


class BaseViewer:
    class __FormPurpose(Enum):
        register = StringGen().AlphaNumeric(5,10)
        login = StringGen().AlphaNumeric(5,10)
        newTask = StringGen().AlphaNumeric(5,10)
        delTask = StringGen().AlphaNumeric(5,10)

    def __init__(self, turbo_app:ModifiedTurbo):
        self.turboApp = turbo_app
        self.viewerID = ""
        self.WSList = []
        self.cookie: Cookie | None = None
        self.formPurposes = BaseViewer.__FormPurpose

        self.activeCSRF:dict[str,dict[str,str]] = {}
        self.turboIdle = True
        self.clientContentCache = {}

    def isActive(self):
        return sorted(self.turboApp.clients.get(self.viewerID)) == sorted(self.WSList)

    def generatePurposeCSRF(self, realPurpose:BaseViewer.__FormPurpose, extras=None):
        if extras is None:
            extras = []
        while True: # while needed
            token = StringGen().AlphaNumeric(_min=5, _max=10)
            csrf = StringGen().AlphaNumeric(_min=10, _max=20)
            purposeString = f"{realPurpose}.{token}"
            if realPurpose not in self.activeCSRF:
                self.activeCSRF[realPurpose.value] = {}
            if purposeString not in self.activeCSRF[realPurpose.value] or not self.activeCSRF[realPurpose.value][purposeString]:
                self.activeCSRF[realPurpose.value][purposeString] = csrf
                return purposeString, csrf, extras

    def useCSRF(self, realPurpose:BaseViewer.__FormPurpose, token:str):
        purposeString = f"{realPurpose.value}.{token}"
        if realPurpose.value in self.activeCSRF and purposeString in self.activeCSRF[realPurpose.value]:
            return self.activeCSRF[realPurpose.value].pop(purposeString)
        return None

    def turboAction(self, htmlData: str, divName: str, method: ModifiedTurbo.TurboMethods, nonBlockingWait: float = 0, removeAfter: float = 0, blockingWait: float = 0, overrideIdle: bool = False):
        """TODO: queue mechanism instead of waiter"""
        if type(htmlData) != str:
            htmlData = str(htmlData)

        if nonBlockingWait>0:
            blockingWait = nonBlockingWait
            Thread(target=self.turboAction, args=(htmlData, divName, method, 0, removeAfter, blockingWait)).start()
            return

        if blockingWait>0:
            sleep(blockingWait)
            self.turboAction(htmlData, divName, method, 0, removeAfter)
            return

        newDivName = divName
        if not overrideIdle:
            for _ in range(1200):
                if not self.turboIdle:
                    sleep(0.01)
            self.turboIdle = False

        for _ in range(50):
            try:
                if not self.isActive():
                    break
                if method == self.turboApp.methods.newDiv:
                    while True: # while needed
                        delimiter = StringGen().AlphaNumeric(_min=5, _max=30)
                        newDivName = f"{divName}_{delimiter}"
                        if newDivName not in self.clientContentCache:
                            self.clientContentCache[newDivName] = ""
                            self.turboAction(f"""<div id='{newDivName}'></div><div id='{divName}_create'></div>""", f'{divName}_create', self.turboApp.methods.replace, 0, 0, overrideIdle=True)
                            break
                        elif not self.clientContentCache[newDivName]:
                            break
                    self.turboAction(htmlData, newDivName, self.turboApp.methods.update, nonBlockingWait, removeAfter, overrideIdle=True)
                    break
                elif method == self.turboApp.methods.replace:
                    self.turboApp.push(self.turboApp.replace(htmlData, divName), to=self.viewerID)
                    self.clientContentCache[divName] = htmlData
                    break
                elif method == self.turboApp.methods.remove:
                    self.turboApp.push(self.turboApp.remove(divName), to=self.viewerID)
                    self.clientContentCache[divName] = ""
                    break
                elif method == self.turboApp.methods.update:
                    if divName not in self.clientContentCache or self.clientContentCache[divName] != htmlData:
                        self.turboApp.push(self.turboApp.update(htmlData, divName), to=self.viewerID)
                        self.clientContentCache[divName] = htmlData
                    if removeAfter:
                        nonBlockingWait = removeAfter
                        Thread(target=self.turboAction, args=('', divName, self.turboApp.methods.remove, 0, 0, removeAfter)).start()
                    break
            except:
                pass
            sleep(1/1000)
        if not overrideIdle:
            self.turboIdle = True

        return newDivName

