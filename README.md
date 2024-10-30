# dynamicWebsite v1.4.3

```pip install dynamicWebsite --upgrade```

###### <br>A simple way to host web server bundled with websocket to send and receive live data, from client to server, and pass live HTML changes from server to client without having to refresh the page."

<br>To install: 
```
pip install dynamicWebsite --upgrade
pip3 install dynamicWebsite --upgrade
python -m pip install dynamicWebsite --upgrade
python3 -m pip install dynamicWebsite --upgrade
```


#### <br><br>Using this program is as simple as:
```

from dynamicWebsite import *


def process_form(viewerObj: BaseViewer, form: dict):
    if form.get("PURPOSE") == "SHOW_IMAGE1":
        initial = f'''<img src="" alt="IMG1"></img>'''
        viewerObj.queueTurboAction(initial, "mainDiv", turboApp.methods.update)
    elif form.get("PURPOSE") == "SHOW_IMAGE2":
        initial = f'''<img src="" alt="IMG2"></img>'''
        viewerObj.queueTurboAction(initial, "mainDiv", turboApp.methods.update)



def newVisitor(viewerObj: BaseViewer):
    initial = f'''
               <form onsubmit="return submit_ws(this)">
               {viewerObj.addCSRF("SHOW_IMAGE1")}
                   <input type="text" name="username"><br>
                   <input type="password" name="password"><br>
                   <input type="file" name="ball" multiple><br>
                   <button type="submit">Search</button>
               </form>
               '''
    viewerObj.queueTurboAction(initial, "mainDiv", turboApp.methods.update)


def visitorLeft(viewerObj: BaseViewer):
    print(f"Visitor Left: {viewerObj.viewerID}")


extraHeads = ""
fernetKey = 'JJafcmKx6WRzZKhC8THl7tfXce2BVdYEntGHPJNFwSU='
bodyBase = """<body><div id="mainDiv"></div></body>"""
title = "Song Player"
resetOnDisconnect = False
baseApp, turboApp = createApps(process_form, newVisitor, visitorLeft, "Song Player", "/", fernetKey, extraHeads, bodyBase, title, resetOnDisconnect)

baseApp.run("0.0.0.0", 5000)

```


### Future implementations:
* Adding ability to add classes and other HTML arguments to elements created
* Adding templates for various uses


###### <br>This project is always open to suggestions and feature requests.
