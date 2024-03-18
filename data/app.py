#!/usr/bin/env pytho

import requests
import dns.resolver
import ping3
import os
import logging

# Scripte
import notification

# LOGGING SETTINGS
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S', level=logging.INFO)
#logging.basicConfig( filename='/var/log/ipv64.log')

# SYSTEM ENVIRONMENT VARIABLES
try:
    token = os.environ['TOKEN']
except:
    token = None
try:
    domain = os.environ['DOMAIN']
except:
    domain = None
try:
    domain_prefix = os.environ['PREFIX']
except:
    domain_prefix = None
try:
    record_type = os.environ['RECORD_TYPE']
except:
    record_type = "A"
try:
    script_version = os.environ['SCRIPT_VERSION']
except:
    script_version = None
try:
    check_ip = os.environ['CHECK_IP']
except:
    check_ip = True

# NOTIFICATIONS ENVIRONMENT VARIABLES
try:
    ntfy = os.environ['NTFY']
except:
    ntfy = None
try:
    discord = os.environ['DISCORD']
except:
    discord = None


if token == None or domain == None or record_type == None:
    logging.warning(f"Environment Variables missing. Exit Script.")
    exit()

# SCRIPT SETTINGS, DO NOT CHANGE BY USER
ipv64_nameservers_ipv4 = ["159.69.110.93","167.235.231.182"]
ipv64_nameserver_ipv6 = ["2a01:4f8:1c1e:a6a8::1", "2a01:4f8:c010:b4fc::1"]
ipv64_api_url = "https://ipv64.net/nic/update"
current_ipv4_check = ["https://ipv4.ipapi.de", "https://ipv4.icanhazip.com"]
current_ipv6_check = ["https://ipv6.ipapi.de", "https://ipv6.icanhazip.com"]
headers = {"User-Agent": "ipv64-updater " + script_version}
timeout = 10

# ======================================
# prüfe ob ipv64 per ipv4 erreichbar ist
# ======================================
def check_ipv64_status_ipv4():
    # Check for nameserver
    nameserver_ipv4 = 0
    api_ipv64 = 0
    for ip in ipv64_nameservers_ipv4:
        response = ping3.ping(ip, timeout=timeout)
    
        if response is not None:
            logging.debug(f"IPv64 Nameserver {ip} is reachable.")
            nameserver_ipv4 += 1
            break
        else:
            logging.warning(f"IPv64 Nameserver {ip} is not reachable. Trying next one.")
            
    #check for api
    response_api = ping3.ping(ipv64_api_url, timeout=timeout)
    if response_api is not None:
        logging.debug(f"IPv64 API is reachable.")
        api_ipv64 += 1
    else:
        logging.warning(f"IPv64 API is not reachable.")

    if nameserver_ipv4 > 0 and api_ipv64 > 0:
        logging.debug(f"All IPv64 services are reachable.")
        return True
    else:
        logging.warning(f"IPv64 services not reachable. Exit Script.")
        exit()


# ======================================
# prüfe ob ipv64 per ipv6 erreichbar ist
# ======================================
def check_ipv64_status_ipv6():
    nameserver_ipv6 = 0
    api_ipv64 = 0
    for ip in ipv64_nameserver_ipv6:
        response = ping3.ping(ip, timeout=10)
    
        if response is not None:
            logging.debug(f"IPv64 Nameserver {ip} is reachable.")
            nameserver_ipv6 += 1
            break
        else:
            logging.warning(f"IPv64 Nameserver {ip} is not reachable. Trying next one.")
            
    #check for api
    response_api = ping3.ping(ipv64_api_url, timeout=timeout)
    if response_api is not None:
        logging.debug(f"IPv64 API is reachable.")
        api_ipv64 += 1
    else:
        logging.warning(f"IPv64 API is not reachable.")

    if nameserver_ipv6 > 0 and api_ipv64 > 0:
        logging.debug(f"All IPv64 services are reachable.")
        return True
    else:
        logging.warning(f"IPv64 services offline. Exit Script.")
        exit()

# ======================================
# get current ipv4
# ======================================
def current_ipv4():
    # current ip preset
    current_ipv4 = None

    for domain in current_ipv4_check:
        try:
            re = requests.get(domain,headers=headers, timeout=timeout)
        except:
            logging.warning(f"Failed to check your IPv4. Exit Script.")
            exit()
        
        if re.status_code == 200:
            current_ipv4 = re.text.replace("\n", "")
        
        # Loop beenden, wenn IP gefunden wurde
        if current_ipv4 != None:
            logging.debug(f"Current IPv4: {current_ipv4}")
            break
        else:
            logging.warning(f"No IPv4 found.")
            
    return current_ipv4

# ======================================
# get current ipv6
# ======================================
def current_ipv6():
    # current ip preset
    current_ipv6 = None

    # get current ipv6
    for domain in current_ipv6_check:
        try:
            re = requests.get(domain,headers=headers, timeout=timeout)
        except:
            logging.warning(f"Failed to check your IPv6. Exit Script.")
            exit()
        
        if re.status_code == 200:
            current_ipv6 = re.text.replace("\n", "")
        
        # Loop beenden, wenn IP gefunden wurde
        if current_ipv6 != None:
            logging.debug(f"Current IPv6: {current_ipv6}")
            break
        else:
            logging.warning(f"No IPv6 found.")
            
    return current_ipv6

# ======================================
# prüfe welcher A Record gesetzt ist
# ======================================
def check_ipv64_nameserver_ipv4(domain, prefix=None):
    ipv64_response = []
    
    if prefix is not None:
        domain = prefix + "." + domain
    
    try:
        my_resolver = dns.resolver.Resolver()
        my_resolver.nameservers = ipv64_nameservers_ipv4
        
        answer = my_resolver.resolve(domain, "A", search=True, raise_on_no_answer=False)
    except:
        logging.warning(f"Error while nameserver request. Exit Script.")
        exit()
    
    if len(answer) > 0:
        for val in answer:
            ipv64_response.append(val.to_text())
        logging.debug(f"DNS record for {domain} found: {ipv64_response}")
    else:
        logging.warning(f"No DNS record found. Exit Script.")
        ipv64_response = None
        exit()
        
    return ipv64_response

# ======================================
# prüfe welcher AAAA Record gesetzt ist
# ======================================
def check_ipv64_nameserver_ipv6(domain, prefix=None):
    ipv64_response = []
    
    if prefix is not None:
        domain = prefix + "." + domain
    
    try:
        my_resolver = dns.resolver.Resolver()
        my_resolver.nameservers = ipv64_nameservers_ipv4
        
        answer = my_resolver.resolve(domain, "AAAA", search=True, raise_on_no_answer=False)
    except:
        logging.warning(f"Error while nameserver request. Exit Script.")
        exit()
    
    if len(answer) > 0:
        for val in answer:
            ipv64_response.append(val.to_text())
        logging.debug(f"DNS record {domain} found: {ipv64_response}")
    else:
        logging.warning(f"No DNS record found. Exit Script.")
        ipv64_response = None
        exit()
        
    return ipv64_response


# ======================================
# ipv64 API
# ======================================
def ipv64_api(current_ip, set_ip, update_token, domain, prefix):
    status = None
    if current_ip not in set_ip:
        if prefix is None:
            try:
                re = requests.post(ipv64_api_url + "?key=" + update_token + "&domain=" + domain + "&ip=" + current_ip)
            except:
                logging.warning(f"API not correct responding.")
        else:
            try:
                re = requests.post(ipv64_api_url + "?key=" + update_token + "&domain=" + domain + "&praefix=" + prefix + "&ip=" + current_ip)
            except:
                logging.warning(f"API not correct responding.")
            
        if re.status_code < 400:
            logging.info(f"{domain} (prefix: {prefix}) update successful (old: {set_ip}, new: {current_ip})")
            
            # Send notification if variable url is set
            notification.ntfy(ntfy, f"{domain} (prefix: {prefix}) Record Update successful (old: {set_ip}, new: {current_ip})", "green_circle")
            notification.discord(discord, f":green_circle: {domain} (prefix: {prefix}) Record Update successful (old: {set_ip}, new: {current_ip})")
        else:
            logging.warning(f"{domain} (prefix: {prefix}) Update NOT successful.")
            
            # Send notification if variable url is set
            notification.ntfy(ntfy, f"{domain} (prefix: {prefix}) Record Update not successful (old: {set_ip}, new: {current_ip})", "red_circle")
            notification.discord(discord, f":red_circle: {domain} (prefix: {prefix}) Record Update not successful (old: {set_ip}, new: {current_ip})")
    else:
        logging.info(f"No record update needed for {domain} (prefix: {prefix})")



# ======================================
# MAIN SCRIPT
# ======================================
        
if record_type.upper() == "A":
    check_ipv64_status_ipv4()
    if check_ip == True:
        current_ip = current_ipv4()
    else:
        current_ip = None
    set_ip = check_ipv64_nameserver_ipv4(domain, domain_prefix)
    ipv64_api(current_ip, set_ip, token, domain, domain_prefix)

elif record_type.upper() == "AAAA":
    check_ipv64_status_ipv6()
    if check_ip == True:
        current_ip = current_ipv6()
    else:
        current_ip = None
    set_ip = check_ipv64_nameserver_ipv6(domain, domain_prefix)
    ipv64_api(current_ip, set_ip, token, domain, domain_prefix)

else:
    logging.warning(f"Unknown record type {record_type}.")