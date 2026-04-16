"""Constants extracted from the Winix Smart APK."""

# AWS Cognito credentials (from Winix Smart v1.5.7 APK).
# Winix rotated the app client on 2026-04-16 and moved to a public (secretless) client.
COGNITO_APP_CLIENT_ID = "5rjk59c5tt7k9g8gpj0vd2qfg9"
COGNITO_USER_POOL_ID = "us-east-1_Ofd50EosD"
COGNITO_REGION = "us-east-1"

# Cognito Identity Pool (from AWSAbstractCognitoIdentityProvider.java in v1.5.7 APK).
# Resolved per user at session establishment; required in mobile API payloads and
# device control URLs as of v1.5.7.
COGNITO_IDENTITY_POOL_ID = "us-east-1:84008e15-d6af-4698-8646-66d05c1abe8b"

# AES-256-CBC encryption (from Winix Smart v1.5.6 APK native library libnative-lib.so)
AES_KEY = bytes.fromhex("84be38f854e320dd4a0a8c7fe0f3a9b84c288445916933fc222465bbd5a518d0")
AES_IV = bytes.fromhex("dfd55f316e72e97b905f8739005c99a7")

# Android device spoofing
MOBILE_APP_VERSION = "1.5.7"
MOBILE_MODEL = "SM-G988B"
MOBILE_OS_TYPE = "android"
MOBILE_OS_VERSION = "29"
MOBILE_LANG = "en"

# Mobile API endpoints (encrypted)
URL_REGISTER_USER = "https://us.mobile.winix-iot.com/registerUser"
URL_INIT = "https://us.mobile.winix-iot.com/init"
URL_CHECK_ACCESS_TOKEN = "https://us.mobile.winix-iot.com/checkAccessToken"
URL_GET_DEVICE_INFO_LIST = "https://us.mobile.winix-iot.com/getDeviceInfoList"

# Device IoT API endpoints (unencrypted, unauthenticated).
# Control URL requires the user's Cognito identityId as of v1.5.7 (replaces hardcoded A211 segment).
URL_DEVICE_STATUS = "https://us.api.winix-iot.com/common/event/sttus/devices/{device_id}"
URL_DEVICE_CONTROL = (
    "https://us.api.winix-iot.com/common/control/devices/{device_id}"
    "/{identity_id}/{attribute}:{value}"
)

# UUID generation prefix for CRC32
UUID_PREFIX = b"github.com/regaw-leinad/winix-purifiers"
UUID_SUFFIX = b"HGF"

# Token management
TOKEN_EXPIRY_BUFFER_SECONDS = 600  # 10 minutes

# Filter
MAX_FILTER_HOURS = 6480
