# parser default cfg
stack = role = type = topics = stack_args = []
parallel = region = jobs = pause = version = template = None
nowait = compact = dryrun = answer_yes = no_stacks = all_stacks = None
debug = False
max_retry_ecs_service_running_count = 0
timedelta = 300
dashboard = "OnChange"
statistic = "Average"
statisticresponse = "p95"
silent = True
vertical = False
profile = False
output = "text"
disable_rollback = False
#

OUT_WIDTH = 1000000

SLACK_CHANNEL = "_cf_deploy"

MAX_SINGLE_STACKS = 5

ACTION_WAITER_SLEEP_TIME = 3

STACK_BASE_DATA = [
    "StackName",
    "Description",
    "StackStatus",
    "CreationTime",
    "LastUpdatedTime",
]

RESOURCES_MAP = {
    "AutoScalingGroup": "AutoScalingGroupName",
    "AutoScalingGroupSpot": "AutoScalingGroupSpotName",
    # 'TargetGroup': 'TargetGroup',
    # 'TargetGroupExternal': 'TargetGroupExternal',
    # 'TargetGroupInternal': 'TargetGroupInternal',
    "Service": "ServiceName",
    "ServiceSpot": "ServiceSpotName",
    "ServiceExternal": "ServiceName",
    "ServiceInternal": "ServiceName",
    "LoadBalancerClassicExternal": "LoadBalancerNameExternal",
    "LoadBalancerClassicInternal": "LoadBalancerNameInternal",
    "LoadBalancerApplicationExternal": "LoadBalancerExternal",
    "LoadBalancerApplicationInternal": "LoadBalancerInternal",
    "Cluster": "ClusterName",
    "ScalableTarget": "ClusterName",
    "ListenerHttpsExternalRules1": "LoadBalancerExternal",
    "ListenerHttpsExternalRules2": "LoadBalancerExternal",
    "ListenerHttpExternalRules1": "LoadBalancerExternal",
    "ListenerHttpInternalRules1": "LoadBalancerInternal",
    "AlarmCPUHigh": None,
    "AlarmCPULow": None,
    "AWS::ElasticLoadBalancingV2::TargetGroup": None,
}
SCALING_POLICY_TRACKINGS_NAMES = {
    "ScalingPolicyTrackings1": None,
    "ScalingPolicyTrackingsApp": None,
    "ScalingPolicyTrackingsASCpu": "ScalingPolicyTrackings1",
    "ScalingPolicyTrackingsASCustom": "ScalingPolicyTrackings1",
    "ScalingPolicyTrackingsAPPCpu": "ScalingPolicyTrackings1",
    "ScalingPolicyTrackingsAPPCustom": "ScalingPolicyTrackings1",
    "AutoScalingScalingPolicyCpu": "ScalingPolicyTrackings1",
    "AutoScalingScalingPolicyCustom": "ScalingPolicyTrackings1",
    "ApplicationAutoScalingScalingPolicyCpu": "ScalingPolicyTrackingsApp",
    "ApplicationAutoScalingScalingPolicyCustom": "ScalingPolicyTrackingsApp",
    # Disabled until they are properly managed in dashboard.py [get_policy].
    # Ideal should be to create two horizontal annotations
    # one for the lower bound and one for the upper one
    # but as AutoScalingScalingPolicy have been replaced with Tracking ones
    # i do not know if it make sense to put much effort in this.
    # 'AutoScalingScalingPolicyDown': 'ScalingPolicyTrackings1',
    # 'AutoScalingScalingPolicyUp': 'ScalingPolicyTrackings1',
    # 'ApplicationAutoScalingScalingPolicyDown': 'ScalingPolicyTrackings1',
    # 'ApplicationAutoScalingScalingPolicyUp': 'ScalingPolicyTrackings1',
}
RESOURCES_MAP.update(SCALING_POLICY_TRACKINGS_NAMES)

RESOURCES_MAP_R53 = {
    "RecordSetExternal": None,
    "RecordSetInternal": None,
    "RecordSetExternalRO": None,
    "RecordSetInternalRO": None,
    "RecordSetCloudFront": None,
    "AWS::ServiceDiscovery::Service": None,
}

STACK_COMPLETE_STATUS = [
    "UPDATE_COMPLETE",
    "CREATE_COMPLETE",
    "ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_FAILED",
    "DELETE_COMPLETE",
    "DELETE_FAILED",
]

CHANGESET_COMPLETE_STATUS = [
    "CREATE_COMPLETE",
    "UPDATE_ROLLBACK_FAILED",
    "FAILED",
]

SHOW_TABLE_FIELDS = [
    "EnvStackVersion",
    "EnvRole",
    "StackName",
    "StackType",
    "UpdateMode",
    "EnvApp1Version",
    "StackStatus",
    "LastUpdatedTime",
]

STACKSET_INSTANCES_SHOW_TABLE_FIELDS = [
    "Region",
    "Account",
    "StackId",
    "Status",
    "StatusReason",
    "StackInstanceStatus",
]

SSM_BASE_PATH = "/ibox"
