"""Constants extracted from the Winix Smart APK."""

# AWS Cognito credentials (from Winix Home v1.0.8 APK)
COGNITO_APP_CLIENT_ID = "14og512b9u20b8vrdm55d8empi"
COGNITO_CLIENT_SECRET_KEY = "k554d4pvgf2n0chbhgtmbe4q0ul4a9flp3pcl6a47ch6rripvvr"
COGNITO_USER_POOL_ID = "us-east-1_Ofd50EosD"
COGNITO_REGION = "us-east-1"

# AES-256-CBC encryption (from Winix Smart v1.5.6 APK native library libnative-lib.so)
AES_KEY = bytes.fromhex("84be38f854e320dd4a0a8c7fe0f3a9b84c288445916933fc222465bbd5a518d0")
AES_IV = bytes.fromhex("dfd55f316e72e97b905f8739005c99a7")

# Android device spoofing
MOBILE_APP_VERSION = "1.5.6"
MOBILE_MODEL = "SM-G988B"
MOBILE_OS_TYPE = "android"
MOBILE_OS_VERSION = "29"
MOBILE_LANG = "en"

# Mobile API endpoints (encrypted)
URL_REGISTER_USER = "https://us.mobile.winix-iot.com/registerUser"
URL_CHECK_ACCESS_TOKEN = "https://us.mobile.winix-iot.com/checkAccessToken"
URL_GET_DEVICE_INFO_LIST = "https://us.mobile.winix-iot.com/getDeviceInfoList"

# Device IoT API endpoints (unencrypted, unauthenticated)
URL_DEVICE_STATUS = "https://us.api.winix-iot.com/common/event/sttus/devices/{device_id}"
URL_DEVICE_CONTROL = (
    "https://us.api.winix-iot.com/common/control/devices/{device_id}" "/A211/{attribute}:{value}"
)

# UUID generation prefix for CRC32
UUID_PREFIX = b"github.com/regaw-leinad/winix-purifiers"
UUID_SUFFIX = b"HGF"

# Token management
TOKEN_EXPIRY_BUFFER_SECONDS = 600  # 10 minutes

# Filter
MAX_FILTER_HOURS = 6480
