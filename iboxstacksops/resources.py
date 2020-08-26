from . import cfg


def get(dash=None):                                                   
    resources = {}                                                              
    res_list = list(cfg.RESOURCES_MAP.keys())                          
                                                                                
    paginator = cfg.client.get_paginator('list_stack_resources')                    
    response_iterator = paginator.paginate(StackName=istack.name)               
                                                                                
    for r in response_iterator:                                                 
        for res in r['StackResourceSummaries']:                                 
            res_lid = res['LogicalResourceId']                                  
            res_type = res['ResourceType']                                      
            if res_lid in res_list:                                             
                res_pid = res['PhysicalResourceId']                             
                if res_pid.startswith('arn'):                                   
                    res_pid = res_pid.split(':', 5)[5]                          
                if res_lid in [                                                 
                        'ListenerHttpsExternalRules1',
                        'ListenerHttpsExternalRules2',
                        'ListenerHttpInternalRules1']:                          
                    res_pid = '/'.join(res_pid.split('/')[1:4])                 
                if res_lid == 'ScalableTarget':                                 
                    res_pid = res_pid.split('/')[1]                             
                if res_lid == 'Service':                                        
                    res_pid_arr = res_pid.split('/')                            
                    if len(res_pid_arr) == 3:                                   
                        res_pid = res_pid_arr[2]                                
                    else:                                                       
                        res_pid = res_pid_arr[1]                                
                if res_lid in [                                                 
                        'LoadBalancerApplicationExternal',                      
                        'LoadBalancerApplicationInternal']:                     
                    res_pid = '/'.join(res_pid.split('/')[1:4])                 
                                                                                
                if dash and cfg.RESOURCES_MAP[res_lid]:                
                    res_lid = cfg.RESOURCES_MAP[res_lid]               
                                                                                
                resources[res_lid] = res_pid

    return resources
