# dynamicWebsite v1.0.3

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

def process_form(viewerObj: BaseViewer, form: dict):
    if form is not None:
        print(f"[{viewerObj.viewerID}] sent: ", form)
    else:
        print("Disconnected: ", viewerObj.viewerID)

def newVisitor(viewerObj: BaseViewer):
    initial = f"""
    <h2>Submit Song Name</h2>
    <div id="searchform" class="container"></div>
    <div id="audioplayer" class="container"></div>    
    <div id="status_create"></div>
    <div id="debug" class="container"></div>
    """
    viewerObj.queueTurboAction(initial, "mainDiv", viewerObj.turboApp.methods.update)
    sendForm(viewerObj)

extraHeads = ""
fernetKey = 'GNwHvssnLQVKYPZk0D_Amy9m3EeSvi6Y1FiHfTO8F48='
appName = "Song Player"
homePageRoute = "/song"
WSRoute = f"/song_ws"
title = "Song Player"
resetOnDisconnect = False
baseApp, turboApp = createApps(process_form, newVisitor, appName, homePageRoute, WSRoute, fernetKey, extraHeads, title, resetOnDisconnect)

turboApp.run("0.0.0.0", 5000)
```


### Future implementations:
* Adding ability to add classes and other HTML arguments to elements created
* Adding templates for various uses


###### <br>This project is always open to suggestions and feature requests.
