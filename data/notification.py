import requests
 
def ntfy(url, message, tag):
    if url != None:
        try:
            re = requests.post(url,
            data=message,
            headers={
                "Title": "ipv64 updater notification",
                "Priority": "3",
                "Tags": tag
            })
        except:
            pass