#!/usr/bin/python2
import json
import logging
import boto3
import botocore
import argparse
import time
import os
import sys
from pprint import pprint, pformat
from datetime import datetime, timedelta, tzinfo
from calendar import timegm
from prettytable import PrettyTable, ALL as ptALL

try:
    import ibox_add_to_dash
    add_to_dashboard = True
except ImportError:
    add_to_dashboard = None

try:
    from slackclient import SlackClient
    slack_client = True
except ImportError:
    slack_client = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DashBoards = []

ScalingPolicyTrackingsNames = {
    'ScalingPolicyTrackings1': None,
    'ScalingPolicyTrackingsASCpu': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsASCustom': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsAPPCpu': 'ScalingPolicyTrackings1',
    'ScalingPolicyTrackingsAPPCustom': 'ScalingPolicyTrackings1',
}

map_resources_on_dashboard = {
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
    'ListenerHttpExternalRules1': 'LoadBalancerExternal',
    'ListenerHttpInternalRules1': 'LoadBalancerInternal',
    'AlarmCPUHigh': None,
    'AlarmCPULow': None,
}

map_resources_on_dashboard.update(ScalingPolicyTrackingsNames)


# full args
class full_args(object):
    pass


# parse main argumets
def get_args():
    parser = argparse.ArgumentParser(
        description='Stack Operations',
        epilog='Note: options for Stack Params must be put at the end!'
    )

    # common args
    parser.add_argument('-s', '--stack', help='Stack Name', required=True, type=str)
    parser.add_argument('-r', '--region', help='Region', type=str)
    parser.add_argument('-c', '--compact', help='Show always Output json in compact form', action='store_true')

    # subparser
    subparsers = parser.add_subparsers(help='Desired Action', dest='action')

    # parent parser args
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('-p', '--params', help='Show Available Stack Parameters', action='store_true')

    # create parser
    parser_create = subparsers.add_parser('create', parents=[parent_parser], help='Create Stack')

    template_version_group_create = parser_create.add_mutually_exclusive_group(required=True)
    template_version_group_create.add_argument('-t', '--template', help='Template Location', type=str)
    template_version_group_create.add_argument('-v', '--version', help='Stack Env Version', type=str)

    parser_create.add_argument('--Env', help='Environment to use', type=str, required=True)
    parser_create.add_argument('--EnvRole', help='Stack Role', type=str, required=True)
    parser_create.add_argument('--EnvApp1Version', help='App Version', type=str, default='')

    # update parser
    parser_update = subparsers.add_parser('update', parents=[parent_parser], help='Update Stack')

    template_version_group_update = parser_update.add_mutually_exclusive_group()
    template_version_group_update.add_argument('-t', '--template', help='Template Location', type=str)
    template_version_group_update.add_argument('-v', '--version', help='Stack Env Version', type=str)

    parser_update.add_argument(
        '-n', '--nochangeset', help='Do Not Use Stack Changeset (no confirmation)',
        required=False, action='store_true'
    )
    parser_update.add_argument(
        '-P', '--policy', help='Policy during Stack Update', type=str,
        choices=['*', 'Modify', 'Delete', 'Replace', 'Modify,Delete', 'Modify,Replace', 'Delete,Replace']
    )
    parser_update.add_argument(
        '-N', '--dryrun',
        help='Show changeset and exit',
        action='store_true'
    )
    parser_update.add_argument(
        '-T', '--showtags',
        help='Show tags changes in changeset',
        action='store_true'
    )
    parser_update.add_argument(
        '-D', '--dashboard',
        help='Update CloudWatch DashBoard',
        choices=['Always', 'OnChange', 'Generic', 'None'],
        default='OnChange'
    )
    parser_update.add_argument(
        '-d', '--showdetails',
        help='Show extra details in changeset',
        action='store_true'
    )
    parser_update.add_argument(
        '-s', '--slack_channel',
        help='Slack Channel [_cf_deploy]',
        nargs='?',
        const='_cf_deploy',
        default=False,
    )

    # show parser
    parser_show = subparsers.add_parser('info', help='Show Stack Info')

    # log parser
    parser_log = subparsers.add_parser('log', help='Show Stack Log')
    parser_log.add_argument('-d', '--day', help='Days, use 0 for realtime', default=1)

    # cancel_update parser
    parser_cancel = subparsers.add_parser('cancel', help='Cancel Update Stack')

    # delete parser
    parser_delete = subparsers.add_parser('delete', help='Delete Stack (WARNING)')

    # continue_update parser
    parser_continue = subparsers.add_parser('continue', help='Continue Update RollBack')
    parser_continue.add_argument('--ResourcesToSkip', '-r', help='Resource to Skip', default=[], nargs='+')

    # args[0] contain know arguments args[1] the unkown remaining ones
    args = parser.parse_known_args()
    return args


# parse stack arguments, the args[1] from get_args() and update fargs
def do_stack_args(stack_parameters, stack_args):
    parser = argparse.ArgumentParser(
        description='',
        add_help=False,
        usage='Allowed Stack Params ... allowed values are in {}',
        formatter_class=argparse.RawTextHelpFormatter,
    )

    for parameter in sorted(stack_parameters, key=lambda x: x['ParameterKey']):
        allowed_values = get_allowed_values(parameter['ParameterConstraints'])
        kwargs = {'type': str, 'metavar': '\t%s' % parameter['Description']}

        if len(allowed_values) > 0:
            kwargs['choices'] = allowed_values
            kwargs['help'] = '{%s}\n\n' % ', '.join(allowed_values)
        else:
            kwargs['help'] = '\n'

        parser.add_argument(
            '--%s' % parameter['ParameterKey'],
            **kwargs
        )

    if fargs.params:
        parser.print_help()
        exit(0)
    else:
        args = parser.parse_args(stack_args)

    return do_fargs(args)


# get allowed stack parameters from supplied template or current one
def do_stack_parameters(client):
    kwargs = {}
    try:
        # using a new template
        if fargs.template:
            template = str(fargs.template)
            if template.startswith('http'):
                kwargs['TemplateURL'] = template
            elif template.startswith('file'):
                f = open(fargs.template[7:], 'r')
                template_content = f.read()
                kwargs['TemplateBody'] = template_content
        # using the same template
        else:
            kwargs['StackName'] = fargs.stack
        template_body = client.get_template_summary(**kwargs)

        return template_body['Parameters']
    except Exception, e:
        print('Error retrieving version/template: %s' % e)
        exit(1)


# get stack parameters (key/value) as dict
def do_stack_param_to_dict(stack_params):
    stack_param_current = {}

    for param in stack_params:
        key = param['ParameterKey']
        value = param['ParameterValue'] if 'ParameterValue' in param else None
        stack_param_current[key] = value

    return stack_param_current


# get stack exports (key/value) as dict
def do_stack_export_to_dict(stack_exports):
    stack_export_current = {}
    for export in stack_exports:
        key = export['Name']
        value = export['Value'] if 'Value' in export else None
        stack_export_current[key] = value
    return stack_export_current


# if template in s3, force version to the one in his url part if from file force fixed value 1
# Ex for version=master-2ed25d5:
# https://eu-west-1-ibox-app-repository.s3.amazonaws.com/ibox/master-2ed25d5/templates/cache-portal.json
def do_envstackversion_from_s3_template():
    global fargs

    template = fargs.template
    fargs.version = template.split("/")[4] if str(template).startswith('http') else '1'
    fargs.EnvStackVersion = fargs.version


# build list for AllowedValues if params specify them
def get_allowed_values(param_constraints):
    if 'AllowedValues' in param_constraints:
        return param_constraints['AllowedValues']
    else:
        return []


# get EnvShort param value based on Env one
def get_envshort(env):
    env_envshort_dict = {
        'dev': 'dev',
        'stg': 'stg',
        'prd': 'prd',
        'prod': 'prd',
    }

    return env_envshort_dict[env]


# change list in a string new line separated element
def list_to_string_list(mylist):
    # unique_list = []
    # [unique_list.append(i) for i in mylist if i not in unique_list]
    joined_string = '\n'.join(mylist)
    mystring = joined_string if len(mylist) < 2 else '(' + joined_string + ')'

    return mystring


# build params for update
def do_stack_params(stack, stack_parameters):
    # parameters in template currently used before update as dictionary - empty for create
    stack_param_current = {} if do_create else do_stack_param_to_dict(stack.parameters)

    # Env - differ if updating or creating
    if do_create:
        env = fargs.Env
    else:
        try:
            env = stack_param_current['Env']
        except:
            env = ''

    # parameters in template used for update as dictionary
    stack_param_template_dict = do_stack_param_to_dict(stack_parameters)

    # unchanged stack params
    params_default = {}

    # changed stack params
    params_changed = {}

    # new stack params - default value
    params_added = {}

    # forced to default stack params - current value not in allowed ones
    params_forced_default = {}
    final_params = []

    # if using template option force version
    if fargs.template:
        do_envstackversion_from_s3_template()

    # if template used for update include EnvShort params force its value based on the Env one
    if 'EnvShort' in stack_param_template_dict:
        fargs.EnvShort = get_envshort(env)

    for param in stack_parameters:
        key = param['ParameterKey']
        default_value = param['DefaultValue']

        if not do_create:
            use_previous_value = False

        # get list of AllowedValues
        allowed_values = get_allowed_values(param['ParameterConstraints'])

        # check if key exist as fargs param/attr too
        try:
            fargs_value = getattr(fargs, key)
            in_fargs = True if fargs_value is not None else None
        except:
            in_fargs = None

        # update param is not new ...
        if key in stack_param_current:
            current_value = stack_param_current[key]

            # current value its different from specified cmd arg
            if in_fargs and current_value != fargs_value:
                # get value from specified cmd arg
                value = fargs_value
                params_changed[key] = current_value + " => " + value

            # current value is not allowed by new template
            elif len(allowed_values) > 0 and (
                    current_value not in allowed_values):
                # get value from template default
                value = default_value
                params_forced_default[key] = (
                    current_value + " => " + default_value)

            # current value is unchanged and allowed
            else:
                # keep current value
                value = current_value if do_create else ''
                if not do_create:
                    use_previous_value = True
                params_default[key] = current_value

        # update param is new ...
        else:
            # template default value its different from specified cmd arg
            if in_fargs and default_value != fargs_value:
                value = fargs_value
                params_changed[key] = value

            # no cmd arg for new param
            else:
                # get template default value
                value = default_value
                params_added[key] = default_value

        # append dictionary element to list
        final_params.append(
            {
                u'ParameterKey': key,
                u'ParameterValue': value,
            } if do_create else
            {
                u'ParameterKey': key,
                u'ParameterValue': value,
                u'UsePreviousValue': use_previous_value,
            }
        )

    print('\n')
    if do_create:
        if len(params_default) > 0:
            print('Default - Stack Parameters\n%s\n' % pformat(params_default, width=1000000))

    if len(params_changed) > 0:
        mylog('Changed - Stack Parameters\n%s' % pformat(params_changed, width=1000000))
        print('\n')

    if not do_create:
        if len(params_added) > 0:
            mylog('Added - Stack Parameters\n%s' % pformat(params_added, width=1000000))
            print('\n')

    if len(params_forced_default) > 0:
        mylog('Forced to Default - Stack Parameters\n%s' % pformat(params_forced_default, width=1000000))
        print('\n')
    # return update list of dict params as ParameterKey ParameterValue keys
    # Ex for EnvRole=cache:
    # [{u'ParameterKey': 'EnvRole', u'ParameterValue': 'cache'}, {...}]

    return final_params


# get current stack EnvRole
def get_stack_role(stack):
    role = ''
    for p in stack.parameters:
        if p['ParameterKey'] == 'EnvRole':
            role = p['ParameterValue']
    return role


# get stack outputs as dict
def get_stack_outputs(stack):
    stack_outputs = stack.outputs
    outputs_current = {}
    if stack_outputs:
        for output in stack_outputs:
            key = output['OutputKey']
            value = output['OutputValue'] if 'OutputValue' in output else None
            outputs_current[key] = value

    outputs_current['StackStatus'] = stack.stack_status

    return outputs_current


# show stack current outputs as dict
def show_stack_outputs(stack_outputs, last_updated_time):
    outputs_current = stack_outputs
    outputs_current['StackName'] = fargs.stack
    if last_updated_time:
        outputs_current['LastUpdatedTime'] = last_updated_time.strftime('%Y-%m-%d %X %Z')
    print('\n')
    mylog(
        'Current - Stack Outputs\n%s' %
        pformat(
            outputs_current,
            width=80 if (fargs.action == 'info' and not fargs.compact) else 1000000
        )
    )
    print('\n')


# show stack parameters override
def show_stack_params_override(stack, stack_parameters):
    params = {}
    for p in stack.parameters:
        name = p['ParameterKey']
        value = p['ParameterValue']
        if (
            not name.startswith('Env') and
            any(name not in n for n in ['UpdateMode']) and
            any(
                name == s['ParameterKey'] and
                (value != s['DefaultValue'] if 'DefaultValue' in s else '')
                for s in stack_parameters
            )
        ):
            params[name] = value

    mylog(
        'Current - Stack Parameters - Not Default\n%s' %
        pformat(
            params,
            width=80 if (fargs.action == 'info' and not fargs.compact) else 1000000
        )
    )
    print('\n')


# build tags for update
def do_stack_tags(stack):
    stack_tags = [
        {u'Key': 'Env', u'Value': fargs.Env},
        {u'Key': 'EnvRole', u'Value': fargs.EnvRole},
        {u'Key': 'EnvStackVersion', u'Value': fargs.version},
        {u'Key': 'EnvApp1Version', u'Value': fargs.EnvApp1Version},
    ] if do_create else stack.tags

    # unchanged tags
    tags_default = {}

    # changed tags - same value as corresponding stack param
    tags_changed = {}
    final_tags = []

    for tag in stack_tags:
        key = tag['Key']
        current_value = tag['Value']

        # check if key exist as fargs param/attr too
        try:
            fargs_value = getattr(fargs, key)
            in_fargs = True if fargs_value is not None else None
        except:
            in_fargs = None

        # Skip LastUpdate Tag
        if key == 'LastUpdate':
            continue

        # current value differ from cmd arg
        if in_fargs and current_value != fargs_value:
            value = fargs_value

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
            u'Key': key,
            u'Value': value
        })

    # Add LastUpdate Tag with current time
    final_tags.append({
        u'Key': 'LastUpdate',
        u'Value': str(datetime.now())
    })

    print('\n')
    if len(tags_default) > 0:
        mylog('Default - Stack Tags\n%s' % pformat(tags_default, width=1000000))
        print('\n')
    if len(tags_changed) > 0:
        mylog('Changed - Stack Tags\n%s' % pformat(tags_changed, width=1000000))
        print('\n')
    return final_tags


# do stack update
def update_stack(stack, us_args):
    response = stack.update(**us_args)
    return response


def create_stack(client, us_args):
    response = client.create_stack(**us_args)
    return response


def cancel_update_stack(stack):
    response = stack.cancel_update()
    return response


def delete_stack(stack):
    response = stack.delete()
    return response


def continue_update_stack(client, stack):
    response = client.continue_update_rollback(
        StackName=stack_name,
        ResourcesToSkip=fargs.ResourcesToSkip,
    )
    return response


# get timestamp from last event available
def get_last_event_timestamp(stack):
    last_event = list(stack.events.all().limit(1))[0]
    return last_event.timestamp


def show_service_update(stack, service_logical_resource_id):
    service = task = cluster = deps_before = None
    deployment_task = ''
    deployments_len = pendingCount = 0
    client = boto3.client('ecs')

    try:
        cluster = stack.Resource('ScalableTarget').physical_resource_id.split('/')[1]
        service = stack.Resource(service_logical_resource_id).physical_resource_id
    except:
        return

    deps = {
        'PRIMARY': {},
        'ACTIVE': {},
    }
    while task != deployment_task or deployments_len > 1 or pendingCount != 0:
        stack.reload()
        task = stack.Resource('TaskDefinition').physical_resource_id
        response = client.describe_services(
            cluster=cluster,
            services=[service],
        )
        deployments = response['services'][0]['deployments']
        deployments_len = len(deployments)
        for dep in deployments:
            status = dep['status']
            for p in ['desiredCount', 'runningCount', 'pendingCount', 'taskDefinition']:
                deps[status][p] = dep[p]

        deployment_task = deps['PRIMARY']['taskDefinition']
        pendingCount = deps['PRIMARY']['pendingCount']

        if str(deps) != deps_before:
            deps_before = str(deps)
            for d in ['PRIMARY', 'ACTIVE']:
                if 'taskDefinition' in deps[d]:
                    deps[d]['taskDefinition'] = deps[d]['taskDefinition'].split('/')[-1]
            mylog(
                'PRIMARY%s' %
                pformat(
                    deps['PRIMARY'],
                    width=1000000
                )
            )
            mylog(
                'ACTIVE%s' %
                pformat(
                    deps['ACTIVE'],
                    width=1000000
                )
            )

        time.sleep(3)


# show all events after specific timestamp and return last event timestamp
def show_update_events(stack, timestamp):
    event_iterator = stack.events.all()
    event_list = []
    for event in event_iterator:
        if event.timestamp > timestamp:
            event_list.insert(0, event)
        else:
            break
    for event in event_list:
        logtime = timegm(event.timestamp.timetuple())
        mylog(
            event.logical_resource_id +
            " " + event.resource_status +
            " " + str(datetime.fromtimestamp(logtime)) +
            " " + str(event.resource_status_reason)
        )
        if event.logical_resource_id == 'Service' and event.resource_status == 'UPDATE_IN_PROGRESS' and event.resource_status_reason is None:
            show_service_update(stack, event.logical_resource_id)

    if len(event_list) > 0:
        return(event_list.pop().timestamp)

    return timestamp


# wait update until complete showing events status
def update_waiter(stack, timestamp):
    last_timestamp = timestamp
    stack.reload()
    while stack.stack_status not in [
        'UPDATE_COMPLETE',
        'CREATE_COMPLETE',
        'ROLLBACK_COMPLETE',
        'UPDATE_ROLLBACK_COMPLETE',
        'UPDATE_ROLLBACK_FAILED',
        'DELETE_COMPLETE',
        'DELETE_FAILED',
    ]:
        stack.reload()
        last_timestamp = show_update_events(stack, last_timestamp)
        time.sleep(5)


# build/update full_args from argparse arg objects
def do_fargs(args):
    global fargs

    for property, value in vars(args).iteritems():
        # fix to avoid overwriting Env and EnvRole with None value
        if not hasattr(fargs, property):
            setattr(fargs, property, value)


# build dict(key: value) from argparse arg objects
def do_args(args):
    myargs = {}
    for property, value in vars(args).iteritems():
        if value is not None:
            myargs[property] = value
    return myargs


# build all args for update stack function
def do_updatestack_args(stack_params, stack_tags):
    us_args = {}
    if do_create:
        us_args['StackName'] = fargs.stack
    us_args['Parameters'] = stack_params
    us_args['Tags'] = stack_tags
    us_args['Capabilities'] = ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']

    # Handle policy during update
    if hasattr(fargs, 'policy') and fargs.policy:
        action = ['"Update:%s"' % a for a in fargs.policy.split(',')]
        action = '[%s]' % ','.join(action)
        us_args['StackPolicyDuringUpdateBody'] = '{"Statement" : [{"Effect" : "Allow","Action" :%s,"Principal": "*","Resource" : "*"}]}' % action

    if not fargs.template:
        us_args['UsePreviousTemplate'] = True
    else:
        template = str(fargs.template)
        if template.startswith('http'):
            us_args['TemplateURL'] = fargs.template
        if template.startswith('file'):
            f = open(fargs.template[7:], 'r')
            template_content = f.read()
            us_args['TemplateBody'] = template_content

    return us_args


# create changeset
def do_changeset(client, stack, us_args):
    if not fargs.showtags:
        # keep existing stack.tags so that they are excluded from changeset (not the new prepared ones)
        us_args['Tags'] = stack.tags

    us_args['StackName'] = stack.stack_name
    us_args['ChangeSetName'] = (
        'CS-%s' % time.strftime('%Y-%m-%dT%H-%M-%S')
    )
    us_args.pop('StackPolicyDuringUpdateBody', None)

    response = client.create_change_set(**us_args)

    return response['Id']


def get_changeset(client, stack_name, changeset_id):
    changeset = client.describe_change_set(
        ChangeSetName=changeset_id,
        StackName=stack_name
    )
    return changeset


# wait until changeset is created
def changeset_waiter(client, stack_name, changeset_id):
    changeset = get_changeset(client, stack_name, changeset_id)
    while changeset['Status'] not in [
            'CREATE_COMPLETE',
            'UPDATE_ROLLBACK_FAILED',
            'FAILED'
    ]:
        time.sleep(3)
        changeset = get_changeset(client, stack_name, changeset_id)


# parse changeset changes
def parse_changeset(changeset):
    changes = []
    for change in changeset['Changes']:
        change_dict = {}
        ResChange = change['ResourceChange']
        change_dict['LogicalResourceId'] = ResChange['LogicalResourceId']
        change_dict['Action'] = ResChange['Action']
        change_dict['ResourceType'] = ResChange['ResourceType']
        if ResChange['Action'] == 'Modify':
            change_dict['Replacement'] = ResChange['Replacement']
            scope = ResChange['Scope']
            change_dict['Scope'] = list_to_string_list(scope)
            target = []
            causingentity = []
            for i in ResChange['Details']:
                if 'Name' in i['Target'] and i['Target']['Name'] not in target:
                    target.append(i['Target']['Name'])
                if 'CausingEntity' in i and 'Name' in i['Target'] and i['CausingEntity'] not in causingentity:
                    causingentity.append(i['CausingEntity'])
            change_dict['Target'] = list_to_string_list(target)
            change_dict['CausingEntity'] = list_to_string_list(causingentity)

        changes.append(change_dict)
    return changes


# show changeset changes
def show_changeset_changes(changes):
    fields = ['LogicalResourceId', 'ResourceType', 'Action']
    fileds_ex = ['Replacement', 'Scope', 'Target', 'CausingEntity']
    fields.extend(fileds_ex)
    table = PrettyTable()
    if not fargs.showdetails:
        fields.remove('Target')
        fields.remove('CausingEntity')
    table.field_names = fields
    table.padding_width = 1
    table.align['LogicalResourceId'] = "l"
    table.align['ResourceType'] = "l"
    for row in changes:
        table.add_row(['None' if i in fileds_ex and row['Action'] != 'Modify' else row[i] for i in fields])

    mylog('ChangeSet:')
    print(table.get_string(fields=fields))


def delete_changeset(client, stack_name, changeset_id):
    response = client.delete_change_set(
        ChangeSetName=changeset_id,
        StackName=stack_name
    )

    return response


def execute_changeset(client, stack_name, changeset_id):
    response = client.execute_change_set(
        ChangeSetName=changeset_id,
        StackName=stack_name
    )

    return response


def show_confirm():
    print("")
    answer = raw_input('Digit [y] to continue or any other key to exit: ')
    if not answer or answer[0].lower() != 'y':
        return False
    else:
        return True


def show_log(stack, last_event_timestamp, time_delta):
    time_event = last_event_timestamp - timedelta(days=time_delta)
    if time_delta == 0:
        update_waiter(stack, time_event)
    else:
        show_update_events(stack, time_event)


def check_EnvAppVersion(client, cloudformation, stack_output, resources_by_type, appindex):
    appversion = 'EnvApp%sVersion' % appindex
    apprepo = 'Apps%sRepoName' % appindex

    # ECS/TSK Stack
    if 'AWS::ECS::TaskDefinition' in resources_by_type:
        ecs = boto3.client('ecs')
        ecr = boto3.client('ecr')
        try:
            task_id = resources_by_type['AWS::ECS::TaskDefinition']
            task_def = ecs.describe_task_definition(taskDefinition=task_id)['taskDefinition']
            image = task_def['containerDefinitions'][int(appindex) - 1]['image'].encode('ascii')
            out = ecr.describe_images(
                registryId=image[0:image.find('.')],
                repositoryName=image[image.find('/')+1:image.find(':')],
                imageIds=[
                    {
                        'imageTag': getattr(fargs, appversion)
                    }
                ]
            )
        except botocore.exceptions.ClientError as e:
            pprint(e)
            exit(0)

    # EC2 Stack
    if stack_type == 'ec2':
        # launch_conf_id = cloudformation.StackResource(fargs.stack, 'LaunchConfiguration').physical_resource_id
        try:
            # bucket = do_stack_export_to_dict(client.list_exports()['Exports'])['BucketAppRepository']
            bucket = get_cloudformation_exports(client)['BucketAppRepository']
            reponame = stack_output[apprepo]
            s3 = boto3.client('s3')
            out = s3.get_object(
                Bucket=bucket,
                Key='%s/%s-%s.tar.gz' % (
                    reponame,
                    reponame,
                    getattr(fargs, appversion),
                )
            )
        except botocore.exceptions.ClientError as e:
            pprint(e)
            exit(0)

    return True


# method should be identically to the one found in bin/ibox_add_to_dash.py, but dash param default to None
def get_resources(client, stack, dash=None):
    resources = {}
    resources_by_type = {}
    res_list = map_resources_on_dashboard.keys()

    paginator = client.get_paginator('list_stack_resources')
    response_iterator = paginator.paginate(StackName=stack.stack_name)

    for r in response_iterator:
        for res in r['StackResourceSummaries']:
            res_lid = res['LogicalResourceId']
            res_type = res['ResourceType']
            if res_lid in res_list:
                res_pid = res['PhysicalResourceId']
                if res_pid.startswith('arn'):
                    res_pid = res_pid.split(':', 5)[5]
                if res_lid in ['ListenerHttpExternalRules1', 'ListenerHttpInternalRules1']:
                    res_pid = '/'.join(res_pid.split('/')[1:4])
                if res_lid == 'ScalableTarget':
                    res_pid = res_pid.split('/')[1]
                if res_lid == 'Service':
                    res_pid_arr = res_pid.split('/')
                    if len(res_pid_arr) == 3:
                        res_pid = res_pid_arr[2]
                    else:
                        res_pid = res_pid_arr[1]
                if res_lid in ['LoadBalancerApplicationExternal', 'LoadBalancerApplicationInternal']:
                    res_pid = '/'.join(res_pid.split('/')[1:4])

                if dash and map_resources_on_dashboard[res_lid]:
                    res_lid = map_resources_on_dashboard[res_lid]

                resources[res_lid] = res_pid

            resources_by_type[res_type] = res['PhysicalResourceId']

    return resources, resources_by_type


def get_resources_changed(resources_before, resources_after):
    changed = {}
    for r, v in resources_before.iteritems():
        if r in resources_after:
            v_after = resources_after[r]
            if v != v_after:
                changed[r] = v_after

    return changed


def get_cloudformation_exports(client):
    exports = {}
    paginator = client.get_paginator('list_exports')
    response_iterator = paginator.paginate()
    for e in response_iterator:
        for export in e['Exports']:
            name = export['Name']
            value = export['Value']
            exports[name] = value
        if all(key in exports for key in ['BucketAppRepository']):
            return exports

    return exports


def do_update_dashboard(cw, resources_changed, mode, dashboard_name):
    dashboard_body = cw.get_dashboard(DashboardName=dashboard_name)['DashboardBody']
    dashboard_body_dict = json.loads(dashboard_body)

    stackname_arr = stack_name.split('-')
    if len(stackname_arr) > 1:
        stack_prefix = stackname_arr[0] + '-' + stackname_arr[1] + '-'
    else:
        stack_prefix = stackname_arr[0] + '-'

    if mode == 'Generic':
        stack_prefix = stackname_arr[0] + '-'

    out_msg = ''
    changed = False
    for k, w in enumerate(dashboard_body_dict['widgets']):
        my_metrics = []
        for j, m in enumerate(w['properties']['metrics']):
            my_metric = []
            for i, v in enumerate(m):
                offset = 0
                if v in ['.', '..', '...']:
                    for n, d in enumerate(v):
                        my_metric.append(my_metrics[j - 1][i + n + offset])
                    offset += len(v) - 1
                else:
                    my_metric.append(v)
            for r, u in resources_changed.iteritems():
                for l in set([2, len(my_metric) - 2]):
                    m_name = my_metric[l]
                    if map_resources_on_dashboard[r] == m_name:
                        m_value_index = int(l) + 1
                        m_value = my_metric[m_value_index]
                        if m_value.startswith(stack_prefix) or '/' + stack_prefix in m_value:
                            out_msg = '%s\t%s: %s --> %s\n' % (out_msg, m_name, m_value, u)
                            my_metric[m_value_index] = u
                            dashboard_body_dict['widgets'][k]['properties']['metrics'][j] = my_metric
                            changed = True
            my_metrics.append(my_metric)

    if changed:
        out = cw.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body_dict, separators=(',', ':'))
        )
        if len(out['DashboardValidationMessages']) > 0:
            pprint(out)
        else:
            print('\n')
            mylog('CloudWatch-DashBoard[%s] Updated:' % dashboard_name)
            print(out_msg)

    return True


def update_dashboards(resources_changed, resources_after, outputs_changed):
    cw_client = boto3.client('cloudwatch')

    response_dash = cw_client.list_dashboards(DashboardNamePrefix='_')

    if fargs.dashboard == 'OnChange':
        resources = resources_changed
        mode = ''
    elif fargs.dashboard in ['Always', 'Generic']:
        resources = resources_after
        mode = fargs.dashboard
    else:
        return

    if not resources and 'ScalingPolicyTrackings' not in outputs_changed:
        return

    # Update dynamic one
    for dash in response_dash['DashboardEntries']:
        if stack_name in dash['DashboardName']:
            # If imported ibox_add_to_dash.py, execute it as external module in silent mode, rebuilding the dash from scratch ..
            if add_to_dashboard:
                dashboard_param_stacks = dash['DashboardName'].split('_')[1:]
                dashboard_params = ['--stack'] + dashboard_param_stacks + ['--silent']
                dashboard_parser = ibox_add_to_dash.get_parser()
                dashboard_args = dashboard_parser.parse_args(dashboard_params)
                ibox_add_to_dash.main(dashboard_args)
            # ... if not use the old method (no more maintained)
            elif resources:
                do_update_dashboard(cw_client, resources, mode, dash['DashboardName'])

    # Update fixed one
    if resources:
        for dash in DashBoards:
            do_update_dashboard(cw_client, resources, mode, dash)


def compare_outputs(outputs_before, outputs_after):
    outputs_changed = {}
    for o, v in outputs_after.iteritems():
        if o in outputs_before and v != outputs_before[o]:
            outputs_changed[o] = outputs_before[o] + ' => ' + v

    if len(outputs_changed) > 0:
        print('\n')
        mylog('Changed - Stack Outputs' + '\n' +
              pformat(outputs_changed, width=1000000))
        print('\n')

    return outputs_changed


def mylog(string):
    message = stack_name + ' # ' + string
    print(message)

    if (
        fargs.action == 'update' and
        fargs.slack_channel and
        slack_client and
        'BUILDKITE_SLACK_TOKEN' in os.environ and
        'BUILDKITE_SLACK_USER' in os.environ
    ):
        slack = SlackClient(os.environ['BUILDKITE_SLACK_TOKEN'])
        ac = slack.api_call(
            "chat.postMessage",
            channel='#%s' % fargs.slack_channel,
            text=message,
            username=os.environ['BUILDKITE_SLACK_USER'],
            icon_emoji=':robot_face:',
        )


def update_template_param(client, stack):
    role = fargs.EnvRole if do_create else get_stack_role(stack)

    app_repository = get_cloudformation_exports(client)['BucketAppRepository']
    s3_prefix = 'ibox/%s/templates/%s.' % (fargs.version, role)
    s3 = boto3.client('s3')

    try:
        response = s3.list_objects_v2(Bucket=app_repository, Prefix=s3_prefix)
        fargs.template = 'https://%s.s3.amazonaws.com/%s' % (app_repository, response['Contents'][0]['Key'])
    except Exception as e:
        print('Error retrieving stack template with prefix: %s' % s3_prefix)
        pprint(e)
        exit(1)


def do_changeset_actions(client, stack, us_args):
    # -create changeset
    changeset_id = do_changeset(client, stack, us_args.copy())
    print('\n')
    mylog('ChangeSetId: %s' % changeset_id)
    print('\n')
    time.sleep(1)
    mylog('Waiting ChangeSet Creation..')

    # -wait changeset creation
    changeset_waiter(client, stack.stack_name, changeset_id)

    # -get changeset
    changeset = get_changeset(client, stack.stack_name, changeset_id)
    # pprint(changeset)

    # -parse changeset changes
    changeset_changes = parse_changeset(changeset)

    # -show changeset changes
    show_changeset_changes(changeset_changes)

    # -delete changeset
    delete_changeset(client, stack.stack_name, changeset_id)

    if not fargs.dryrun and show_confirm():
        pass
        # execute_changeset(client, stack.stack_name, changeset_id)
    else:
        # delete_changeset(client, stack.stack_name, changeset_id)
        exit(0)


def get_stack(cloudformation):
    try:
        stack = cloudformation.Stack(fargs.stack)
    except:
        logging.error('Stack %s do not exist!')
        exit(1)

    return stack


def do_action_update(cloudformation, client, stack_args):
    global stack_type
    global do_create

    do_create = None

    # get stack
    stack = get_stack(cloudformation)

    # update template param if using version one
    if fargs.version:
        update_template_param(client, stack)

    # -get allowed stack parameters from supplied template or current one
    stack_parameters = do_stack_parameters(client)

    # -get stack args as argparse objects (unparsed args[1] object) and update fargs
    do_stack_args(stack_parameters, stack_args)

    # get stack outputs before update
    stack_outputs_before = get_stack_outputs(stack)

    # set stack_type
    stack_type = stack_outputs_before['StackType'] if 'StackType' in stack_outputs_before else None

    # show current stack outputs
    show_stack_outputs(stack_outputs_before, stack.last_updated_time)

    # get stack resources before update (and resources by type needed by check_EnvAppVersion)
    resources_before, resources_by_type = get_resources(client, stack)

    # check if supplied EnvAppNVersion does exist
    for n, v in vars(fargs).iteritems():
        if n.startswith('EnvApp') and n.endswith('Version'):
            appindex = n.replace('EnvApp', '').replace('Version', '')
            if v:
                check_EnvAppVersion(client, cloudformation, stack_outputs_before, resources_by_type, appindex)

    # -build params for update
    stack_params = do_stack_params(stack, stack_parameters)

    # -build tags for update
    stack_tags = do_stack_tags(stack)

    # -build all args for update stack function
    us_args = do_updatestack_args(stack_params, stack_tags)
    # pprint(us_args)

    # -get timestamp from last event
    last_event_timestamp = get_last_event_timestamp(stack)

    # -if using changeset ...
    if not fargs.nochangeset:
        do_changeset_actions(client, stack, us_args)

    # -do update
    update_response = update_stack(stack, us_args)
    mylog(json.dumps(update_response))
    time.sleep(1)

    # -show update status until complete
    update_waiter(stack, last_event_timestamp)

    # get stack resources after update
    resources_after, resources_by_type = get_resources(client, stack)

    # get stack resources changed
    resources_changed = get_resources_changed(resources_before, resources_after)

    # get stack outputs after update
    stack.reload()
    stack_outputs_after = get_stack_outputs(stack)

    # compare outputs
    outputs_changed = compare_outputs(stack_outputs_before, stack_outputs_after)

    # update dashboards
    update_dashboards(resources_changed, resources_after, outputs_changed)


def do_action_create(cloudformation, client, stack_args):
    global do_create

    do_create = True
    stack = None

    # update template param if using version one
    if fargs.version:
        update_template_param(client, stack)

    # -get allowed stack parameters from supplied template or current one
    stack_parameters = do_stack_parameters(client)

    # -get stack args as argparse objects (unparsed args[1] object) and update fargs
    do_stack_args(stack_parameters, stack_args)

    # -build params for create
    stack_params = do_stack_params(stack, stack_parameters)

    # -build tags for create
    stack_tags = do_stack_tags(stack)

    # -build all args for create stack function
    us_args = do_updatestack_args(stack_params, stack_tags)
    # pprint(us_args)

    if show_confirm():
        create_response = create_stack(client, us_args)
        print(create_response)
        time.sleep(1)

        stack = cloudformation.Stack(fargs.stack)
        last_event_timestamp = get_last_event_timestamp(stack)

        # -show update status until complete
        update_waiter(stack, last_event_timestamp)


def do_action_info(cloudformation, client, stack_args):
    # get stack
    stack = get_stack(cloudformation)

    # -get stack parameters from current stack
    stack_parameters = client.get_template_summary(StackName=fargs.stack)['Parameters']

    # show stack output
    stack_outputs_before = get_stack_outputs(stack)
    show_stack_outputs(stack_outputs_before, stack.last_updated_time)
    show_stack_params_override(stack, stack_parameters)


def do_action_log(cloudformation, client, stack_args):
    # get stack
    stack = get_stack(cloudformation)

    # -get stack parameters from current stack
    stack_parameters = client.get_template_summary(StackName=fargs.stack)['Parameters']

    # -get timestamp from last event
    last_event_timestamp = get_last_event_timestamp(stack)
    show_log(stack, last_event_timestamp, int(fargs.day))


def do_action_cancel(cloudformation, client, stack_args):
    # get stack
    stack = get_stack(cloudformation)

    # -get stack parameters from current stack
    stack_parameters = client.get_template_summary(StackName=fargs.stack)['Parameters']

    # -get timestamp from last event
    last_event_timestamp = get_last_event_timestamp(stack)

    # -do cancel_update
    cancel_response = cancel_update_stack(stack)
    mylog(json.dumps(cancel_response))
    time.sleep(1)

    # -show update status until complete
    update_waiter(stack, last_event_timestamp)


def do_action_delete(cloudformation, client, stack_args):
    # get stack
    stack = get_stack(cloudformation)

    # -get stack parameters from current stack
    stack_parameters = client.get_template_summary(StackName=fargs.stack)['Parameters']

    print('WARNING - DELETING STACK %s  - WARNING' % stack_name)
    if show_confirm():
        # -get timestamp from last event
        last_event_timestamp = get_last_event_timestamp(stack)

        # -do delete
        delete_response = delete_stack(stack)
        mylog(json.dumps(delete_response))
        time.sleep(1)

        # -show update status until complete
        update_waiter(stack, last_event_timestamp)


def do_action_continue(cloudformation, client, stack_args):
    # get stack
    stack = get_stack(cloudformation)

    # -get stack parameters from current stack
    stack_parameters = client.get_template_summary(StackName=fargs.stack)['Parameters']

    # -get timestamp from last event
    last_event_timestamp = get_last_event_timestamp(stack)

    # -do continue_update
    continue_response = continue_update_stack(client, stack)
    mylog(json.dumps(continue_response))
    time.sleep(1)

    # -show update status until complete
    update_waiter(stack, last_event_timestamp)


# main program function
def run():
    global stack_name
    global boto3
    global fargs

    # init class for full args program args + stack args
    fargs = full_args()

    # -get cmd args as argparse objects
    args = get_args()

    do_fargs(args[0])

    # set region from parameter if exist
    kwarg_session = {}
    if fargs.region:
        kwarg_session['region_name'] = fargs.region
    boto3 = boto3.session.Session(**kwarg_session)

    # create boto3 client/resource
    cloudformation = boto3.resource('cloudformation')
    client = boto3.client('cloudformation')

    # -set global var stack_name used for logging with stack name prepended
    stack_name = fargs.stack

    if fargs.action == 'create':
        do_action_create(cloudformation, client, args[1])

    if fargs.action == 'update':
        do_action_update(cloudformation, client, args[1])

    if fargs.action == 'info':
        do_action_info(cloudformation, client, args[1])

    if fargs.action == 'log':
        do_action_log(cloudformation, client, args[1])

    if fargs.action == 'cancel':
        do_action_cancel(cloudformation, client, args[1])

    if fargs.action == 'delete':
        do_action_delete(cloudformation, client, args[1])

    if fargs.action == 'continue':
        do_action_continue(cloudformation, client, args[1])

    exit(0)

if __name__ == "__main__":
    run()
