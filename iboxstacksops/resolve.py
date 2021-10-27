from collections import OrderedDict
from .log import logger
from .common import *


def _process_template(istack):
    def _recursive_resolve(name, value):
        if isinstance(value, (dict, OrderedDict)):
            r_root = {}
            for r, v in value.items():
                if r == "Fn::If":
                    return _resolve_if(name, v)
                elif r == "Ref":
                    return _resolve_ref(name, v)
                elif r == "Fn::GetAtt":
                    return "!GetAtt %s.%s" % (v[0], v[1])
                elif r == "Fn::GetAZs":
                    return "!GetAZs %s" % istack.boto3.region_name
                elif r == "Fn::ImportValue":
                    return _resolve_import(name, v)
                elif r == "Fn::Sub":
                    return _resolve_sub(name, v)
                elif r == "Fn::FindInMap":
                    return _resolve_findinmap(name, v)
                elif r == "Fn::Join":
                    return _resolve_join(name, v)
                elif r == "Fn::Select":
                    return _resolve_select(name, v)
                elif r == "Fn::Split":
                    return _resolve_split(name, v)
                elif r == "Fn::Or":
                    return _resolve_or(name, v)
                elif r == "Fn::And":
                    return _resolve_and(name, v)
                elif r == "Fn::Equals":
                    return _resolve_equals(name, v)
                elif r == "Fn::Not":
                    return _resolve_not(name, v)
                elif r == "Condition" and isinstance(v, str):
                    return _resolve_condition(name, v)
                elif r == "Fn::Base64":
                    return _recursive_resolve(name, v)
                else:
                    r_value = _recursive_resolve(name, v)

                    if not _awsnovalue(r_value):
                        r_root[r] = r_value

            return r_root

        elif isinstance(value, list):
            r_root = []
            for n, l in enumerate(value):
                r_value = _recursive_resolve(n, l)

                if not _awsnovalue(r_value):
                    r_root.append(r_value)

            return r_root

        elif isinstance(value, (int, str)):

            return value

    def _resolve_sub(name, value):
        if isinstance(value, list):
            sub_string = value[0]
            sub_data = value[1]
        else:
            sub_string = value
            sub_data = ""

        while True:
            found = sub_string.find("${")
            if found == -1:
                break
            find_start = found + 2
            find_end = sub_string[find_start:].find("}") + find_start
            key = sub_string[find_start:find_end]
            replace_from = "${" + key + "}"

            if key in sub_data:
                r_value = _recursive_resolve(key, sub_data[key])
                replace_to = r_value
            elif key in istack.r_parameters:
                replace_to = istack.r_parameters[key]
            elif key == "AWS::Region":
                replace_to = istack.boto3.region_name
            elif key == "AWS::AccountId":
                replace_to = istack.boto3.client("sts").get_caller_identity()["Account"]
            else:
                replace_to = key

            sub_string = sub_string.replace(replace_from, str(replace_to))

        if sub_string.startswith("https://"):
            _find_s3_files(name, sub_string)

        return sub_string

    def _resolve_if(name, v):
        value = v[1] if istack.r_conditions[v[0]] else v[2]

        return _recursive_resolve(name, value)

    def _resolve_ref(name, v):
        if v == "AWS::Region":
            value = istack.boto3.region_name
        elif v in istack.r_parameters:
            value = istack.r_parameters[v]
        else:
            # value = {'Ref': v}
            value = f"!Ref {v}"

        return value

    def _resolve_import(name, v):
        value = _recursive_resolve(name, v)

        return istack.exports[value]

    def _resolve_findinmap(name, v):
        mapname = _recursive_resolve(name, v[0])
        key = _recursive_resolve(name, v[1])
        key_value = _recursive_resolve(name, v[2])

        value = istack.mappings[mapname][key][key_value]

        if isinstance(value, list):
            return value
        else:
            return str(value)

        return str(istack.mappings[mapname][key][key_value])

    def _resolve_join(name, v):
        sep = v[0]
        data = v[1]

        return sep.join(map(str, _recursive_resolve(name, data)))

    def _resolve_select(name, v):
        index = v[0]
        s_list = _recursive_resolve(name, v[1])

        try:
            value = s_list[index]
        except Exception:
            value = s_list

        return value

    def _resolve_split(name, v):
        delimeter = v[0]
        s_string = _recursive_resolve(name, v[1])

        return s_string.split(delimeter)

    def _resolve_or(name, v):
        o_list = []
        for n in v:
            o_list.append(_recursive_resolve(name, n))

        return any(o_list)

    def _resolve_and(name, v):
        o_list = []
        for n in v:
            o_list.append(_recursive_resolve(name, n))

        return all(o_list)

    def _resolve_equals(name, v):
        first_value = str(_recursive_resolve(name, v[0]))
        second_value = str(_recursive_resolve(name, v[1]))

        return True if first_value == second_value else False

    def _resolve_not(name, v):
        value = True if not _recursive_resolve(name, v[0]) else False

        return value

    def _resolve_condition(name, v):
        istack.r_conditions[v] = _recursive_resolve(name, istack.conditions[v])

        return istack.r_conditions[v]

    def _awsnovalue(value):
        if value == "AWS::NoValue" or value == "!Ref AWS::NoValue":
            return True

        return False

    def _find_s3_files(name, sub_string):
        if (
            "AWS::AutoScaling::LaunchConfiguration" in istack.t_resources
            and istack.t_resources["AWS::AutoScaling::LaunchConfiguration"] == name
        ):
            data = sub_string[8:].partition("/")
            host = data[0]
            if not host.endswith("amazonaws.com"):
                return
            key = data[2]
            s_bucket = host.rsplit(".", 3)
            if s_bucket[1].startswith("s3-"):
                bucket = s_bucket[0]
            else:
                bucket = host[: host.rfind(".s3.")]

            if host == bucket:
                return

            istack.s3_files.add((bucket, key))

    def _check_lambda(r):
        try:
            bucket = istack.r_resources[r]["Properties"]["Code"]["S3Bucket"]
            key = istack.r_resources[r]["Properties"]["Code"]["S3Key"]
        except Exception:
            pass
        else:
            istack.s3_files.add((bucket, key))

    def _process_conditions():
        istack.r_conditions = {}
        for c in sorted(istack.conditions):
            v = istack.conditions[c]
            if c not in istack.r_conditions:
                istack.r_conditions[c] = _recursive_resolve(c, v)

    def _process_resources():
        istack.r_resources = {}
        istack.t_resources = {}
        istack.s3_files = set()

        for r in sorted(istack.resources):
            v = istack.resources[r]
            if not ("Condition" in v and not istack.r_conditions[v["Condition"]]):
                try:
                    del v["Condition"]
                except Exception:
                    pass
                istack.t_resources[v["Type"]] = r
                istack.r_resources[r] = _recursive_resolve(r, v)

                if v["Type"] == "AWS::Lambda::Function":
                    _check_lambda(r)

    _process_conditions()
    _process_resources()


def _check_s3_files(istack):
    for f in istack.s3_files:
        bucket = f[0]
        key = f[1]
        try:
            istack.s3.head_object(Bucket=bucket, Key=key)
        except botocore.exceptions.ClientError as e:
            logger.error(f"Missing: {bucket}/{key}")
            raise IboxError(e)


def _check_ecr_images(istack):
    name = istack.t_resources["AWS::ECS::TaskDefinition"]
    images = []
    ecr = istack.boto3.client("ecr")

    for c in istack.r_resources[name]["Properties"]["ContainerDefinitions"]:
        image = c["Image"]
        registry_id = image[0 : image.find(".")]
        repository_name = image[image.find("/") + 1 : image.find(":")]
        image_id = image[image.find(":") + 1 :]
        # Skip already processed images and images from public docker repo
        if image not in images and ".dkr.ecr." in image:
            try:
                ecr.describe_images(
                    registryId=registry_id,
                    repositoryName=repository_name,
                    imageIds=[
                        {
                            "imageTag": image_id,
                        }
                    ],
                )
                images.append(image)
            except botocore.exceptions.ClientError as e:
                logger.error(f"Missing: {image}")
                raise IboxError(e)


def _do_check(istack):
    if istack.s3_files:
        _check_s3_files(istack)

    if "AWS::ECS::TaskDefinition" in istack.t_resources:
        _check_ecr_images(istack)


def show(istack):
    _process_template(istack)
    print("")
    logger.info(f"Resolved: {istack.name}")
    print(yaml.dump(istack.r_resources))


def process(istack):
    logger.debug("Processing Template")

    try:
        _process_template(istack)
        _do_check(istack)
    except IboxError:
        raise
    except Exception as e:
        pprint(e)
        logger.warning(
            "Error resolving template. "
            "Will not be able to validate s3 files and ecr images."
        )
