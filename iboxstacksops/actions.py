from . import resources, changeset, events, outputs, dashboard
from .tags import get_action_tags
from .tools import show_confirm
from .log import logger
from .common import *


# build all args for action
def _get_action_args(istack):
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
    us_args['NotificationARNs'] = istack.cfg.topics

    # Handle policy during update
    if hasattr(istack.cfg, 'policy') and istack.cfg.policy:
        action = ['"Update:%s"' % a for a in istack.cfg.policy.split(',')]
        action = '[%s]' % ','.join(action)
        us_args['StackPolicyDuringUpdateBody'] = (
            '{"Statement" : [{"Effect" : "Allow",'
            '"Action" :%s,"Principal": "*","Resource" : "*"}]}' % action)

    if istack.template_from == 'Current':
        us_args['UsePreviousTemplate'] = True
    if istack.template_from == 'S3':
        us_args['TemplateURL'] = istack.cfg.template
    if istack.template_from == 'File':
        us_args['TemplateBody'] = json.dumps(istack.template)

    return us_args


# wait update until complete showing events status
def _update_waiter(istack, timestamp=None):
    last_timestamp = timestamp if timestamp else istack.last_event_timestamp

    # return without waiting
    if istack.cfg.nowait:
        istack.stack.reload()
        return

    while True:
        try:
            istack.stack.reload()
        except botocore.exceptions.ClientError as e:
            print(e)

        if istack.stack.stack_status in istack.cfg.STACK_COMPLETE_STATUS:
            events.show(istack, last_timestamp)
            break

        time.sleep(istack.cfg.ACTION_WAITER_SLEEP_TIME)

        try:
            last_timestamp = events.show(istack, last_timestamp)
        except IboxErrorECSService as e:
            # ECS Service did not stabilize, cancel update [ROLLBACK]
            logger.warning(e.args[0])
            do_action_cancel()

    print('\n')


def create(istack):
    stack_tags = [
        {'Key': 'Env', 'Value': istack.cfg.Env},
        {'Key': 'EnvRole', 'Value': istack.cfg.EnvRole},
        {'Key': 'EnvStackVersion', 'Value': istack.cfg.version},
        {'Key': 'EnvApp1Version', 'Value': istack.cfg.EnvApp1Version},
    ]

    # set tags
    istack.action_tags = get_action_tags(istack, stack_tags)

    if not show_confirm():
        return

    # get final args for update
    us_args = _get_action_args(istack)

    response = istack.client.create_stack(**us_args)
    istack.mylog(f'{json.dumps(response)}\n')
    time.sleep(1)

    istack.stack = istack.cloudformation.Stack(istack.name)
    istack.last_event_timestamp = events.get_last_timestamp(istack)
    _update_waiter(istack)

    return True


def update(istack):
    # set tags
    istack.action_tags = get_action_tags(istack, istack.stack.tags)

    # get final args for update
    us_args = _get_action_args(istack)

    outputs.show(istack, 'before')

    # -if using changeset ...
    if not istack.cfg.nochangeset and len(istack.cfg.stacks) == 1:
        changeset_ok = changeset.process(istack, us_args)
        if not changeset_ok:
            return

    istack.before['resources'] = resources.get(istack)
    istack.last_event_timestamp = events.get_last_timestamp(istack)

    # do stack update
    response = istack.client.update_stack(**us_args)
    istack.mylog(f'{json.dumps(response)}\n')
    time.sleep(1)

    # -show update status until complete
    _update_waiter(istack)

    # show changed outputs
    outputs.show_changed(istack)

    # update dashboard
    dashboard.update(istack)

    return True


def delete(istack):
    istack.last_event_timestamp = events.get_last_timestamp(istack)
    response = istack.stack.delete()
    istack.mylog(f'{json.dumps(response)}\n')
    # -show update status until complete
    _update_waiter(istack)

    return True


def cancel_update(istack):
    istack.last_event_timestamp = events.get_last_timestamp(istack)
    response = istack.stack.cancel_update()
    istack.mylog(f'{json.dumps(response)}\n')
    # -show update status until complete
    _update_waiter(istack)

    return True


def continue_update(istack):
    istack.last_event_timestamp = events.get_last_timestamp(istack)
    response = istack.client.continue_update_rollback(
        StackName=istack.name,
        ResourcesToSkip=istack.cfg.resources_to_skip)
    istack.mylog(f'{json.dumps(response)}\n')
    # -show update status until complete
    _update_waiter(istack)

    return True


def log(istack):
    last_timestamp = events.get_last_timestamp(istack)
    time_delta = int(istack.cfg.timedelta)

    if time_delta == 0:
        time_event = last_timestamp - timedelta(seconds=1)
        _update_waiter(istack, time_event)
    else:
        if time_delta < 30:
            time_delta = time_delta * 86400
        time_event = last_timestamp - timedelta(seconds=time_delta)
        events.show(istack, time_event, time_delta)
