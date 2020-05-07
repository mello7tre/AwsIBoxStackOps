#!/usr/bin/env python3
import json
import logging
import boto3 as base_boto3
import botocore
import argparse
import time
import os
import sys
from collections.abc import Mapping
from collections import OrderedDict
from pprint import pprint, pformat
from datetime import datetime, timedelta, tzinfo
from calendar import timegm

try:
    from prettytable import PrettyTable, ALL as ptALL
    have_prettytable = True
except ImportError:
    have_prettytable = None

try:
    import ibox_add_to_dash
    add_to_dashboard = True
except ImportError:
    add_to_dashboard = None

try:
    import slack
    slack_client = True
except ImportError:
    slack_client = None

logging.basicConfig()
logging.getLogger('botocore').setLevel('CRITICAL')
logger = logging.getLogger('ibox')
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
    'ListenerHttpsExternalRules1': 'LoadBalancerExternal',
    'ListenerHttpInternalRules1': 'LoadBalancerInternal',
    'AlarmCPUHigh': None,
    'AlarmCPULow': None,
}

map_resources_on_dashboard.update(ScalingPolicyTrackingsNames)


# full args
class full_args(object):
    pass


# ibox stack
class ibox_stack(object):
    pass


class IboxError(Exception):
    pass


# parse main argumets
def get_parser():
    parser = argparse.ArgumentParser(
        description='Stack Operations',
        epilog='Note: options for Stack Params must be put at the end!'
    )

    # common args
    parser.add_argument('-s', '--stack',
                        help='Stack Name', required=True, type=str)
    parser.add_argument('-r', '--region',
                        help='Region', type=str)
    parser.add_argument('-c', '--compact',
                        help='Show always Output json in compact form',
                        action='store_true')

    # subparser
    subparsers = parser.add_subparsers(help='Desired Action', dest='action')

    # common parser
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('-n', '--noconfirm',
                               help='No confirmation',
                               required=False, action='store_true')
    common_parser.add_argument('-W', '--nowait',
                               help='Do not Wait for action to end',
                               required=False, action='store_true')
    common_parser.add_argument('-s', '--slack_channel',
                               help='Slack Channel [_cf_deploy]', nargs='?',
                               const='_cf_deploy', default=False)

    # updatecreate parser common args
    updatecreate_parser = argparse.ArgumentParser(add_help=False)

    updatecreate_parser.add_argument('-p', '--params',
                                     help='Show Available Stack Parameters',
                                     action='store_true')

    updatecreate_parser.add_argument('--debug',
                                     help='Show parsed/resolved template'
                                          'and exit',
                                     action='store_true')
    updatecreate_parser.add_argument('--topic',
                                     help='SNS Topic Arn for notification')

    # create parser
    parser_create = subparsers.add_parser('create',
                                          parents=[common_parser,
                                                   updatecreate_parser],
                                          help='Create Stack')

    template_version_group_create = parser_create.add_mutually_exclusive_group(
        required=True)
    template_version_group_create.add_argument('-t', '--template',
                                               help='Template Location',
                                               type=str)
    template_version_group_create.add_argument('-v', '--version',
                                               help='Stack Env Version',
                                               type=str)

    parser_create.add_argument('--Env',
                               help='Environment to use',
                               type=str, required=True)
    parser_create.add_argument('--EnvRole',
                               help='Stack Role',
                               type=str, required=True)
    parser_create.add_argument('--EnvApp1Version',
                               help='App Version',
                               type=str, default='')

    # update parser
    parser_update = subparsers.add_parser('update',
                                          parents=[common_parser,
                                                   updatecreate_parser],
                                          help='Update Stack')

    template_version_group_update = parser_update.add_mutually_exclusive_group(
        )
    template_version_group_update.add_argument('-t', '--template',
                                               help='Template Location',
                                               type=str)
    template_version_group_update.add_argument('-v', '--version',
                                               help='Stack Env Version',
                                               type=str)

    parser_update.add_argument('-P', '--policy',
                               help='Policy during Stack Update',
                               type=str, choices=[
                                   '*', 'Modify', 'Delete', 'Replace',
                                   'Modify,Delete', 'Modify,Replace',
                                   'Delete,Replace'])

    parser_update.add_argument('-N', '--dryrun',
                               help='Show changeset and exit',
                               action='store_true')

    parser_update.add_argument('-T', '--showtags',
                               help='Show tags changes in changeset',
                               action='store_true')

    parser_update.add_argument('-D', '--dashboard',
                               help='Update CloudWatch DashBoard',
                               choices=[
                                   'Always', 'OnChange', 'Generic', 'None'],
                               default='OnChange')

    parser_update.add_argument('-d', '--showdetails',
                               help='Show extra details in changeset',
                               action='store_true')

    # show parser
    parser_show = subparsers.add_parser('info', help='Show Stack Info')

    # log parser
    parser_log = subparsers.add_parser('log',
                                       parents=[common_parser],
                                       help='Show Stack Log')
    parser_log.add_argument('-d', '--day',
                            help='Days, use 0 for realtime', default=1)

    # cancel_update parser
    parser_cancel = subparsers.add_parser('cancel',
                                          parents=[common_parser],
                                          help='Cancel Update Stack')

    # delete parser
    parser_delete = subparsers.add_parser('delete',
                                          parents=[common_parser],
                                          help='Delete Stack (WARNING)')

    # continue_update parser
    parser_continue = subparsers.add_parser('continue',
                                            parents=[common_parser],
                                            help='Continue Update RollBack')
    parser_continue.add_argument('--ResourcesToSkip', '-r',
                                 help='Resource to Skip',
                                 default=[], nargs='+')

    return parser


# parse stack arguments, the args[1] from get_args() and update fargs
def add_stack_params_as_args():
    parser = argparse.ArgumentParser(
        description='',
        add_help=False,
        allow_abbrev=False,
        usage='Allowed Stack Params ... allowed values are in {}',
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # for parameter in sorted(
    #    stack_parameters, key=lambda x: x['ParameterKey']):
    for p in sorted(istack.parameters):
        v = istack.parameters[p]
        allowed_values = v['AllowedValues'] if 'AllowedValues' in v else []
        kwargs = {'type': str, 'metavar': '\t%s' % v['Description']}

        # If Parameter do not have Default value and is new or
        # current value is not allowed in new template,
        # enforce it as required
        if 'Default' not in v and (
                p not in istack.c_parameters or (
                    allowed_values and
                    istack.c_parameters[p] not in allowed_values)):
            kwargs['required'] = True

        if len(allowed_values) > 0:
            kwargs['choices'] = allowed_values
            kwargs['help'] = '{%s}\n\n' % ', '.join(allowed_values)
        else:
            kwargs['help'] = '\n'

        parser.add_argument(
            '--%s' % p,
            **kwargs
        )

    if fargs.params:
        parser.print_help()
        exit(0)
    else:
        args = parser.parse_args(istack.args)
        do_fargs(args)


def get_parameters_current():
    params = {}
    try:
        for p in istack.stack.parameters:
            key = p['ParameterKey']
            try:
                value = p['ResolvedValue']
            except:
                try:
                    value = p['ParameterValue']
                except:
                    value = None
            params[key] = value
    except:
        pass

    return params


# if template in s3, force version to the one in his url part
# if from file force fixed value 1
# Ex for version=master-2ed25d5:
# https://eu-west-1-ibox-app-repository.s3.amazonaws.com
# /ibox/master-2ed25d5/templates/cache-portal.json
def do_envstackversion_from_s3_template():
    template = fargs.template
    fargs.version = template.split("/")[4] if str(
        template).startswith('https') else '1'
    fargs.EnvStackVersion = fargs.version


# force EnvShort param value based on Env one
def force_envshort():
    # use arg if exist or use current value
    env = fargs.Env if fargs.Env else istack.c_parameters['Env']

    env_envshort_dict = {
        'dev': 'dev',
        'stg': 'stg',
        'prd': 'prd',
        'prod': 'prd',
    }

    fargs.EnvShort = env_envshort_dict[env]


# change list in a string new line separated element
def list_to_string_list(mylist):
    # unique_list = []
    # [unique_list.append(i) for i in mylist if i not in unique_list]
    joined_string = '\n'.join(mylist)
    mystring = joined_string if len(mylist) < 2 else '(' + joined_string + ')'

    return mystring


# set final parameters values to use for exectuing actions -
# istack.action_parameters and istack.r_parameters
def set_action_parameters(params_default, params_changed,
                          params_added, params_forced_default):
    for key in sorted(istack.parameters):
        v = istack.parameters[key]

        try:
            default_value = v['Default']
        except:
            default_value = None
        use_previous_value = False

        # get list of AllowedValues
        allowed_values = v['AllowedValues'] if 'AllowedValues' in v else []

        # check if key exist as fargs param/attr too
        try:
            fargs_value = getattr(fargs, key)
            in_fargs = True if fargs_value is not None else None
        except:
            in_fargs = None

        # update param is not new ...
        if key in istack.c_parameters:
            current_value = istack.c_parameters[key]

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
                value = ''
                use_previous_value = True
                params_default[key] = current_value

        # update param is new ...
        else:
            # template default value its different from specified cmd arg
            if in_fargs and default_value != fargs_value:
                value = fargs_value
                params_changed[key] = value

            # no cmd arg for new param
            # should never be here make a change to enforce param
            # in add_stack_params_as_args
            else:
                # get template default value
                value = default_value
                params_added[key] = default_value

        # append dictionary element to list
        istack.action_parameters.append(
            {
                'ParameterKey': key,
                'ParameterValue': value,
            } if istack.create else
            {
                'ParameterKey': key,
                'ParameterValue': value,
                'UsePreviousValue': use_previous_value,
            }
        )

        # update resolved parameter final value istack.r_parameters
        istack.r_parameters[key] = (current_value
                                    if use_previous_value else value)


# get stack outputs as dict
def get_stack_outputs():
    stack_outputs = istack.stack.outputs
    last_updated_time = istack.stack.last_updated_time
    outputs_current = {}

    if stack_outputs:
        for output in stack_outputs:
            key = output['OutputKey']
            value = (output['OutputValue']
                     if 'OutputValue' in output else None)
            outputs_current[key] = value

    outputs_current['StackStatus'] = istack.stack.stack_status
    outputs_current['StackName'] = fargs.stack
    if last_updated_time:
        outputs_current['LastUpdatedTime'] = last_updated_time.strftime(
            '%Y-%m-%d %X %Z')

    return outputs_current


# show stack current outputs as dict
def show_stack_outputs(when):
    outputs = getattr(istack, when)['outputs']

    print('\n')
    mylog(
        '%s - Stack Outputs\n%s' % (when.capitalize(), pformat(
            outputs,
            width=80 if (
                fargs.action == 'info' and not fargs.compact) else 1000000
        ))
    )
    print('\n')


# store stack info - ouputs, resources
def store_stack_info(when):
    value = {}
    setattr(istack, when, value)

    value['outputs'] = get_stack_outputs()
    value['resources'] = get_resources()


def store_stack_info_changed():
    istack.stack.reload()
    store_stack_info('after')

    istack.changed = {}
    istack.changed['resources'] = get_resources_changed()
    istack.changed['outputs'] = get_outputs_changed()


# show stack parameters override
def show_stack_params_override(stack_parameters):
    params = {}
    for p in istack.stack.parameters:
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
            width=80 if (
                fargs.action == 'info' and not fargs.compact) else 1000000
        )
    )
    print('\n')


# build tags for update
def do_action_tags():
    stack_tags = [
        {'Key': 'Env', 'Value': fargs.Env},
        {'Key': 'EnvRole', 'Value': fargs.EnvRole},
        {'Key': 'EnvStackVersion', 'Value': fargs.version},
        {'Key': 'EnvApp1Version', 'Value': fargs.EnvApp1Version},
    ] if istack.create else istack.stack.tags

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


# do stack update
def update_stack(us_args):
    response = istack.stack.update(**us_args)
    return response


def create_stack(us_args):
    response = client.create_stack(**us_args)
    return response


def cancel_update_stack():
    response = istack.stack.cancel_update()
    return response


def delete_stack():
    response = istack.stack.delete()
    return response


def continue_update_stack():
    response = client.continue_update_rollback(
        StackName=istack.name,
        ResourcesToSkip=fargs.ResourcesToSkip,
    )
    return response


# get timestamp from last event available
def get_last_event_timestamp():
    last_event = list(istack.stack.events.all().limit(1))[0]

    return last_event.timestamp


# show old and new service tasks during an update
def show_service_update(service_logical_resource_id):
    service = task = cluster = deps_before = None
    deployment_task = ''
    deployments_len = pendingCount = 0
    client = boto3.client('ecs')

    try:
        cluster = istack.stack.Resource(
            'ScalableTarget').physical_resource_id.split('/')[1]
        service = istack.stack.Resource(
            service_logical_resource_id).physical_resource_id
    except:
        return

    deps = {
        'PRIMARY': {},
        'ACTIVE': {},
    }
    while task != deployment_task or deployments_len > 1 or pendingCount != 0:
        istack.stack.reload()
        task = istack.stack.Resource('TaskDefinition').physical_resource_id
        response = client.describe_services(
            cluster=cluster,
            services=[service],
        )
        deployments = response['services'][0]['deployments']
        deployments_len = len(deployments)
        for dep in deployments:
            status = dep['status']
            for p in [
                    'desiredCount', 'runningCount',
                    'pendingCount', 'taskDefinition']:
                deps[status][p] = dep[p]

        deployment_task = deps['PRIMARY']['taskDefinition']
        pendingCount = deps['PRIMARY']['pendingCount']

        if str(deps) != deps_before:
            deps_before = str(deps)
            for d in ['PRIMARY', 'ACTIVE']:
                if 'taskDefinition' in deps[d]:
                    deps[d]['taskDefinition'] = deps[d][
                        'taskDefinition'].split('/')[-1]
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
def show_update_events(timestamp):
    event_iterator = istack.stack.events.all()
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
        if (event.logical_resource_id == 'Service' and
                event.resource_status == 'UPDATE_IN_PROGRESS' and
                event.resource_status_reason is None):
            show_service_update(event.logical_resource_id)

    if len(event_list) > 0:
        return(event_list.pop().timestamp)

    return timestamp


# wait update until complete showing events status
def update_waiter(timestamp):
    last_timestamp = timestamp
    istack.stack.reload()

    # return without waiting
    if fargs.nowait:
        return

    while istack.stack.stack_status not in [
        'UPDATE_COMPLETE',
        'CREATE_COMPLETE',
        'ROLLBACK_COMPLETE',
        'UPDATE_ROLLBACK_COMPLETE',
        'UPDATE_ROLLBACK_FAILED',
        'DELETE_COMPLETE',
        'DELETE_FAILED',
    ]:
        istack.stack.reload()
        last_timestamp = show_update_events(last_timestamp)
        time.sleep(5)


# build/update full_args from argparse arg objects
def do_fargs(args):
    for property, value in vars(args).items():
        # fix to avoid overwriting Env and EnvRole with None value
        if not hasattr(fargs, property):
            setattr(fargs, property, value)


# build all args for action
def do_action_args():
    us_args = {}
    if istack.create:
        us_args['StackName'] = istack.name
    us_args['Parameters'] = istack.action_parameters
    us_args['Tags'] = istack.action_tags
    us_args['Capabilities'] = [
        'CAPABILITY_IAM',
        'CAPABILITY_NAMED_IAM',
        'CAPABILITY_AUTO_EXPAND',
    ]

    # sns topic
    if fargs.topic:
        us_args['NotificationARNs'] = [fargs.topic]

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


# create changeset
def do_changeset(us_args):
    if not fargs.showtags:
        # keep existing stack.tags so that they are excluded from changeset
        # (not the new prepared ones)
        us_args['Tags'] = istack.stack.tags

    us_args['StackName'] = istack.name
    us_args['ChangeSetName'] = (
        'CS-%s' % time.strftime('%Y-%m-%dT%H-%M-%S')
    )
    us_args.pop('StackPolicyDuringUpdateBody', None)

    response = client.create_change_set(**us_args)

    return response['Id']


def get_changeset(changeset_id):
    changeset = client.describe_change_set(
        ChangeSetName=changeset_id,
        StackName=istack.name
    )
    return changeset


# wait until changeset is created
def changeset_waiter(changeset_id):
    changeset = get_changeset(changeset_id)
    while changeset['Status'] not in [
            'CREATE_COMPLETE',
            'UPDATE_ROLLBACK_FAILED',
            'FAILED'
    ]:
        time.sleep(3)
        changeset = get_changeset(changeset_id)


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
                if ('CausingEntity' in i and
                        'Name' in i['Target'] and
                        i['CausingEntity'] not in causingentity):
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
        table.add_row([
            'None' if i in fileds_ex and row['Action'] != 'Modify'
            else row[i] for i in fields])

    mylog('ChangeSet:')
    print(table.get_string(fields=fields))


def delete_changeset(changeset_id):
    response = client.delete_change_set(
        ChangeSetName=changeset_id,
        StackName=istack.name
    )

    return response


def execute_changeset(changeset_id):
    response = client.execute_change_set(
        ChangeSetName=changeset_id,
        StackName=istack.name
    )

    return response


def show_confirm():
    if fargs.noconfirm:
        return True
    print("")
    answer = input('Digit [y] to continue or any other key to exit: ')
    if not answer or answer[0].lower() != 'y':
        return False
    else:
        return True


def show_log(time_delta):
    time_event = istack.last_event_timestamp - timedelta(days=time_delta)

    if time_delta == 0:
        update_waiter(time_event)
    else:
        show_update_events(time_event)


def find_s3_files(name, sub_string):
    if ('AWS::AutoScaling::LaunchConfiguration' in istack.t_resources and
            istack.t_resources[
                'AWS::AutoScaling::LaunchConfiguration'] == name):
        data = sub_string[8:].partition('/')
        host = data[0]
        if not host.endswith('amazonaws.com'):
            return
        key = data[2]
        s_bucket = host.rsplit('.', 3)
        if s_bucket[1].startswith('s3-'):
            bucket = s_bucket[0]
        else:
            bucket = host[:host.rfind('.s3.')]

        if host == bucket:
            return

        istack.s3_files.add((bucket, key))


def check_s3_files():
    s3 = boto3.client('s3')
    for f in istack.s3_files:
        bucket = f[0]
        key = f[1]
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except botocore.exceptions.ClientError as e:
            print('%s/%s' % (bucket, key))
            raise IboxError(e)


def check_ecr_images():
    name = istack.t_resources['AWS::ECS::TaskDefinition']
    images = []
    ecr = boto3.client('ecr')

    for c in istack.r_resources[name]['Properties']['ContainerDefinitions']:
        image = c['Image']
        registry_id = image[0:image.find('.')]
        repository_name = image[image.find('/')+1:image.find(':')]
        image_id = image[image.find(':') + 1:]
        # Skip already processed images and images from public docker repo
        if (image not in images and
                registry_id != f'{repository_name}:'):
            try:
                ecr.describe_images(
                    registryId=registry_id,
                    repositoryName=repository_name,
                    imageIds=[{
                        'imageTag': image_id,
                    }],
                )
                images.append(image)
            except botocore.exceptions.ClientError as e:
                print(image)
                raise IboxError(e)


# method should be identically to the one found in bin/ibox_add_to_dash.py,
# but dash param default to None
def get_resources(dash=None):
    resources = {}
    res_list = list(map_resources_on_dashboard.keys())

    paginator = client.get_paginator('list_stack_resources')
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

                if dash and map_resources_on_dashboard[res_lid]:
                    res_lid = map_resources_on_dashboard[res_lid]

                resources[res_lid] = res_pid

    return resources


def get_resources_changed():
    before = istack.before['resources']
    after = istack.after['resources']

    changed = {}
    for r, v in before.items():
        if r in after and v != after[r]:
            changed[r] = after[r]

    return changed


def get_outputs_changed():
    before = istack.before['outputs']
    after = istack.after['outputs']

    changed = {}
    for o, v in after.items():
        if o in before and v != before[o]:
            changed[o] = before[o] + ' => ' + v

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
        # if all(key in exports for key in ['BucketAppRepository']):
        #    return exports

    return exports


def do_update_dashboard(cw, resources_changed, mode, dashboard_name):
    dashboard_body = cw.get_dashboard(
        DashboardName=dashboard_name)['DashboardBody']
    dashboard_body_dict = json.loads(dashboard_body)

    stackname_arr = istack.name.split('-')
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
            for r, u in resources_changed.items():
                for l in set([2, len(my_metric) - 2]):
                    m_name = my_metric[l]
                    if map_resources_on_dashboard[r] == m_name:
                        m_value_index = int(l) + 1
                        m_value = my_metric[m_value_index]
                        if (m_value.startswith(stack_prefix) or
                                '/' + stack_prefix in m_value):
                            out_msg = '%s\t%s: %s --> %s\n' % (
                                out_msg, m_name, m_value, u)
                            my_metric[m_value_index] = u
                            dashboard_body_dict['widgets'][k][
                                'properties']['metrics'][j] = my_metric
                            changed = True
            my_metrics.append(my_metric)

    if changed:
        out = cw.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(
                dashboard_body_dict, separators=(',', ':'))
        )
        if len(out['DashboardValidationMessages']) > 0:
            pprint(out)
        else:
            print('\n')
            mylog('CloudWatch-DashBoard[%s] Updated:' % dashboard_name)
            print(out_msg)

    return True


def update_dashboards():
    cw_client = boto3.client('cloudwatch')

    response_dash = cw_client.list_dashboards(DashboardNamePrefix='_')

    if fargs.dashboard == 'OnChange':
        resources = istack.changed['resources']
        mode = ''
    elif fargs.dashboard in ['Always', 'Generic']:
        resources = istack.after['resources']
        mode = fargs.dashboard
    else:
        return

    if (not resources and
            'ScalingPolicyTrackings' not in istack.changed['outputs']):
        return

    # Update dynamic one
    for dash in response_dash['DashboardEntries']:
        if istack.name in dash['DashboardName']:
            # If imported ibox_add_to_dash.py, execute it as external module
            # in silent mode, rebuilding the dash from scratch ..
            if add_to_dashboard:
                dashboard_param_stacks = dash['DashboardName'].split('_')[1:]
                dashboard_params = ['--stack'] + dashboard_param_stacks + [
                    '--silent']
                dashboard_parser = ibox_add_to_dash.get_parser()
                dashboard_args = dashboard_parser.parse_args(dashboard_params)
                ibox_add_to_dash.main(dashboard_args)
            # ... if not use the old method (no more maintained)
            elif resources:
                do_update_dashboard(
                    cw_client, resources, mode, dash['DashboardName'])

    # Update fixed one
    if resources:
        for dash in DashBoards:
            do_update_dashboard(cw_client, resources, mode, dash)


def mylog(string):
    message = f'{istack.name} # {string}'
    print(message)

    if (
        fargs.action != 'info' and
        fargs.slack_channel and
        slack_client and
        'IBOX_SLACK_TOKEN' in os.environ and
        'IBOX_SLACK_USER' in os.environ
    ):
        slack_web = slack.WebClient(token=os.environ['IBOX_SLACK_TOKEN'])
        ac = slack_web.chat_postMessage(
            channel=f'#{fargs.slack_channel}',
            text=message,
            username=os.environ['IBOX_SLACK_USER'],
            icon_emoji=':robot_face:',
        )


def update_template_param():
    # try to get role from fargs or use current stack parameter value
    try:
        role = fargs.EnvRole
    except:
        role = istack.c_parameters['EnvRole']

    app_repository = istack.exports['BucketAppRepository']
    s3_prefix = 'ibox/%s/templates/%s.' % (fargs.version, role)
    s3 = boto3.client('s3')

    try:
        response = s3.list_objects_v2(Bucket=app_repository, Prefix=s3_prefix)
        fargs.template = 'https://%s.s3.amazonaws.com/%s' % (
            app_repository, response['Contents'][0]['Key'])
    except Exception:
        raise IboxError(
            f'Error retrieving stack template with prefix: {s3_prefix}')


def do_changeset_actions(us_args):
    # -create changeset
    changeset_id = do_changeset(us_args.copy())
    print('\n')
    mylog('ChangeSetId: %s' % changeset_id)
    print('\n')
    time.sleep(1)
    mylog('Waiting ChangeSet Creation..')

    # -wait changeset creation
    changeset_waiter(changeset_id)

    # -get changeset
    changeset = get_changeset(changeset_id)
    # pprint(changeset)

    # -parse changeset changes
    changeset_changes = parse_changeset(changeset)

    # -show changeset changes
    if have_prettytable:
        show_changeset_changes(changeset_changes)

    # -delete changeset
    delete_changeset(changeset_id)

    if not fargs.dryrun and show_confirm():
        # execute_changeset(changeset_id)
        return True
    else:
        return None
        # delete_changeset(changeset_id)


def get_stack():
    try:
        stack = cloudformation.Stack(fargs.stack)
        stack.stack_status
    except Exception as e:
        raise IboxError(e)

    return stack


# Get template and set istack.template_from (S3|File|Current)
def get_template():
    try:
        # New template
        if fargs.template:
            template = str(fargs.template)
            # From s3
            if template.startswith('https'):
                url = template[template.find('//') + 2:]
                s3 = boto3.client('s3')
                bucket = url[:url.find('.')]
                key = url[url.find('/') + 1:]

                response = s3.get_object(Bucket=bucket, Key=key)
                body = response['Body'].read()
                istack.template_from = 'S3'
            # From file
            else:
                f = open(fargs.template[7:], 'r')
                body = f.read()
                istack.template_from = 'File'
        # Current template
        else:
            response = client.get_template(StackName=istack.name)
            body = json.dumps(response['TemplateBody'])
            istack.template_from = 'Current'

    except Exception as e:
        raise IboxError(f'Error retrieving template: %s {e}')
    else:
        template = json.loads(body)

    return template


def resolve_sub(name, value):
    if isinstance(value, list):
        sub_string = value[0]
        sub_data = value[1]
    else:
        sub_string = value
        sub_data = ''

    while True:
        found = sub_string.find('${')
        if found == -1:
            break
        find_start = found + 2
        find_end = sub_string[find_start:].find('}') + find_start
        key = sub_string[find_start:find_end]
        replace_from = '${' + key + '}'

        if key in sub_data:
            r_value = recursive_resolve(key, sub_data[key])
            replace_to = r_value
        elif key in istack.r_parameters:
            replace_to = istack.r_parameters[key]
        elif key == 'AWS::Region':
            replace_to = boto3.region_name
        else:
            replace_to = key

        sub_string = sub_string.replace(replace_from, str(replace_to))

    if sub_string.startswith('https://'):
        find_s3_files(name, sub_string)

    return sub_string


def resolve_if(name, v):
    value = v[1] if istack.r_conditions[v[0]] else v[2]

    return recursive_resolve(name, value)


def resolve_ref(name, v):
    if v == 'AWS::Region':
        value = boto3.region_name
    else:
        value = istack.r_parameters[v] if v in istack.r_parameters else v

    return value


def resolve_import(name, v):
    value = recursive_resolve(name, v)

    return istack.exports[value]


def resolve_findinmap(name, v):
    mapname = recursive_resolve(name, v[0])
    key = recursive_resolve(name, v[1])
    key_value = recursive_resolve(name, v[2])

    return str(istack.mappings[mapname][key][key_value])


def resolve_join(name, v):
    j_list = []
    for n in v[1]:
        j_list.append(recursive_resolve(name, n))

    return v[0].join(j_list)


def resolve_select(name, v):
    index = v[0]
    s_list = recursive_resolve(name, v[1])

    try:
        value = s_list[index]
    except:
        value = s_list

    return value


def resolve_split(name, v):
    delimeter = v[0]
    s_string = recursive_resolve(name, v[1])

    return s_string.split(delimeter)


def resolve_or(name, v):
    o_list = []
    for n in v:
        o_list.append(recursive_resolve(name, n))

    return any(o_list)


def resolve_and(name, v):
    o_list = []
    for n in v:
        o_list.append(recursive_resolve(name, n))

    return all(o_list)


def resolve_equals(name, v):
    first_value = str(recursive_resolve(name, v[0]))
    second_value = str(recursive_resolve(name, v[1]))

    return True if first_value == second_value else False


def resolve_not(name, v):
    value = True if not recursive_resolve(name, v[0]) else False

    return value


def resolve_condition(name, v):
    istack.r_conditions[v] = recursive_resolve(name, istack.conditions[v])

    return istack.r_conditions[v]


def awsnovalue(value):
    if value == 'AWS::NoValue':
        return True

    return False


def recursive_resolve(name, value):
    if isinstance(value, (dict, OrderedDict)):
        r_root = {}
        for r, v in value.items():
            if r == 'Fn::If':
                return resolve_if(name, v)
            elif r == 'Ref':
                return resolve_ref(name, v)
            elif r == 'Fn::GetAtt':
                return '%s.%s' % (v[0], v[1])
            elif r == 'Fn::ImportValue':
                return resolve_import(name, v)
            elif r == 'Fn::Sub':
                return resolve_sub(name, v)
            elif r == 'Fn::FindInMap':
                return resolve_findinmap(name, v)
            elif r == 'Fn::Join':
                return resolve_join(name, v)
            elif r == 'Fn::Select':
                return resolve_select(name, v)
            elif r == 'Fn::Split':
                return resolve_split(name, v)
            elif r == 'Fn::Or':
                return resolve_or(name, v)
            elif r == 'Fn::And':
                return resolve_and(name, v)
            elif r == 'Fn::Equals':
                return resolve_equals(name, v)
            elif r == 'Fn::Not':
                return resolve_not(name, v)
            elif r == 'Condition' and isinstance(v, str):
                return resolve_condition(name, v)
            else:
                r_value = recursive_resolve(name, v)

                if not awsnovalue(r_value):
                    r_root[r] = r_value

        return r_root

    elif isinstance(value, list):
        r_root = []
        for n, l in enumerate(value):
            r_value = recursive_resolve(n, l)

            if not awsnovalue(r_value):
                r_root.append(r_value)

        return r_root

    elif isinstance(value, (int, str)):

        return value


def process_resources():
    istack.r_resources = {}
    istack.t_resources = {}
    istack.s3_files = set()

    for r in sorted(istack.resources):
        v = istack.resources[r]
        if not ('Condition' in v and not istack.r_conditions[v['Condition']]):
            try:
                del v['Condition']
            except:
                pass
            istack.t_resources[v['Type']] = r
            istack.r_resources[r] = recursive_resolve(r, v)

    if fargs.debug:
        pprint(istack.r_resources)
        pprint(istack.t_resources)
        exit(0)

    if istack.s3_files:
        check_s3_files()

    if 'AWS::ECS::TaskDefinition' in istack.t_resources:
        check_ecr_images()


def process_conditions():
    istack.r_conditions = {}
    for c in sorted(istack.conditions):
        v = istack.conditions[c]
        if c not in istack.r_conditions:
            istack.r_conditions[c] = recursive_resolve(c, v)


def process_parameters():
    # add stack parameters as argparse args and update fargs
    add_stack_params_as_args()

    # if template include EnvShort params force its value based on the Env one
    if 'EnvShort' in istack.parameters:
        force_envshort()

    # if using template option set/force EnvStackVersion
    if fargs.template:
        do_envstackversion_from_s3_template()

    # unchanged stack params
    params_default = {}

    # changed stack params
    params_changed = {}

    # new stack params - default value
    params_added = {}

    # forced to default stack params - current value not in allowed ones
    params_forced_default = {}

    # list of final parameters args to use for executing action
    # as dict with ParameterKey ParameterValue keys
    # Ex for EnvRole=cache:
    # [{u'ParameterKey': 'EnvRole', u'ParameterValue': 'cache'}, {...}]
    istack.action_parameters = []

    # final resolved value stack parameters - {name: value} dictionary
    istack.r_parameters = {}

    # set final parameters values to use for exectuing action -
    # istack.action_parameters and istack.r_parameters
    set_action_parameters(params_default, params_changed,
                          params_added, params_forced_default)

    # show changes to output
    print('\n')
    if istack.create and params_default:
        print('Default - Stack Parameters\n%s\n' % pformat(
            params_default, width=1000000))

    if params_changed:
        mylog('Changed - Stack Parameters\n%s' % pformat(
            params_changed, width=1000000))
        print('\n')

    if not istack.create and params_added:
        mylog('Added - Stack Parameters\n%s' % pformat(
            params_added, width=1000000))
        print('\n')

    if params_forced_default:
        mylog('Forced to Default - Stack Parameters\n%s' % pformat(
            params_forced_default, width=1000000))
        print('\n')


def try_template_section(name):
    try:
        section = istack.template[name]
    except:
        section = None

    return section


def do_action_params():
    istack.parameters = try_template_section('Parameters')
    istack.conditions = try_template_section('Conditions')
    istack.mappings = try_template_section('Mappings')
    istack.resources = istack.template['Resources']

    # process parameters: update fargs, istack.r_parameters
    # and istack.action_parameters and show changes
    logger.info('Processing Parameters')
    process_parameters()

    try:
        # resolve conditions
        logger.debug('Processing Conditions')
        process_conditions()

        # resolve resources
        logger.debug('Processing Resources')
        process_resources()
    except IboxError:
        raise
    except Exception as e:
        pprint(e)
        logger.warning('Error resolving template. '
                       'Will not be able to validate s3 files and ecr images.')


def get_args_for_action():
    # get cloudformation exports
    logger.info('Getting CloudFormation Exports')
    istack.exports = get_cloudformation_exports(client)

    # get current version parameters value - if creating return empty dict
    logger.info('Getting Parameters current values')
    istack.c_parameters = get_parameters_current()

    # update template param if using version one
    if fargs.version:
        update_template_param()

    # get template body supplied or current one
    logger.info('Getting Template Body')
    istack.template = get_template()

    # set istack.action_parameters - parameters args for action
    do_action_params()

    # -build tags
    do_action_tags()

    # -build all args for action
    us_args = do_action_args()
    # pprint(us_args)

    return us_args


def do_action_update():
    # get final args for update/create
    us_args = get_args_for_action()

    # store stack info - ouputs, resources, last update time
    store_stack_info('before')

    # show stack outputs
    show_stack_outputs('before')

    # -if using changeset ...
    if not fargs.noconfirm:
        do_update = do_changeset_actions(us_args)
        if not do_update:
            return

    # -do update
    update_response = update_stack(us_args)
    mylog(json.dumps(update_response))
    time.sleep(1)

    # -show update status until complete
    update_waiter(istack.last_event_timestamp)

    # store stack info changed
    store_stack_info_changed()

    # show changed stack outputs
    show_stack_outputs('changed')

    # update dashboards
    update_dashboards()


def do_action_create():
    # get final args for update/create
    us_args = get_args_for_action()

    if show_confirm():
        create_response = create_stack(us_args)
        print(create_response)
        time.sleep(1)

        istack.stack = cloudformation.Stack(fargs.stack)
        istack.last_event_timestamp = get_last_event_timestamp()

        # -show update status until complete
        update_waiter(istack.last_event_timestamp)


def do_action_info():
    # -get stack parameters from current stack
    stack_parameters = client.get_template_summary(
        StackName=fargs.stack)['Parameters']

    # store stack info - ouputs, resources, last update time
    store_stack_info('current')

    # show stack output
    show_stack_outputs('current')
    show_stack_params_override(stack_parameters)


def do_action_log():
    show_log(int(fargs.day))


def do_action_cancel():
    cancel_response = cancel_update_stack()
    mylog(json.dumps(cancel_response))
    time.sleep(1)

    # -show update status until complete
    update_waiter(istack.last_event_timestamp)


def do_action_delete():
    print('WARNING - DELETING STACK %s  - WARNING' % istack.name)
    if show_confirm():
        # -do delete
        delete_response = delete_stack()
        mylog(json.dumps(delete_response))
        time.sleep(1)

        # -show update status until complete
        try:
            update_waiter(istack.last_event_timestamp)
        except:
            return


def do_action_continue():
    # -do continue_update
    continue_response = continue_update_stack()
    mylog(json.dumps(continue_response))
    time.sleep(1)

    # -show update status until complete
    update_waiter(istack.last_event_timestamp)


# main program function
def run(args):
    global istack
    global boto3
    global fargs
    global client
    global cloudformation

    # init class for full args program args + stack args
    fargs = full_args()

    # init istack class
    istack = ibox_stack()

    do_fargs(args[0])

    # set region from parameter if exist
    kwarg_session = {}
    if fargs.region:
        kwarg_session['region_name'] = fargs.region
    boto3 = base_boto3.session.Session(**kwarg_session)

    # create boto3 client/resource
    cloudformation = boto3.resource('cloudformation')
    client = boto3.client('cloudformation')

    # -set stack name used for logging with stack name prepended
    istack.name = fargs.stack
    istack.args = args[1]

    istack.create = None

    if fargs.action == 'create':
        istack.create = True
        istack.stack = None
        do_action_create()
    else:
        # get stack resource
        istack.stack = get_stack()

        # get last_event_time
        istack.last_event_timestamp = get_last_event_timestamp()

        if fargs.action == 'update':
            do_action_update()
        if fargs.action == 'info':
            do_action_info()
        if fargs.action == 'log':
            do_action_log()
        if fargs.action == 'cancel':
            do_action_cancel()
        if fargs.action == 'delete':
            do_action_delete()
        if fargs.action == 'continue':
            do_action_continue()

    if fargs.action != 'delete' and istack.stack:
        return istack.stack.stack_status

    return True


def main(args):
    try:
        result = run(args)
        return result
    except IboxError as e:
        logging.error(e.args[0])


if __name__ == "__main__":
    parser = get_parser()
    # -get cmd args as argparse objects
    # args[0] contain know arguments args[1] the unkown remaining ones
    args = parser.parse_known_args(sys.argv[1:])
    result = main(args)
    if not result:
        exit(1)
