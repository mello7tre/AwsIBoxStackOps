from collections import OrderedDict
from .log import logger, get_msg_client
from .common import *


def _update_template_param(istack):
    # try to get role from istack.cfg or use current stack parameter value
    try:
        role = istack.cfg.EnvRole
    except Exception:
        role = istack.c_parameters["EnvRole"]

    app_repository = istack.exports["BucketAppRepository"]
    s3_prefix = "ibox/%s/templates/%s." % (istack.cfg.version, role)

    try:
        response = istack.s3.list_objects_v2(Bucket=app_repository, Prefix=s3_prefix)
        istack.cfg.template = "https://%s.s3.amazonaws.com/%s" % (
            app_repository,
            response["Contents"][0]["Key"],
        )
    except Exception:
        raise IboxError(f"Error retrieving stack template with prefix: {s3_prefix}")


def get_template(istack, stackset=None):
    logger.info("Getting Template Body")
    # update template param if using version one
    if istack.cfg.version:
        _update_template_param(istack)

    try:
        # New template
        if istack.cfg.template:
            template = str(istack.cfg.template)
            # From s3
            if template.startswith("https"):
                url = template[template.find("//") + 2 :]
                bucket = url[: url.find(".")]
                key = url[url.find("/") + 1 :]

                response = istack.s3.get_object(Bucket=bucket, Key=key)
                body = response["Body"].read()
                istack.template_from = "S3"
            # From file
            else:
                f = open(istack.cfg.template, "r")
                body = f.read()
                istack.template_from = "File"
        # Current template
        else:
            if stackset:
                tbody = istack.TemplateBody
            else:
                response = istack.client.get_template(StackName=istack.name)
                tbody = response["TemplateBody"]
            if isinstance(tbody, OrderedDict):
                body = json.dumps(tbody)
            else:
                body = tbody
            istack.template_from = "Current"

    except Exception as e:
        raise IboxError(f"Error retrieving template: {e}")
    else:
        try:
            template = json.loads(body)
        except Exception:
            try:
                template = yaml.load(body, Loader=yaml.FullLoader)
            except Exception:
                raise IboxError("Error parsing template body")

        for n in ["Parameters", "Conditions", "Mappings", "Resources"]:
            setattr(istack, n.lower(), template.get(n))

        return template
