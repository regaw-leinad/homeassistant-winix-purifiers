"""Tests for Winix API constants, locking in the v1.5.7 Cognito/URL changes."""

from custom_components.winix_purifiers.api import const


class TestCognitoConfig:
    """Cognito IDs moved to a secretless app client and added an identity pool in v1.5.7."""

    def test_app_client_id_is_secretless_client(self):
        assert const.COGNITO_APP_CLIENT_ID == "5rjk59c5tt7k9g8gpj0vd2qfg9"

    def test_user_pool_id_unchanged(self):
        assert const.COGNITO_USER_POOL_ID == "us-east-1_Ofd50EosD"

    def test_region(self):
        assert const.COGNITO_REGION == "us-east-1"

    def test_identity_pool_id(self):
        assert const.COGNITO_IDENTITY_POOL_ID == "us-east-1:84008e15-d6af-4698-8646-66d05c1abe8b"

    def test_client_secret_key_removed(self):
        """Old client secret is gone as of v1.5.7 (public client)."""
        assert not hasattr(const, "COGNITO_CLIENT_SECRET_KEY")


class TestMobileAppVersion:
    def test_version_bumped_to_1_5_7(self):
        assert const.MOBILE_APP_VERSION == "1.5.7"


class TestControlUrlFormat:
    """Control URL now embeds the user's Cognito identityId (replaces hardcoded A211)."""

    def test_url_has_identity_id_placeholder(self):
        assert "{identity_id}" in const.URL_DEVICE_CONTROL

    def test_url_no_longer_has_hardcoded_a211(self):
        assert "/A211/" not in const.URL_DEVICE_CONTROL

    def test_url_formats_as_expected(self):
        url = const.URL_DEVICE_CONTROL.format(
            device_id="dev123",
            identity_id="us-east-1:abc",
            attribute="A02",
            value="1",
        )
        assert url == (
            "https://us.api.winix-iot.com/common/control/devices/dev123" "/us-east-1:abc/A02:1"
        )


class TestMobileEndpoints:
    def test_init_endpoint_added(self):
        assert const.URL_INIT == "https://us.mobile.winix-iot.com/init"

    def test_register_user_unchanged(self):
        assert const.URL_REGISTER_USER == "https://us.mobile.winix-iot.com/registerUser"

    def test_check_access_token_unchanged(self):
        assert const.URL_CHECK_ACCESS_TOKEN == "https://us.mobile.winix-iot.com/checkAccessToken"
