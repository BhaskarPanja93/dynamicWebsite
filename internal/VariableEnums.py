from enum import Enum


class DivNames(Enum):
    time = "time"
    mainDiv = "maindiv"
    tasks = "tasks"


class Constants(Enum):
    appName = "Plan Ahead"
    templatesFolderName = "templates"


class Secrets(Enum):
    fernetKey = b'GNwHvssnLQVKYPZk0D_Amy9m3EeSvi6Y1FiHfTO8F48=' #Fernet.generate_key()


class Routes(Enum):
    homeRoute = "/pa"
    wsRoute = f"{homeRoute}_ws"
