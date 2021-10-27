import argparse
from .log import logger
from .common import *


# set final parameters values to use for exectuing commands -
# istack.action_parameters and istack.r_parameters
def _set_action_parameters(
    istack, params_default, params_changed, params_added, params_forced_default
):
    for key in sorted(istack.parameters):
        v = istack.parameters[key]

        try:
            default_value = v["Default"]
        except Exception:
            default_value = None
        use_previous_value = False

        # get list of AllowedValues
        allowed_values = v["AllowedValues"] if "AllowedValues" in v else []

        # check if key exist as istack.cfg param/attr too
        try:
            cfg_value = getattr(istack.cfg, key)
            in_cfg = True if cfg_value is not None else None
        except Exception:
            in_cfg = None

        # update param is not new ...
        if key in istack.c_parameters:
            current_value = istack.c_parameters[key]

            # current value its different from specified cmd arg
            if in_cfg and current_value != cfg_value:
                # get value from specified cmd arg
                value = cfg_value
                params_changed[key] = f"{current_value} => {value}"

            # current value is not allowed by new template
            elif len(allowed_values) > 0 and (current_value not in allowed_values):
                # get value from template default
                value = default_value
                params_forced_default[key] = f"{current_value} => {default_value}"

            # current value is unchanged and allowed
            else:
                value = ""
                use_previous_value = True
                params_default[key] = current_value

        # update param is new ...
        else:
            # template default value its different from specified cmd arg
            if in_cfg and default_value != cfg_value:
                value = cfg_value
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
                "ParameterKey": key,
                "ParameterValue": str(value),
                "UsePreviousValue": use_previous_value,
            }
            if istack.stack
            else {
                "ParameterKey": key,
                "ParameterValue": str(value),
            }
        )

        # update resolved parameter final value istack.r_parameters
        istack.r_parameters[key] = current_value if use_previous_value else value


# force EnvShort param value based on Env one
def _force_envshort(istack):
    # use arg if exist or use current value
    env = istack.cfg.Env if istack.cfg.Env else istack.c_parameters["Env"]

    env_envshort_dict = {
        "dev": "dev",
        "stg": "stg",
        "prd": "prd",
        "prod": "prd",
    }

    istack.cfg.EnvShort = env_envshort_dict[env]


# if template in s3, force version to the one in his url part
# if from file force fixed value 1
# Ex for version=master-2ed25d5:
# https://eu-west-1-ibox-app-repository.s3.amazonaws.com
# /ibox/master-2ed25d5/templates/cache-portal.json
def _do_envstackversion_from_s3_template(istack):
    template = istack.cfg.template
    istack.cfg.version = (
        template.split("/")[4] if str(template).startswith("https") else "1"
    )
    istack.cfg.EnvStackVersion = istack.cfg.version


def get_stack_parameter_parser(istack):
    parser = argparse.ArgumentParser(
        description="",
        add_help=False,
        allow_abbrev=False,
        usage="Allowed Stack Params ... allowed values are in {}",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # for parameter in sorted(
    #    stack_parameters, key=lambda x: x['ParameterKey']):
    for p in sorted(istack.parameters):
        v = istack.parameters[p]
        allowed_values = v["AllowedValues"] if "AllowedValues" in v else []
        kwargs = {"type": str, "metavar": "\t%s" % v["Description"]}

        # If Parameter do not have Default value and is new or
        # current value is not allowed in new template,
        # enforce it as required
        if "Default" not in v and (
            p not in istack.c_parameters
            or (allowed_values and istack.c_parameters[p] not in allowed_values)
        ):
            kwargs["required"] = True

        if len(allowed_values) > 0:
            kwargs["choices"] = allowed_values
            kwargs["help"] = "{%s}\n\n" % ", ".join(allowed_values)
        else:
            kwargs["help"] = "\n"

        parser.add_argument("--%s" % p, **kwargs)

    return parser


def add_stack_params_as_args(istack, parser):
    args = parser.parse_args(istack.cfg.stack_args)
    istack.stack_parsed_args = args

    for n, v in vars(args).items():
        if not hasattr(istack.cfg, n):
            setattr(istack.cfg, n, v)


def show_override(istack):
    params = {}
    for name, value in istack.c_parameters.items():
        if (
            not name.startswith("Env")
            and any(name not in n for n in ["UpdateMode"])
            and any(
                name == t_name and (value != t_value.get("Default"))
                for t_name, t_value in istack.parameters.items()
            )
        ):
            params[name] = value

    out = pformat(params, width=istack.cfg.OUT_WIDTH)

    istack.mylog(f"CURRENT NOT DEFAULT - STACK PARAMETERS\n{out}\n")


def process(istack, show=True):
    logger.info("Processing Parameters")

    # get stack parameter parser
    parser = get_stack_parameter_parser(istack)

    # add stack parameters as argparse args and update istack.cfg
    add_stack_params_as_args(istack, parser)

    # if template include EnvShort params force its value based on the Env one
    if "EnvShort" in istack.parameters:
        _force_envshort(istack)

    # if using template option set/force EnvStackVersion
    if istack.cfg.template:
        _do_envstackversion_from_s3_template(istack)

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
    _set_action_parameters(
        istack, params_default, params_changed, params_added, params_forced_default
    )

    if not show:
        return

    # show changes to output
    print("\n")
    # disabled for now - it make no sense to display them
    # if not istack.stack and params_default:
    #     print('DEFAULT - STACK PARAMETERS\n%s\n' % pformat(
    #         params_default, width=1000000))

    if params_changed:
        istack.mylog(
            "CHANGED - STACK PARAMETERS\n%s\n" % pformat(params_changed, width=1000000)
        )

    if istack.stack and params_added:
        istack.mylog(
            "ADDED - STACK PARAMETERS\n%s\n" % pformat(params_added, width=1000000)
        )

    if params_forced_default:
        istack.mylog(
            "FORCED TO DEFAULT - STACK PARAMETERS\n%s\n"
            % pformat(params_forced_default, width=1000000)
        )


def get(stack):
    try:
        s_parameters = stack["Parameters"]
    except Exception as e:
        pass
    else:
        parameters = {}
        for parameter in s_parameters:
            key = parameter["ParameterKey"]
            # Think is better to use always value not the resolved one,
            # or i will have problem later when i check if value is allowed
            # value = parameter.get(
            #     'ResolvedValue', parameter.get('ParameterValue'))
            value = parameter.get("ParameterValue")
            parameters[key] = value

        return parameters
