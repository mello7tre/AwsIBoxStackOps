from . import cfg, resources, changeset, events, outputs, dashboard
from .tags import get_action_tags
from .tools import IboxErrorECSService
from .common import *


# build all args for action
def _get_action_args():
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
    us_args['NotificationARNs'] = cfg.topics

    # Handle policy during update
    if hasattr(cfg, 'policy') and cfg.policy:
        action = ['"Update:%s"' % a for a in cfg.policy.split(',')]
        action = '[%s]' % ','.join(action)
        us_args['StackPolicyDuringUpdateBody'] = (
            '{"Statement" : [{"Effect" : "Allow",'
            '"Action" :%s,"Principal": "*","Resource" : "*"}]}' % action)

    if istack.template_from == 'Current':
        us_args['UsePreviousTemplate'] = True
    if istack.template_from == 'S3':
        us_args['TemplateURL'] = cfg.template
    if istack.template_from == 'File':
        us_args['TemplateBody'] = json.dumps(istack.template)

    return us_args


# wait update until complete showing events status
def _update_waiter(timestamp):
    last_timestamp = timestamp
    istack.stack.reload()

    # return without waiting
    if cfg.nowait:
        return

    while istack.stack.stack_status not in cfg.STACK_COMPLETE_STATUS:
        try:
            last_timestamp = events.show(istack, last_timestamp)

        # ECS Service did not stabilize, cancel update [ROLLBACK]
        except IboxErrorECSService as e:
            logger.warning(e.args[0])
            do_action_cancel()

        time.sleep(5)
        istack.stack.reload()


def update(obj):
    global istack
    istack = obj

    # set tags
    istack.action_tags = get_action_tags(istack)

    # get final args for update
    us_args = _get_action_args()

    outputs.show(istack, 'before')

    # -if using changeset ...
    if not cfg.nochangeset and len(cfg.stack) == 1:
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
    _update_waiter(istack.last_event_timestamp)

    # show changed outputs
    outputs.show_changed(istack)

    # update dashboard
    dashboard.update(self)

    return True
