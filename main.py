from gevent import monkey

monkey.patch_all()

from gevent.pywsgi import WSGIServer
from internal.apps import *


def process_form(viewerObj: BaseViewer, form: dict):
    if form is not None:
        print(viewerObj.viewerID, form)
    else:
        print("Disconnected: ", viewerObj.viewerID)


def newVisitor(viewerObj: BaseViewer):
    print("New Viewer: ", viewerObj.viewerID)
    HTMLtoSend = "helo"
    viewerObj.queueTurboAction(HTMLtoSend, "mainDiv", viewerObj.turboApp.methods.update)


fernetKey = 'GNwHvssnLQVKYPZk0D_Amy9m3EeSvi6Y1FiHfTO8F48='
appName = "Dynamic Website"
homePageRoute = "/demo"
WSRoute = f"{homePageRoute}_ws"
purposes = ["login", "register"]
extraHeads = """ """
baseApp, turboApp = createApps(process_form, newVisitor, appName, homePageRoute, WSRoute, fernetKey, purposes, extraHeads)

print(f"http://127.0.0.1:49000{homePageRoute}")
WSGIServer(('0.0.0.0', 49000,), baseApp, log=None).serve_forever()
