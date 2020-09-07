from . import cfg
from .tools import stack_resource_to_dict
from .common import *


def show_changed(istack):
    before = istack.before['outputs']
    after = get(istack.stack)

    changed = {}
    for o, v in after.items():
        if o in before and v != before[o]:
            changed[o] = f'{before[o]} => {v}'

    istack.changed['outputs'] = changed
    show(istack, 'changed')


# show stack current outputs as dict
def show(istack, when):
    outputs = getattr(istack, when)['outputs']

    out_with = 80 if (istack.cfg.command == 'info'
                      and not istack.cfg.compact) else 1000000
    out_output = pformat(outputs, width=out_with)

    istack.mylog(f'{when.upper()} - STACK OUTPUTS\n{out_output}\n')


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
        value = stack.get(d, None)
        if isinstance(value, datetime):
            value = value.strftime('%Y-%m-%d %X %Z')
        outputs[d] = value

    return outputs
