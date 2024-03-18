import requests
 
def ntfy(url=None, message=None, tag=None):
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