from __future__ import annotations
__version__ = "1.4.1"
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
    from base64 import b64decode
    from flask import Flask, make_response, render_template_string, request, Response
    from enum import Enum
    from json import dumps, loads
    from threading import Thread
    from time import sleep, time
    from cryptography.fernet import Fernet
    from flask_sock import Sock
    from turbo_flask import Turbo
    from randomisedString import Generator as StringGen
    from rateLimitedQueues import Manager as QueueManager


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
    def baseHTML(CSRF:str, turboHeader:str, extraHeads:str, WSRoute:str, title:str, resetOnDisconnect:bool, bodyBase:str) -> str:
        """
        Minimalistic HTML with no extra functionality
        :param CSRF: Handshaking CSRF
        :param turboHeader: Module to init turbo, containing its version and other details
        :param extraHeads: (optional) Extra scripts or styles to be added to the head
        :param WSRoute: The route to websocket
        :param title: (optional) The title for the webpage
        :param resetOnDisconnect: (optional) Whether the client body be cleaned upon websocket disconnection
        :param bodyBase: Initial body element
        :return:
        """
        return f"""
        <html>
            <head>
                {turboHeader.replace("module", "")}
                <script id="dynamicWebsiteWebsocketHandshake">
                    document.getElementById("dynamicWebsiteWebsocketHandshake").remove();
                
                    function base64ArrayBuffer(arrayBuffer) 
                    {{
                        var base64    = ''
                        var encodings = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
                        var bytes         = new Uint8Array(arrayBuffer)
                        var byteLength    = bytes.byteLength
                        var byteRemainder = byteLength % 3
                        var mainLength    = byteLength - byteRemainder
                        var a, b, c, d
                        var chunk
                        for (var i = 0; i < mainLength; i = i + 3) 
                        {{
                            chunk = (bytes[i] << 16) | (bytes[i + 1] << 8) | bytes[i + 2]
                            a = (chunk & 16515072) >> 18 // 16515072 = (2^6 - 1) << 18
                            b = (chunk & 258048)   >> 12 // 258048   = (2^6 - 1) << 12
                            c = (chunk & 4032)     >>  6 // 4032     = (2^6 - 1) << 6
                            d = chunk & 63               // 63       = 2^6 - 1
                            base64 += encodings[a] + encodings[b] + encodings[c] + encodings[d]
                        }}
                        if (byteRemainder == 1) 
                        {{
                            chunk = bytes[mainLength]
                            a = (chunk & 252) >> 2 // 252 = (2^6 - 1) << 2
                            b = (chunk & 3)   << 4 // 3   = 2^2 - 1
                            base64 += encodings[a] + encodings[b] + '=='
                        }} 
                        else if (byteRemainder == 2) 
                        {{
                            chunk = (bytes[mainLength] << 8) | bytes[mainLength + 1]
                            a = (chunk & 64512) >> 10 // 64512 = (2^6 - 1) << 10
                            b = (chunk & 1008)  >>  4 // 1008  = (2^6 - 1) << 4
                            c = (chunk & 15)    <<  2 // 15    = 2^4 - 1
                            base64 += encodings[a] + encodings[b] + encodings[c] + '='
                        }}
                        return base64
                    }}


                    class FileToSend 
                    {{
                        constructor(fileID, file) 
                        {{
                            this.fileID = fileID;
                            this.file = file;
                            this.lastSentPartIndex = -1
                            this.maxPartIndex = Math.ceil(file.size/window.chunk_size)-1;
                        }}

                        resumeSending()
                        {{
                            let mainInterval = setInterval(() =>
                            {{
                                if (window.web_sock.bufferedAmount < window.max_buffer_size)
                                {{
                                    clearInterval(mainInterval);
                                    let indexToSend = ++this.lastSentPartIndex;
                                    if (indexToSend>this.maxPartIndex) return;
                                    
                                    let reader = new FileReader();
                                    reader.fileClass = this;
                                    reader.partIndex = indexToSend;
                                    reader.onload = function(e) 
                                    {{ 
                                        window.web_sock.send(
                                        JSON.stringify(
                                        {{
                                            "ISFILE":true,
                                            "FILEID":e.target.fileClass.fileID, 
                                            "CURRENT":e.target.partIndex,
                                            "DATA":base64ArrayBuffer(e.target.result)
                                        }}
                                        ));
                                        console.log("sent", e.target.partIndex, e.target.fileClass.maxPartIndex);
                                        e.target.fileClass.resumeSending();
                                    }}
                                    let start_byte = (indexToSend)*window.chunk_size
                                    reader.readAsArrayBuffer(this.file.slice(start_byte, Math.min(this.file.size, start_byte+window.chunk_size)));
                                }}
                            }}, 200);
                        }}
                    }}


                    function submit_ws(form)
                    {{
                        let fileUploadListName = "dynamicWebsiteUploadingFilesList";
                        let form_data = Object.fromEntries(new FormData(form));
                        form_data[fileUploadListName] = {{}};
                        let filesToUpload = {{}};
                        for (let formElementIndex = 0; formElementIndex < form.children.length; formElementIndex++)
                        {{
                            let element = form.children[formElementIndex];
                            if (element.type == "file")
                            {{
                                let elementName = element.name;
                                form_data[fileUploadListName][elementName] = {{}};
                                delete form_data[elementName];
                                for (let fileIndex = 0; fileIndex < element.files.length; fileIndex++)
                                {{
                                    let fileUploadId = parseInt(localStorage.dynamicWebsiteNextFileUploadId);
                                    if (isNaN(fileUploadId) || fileUploadId >= Number.MAX_SAFE_INTEGER-1) {{fileUploadId=0;}}
                                    localStorage.setItem('dynamicWebsiteNextFileUploadId', fileUploadId+1);
                                    let file = element.files[fileIndex];
                                    form_data[fileUploadListName][elementName][fileUploadId] = {{"NAME":file.name, "SIZE":file.size, "TYPE":file.type, "MAXPART":Math.ceil(file.size/window.chunk_size)-1}};
                                    filesToUpload[fileUploadId] = file;
                                }}
                            }}
                        }}
                        
                        window.web_sock.send(JSON.stringify(form_data));
                        for (const [fileID, fileObj] of Object.entries(filesToUpload)) 
                        {{
                            let fileSender = new FileToSend(fileID, fileObj);
                            for (let i=0;i<10;i++) fileSender.resumeSending()
                        }}
                        return false;
                    }}

                    window.transferred_bytes = 0;
                    window.to_be_transferred_bytes = 0;
                    
                    window.chunk_size = 1024*1024*16;
                    window.max_buffer_size = 1024*1024*256;

                    Turbo.disconnectStreamSource(window.web_sock);
                    window.web_sock = new WebSocket(`ws${{location.protocol.substring(4)}}//${{location.host}}{WSRoute}`); 
                    {"window.web_sock.addEventListener('close', function() {document.getElementById('mainDiv').innerHTML = 'DISCONNECTED, REFRESH TO CONTINUE';});" if resetOnDisconnect else ""}
                    Turbo.connectStreamSource(window.web_sock);
                    window.web_sock.onopen = function() {{window.web_sock.send("{CSRF}");}};
                </script>
                {extraHeads}
                <title>{title}</title>
            </head>
            {bodyBase}
        </html>
        """


class Cookie:
    """
    Internal DataStructure to hold a visitor's uniquely identifying information and methods to convert to and from cookies
    """
    def __init__(self):
        self.remoteAddress = ""
        self.UA = ""
        self.viewerID = ""
        self.hostURL = ""
        self.origin = ""
        self.CSRF = ""

    def readDict(self, inputDict: dict) -> Cookie:
        """
        Read from a dictionary into current cookie object and return itself
        :param inputDict: the dictionary to read from
        :return:
        """
        self.remoteAddress = inputDict["REMOTE_ADDRESS"]
        self.UA = inputDict["USER_AGENT"]
        self.viewerID = inputDict["VIEWER_ID"]
        self.hostURL = inputDict["HOST_URL"]
        self.origin = inputDict["ORIGIN"]
        self.CSRF = inputDict["CSRF"]
        return self

    def readRequest(self, requestObj: Imports.request) -> Cookie:
        """
        Read from a request context environ object into current cookie object and return itself
        :param requestObj: the request context to read from
        :return:
        """
        self.remoteAddress = requestObj.remote_addr
        self.UA = requestObj.user_agent.string
        from urllib.parse import urlparse
        self.hostURL = f"{urlparse(requestObj.host_url).hostname}{f':{urlparse(requestObj.host_url).port}' if urlparse(requestObj.host_url).port is not None else ''}"
        self.origin = f"{urlparse(requestObj.origin).hostname}{f':{urlparse(requestObj.origin).port}' if urlparse(requestObj.origin).port is not None else ''}"
        return self

    def readAnotherCookie(self, cookie: Cookie) -> Cookie:
        """
        Read from a different cookie object into current cookie object and return itself
        :param cookie: another cookie object of self type
        :return:
        """
        self.remoteAddress = cookie.remoteAddress
        self.UA = cookie.UA
        self.viewerID = cookie.viewerID
        self.hostURL = cookie.hostURL
        self.origin = cookie.origin
        self.CSRF = cookie.CSRF
        return self

    def attachToResponse(self, response: Imports.Response, fernetKey) -> Imports.Response:
        """
        Attach required cookies and headers into argument response object of Response type and return it
        :param response: the response object to attach cookies and headers to
        :param fernetKey: the fernet string to encrypt the cookie with
        :return:
        """
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
            return self

    def isReadSuccessfully(self):
        """
        Check if all values of current cookie seem valid, and none empty
        :return:
        """
        valid = False
        if len(self.UA) > 0 and len(self.viewerID) > 0 and len(self.hostURL) > 0 and len(self.remoteAddress) > 0 and len(self.CSRF) > 0: valid = True
        return valid

    def originMatchesHost(self) -> bool:
        """
        Check if webpage request and websocket request origin from same place
        :return:
        """
        return self.hostURL == self.origin

    def __eq__(self, other: Cookie):
        """
        Check if 2 cookie objects are same
        :param other: the other cookie object to compare to
        :return:
        """
        return self.UA == other.UA and self.viewerID == other.viewerID and self.hostURL == other.hostURL and self.remoteAddress == other.remoteAddress and self.CSRF == other.CSRF

    def __str__(self):
        """
        Convert self to a json dumped string
        :return:
        """
        return Imports.dumps({"HOST_URL": self.hostURL, "REMOTE_ADDRESS": self.remoteAddress, "USER_AGENT": self.UA, "VIEWER_ID": self.viewerID, "ORIGIN": self.origin, "CSRF": self.CSRF})


class File:
    """
    Internal Structure for receiving parts of Files uploaded by Visitor and storing when required by the server
    """
    def __init__(self, viewer: BaseViewer):
        self.viewer = viewer
        self.isReady = False
        self.ID = ""
        self.fileName = ""
        self.fileType = ""
        self.fileSize = 0
        self.maxPartIndex = 0
        self.partsQueue = {}
        self.finalData = b""

    def acceptNewData(self, fileData:dict):
        newPartIndex = fileData["CURRENT"]
        data = Imports.b64decode(fileData["DATA"])
        self.partsQueue[newPartIndex] = data

    def getExtension(self):
        try:
            return self.fileName.split(".")[-1]
        except:
            return ""

    def save(self, location: str, fileName:str|None=None):
        nextpartIndex = 0
        while not self.isReady:
            if nextpartIndex in self.partsQueue:
                self.finalData += self.partsQueue.pop(nextpartIndex)
                nextpartIndex += 1
            else:
                if nextpartIndex > self.maxPartIndex:
                    if self.ID in self.viewer.pendingFiles: del self.viewer.pendingFiles[self.ID]
                    self.isReady = True
                    break
                else: Imports.sleep(1)


        if fileName: self.fileName = fileName
        open(f"{location}/{self.fileName}", "wb").write(self.finalData)
        self.partsQueue = {}
        self.finalData = b""


class BaseViewer:
    """
    Internal (BASE) Datastructure to hold all information regarding individual visitor
    """
    def __init__(self, _id: str, WSList: list, cookie: Cookie, turbo_app: ModifiedTurbo):
        self.__idleSender = True
        self.__turboIdle = True
        self.__activeCSRF: dict[str, dict[str, str]] = {}
        self.pendingFiles:dict[str, File] = {}
        self.turboApp = turbo_app
        self.turboApp.activeViewers.append(self)
        self.queueHandler = Imports.QueueManager()
        self.purposeToHidden = {}
        self.hiddenToPurpose = {}
        self.clientContentCache = {}
        self.viewerID = _id
        self.WSList = WSList
        self.cookie: Cookie = cookie

    def __startFlaskSender(self, stream, htmlData, divName) -> None:
        """
        Private method to start executing all pending actions for current visitor. Has to be called everytime there is a new action queued
        :return:
        """

        if self.isActive():
            try:
                self.turboApp.push(stream, to=self.viewerID)
                self.clientContentCache[divName] = htmlData
            except:
                pass

    def __cleanseForm(self, form: dict) -> dict | None:
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
            if "dynamicWebsiteUploadingFilesList" in form:
                fileData = form.pop("dynamicWebsiteUploadingFilesList")

                for formEntryName in fileData:
                    form[formEntryName] = []
                    for fileId in fileData[formEntryName]:
                        fileDetails = fileData[formEntryName][fileId]
                        fileObj = File(self)
                        fileObj.ID = fileId
                        fileObj.fileName = fileDetails.get("NAME", "")
                        fileObj.fileSize = fileDetails.get("SIZE", 0)
                        fileObj.fileType = fileDetails.get("TYPE", "")
                        fileObj.maxPartIndex = fileDetails.get("MAXPART", 0)
                        self.pendingFiles[fileId] = fileObj
                        form[formEntryName].append(fileObj)
            return form

    def __receiveFilePart(self, fileData: dict):
        """
        Upon form submit through websocket CSRF and other security parameters are checked and removed and returns a clean form dictionary with no extra parameters. Returns None if Securities don't match
        :param fileData: FilePart dictionary received from client
        :return:
        """
        if self.isActive():
            fileID = fileData["FILEID"]
            if fileID not in self.pendingFiles: return
            fileObj = self.pendingFiles[fileID]
            fileObj.acceptNewData(fileData)

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
            received = WSObj.receive(timeout=5)
            if received:
                if self.isActive():
                    dictReceived:dict = Imports.loads(received)
                    if dictReceived.get("ISFILE", False)==True and "CURRENT" in dictReceived and "FILEID" in dictReceived and "DATA" in dictReceived:
                        dictReceived.pop("ISFILE")
                        Imports.Thread(target=self.__receiveFilePart, args=(dictReceived,)).start()
                    else:
                        stripped = self.__cleanseForm(dictReceived)
                        if stripped is not None: return stripped
                else: raise Errors.ViewerDisconnected


    def queueTurboAction(self, htmlData: Imports.Any, divID: str, method: TurboMethods, nonBlockingWait: float = 0, removeAfter: float = 0, blockingWait: float = 0, newDivAttributes: dict|None = None) -> str|None:
        """
        Method to queue live update actions to be executed on current visitor. All actions get queued up and executed sequentially
        :param htmlData: The data to be sent to the client, can be of type str or bytes or any JSON serializable or an object with the __str__ method
        :param divID: The target div ID
        :param method: The kind of action to perform
        :param nonBlockingWait: Duration to wait before executing the action (doesn't block the calling function)
        :param removeAfter: Duration to wait before removing the div entirely. 0 means the div isn't supposed to be removed
        :param blockingWait: Duration to wait before executing the action (blocks the calling function)
        :param newDivAttributes: Extra attributes to pass into new div
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
                    divAttributes = ""
                    if newDivAttributes:
                        for key in newDivAttributes:
                            value = newDivAttributes[key]
                            divAttributes+=f' {key}=\"{value}\"'
                    self.queueTurboAction(f"""<div id='{divID}'{divAttributes}></div><div id='{readDivID}_create'></div>""", f'{readDivID}_create', self.turboApp.methods.replace, 0, 0)
                    break
            self.queueTurboAction(htmlData, divID, self.turboApp.methods.update, nonBlockingWait, removeAfter)

        elif method in [self.turboApp.methods.replace, self.turboApp.methods.replace.value]:
            self.queueHandler.queueAction(self.__startFlaskSender, 0, False, None, None, None, self.turboApp.replace(htmlData, divID), htmlData, divID)

        elif method in [self.turboApp.methods.remove, self.turboApp.methods.remove.value]:
            self.queueHandler.queueAction(self.__startFlaskSender, 0, False, None, None, None, self.turboApp.remove(divID), "", divID)

        elif method in [self.turboApp.methods.update, self.turboApp.methods.update.value]:
            if divID not in self.clientContentCache or self.clientContentCache[divID] != htmlData:
                self.queueHandler.queueAction(self.__startFlaskSender, 0, False, None, None, None, self.turboApp.update(htmlData, divID), htmlData, divID)
            if removeAfter: self.queueTurboAction("", divID, self.turboApp.methods.remove, removeAfter, 0, removeAfter)

        return divID

class ModifiedTurbo(Imports.Turbo):
    """
    Derived TurboFlask's class with extra functionalities and methods
    """
    def __init__(self, baseApp:Imports.Flask=None, route='', visitorLeftCallback=None):
        self.__route = route
        self.__pendingHandshakes ={}
        self.__WSWaitViewerIDs: list[str] = []
        self.baseApp = baseApp
        self.visitorLeftCallback = visitorLeftCallback
        self.activeViewers: list[BaseViewer] = []
        self.methods = TurboMethods
        super().__init__()
        self.sock = Imports.Sock()

    def initSock(self):
        """
        Initialise sock blueprint and context w.r.t. Websocket
        :return:
        """
        self.baseApp.config.setdefault('TURBO_WEBSOCKET_ROUTE', None)
        self.sock.init_app(self.baseApp)
        self.baseApp.context_processor(self.context_processor)

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

    def generateHandshake(self, viewerObj:BaseViewer) -> str:
        """
        Check if viewer ID has pending websocket connection to be made, if so remove from pending and assign the websocket to the viewer
        :param viewerObj: Visitor who owns the handshake
        :return:
        """
        def freeHandshake(handshake):
            Imports.sleep(20)
            if handshake in self.__pendingHandshakes:
                del self.__pendingHandshakes[handshake]

        while True:  # while needed
            handshake = Imports.StringGen().AlphaNumeric(100, 200)
            if handshake not in self.__pendingHandshakes:
                self.__pendingHandshakes[handshake] = viewerObj
                Imports.Thread(target=freeHandshake, args=(handshake,)).start()
                return handshake

    def consumeHandshake(self, handshake:str) -> BaseViewer|None:
        """
        Check if viewer ID has pending websocket connection to be made, if so remove from pending and assign the websocket to the viewer
        :param handshake: Handshake string to return visitor for
        :return:
        """
        try: return self.__pendingHandshakes.pop(handshake)
        except: return None


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


def createApps(formCallback, newVisitorCallback, visitorLeftCallback, appName:str= "Live App", homeRoute:str= "/", WSRoute:str= "/ws", fernetKey:str=Imports.Fernet.generate_key(), extraHeads:str= "", bodyBase:str= "", title:str= "Live", resetOnDisconnect:bool=True):
    baseApp = Imports.Flask(appName)
    turboApp = ModifiedTurbo(baseApp, WSRoute, visitorLeftCallback)

    @baseApp.route(homeRoute, methods=['GET'])
    def _root_url():
        """
        Executed for every viewer that opens the webpage. Checks and generates cookie if needed then sends the base page.
        :return:
        """
        cookieObjRequest = Cookie().readRequest(Imports.request)
        cookieObj = Cookie().decrypt(Imports.request.cookies, fernetKey)
        if (not cookieObj.isReadSuccessfully()) or cookieObj.remoteAddress!=cookieObjRequest.remoteAddress or cookieObj.UA!=cookieObjRequest.UA or cookieObj.hostURL!=cookieObjRequest.hostURL:
            cookieObj = Cookie().readRequest(Imports.request)
            cookieObj.viewerID = turboApp.generateViewerID()
        else:
            turboApp.checkAndWSBlockViewerID(cookieObj.viewerID)
        viewerObj = BaseViewer(cookieObj.viewerID, [], cookieObj, turboApp)
        handshake = turboApp.generateHandshake(viewerObj)
        cookieObj.CSRF = handshake
        return cookieObj.attachToResponse(Imports.make_response(Imports.render_template_string(Extras.baseHTML(handshake, turboApp.turbo(), extraHeads, WSRoute, title, resetOnDisconnect, bodyBase))), fernetKey)


    @turboApp.sock.route(WSRoute)
    def _turbo_stream(WSObj):
        """
        Executed for every websocket connection request received. Handles initial handshake token exchange along with all future communication
        :param WSObj: The Sock object that will be used for communication
        :return:
        """
        cookieObjRequest = Cookie().readRequest(Imports.request)
        cookieObj = Cookie().decrypt(Imports.request.cookies, fernetKey)
        if cookieObj.isReadSuccessfully() and cookieObjRequest.originMatchesHost() and cookieObj.remoteAddress==cookieObjRequest.remoteAddress and  cookieObj.UA==cookieObjRequest.UA and  cookieObj.hostURL==cookieObjRequest.hostURL:
            if not cookieObj.isReadSuccessfully() or not turboApp.consumeWSBlockedViewerID(cookieObj.viewerID): return
            for handshakeWaitTimer in range(2):
                try:
                    handshake = WSObj.receive(timeout=5)
                    if handshake is not None:
                        viewerObj = turboApp.consumeHandshake(handshake)
                        if viewerObj is None: return WSObj.close()
                        else: break
                except: return
            else: return
            turboApp.clients[cookieObj.viewerID] = [WSObj]
            viewerObj.WSList = [WSObj]
            Imports.Thread(target=newVisitorCallback, args=(viewerObj,)).start()
            while True:
                try:
                    received = viewerObj.turboReceive(WSObj)
                    if received is not None: Imports.Thread(target=formCallback, args=(viewerObj, received,)).start()
                except:
                    Imports.Thread(target=turboApp.visitorLeftCallback, args=(viewerObj,)).start()
                    turboApp.clients.pop(cookieObj.viewerID)
                    turboApp.activeViewers.remove(viewerObj)
                    return


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


    turboApp.initSock()
    return baseApp, turboApp
