from gevent import monkey
monkey.patch_all()

from gevent.pywsgi import WSGIServer
from internal.apps import *


def process_form(viewerObj:BaseViewer, form:dict):
    print(viewerObj.viewerID, form)

def newVisitor(viewerObj:BaseViewer):
    print("New Viewer: ", viewerObj.viewerID)
    HTMLtoSend = ""
    viewerObj.queueTurboAction(HTMLtoSend, "mainDiv", viewerObj.turboApp.methods.update)


baseApp, turboApp = createApps(process_form, newVisitor, "Dynamic Website", "/", "/ws", 'GNwHvssnLQVKYPZk0D_Amy9m3EeSvi6Y1FiHfTO8F48=', ["login", "register"], "")


print(f"http://127.0.0.1:49000")
WSGIServer(('0.0.0.0', 49000,), baseApp, log=None).serve_forever()
