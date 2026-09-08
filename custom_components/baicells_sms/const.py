"""Constants for the Baicells SMS integration."""

DOMAIN = "baicells_sms"

CONF_DEVICE_PATH = "device_path"
CONF_POLL_INTERVAL = "poll_interval"
CONF_DELETE_AFTER_READ = "delete_after_read"
CONF_STRICT_HOST_KEY = "strict_host_key"
CONF_COMMAND_TIMEOUT = "command_timeout"
CONF_LOGO_PATH = "logo_path"

DEFAULT_NAME = "Baicells SMS"
DEFAULT_PORT = 27149
DEFAULT_DEVICE_PATH = "/dev/ttyUSB1"
DEFAULT_POLL_INTERVAL = 300
DEFAULT_DELETE_AFTER_READ = True
DEFAULT_STRICT_HOST_KEY = False
DEFAULT_COMMAND_TIMEOUT = 30
DEFAULT_LOGO_PATH = "/local/baicells_sms/logo.png"

PLATFORMS = ["sensor", "button"]

SERVICE_FORCE_READ = "force_read"
