# parser default cfg
stack = role = type = topics = stack_args = cmd_args = tags = []
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
# changeset_original = False
print_mylog = True
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
    "AWS::AutoScaling::AutoScalingGroup": {},
    "AWS::ECS::Service": {
        "PidEval": 'res_pid.split("/")[2]',
    },
    "AWS::ElasticLoadBalancing::LoadBalancer": {
        "Prefix": "LoadBalancerName",
    },
    "AWS::ElasticLoadBalancingV2::LoadBalancer": {
        "Prefix": "LoadBalancer",
        "PidEval": '"/".join(res_pid.split("/")[1:4]',
    },
    "AWS::ElasticLoadBalancingV2::Listener": {
        "Prefix": "LoadBalancer",
        "PidEval": '"/".join(res_pid.split("/")[1:4])',
    },
    "AWS::ECS::Cluster": {},
    "AWS::ElasticLoadBalancingV2::TargetGroup": {
        "PidEval": 'res_pid.split(":", 5)[5]',
    },
    "AWS::ApplicationAutoScaling::ScalableTarget": {
        "Name": "ClusterName",
        "PidEval": 'res_pid.split("/")[1]',
    },
    "AWS::CloudWatch::Alarm": {},
    "AWS::Route53::RecordSet": {},
    "AWS::AutoScaling::ScalingPolicy": {
        "Name": "ScalingPolicyTrackings1",
        "PidEval": 'res_pid.split("/")[2]',
    },
    "AWS::ApplicationAutoScaling::ScalingPolicy": {
        "Name": "ScalingPolicyTrackingsApp",
        "PidEval": '"/".join(res_pid.split("/")[2:6])'
    },
    "AWS::ServiceDiscovery::Service": {},
    # LogicalResourceId
    "AutoScalingGroupSpot": {
        "Name": "AutoScalingGroupSpotName",
    },
    "AlarmCPUHigh": {},
    "AlarmCPULow": {},
    "ServiceSpot": {
        "Name": "ServiceSpotName",
    },
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
    "EnvApp1Version",
    "StackStatus",
    "LastUpdatedTime",
]

SHOW_RESOURCES_FIELDS = [
    "LogicalResourceId",
    "ResourceType",
    "ResourceStatus",
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
