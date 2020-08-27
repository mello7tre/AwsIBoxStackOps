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
    # ScalingPolicyTracking
    'ScalingPolicyTrackings1': None,
    'ScalingPolicyTrackingsASCpu': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsASCustom': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsAPPCpu': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsAPPCustom': 'ScalingPolicyTrackings1',
}

STACK_COMPLETE_STATUS = [
    'UPDATE_COMPLETE',
    'CREATE_COMPLETE',
    'ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_FAILED',
    'DELETE_COMPLETE',
    'DELETE_FAILED',
]
