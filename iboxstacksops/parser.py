import argparse
from . import cfg
from .actions import (create, update, parameters, resolve)


def set_create_parser(subparser, parents=[]):
    parser = subparser.add_parser('create',
                                  parents=parents,
                                  help='Create Stack')
    parser.set_defaults(func=create)
    
    parser.add_argument('--Env',
                        help='Environment to use',
                        type=str, required=True)
    parser.add_argument('--EnvRole',
                        help='Stack Role',
                        type=str, required=True)
    parser.add_argument('--EnvApp1Version',
                        help='App Version',
                        type=str, default='')



def set_update_parser(subparser, parents=[]):
    parser = subparser.add_parser('update',
                                  parents=parents,
                                  help='Update Stack')
    parser.set_defaults(func=update)

    parser.add_argument('-P', '--policy',
                        help='Policy during Stack Update',
                        type=str, choices=[
                            '*', 'Modify', 'Delete', 'Replace',
                            'Modify,Delete', 'Modify,Replace',
                            'Delete,Replace'])
    parser.add_argument('--dryrun',
                        help='Show changeset and exit',
                        action='store_true')
    parser.add_argument('-T', '--showtags',
                        help='Show tags changes in changeset',
                        action='store_true')
    parser.add_argument('-D', '--dashboard',
                        help='Update CloudWatch DashBoard',
                        choices=[
                            'Always', 'OnChange', 'Generic', 'None'],
                        default='OnChange')
    parser.add_argument('-d', '--showdetails',
                        help='Show extra details in changeset',
                        action='store_true')

    parser.add_argument(
        '-j', '--jobs',
	help='Max Concurrent jobs - default to number of stacks', type=int)
    parser.add_argument(
        '--pause',
        help='Pause for seconds between jobs - '
	     '0 for interactive - valid only for jobs=1',
        type=int)


def get_template_parser(required=True):
    parser = argparse.ArgumentParser(add_help=False)

    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument('--template',
                       help='Template Location',
                       type=str)
    group.add_argument('-v', '--version',
                       help='Stack Env Version',
                       type=str)

    return parser


def get_stack_selection_parser():
    parser = argparse.ArgumentParser(add_help=False)
    
    parser.add_argument(
        '-s', '--stack', nargs='+',
        help='Stack Names space separated',
        type=str, default=[])
    parser.add_argument(
        '-r', '--role', nargs='+',
        help='Stack Roles space separated',
        type=str, default=[])
    parser.add_argument(
        '-t', '--type', nargs='+',
        help='Stack Types space separated - use ALL for any type',
        type=str, default=[])

    return parser


# parse main argumets
def get_parser():
    parser = argparse.ArgumentParser(
        description='Stacks Operations',
        epilog='Note: options for Stack Params must be put at the end!'
    )
    parser.set_defaults(role=None, type=None, jobs=None, pause=None)

    # common parser
    parser.add_argument('--region',
                        help='Region', type=str)
    parser.add_argument('--compact',
                        help='Show Output in compact form',
                        action='store_true')

    # action parser
    action_parser = argparse.ArgumentParser(add_help=False)

    action_parser.add_argument('-N', '--noconfirm',
                               help='No confirmation',
                               required=False, action='store_true')
    action_parser.add_argument('-W', '--nowait',
                               help='Do not Wait for action to end',
                               required=False, action='store_true')
    action_parser.add_argument('-C', '--slack_channel',
                               help='Slack Channel [_cf_deploy]', nargs='?',
                               const='_cf_deploy', default=False)

    # template parser
    template_parser_create = get_template_parser()
    template_parser_update = get_template_parser(required=False)

    # stack selection parser
    stack_selection_parser = get_stack_selection_parser()

    # stack single parser
    stack_single_parser = argparse.ArgumentParser(add_help=False)
    stack_single_parser.add_argument(
        '-s', '--stack',
        help='Stack Name',
        required=True, type=str)

    # update create parser
    updcrt_parser = argparse.ArgumentParser(add_help=False)

    updcrt_parser.add_argument('--topics', nargs='+',
                               help='SNS Topics Arn for notification',
                               type=str, default=[])
    updcrt_parser.add_argument('-M', '--max_retry_ecs_service_running_count',
                               help='Max retry numbers when updating ECS '
                                    'service and runningCount is stuck to '
                                    'zero',
                               type=int, default=0)

    # command subparser
    command_subparser = parser.add_subparsers(
        help='Desired Command',
        required=True,
        dest='command')

    # create parser
    set_create_parser(
        command_subparser, [
            action_parser,
            template_parser_create,
            stack_single_parser,
            updcrt_parser,
        ])

    # update parser
    set_update_parser(
        command_subparser, [
            action_parser,
            template_parser_update,
            stack_selection_parser,
            updcrt_parser,
        ])

    # cancel_update parser
    parser_cancel = command_subparser.add_parser(
        'cancel',
        parents=[
            action_parser,
            stack_selection_parser],
        help='Cancel Update Stack')

    # delete parser
    parser_delete = command_subparser.add_parser(
        'delete',
        parents=[action_parser],
        help='Delete Stack (WARNING)')

    # continue_update parser
    parser_continue = command_subparser.add_parser(
        'continue',
        parents=[action_parser],
        help='Continue Update RollBack')
    parser_continue.add_argument(
        '--resources_to_Skip', '-R',
        help='Resource to Skip',
        default=[], nargs='+')

    # show parser
    parser_show = command_subparser.add_parser(
        'info', parents=[],
        help='Show Stack Info')

    # parameters parser
    parser_parameters = command_subparser.add_parser(
        'parameters', parents=[
            template_parser_update,
            stack_selection_parser],
        help='Show Available Stack Parameters')
    parser_parameters.set_defaults(func=parameters)

    
    # resolve parser
    parser_resolve = command_subparser.add_parser(
        'resolve', parents=[
            template_parser_update,
            stack_selection_parser],
        help='Resolve Stack template - output in yaml short format')
    parser_resolve.set_defaults(func=resolve)

    # log parser
    parser_log = command_subparser.add_parser(
        'log',
        parents=[],
        help='Show Stack Log')
    parser_log.add_argument(
        '-d', '--timedelta',
        help='How many seconds go back in time from stack last event - '
             'use 0 for realtime - if < 30 assume days', default=300)

    return parser


def set_cfg(argv):
    parser = get_parser()
    args = parser.parse_known_args(argv)

    for n, v in vars(args[0]).items():
        if not hasattr(cfg, n):
            setattr(cfg, n, v)

    cfg.stack_args = args[1]
