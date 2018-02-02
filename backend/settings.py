import json

json_settings_fh = open("../settings.json")
json_settings = json.load(json_settings_fh)
json_settings_fh.close()

google_key = json_settings["googleKey"]
google_secret = json_settings["googleSecret"]
redirect_uri = json_settings["redirectUri"]

elixir = json_settings["elixir"]

## Generated with base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
cookie_secret = json_settings["cookieSecret"]

# MySql settings
mysql_host = json_settings["mysqlHost"]
mysql_schema = json_settings["mysqlSchema"]
mysql_user = json_settings["mysqlUser"]
mysql_passwd = json_settings["mysqlPasswd"]
mysql_port = json_settings["mysqlPort"]

# Mongodb settings
mongo_host = json_settings["mongoHost"]
mongo_port = json_settings["mongoPort"]
mongo_user = json_settings["mongoUser"]
mongo_password = json_settings["mongoPassword"]

# e-mail config
mail_server = json_settings["mailServer"]
from_address = json_settings["fromAddress"]
reply_to_address = json_settings["replyToAddress"]
