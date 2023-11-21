import pytest
from rancher import ApiError
from .conftest import wait_for, pandaria_create_project_role_template_binding
from .alert_common import MockReceiveAlert

dingtalk_config = {
    "type": "/v3/schemas/dingtalkConfig",
    "url": "http://127.0.0.1:4050/dingtalk/test/",
}

microsoft_teams_config = {
    "type": "/v3/schemas/msTeamsConfig",
    "url": "http://127.0.0.1:4050/microsoftTeams",
}

MOCK_RECEIVER_ALERT_PORT = 4050


def test_alert_access(admin_mc, admin_pc, admin_cc, user_mc, remove_resource):
    """Tests that a user with read-only access is not
    able to deactivate an alert.
    """
    client = admin_mc.client
    notifier_dingtalk = client.create_notifier(name="dingtalk1",
                                               clusterId="local",
                                               dingtalkConfig=dingtalk_config)
    remove_resource(notifier_dingtalk)

    prtb = pandaria_create_project_role_template_binding(
        client,
        user_mc.user.id,
        admin_pc.project.id,
        "read-only")
    remove_resource(prtb)

    # we get some project defaults, wait for them to come up
    wait_for(projectAlertRules(user_mc.client),
             fail_handler=lambda: "failed waiting for project alerts",
             timeout=120)
    # list with admin_mc to get action not available to user
    alerts = client.list_projectAlertRule(
        projectId=admin_pc.project.id
    )
    with pytest.raises(ApiError) as e:
        user_mc.client.action(obj=alerts.data[0], action_name="deactivate")
    assert e.value.error.status == 404


def projectAlertRules(client):
    """Wait for the crtb to have the userId populated"""
    def cb():
        return len(client.list_projectAlertRule().data) > 0
    return cb


@pytest.fixture(scope="module")
def mock_receiver_alert():
    server = MockReceiveAlert(port=MOCK_RECEIVER_ALERT_PORT)
    server.start()
    yield server
    server.shutdown_server()


@pytest.mark.skip(reason="TODO: can not send to mock server")
def test_add_notifier(admin_mc, remove_resource, mock_receiver_alert):
    client = admin_mc.client

    # Add the notifier dingtalk and microsoftTeams
    notifier_dingtalk = client.create_notifier(name="dingtalk",
                                               clusterId="local",
                                               dingtalkConfig=dingtalk_config)

    notifier_microsoft_teams = client.create_notifier(
        name="microsoftTeams",
        clusterId="local",
        msteamsConfig=microsoft_teams_config)

    client.action(obj=notifier_microsoft_teams,
                  action_name="send",
                  msteamsConfig=microsoft_teams_config)

    client.action(obj=notifier_dingtalk,
                  action_name="send",
                  dingtalkConfig=dingtalk_config)

    # Remove the notifiers
    remove_resource(notifier_dingtalk)
    remove_resource(notifier_microsoft_teams)
