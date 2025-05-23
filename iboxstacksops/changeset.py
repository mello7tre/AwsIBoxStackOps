import time
from prettytable import PrettyTable

from .tools import show_confirm


# create changeset
def _do_changeset(istack, us_args):
    if not istack.cfg.showtags:
        # keep existing stack.tags so that they are excluded from changeset
        # (not the new prepared ones)
        us_args["Tags"] = istack.stack.tags

    us_args["StackName"] = istack.name
    us_args["ChangeSetName"] = "CS-%s" % time.strftime("%Y-%m-%dT%H-%M-%S")
    us_args.pop("StackPolicyDuringUpdateBody", None)

    response = istack.client.create_change_set(**us_args)

    return response["Id"]


# wait until changeset is created
def _changeset_waiter(istack, changeset_id):
    while True:
        time.sleep(3)
        changeset = istack.client.describe_change_set(
            ChangeSetName=changeset_id,
            StackName=istack.name,
            IncludePropertyValues=True,
        )
        if changeset["Status"] in istack.cfg.CHANGESET_COMPLETE_STATUS:
            return changeset


# parse changeset changes
def _parse_changeset(changeset):
    changes = []
    not_replaced = []
    for change in changeset["Changes"]:
        change_dict = {}
        ResChange = change["ResourceChange"]
        change_dict["LogicalResourceId"] = ResChange["LogicalResourceId"]
        change_dict["Action"] = ResChange["Action"]
        change_dict["ResourceType"] = ResChange["ResourceType"]
        if ResChange["Action"] == "Modify":
            change_dict["Replacement"] = ResChange["Replacement"]
            if change_dict["Replacement"] == "False":
                not_replaced.append(change_dict["LogicalResourceId"])
            scope = ResChange["Scope"]
            change_dict["Scope"] = list_to_string_list(scope)
            target = []
            causingentity = []
            for i in ResChange["Details"]:
                if "Name" in i["Target"] and i["Target"]["Name"] not in target:
                    target.append(i["Target"]["Name"])
                if (
                    "CausingEntity" in i
                    and "Name" in i["Target"]
                    and i["CausingEntity"] not in causingentity
                ):
                    causingentity.append(i["CausingEntity"])
            change_dict["Target"] = list_to_string_list(target)
            change_dict["TargetList"] = target
            change_dict["CausingEntity"] = list_to_string_list(causingentity)
            change_dict["CausingEntityList"] = causingentity

        changes.append(change_dict)
    return changes, not_replaced


# semplify changeset by removing changes where all CausingEntity items will be not replaced
def _simplify_changeset(changes, not_replaced):
    recurse = False
    for row in list(changes):
        causing_entity = row.get("CausingEntityList", [])
        if (
            causing_entity
            and all(n.split(".")[0] in not_replaced for n in causing_entity)
            and len(row.get("TargetList", [])) <= len(causing_entity)
        ):
            not_replaced.append(row["LogicalResourceId"])
            changes.remove(row)
            recurse = True
    if recurse:
        return _simplify_changeset(changes, not_replaced)

    return changes


def _show_changeset_changes(istack, changes):
    fields = ["LogicalResourceId", "ResourceType", "Action"]
    fileds_ex = ["Replacement", "Scope", "Target", "CausingEntity"]
    fields.extend(fileds_ex)
    table = PrettyTable()
    if istack.cfg.nodetails:
        fields.remove("Target")
        fields.remove("CausingEntity")
    table.field_names = fields
    table.padding_width = 1
    table.align["LogicalResourceId"] = "l"
    table.align["ResourceType"] = "l"
    for row in changes:
        table.add_row(
            [
                "None" if i in fileds_ex and row["Action"] != "Modify" else row[i]
                for i in fields
            ]
        )

    istack.mylog("ChangeSet:")
    print(table.get_string(fields=fields))


def _delete_changeset(istack, changeset_id):
    response = istack.client.delete_change_set(
        ChangeSetName=changeset_id, StackName=istack.name
    )

    return response


def _execute_changeset(istack, changeset_id):
    response = istack.client.execute_change_set(
        ChangeSetName=changeset_id, StackName=istack.name
    )

    return response


# change list in a string new line separated element
def list_to_string_list(mylist):
    return ",".join(mylist)
    # joined_string = "\n".join(mylist)
    # mystring = joined_string if len(mylist) < 2 else f"({joined_string})"
    # return mystring


def process(istack, us_args):
    # -create changeset
    changeset_id = _do_changeset(istack, us_args.copy())
    print("\n")
    istack.mylog("ChangeSetId: %s" % changeset_id)
    print("\n")
    time.sleep(1)
    istack.mylog("Waiting ChangeSet Creation..")

    # -wait changeset creation and return it
    changeset = _changeset_waiter(istack, changeset_id)
    # pprint(changeset)

    # -parse changeset changes
    changeset_changes, not_replaced = _parse_changeset(changeset)

    # simplify changeset - replaced by IncludePropertyValues
    #    if not istack.cfg.changeset_original:
    #        changeset_changes = _simplify_changeset(changeset_changes, not_replaced)

    # -show changeset changes
    _show_changeset_changes(istack, changeset_changes)

    # -delete changeset
    _delete_changeset(istack, changeset_id)

    if not istack.cfg.dryrun and show_confirm():
        # _execute_changeset(istack, changeset_id)
        return True
    else:
        return None
        # _delete_changeset(istack, changeset_id)
