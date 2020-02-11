#!/usr/bin/env python3
import json
import logging
import boto3
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
from prettytable import PrettyTable, ALL as ptALL


SSM_PATH='/ibox'

# full args
class full_args(object):
    pass


# ibox stack
class ibox_stack(object):
    pass


# parse main argumets
def get_args():
    parser = argparse.ArgumentParser(
        description='SSM Parameters Distribution for ibox_stackops',
        epilog='Note: options for Stack Params must be put at the end!')

    # common args

    # subparser
    subparsers = parser.add_subparsers(help='Desired Action', dest='action')

    # setup parser
    parser_setup = subparsers.add_parser('setup',
                                          help='Setup Regions Distribution')

    parser_setup.add_argument('-r', '--regions',
                              help='Regions', type=str,
                              required=True, default=[], nargs='+')

    parser_setup.add_argument('-s', '--stack',
                              help='Stack Name', type=str)

    # putshow parser args - common to put and show
    parser_putshow = argparse.ArgumentParser(add_help=False)

    parser_putshow.add_argument('-s', '--stack',
                                help='Stack Name', required=True, type=str)

    parser_putshow.add_argument('-R', '--EnvRole',
                                help='Stack Role',
                                type=str, required=True)

    # put parser
    parser_put = subparsers.add_parser('put',
                                       help='Put Parameters',
                                       parents=[parser_putshow])

    parser_put.add_argument('-r', '--regions',
                            help='Regions', type=str, default=[], nargs='+')

    template_version_group_put = parser_put.add_mutually_exclusive_group(
        required=True)
    template_version_group_put.add_argument('-t', '--template',
                                            help='Template Location',
                                            type=str)
    template_version_group_put.add_argument('-v', '--version',
                                            help='Stack Env Version',
                                            type=str)

    # show parser
    parser_show = subparsers.add_parser('show',
                                        help='Show Regions Distribution',
                                        parents=[parser_putshow])

    # args[0] contain know arguments args[1] the unkown remaining ones
    args = parser.parse_known_args()
    return args


# parse stack arguments, the args[1] from get_args() and update fargs
def add_stack_params_as_args():
    parser = argparse.ArgumentParser(
        description='',
        add_help=False,
        usage='Allowed Stack Params ... allowed values are in {}',
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # for parameter in sorted(
    #    stack_parameters, key=lambda x: x['ParameterKey']):
    for p in sorted(istack.parameters):
        v = istack.parameters[p]
        allowed_values = v['AllowedValues'] if 'AllowedValues' in v else []
        kwargs = {'type': str, 'metavar': '\t%s' % v['Description']}

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


# change list in a string new line separated element
def list_to_string_list(mylist):
    # unique_list = []
    # [unique_list.append(i) for i in mylist if i not in unique_list]
    joined_string = '\n'.join(mylist)
    mystring = joined_string if len(mylist) < 2 else '(' + joined_string + ')'

    return mystring


# build/update full_args from argparse arg objects
def do_fargs(args):
    for property, value in vars(args).items():
        # fix to avoid overwriting Env and EnvRole with None value
        if not hasattr(fargs, property):
            setattr(fargs, property, value)


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
    except Exception as e:
        print(f'Error retrieving stack template with prefix: {s3_prefix}')
        pprint(e)
        exit(1)


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
        print('Error retrieving template: %s' % e)
        exit(1)
    else:
        template = json.loads(body)

    return template


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
    if not fargs.nochangeset:
        do_changeset_actions(us_args)

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


def put_parameter(param):
   resp = ssm.put_parameter(Name=param['name'],
                            Description=param['desc'],
                            Value=param['value'],
                            Type='String',
                            Overwrite=True,
                            Tier='Standard')


def set_region(region):
    global ssm

    kwarg_session = {}
    kwarg_session['region_name'] = region
    myboto3 = boto3.session.Session(**kwarg_session)
    ssm = myboto3.client('ssm')
 

def do_action_setup():
    param = {}
    if fargs.stack:
        param['name'] = f'{SSM_PATH}/{fargs.stack}/regions'
    else:
        param['name'] = f'{SSM_PATH}/regions'

    param['desc'] = 'Regions where to replicate'
    param['value'] = ' '.join(fargs.regions)

    for r in fargs.regions:
        set_region(r)
        put_parameter(param)


# main program function
def run():
    global fargs
    global client
    global cloudformation

    # init class for full args program args + stack args
    fargs = full_args()

    # -get cmd args as argparse objects
    args = get_args()

    do_fargs(args[0])


    if fargs.action == 'setup':
        do_action_setup()


    # create boto3 client/resource
#    cloudformation = boto3.resource('cloudformation')
#    client = boto3.client('cloudformation')

    exit(0)

if __name__ == "__main__":
    run()
