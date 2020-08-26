from . import resources

# build all args for action                                                     
def do_action_args():                                                           
    us_args = {}                                                                
    us_args['StackName'] = istack.name                                      
    us_args['Parameters'] = istack.action_parameters                            
    us_args['Tags'] = istack.action_tags                                        
    us_args['Capabilities'] = [                                                 
        'CAPABILITY_IAM',                                                       
        'CAPABILITY_NAMED_IAM',                                                 
        'CAPABILITY_AUTO_EXPAND',                                               
    ]                                                                           
                                                                                
    # sns topic                                                                 
    us_args['NotificationARNs'] = fargs.topics                                  
                                                                                
    # Handle policy during update                                               
    if hasattr(fargs, 'policy') and fargs.policy:                               
        action = ['"Update:%s"' % a for a in fargs.policy.split(',')]           
        action = '[%s]' % ','.join(action)                                      
        us_args['StackPolicyDuringUpdateBody'] = (                              
            '{"Statement" : [{"Effect" : "Allow",'                              
            '"Action" :%s,"Principal": "*","Resource" : "*"}]}' % action)       
                                                                                
    if istack.template_from == 'Current':                                       
        us_args['UsePreviousTemplate'] = True                                   
    if istack.template_from == 'S3':                                            
        us_args['TemplateURL'] = fargs.template                                 
    if istack.template_from == 'File':                                          
        us_args['TemplateBody'] = json.dumps(istack.template)                   
                                                                                
    return us_args


def update(obj):
    global istack

    istack = obj

    # get final args for update
    do_action_args()

    istack.before['resources'] = resources.get()
