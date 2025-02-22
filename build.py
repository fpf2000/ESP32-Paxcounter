# build.py
# pre-build script, setting up build environment

import sys
import os
import os.path
import requests
from os.path import basename
from platformio import util

Import("env")

# get platformio environment variables
project_config = util.load_project_config()

# get platformio source path
srcdir = env.get("PROJECTSRC_DIR")

# check if lmic config file is present in source directory
lmicconfig = project_config.get("common", "lmicconfigfile")
lmicconfigfile = os.path.join (srcdir, lmicconfig)
if os.path.isfile(lmicconfigfile) and os.access(lmicconfigfile, os.R_OK):
    print "Parsing LMIC configuration from " + lmicconfigfile
else:
    sys.exit("Missing file " + lmicconfigfile + ", please create it! Aborting.")

# check if lora key file is present in source directory
lorakeyfile = os.path.join (srcdir, project_config.get("common", "lorakeyfile"))
if os.path.isfile(lorakeyfile) and os.access(lorakeyfile, os.R_OK):
    print "Parsing LORAWAN keys from " + lorakeyfile
else:
    sys.exit("Missing file " + lorakeyfile + ", please create it! Aborting.")

# check if ota key file is present in source directory
otakeyfile = os.path.join (srcdir, project_config.get("common", "otakeyfile"))
if os.path.isfile(otakeyfile) and os.access(otakeyfile, os.R_OK):
    print "Parsing OTA keys from " + otakeyfile
else:
    sys.exit("Missing file " + otakeyfile + ", please create it! Aborting.")

# parse ota key file
mykeys = {}
with open(otakeyfile) as myfile:
    for line in myfile:
        key, value = line.partition("=")[::2]
        mykeys[key.strip()] = str(value).strip()

# get bintray user credentials from ota key file
user = mykeys["BINTRAY_USER"]
repository = mykeys["BINTRAY_REPO"]
apitoken = mykeys["BINTRAY_API_TOKEN"]

# get bintray upload parameters from platformio environment
version = project_config.get("common", "release_version")
package = str(env.get("PIOENV"))

# put bintray user credentials to platformio environment
env.Replace(BINTRAY_USER=user)
env.Replace(BINTRAY_REPO=repository)
env.Replace(BINTRAY_API_TOKEN=apitoken)

# get runtime credentials and put them to compiler directive
env.Append(BUILD_FLAGS=[
    u'-DWIFI_SSID=\\"' + mykeys["OTA_WIFI_SSID"] + '\\"', 
    u'-DWIFI_PASS=\\"' + mykeys["OTA_WIFI_PASS"] + '\\"', 
    u'-DBINTRAY_USER=\\"' + mykeys["BINTRAY_USER"] + '\\"', 
    u'-DBINTRAY_REPO=\\"' + mykeys["BINTRAY_REPO"] + '\\"', 
    u'-DBINTRAY_PACKAGE=\\"$PIOENV\\"',
    u'-DARDUINO_LMIC_PROJECT_CONFIG_H=' + lmicconfig,
    u'-I \"' + srcdir + '\"'
    ])

# function for pushing new firmware to bintray storage using API
def publish_bintray(source, target, env):
    firmware_path = str(source[0])
    firmware_name = basename(firmware_path)
    url = "/".join([
        "https://api.bintray.com", "content",
        user, repository, package, version, firmware_name
    ])

    print("Uploading {0} to Bintray. Version: {1}".format(
        firmware_name, version))
    print(url)

    headers = {
        "Content-type": "application/octet-stream",
        "X-Bintray-Publish": "1",
        "X-Bintray-Override": "1"
    }

    r = None
    
    try:
        r = requests.put(url,
                         data=open(firmware_path, "rb"),
                         headers=headers,
                         auth=(user,apitoken))
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        sys.stderr.write("Failed to submit package: %s\n" %
                         ("%s\n%s" % (r.status_code, r.text) if r else str(e)))
        env.Exit(1)

    print("The firmware has been successfuly published at Bintray.com!")

# put build file name and upload command to platformio environment
env.Replace(
    PROGNAME="firmware_" + package + "_v%s" % version,
    UPLOADCMD=publish_bintray)