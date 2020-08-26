from . import resources

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


def do_action_tags():
    stack_tags = [
        {'Key': 'Env', 'Value': cfg.Env},
        {'Key': 'EnvRole', 'Value': cfg.EnvRole},
        {'Key': 'EnvStackVersion', 'Value': cfg.version},
        {'Key': 'EnvApp1Version', 'Value': cfg.EnvApp1Version},
    ] if istack.create else istack.stack.tags

    # unchanged tags
    tags_default = {}

    # changed tags - same value as corresponding stack param
    tags_changed = {}
    final_tags = []

    for tag in stack_tags:
        key = tag['Key']
        current_value = tag['Value']

        # check if key exist as cfg param/attr too
        try:
            cfg_value = getattr(cfg, key)
            in_cfg = True if cfg_value is not None else None
        except Exception:
            in_cfg = None

        # Skip LastUpdate Tag
        if key == 'LastUpdate':
            continue

        # current value differ from cmd arg
        if in_cfg and current_value != cfg_value:
            value = cfg_value

            # tags value cannot be empty
            if len(value) == 0:
                value = "empty"

            tags_changed[key] = '%s => %s' % (current_value, value)

        # keep current tag value
        else:
            value = current_value

            # tags value cannot be empty
            if len(value) == 0:
                value = "empty"

            tags_default[key] = value

        final_tags.append({
            'Key': key,
            'Value': value
        })

    # Add LastUpdate Tag with current time
    final_tags.append({
        'Key': 'LastUpdate',
        'Value': str(datetime.now())
    })

    print('\n')
    if len(tags_default) > 0:
        mylog(
            'Default - Stack Tags\n%s' % pformat(tags_default, width=1000000))
        print('\n')
    if len(tags_changed) > 0:
        mylog(
            'Changed - Stack Tags\n%s' % pformat(tags_changed, width=1000000))
        print('\n')

    istack.action_tags = final_tags


def update(obj):
    global istack

    istack = obj

    # get final args for update
    us_args = get_action_args()

    istack.before['resources'] = resources.get()
