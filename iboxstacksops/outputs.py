from . import cfg
from .tools import stack_resource_to_dict
from .common import *


def show_changed(istack):                                                     
    before = istack.before['outputs']                                           
    after = get(istack.stack)                                      
                                                                                
    changed = {}                                                                
    for o, v in after.items():                                                  
        if o in before and v != before[o]:                                      
            changed[o] = before[o] + ' => ' + v                                 

    istack.changed['outputs'] = changed
    show(istack, 'changed')   


# show stack current outputs as dict                                            
def show(istack, when):                                           
    outputs = getattr(istack, when)['outputs']                                  
                                                                                
    istack.mylog(                                                               
        '%s - STACK OUTPUTS\n%s\n' % (when.upper(), pformat(                    
            outputs,                                                            
            width=80 if (                                                       
                cfg.command == 'info' and not cfg.compact) else 1000000         
        ))                                                                      
    )


def get(stack):                                                        
    outputs = {}

    try:
        stack['StackName']
    except Exception:
        stack = stack_resource_to_dict(stack) 
    
    try:                                                                        
        s_outputs = stack['Outputs']                                            
    except Exception:                                                           
        pass                                                                    
    else:                                                                       
        for output in s_outputs:                                                
            key = output['OutputKey']                                           
            value = output.get('OutputValue', None)                             
            outputs[key] = value                                                
        
    for d in cfg.STACK_BASE_DATA:
        outputs[d] = stack.get(d, None)

    try:
        outputs['LastUpdatedTime'] = outputs['LastUpdatedTime'].strftime(             
        '%Y-%m-%d %X %Z')
        # outputs['LastUpdatedTime'] = outputs['LastUpdatedTime'][0:19]
    except Exception:
        pass

    return outputs
