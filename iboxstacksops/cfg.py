MAX_SINGLE_STACKS = 5

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
