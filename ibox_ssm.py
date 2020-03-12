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

logging.basicConfig()
logger = logging.getLogger('ibox')
logger.setLevel(logging.INFO)

SSM_PATH = '/ibox'


# full args
class full_args(object):
    pass


# ibox stack
class ibox_stack(object):
    def __init__(self):
        self.c_parameters = {}
        self.stack = None


def get_arg_stackname():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-s', '--stack',
                        help='Stack Name', type=str)
    parser.add_argument('-v', '--version',
                        help='Stack Env Version',
                        type=str)

    args = parser.parse_known_args()

    return args[0]


# parse main argumets
def get_args():
    parser = argparse.ArgumentParser(
        description='SSM Parameters override for Stack Replicator',
        epilog='Note: options for Stack Params must be put at the end!')

    # common args

    # subparser
    subparsers = parser.add_subparsers(help='Desired Action',
                                       dest='action', required=True)

    # setup parser
    parser_setup = subparsers.add_parser('setup',
                                         help='Setup Regions')

    parser_setup.add_argument('-r', '--regions',
                              help='Regions', type=str,
                              required=True, default=[], nargs='+')

    parser_setup.add_argument('-s', '--stack',
                              help='Stack Name', type=str)

    # putshow parser args - common to put and show
    parser_putshow = argparse.ArgumentParser(add_help=False)

    parser_putshow.add_argument('-s', '--stack',
                                help='Stack Name', required=True, type=str)

    # put parser
    parser_put = subparsers.add_parser('put',
                                       help='Put Parameters - '
                                            'leave empty for a list',
                                       parents=[parser_putshow])

    parser_put.add_argument('-r', '--regions',
                            help='Regions', type=str,
                            required=True, default=[], nargs='+')

    parser_put.add_argument('-R', '--EnvRole',
                            help='Stack Role', type=str,
                            required=True if fargs.version and
                            'EnvRole' not in istack.c_parameters else False)

    template_version_group = parser_put.add_mutually_exclusive_group(
        required=False if istack.stack else True)
    template_version_group.add_argument('-t', '--template',
                                        help='Template Location',
                                        type=str)
    if 'BucketAppRepository' in istack.exports:
        template_version_group.add_argument('-v', '--version',
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

    if not istack.args:
        parser.print_help()
        exit(0)
    else:
        istack.p_args = parser.parse_args(istack.args)
        do_fargs(istack.p_args)


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


# build/update full_args from argparse arg objects
def do_fargs(args):
    for property, value in vars(args).items():
        # fix to avoid overwriting Env and EnvRole with None value
        if not hasattr(fargs, property):
            setattr(fargs, property, value)


def get_cloudformation_exports():
    logger.info('Getting CloudFormation Exports')
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


def update_template_param():
    # try to get role from fargs or use current stack parameter value
    if fargs.EnvRole:
        role = fargs.EnvRole
    else:
        role = istack.c_parameters['EnvRole']

    app_repository = istack.exports['BucketAppRepository']
    s3_prefix = f'ibox/{fargs.version}/templates/{role}.'
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


def try_template_section(name):
    try:
        section = istack.template[name]
    except:
        section = None

    return section


def put_ssm_parameter(param):
    resp = ssm.put_parameter(Name=param['name'],
                             Description=param['desc'],
                             Value=param['value'],
                             Type='String',
                             Overwrite=True,
                             Tier='Standard')


def get_ssm_parameter(param):
    resp = ssm.get_parameter(Name=param)

    return resp['Parameter']['Value']


def get_ssm_parameters_by_path(path):
    params = {}
    paginator = ssm.get_paginator('get_parameters_by_path')
    response_iterator = paginator.paginate(Path=path)

    for page in response_iterator:
        for p in page['Parameters']:
            name = p['Name']
            name = name.split('/')[3]
            value = p['Value']

            params[name] = value

    return params


def set_region(region):
    global ssm

    kwarg_session = {}
    kwarg_session['region_name'] = region
    myboto3 = boto3.session.Session(**kwarg_session)
    ssm = myboto3.client('ssm')


def get_stack():
    cloudformation = boto3.resource('cloudformation')
    try:
        stack = cloudformation.Stack(fargs.stack)
        stack.stack_status
    except Exception as e:
        return None

    return stack


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


def get_parameters_from_template():
    # update template param if using version one
    if fargs.version:
        update_template_param()

    logger.info('Getting Template Body')
    istack.template = get_template()

    istack.parameters = try_template_section('Parameters')
    add_stack_params_as_args()
    # if using template option set/force EnvStackVersion
    if fargs.template:
        do_envstackversion_from_s3_template()


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
        put_ssm_parameter(param)


def get_setupped_regions():
    set_region(current_region)
    try:
        rgs = get_ssm_parameter(f'{SSM_PATH}/{fargs.stack}/regions')
    except Exception as e:
        rgs = get_ssm_parameter(f'{SSM_PATH}/regions')

    params = []

    return rgs.split()


def do_action_put():
    get_parameters_from_template()
    regions = get_setupped_regions()
    params = []

    for n, v in vars(istack.p_args).items():
        if not v:
            continue
        param = {}
        param['name'] = f'{SSM_PATH}/{fargs.stack}/{n}'
        param['desc'] = istack.parameters[n]['Description']
        param['value'] = v

        params.append(param)

    # check if is passed as param a list of regions
    # and use them, but only for regions that do alredy exist
    # in ssm regions parameter.
    if fargs.regions:
        rgs = []
        for r in fargs.regions:
            if r in regions:
                rgs.append(r)
        regions = rgs

    for r in regions:
        logger.info(f'Inserting SSM Parameters in {r}')
        set_region(r)
        for p in params:
            put_ssm_parameter(p)


def do_action_show():
    regions = get_setupped_regions()
    params_map = {}
    params_keys = []
    first_column = None
    table = PrettyTable()
    table.padding_width = 1

    for r in regions:
        set_region(r)
        params_map[r] = get_ssm_parameters_by_path(
            f'{SSM_PATH}/{fargs.stack}')
        params_keys.extend(list(params_map[r].keys()))

    params_keys = sorted(list(set(params_keys)))
    table.add_column('Parameter', params_keys)

    for r, v in params_map.items():
        params_values = []
        for n in params_keys:
            if n in v:
                params_values.append(v[n])
            else:
                params_values.append('')
        table.add_column(r, params_values)

    table.align['Parameter'] = 'l'
    print(table)


# main program function
def run():
    global istack
    global fargs
    global client
    global cloudformation
    global current_region

    session = boto3.session.Session()
    current_region = session.region_name

    client = boto3.client('cloudformation')

    # init istack class
    istack = ibox_stack()
    istack.exports = get_cloudformation_exports()

    # init class for full args program args + stack args
    fargs = full_args()

    # get arg stack_name if present
    do_fargs(get_arg_stackname())

    if fargs.stack:
        istack.name = fargs.stack
        istack.stack = get_stack()
        if istack.stack:
            logger.info('Getting Parameters current values')
            istack.c_parameters = get_parameters_current()

    # -get cmd args as argparse objects
    args = get_args()
    istack.args = args[1]

    do_fargs(args[0])

    if fargs.action == 'setup':
        do_action_setup()
    if fargs.action == 'put':
        do_action_put()
    if fargs.action == 'show':
        do_action_show()

if __name__ == "__main__":
    run()
