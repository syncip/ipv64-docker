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
        
def discord(url=None, message=None):
    if url != None:
        try:
            re = requests.post(url,
            data = {                 
		    "content": message,     # Den Content geben wir der Funktion mit...
		    "username": "ipv64 updater notification"    # ... und den Username haben wir eh schon hinterlegt... ;-)
	        })
        except:
            pass