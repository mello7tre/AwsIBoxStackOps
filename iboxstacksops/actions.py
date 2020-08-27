from . import cfg, resources
from .tags import get_action_tags

# build all args for action
def get_action_args():
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


def update(obj):
    global istack

    istack = obj

    # set tags
    istack.action_tags = get_action_tags(istack)

    # get final args for update
    us_args = get_action_args()

    istack.before['resources'] = resources.get(istack)
