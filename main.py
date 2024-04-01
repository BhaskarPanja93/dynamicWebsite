from gevent import monkey
monkey.patch_all()

from gevent.pywsgi import WSGIServer
from flask import Flask, make_response, render_template

from internal.VariableEnums import *
from internal.classes import *
from customisedLogs import Manager as LogManager

activeViewers:list[BaseViewer] = []

baseApp = Flask(Constants.appName.value, template_folder=Constants.templatesFolderName.value)
turboApp = ModifiedTurbo(baseApp, Routes.wsRoute.value)
logger = LogManager()


def process_form(viewerObj:BaseViewer, form:dict):
    if not viewerObj or not viewerObj.isActive():
        print(f"PLAYER OFFLINE")
        return
    print(form)
    _purpose:str = form["PURPOSE"]
    generalPurpose, token = _purpose.split(".")

    if generalPurpose == viewerObj.formPurposes.register.value:
        if "PURPOSE" not in form or "CSRF" not in form:
            print("PURPOSE CSRF not in form")
            return
        if not form["CSRF"] or form["CSRF"] != viewerObj.useCSRF(generalPurpose, token):
            print("invalid PURPOSE or CSRF")
            return
        userName = form.get("username")
        password = form.get("password")
        viewerObj.username = userName


@turboApp.sock.route(turboApp.route)
def _turbo_stream(WSObj):
    cookieObjRequest = Cookie().readRequest(request)
    cookieObj = Cookie().decrypt(request.cookies, Secrets.fernetKey.value)
    if cookieObjRequest.isValid and cookieObj == (Cookie().decrypt(request.cookies, Secrets.fernetKey.value)):
        if not cookieObj.checkValid() or cookieObj.viewerID not in turboApp.WSWaitViewerIDs: return
        viewerObj = BaseViewer(turboApp)
        turboApp.clients[cookieObj.viewerID] = [WSObj]
        viewerObj.WSList = [WSObj]
        turboApp.WSWaitViewerIDs.remove(cookieObj.viewerID)
        viewerObj.viewerID = cookieObj.viewerID
        viewerObj.cookieObj = cookieObj

        activeViewers.append(viewerObj)
        while True: # while needed
            try:
                received = WSObj.receive(timeout=10)
                if viewerObj.isActive():
                    if received:
                        Thread(target=process_form, args=(viewerObj, loads(received))).start()
                else:
                    raise Error.ViewerDisconnected
            except:
                break
        if viewerObj in activeViewers: activeViewers.remove(viewerObj)


@baseApp.route(Routes.homeRoute.value, methods=['GET'])
def _root_url():
    cookieObj = Cookie().decrypt(request.cookies, Secrets.fernetKey.value)
    if not cookieObj.checkValid():
        cookieObj = Cookie().readRequest(request)
        viewerID = turboApp.generateViewerID()
        cookieObj.viewerID = viewerID
        cookieObj.delim = StringGen().AlphaNumeric(20,20)
    else: turboApp.checkAndWSBlockViewerID(cookieObj.viewerID)
    response = make_response(render_template("main.html"))
    return cookieObj.attachToResponse(response, Secrets.fernetKey.value)


@baseApp.before_request
def userBeforeRequest():
    """
    Before any request goes to any route, it passes through this function.
    Applies user remote address correctly (received from proxy)
    :return:
    """
    address = "BANNED"
    if request.remote_addr == "127.0.0.1":
        if request.environ.get("HTTP_X_FORWARDED_FOR") == request.headers.get("X-Forwarded-For"):
            if request.environ.get("HTTP_X_FORWARDED_FOR") is not None:
                address = request.environ.get("HTTP_X_FORWARDED_FOR")
            else:
                address = "LOCAL"
    else:
        address = request.remote_addr
    request.remote_addr = address

print(f"http://127.0.0.1:49000{Routes.homeRoute.value}")
#baseApp.run("0.0.0.0", 49000)
WSGIServer(('0.0.0.0', 49000,), baseApp, log=None).serve_forever()
