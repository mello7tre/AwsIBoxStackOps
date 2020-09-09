# parser default cfg
stack = role = type = stack_args = []
region = jobs = pause = version = template = nowait = compact = dryrun = None
max_retry_ecs_service_running_count = 0
timedelta = 300
dashboard = 'OnChange'
#

OUT_WIDTH = 1000000

SLACK_CHANNEL = '_cf_deploy'

MAX_SINGLE_STACKS = 5

STACK_BASE_DATA = [
    'StackName',
    'Description',
    'StackStatus',
    'CreationTime',
    'LastUpdatedTime',
]

RESOURCES_MAP = {
    'AutoScalingGroup': 'AutoScalingGroupName',
    'AutoScalingGroupSpot': 'AutoScalingGroupSpotName',
    'TargetGroup': 'TargetGroup',
    'TargetGroupExternal': 'TargetGroupExternal',
    'TargetGroupInternal': 'TargetGroupInternal',
    'Service': 'ServiceName',
    'ServiceExternal': 'ServiceName',
    'ServiceInternal': 'ServiceName',
    'LoadBalancerClassicExternal': 'LoadBalancerNameExternal',
    'LoadBalancerClassicInternal': 'LoadBalancerNameInternal',
    'LoadBalancerApplicationExternal': 'LoadBalancerExternal',
    'LoadBalancerApplicationInternal': 'LoadBalancerInternal',
    'Cluster': 'ClusterName',
    'ScalableTarget': 'ClusterName',
    'ListenerHttpsExternalRules1': 'LoadBalancerExternal',
    'ListenerHttpsExternalRules2': 'LoadBalancerExternal',
    'ListenerHttpInternalRules1': 'LoadBalancerInternal',
    'AlarmCPUHigh': None,
    'AlarmCPULow': None,
}
SCALING_POLICY_TRACKINGS_NAMES = {
    'ScalingPolicyTrackings1': None,
    'ScalingPolicyTrackingsASCpu': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsASCustom': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsAPPCpu': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsAPPCustom': 'ScalingPolicyTrackings1',
}
RESOURCES_MAP.update(SCALING_POLICY_TRACKINGS_NAMES)

STACK_COMPLETE_STATUS = [
    'UPDATE_COMPLETE',
    'CREATE_COMPLETE',
    'ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_FAILED',
    'DELETE_COMPLETE',
    'DELETE_FAILED',
]

CHANGESET_COMPLETE_STATUS = [
    'CREATE_COMPLETE',
    'UPDATE_ROLLBACK_FAILED',
    'FAILED',
]

SHOW_TABLE_FIELDS = [
    'EnvStackVersion',
    'EnvRole',
    'StackName',
    'StackType',
    'UpdateMode',
    'EnvApp1Version',
    'LastUpdatedTime',
]

SSM_BASE_PATH = '/ibox'
