from prettytable import PrettyTable

from . import cfg


def get(data, fields=[]):
    table_data_names = {}

    for f in fields if fields else cfg.fields:
        if "=" in f:
            # custom ad hoc field can use = to split data name from column name
            loc = f.find("=")
            data_name = f[0:loc]
            field_name = f[loc + 1 :]
        else:
            data_name = field_name = f

        if any(data_name in n for n in data):
            table_data_names[field_name] = data_name

    fields = list(table_data_names)
    table_data = list(table_data_names.values())

    table = PrettyTable()
    table.padding_width = 1
    table.field_names = fields
    for n in data:
        parameter_not_empty = n.get("parameter_not_empty", [])
        table.add_row(
            [
                "Null"
                if (i not in n or not n[i])
                else f"{n[i]} *"
                if i in parameter_not_empty
                else n[i]
                for i in table_data
            ]
        )

    if fields:
        table.sortby = fields[0]
    table.reversesort = True
    table.align = "l"

    if cfg.output == "html":
        table.format = True

        return table.get_html_string(fields=fields)

    if cfg.output == "bare":
        table.header = False
        table.border = False
        table.left_padding_width = 0
        table.padding_width = 1

    return table.get_string(fields=fields)
