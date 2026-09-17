"""Constants for the Baicells SMS integration."""

DOMAIN = "baicells_sms"

CONF_DEVICE_PATH = "device_path"
CONF_POLL_INTERVAL = "poll_interval"
CONF_DELETE_AFTER_READ = "delete_after_read"
CONF_STRICT_HOST_KEY = "strict_host_key"
CONF_COMMAND_TIMEOUT = "command_timeout"
CONF_LOGO_PATH = "logo_path"
CONF_MAX_ATTR_MESSAGES = "max_attribute_messages"

DEFAULT_NAME = "Baicells SMS"
DEFAULT_PORT = 27149
DEFAULT_DEVICE_PATH = "/dev/ttyUSB1"
DEFAULT_POLL_INTERVAL = 300
DEFAULT_DELETE_AFTER_READ = True
DEFAULT_STRICT_HOST_KEY = False
DEFAULT_COMMAND_TIMEOUT = 30
DEFAULT_LOGO_PATH = "/local/baicells_sms/logo.png"
# Home Assistant's recorder refuses to store state attributes larger than
# 16384 bytes. Exposing the entire, ever-growing SMS history as a state
# attribute eventually exceeds that limit (attributes then simply aren't
# recorded), so only a bounded number of the most recent messages are
# exposed here by default. The full history is always available on disk
# in the JSON history file regardless of this setting.
DEFAULT_MAX_ATTR_MESSAGES = 25

PLATFORMS = ["sensor", "button"]

SERVICE_FORCE_READ = "force_read"
