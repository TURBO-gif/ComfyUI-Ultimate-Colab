from datetime import datetime


def log(message):

    print(
        f"[{datetime.now()}] {message}"
    )
