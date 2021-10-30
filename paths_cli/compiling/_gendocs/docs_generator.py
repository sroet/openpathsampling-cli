import sys
from paths_cli.compiling.core import Parameter
from .json_type_handlers import json_type_to_string
from .config_handler import DocCategoryInfo

PARAMETER_RST = """* **{p.name}**{type_str} - {p.description}{required}\n"""


class DocsGenerator:
    """This generates the RST to describe options for compile input files.
    """

    parameter_template = PARAMETER_RST
    _ANCHOR_SEP = "--"
    def __init__(self, config):
        self.config = config

    def format_parameter(self, parameter, type_str=None):
        required = " (required)" if parameter.required else ""
        return self.parameter_template.format(
            p=parameter, type_str=type_str, required=required
        )

    def _get_cat_info(self, category_plugin):
        cat_info = self.config.get(category_plugin.label, None)
        if cat_info is None:
            cat_info = DocCategoryInfo(category_plugin.label)
        return cat_info

    def generate_category_rst(self, category_plugin, type_required=True):
        cat_info = self._get_cat_info(category_plugin)
        rst = f".. _compiling--{category_plugin.label}:\n\n"
        rst += f"{cat_info.header}\n{'=' * len(str(cat_info.header))}\n\n"
        if cat_info.description:
            rst += cat_info.description + "\n\n"
        rst += ".. contents:: :local:\n\n"
        for obj in category_plugin.type_dispatch.values():
            rst += self.generate_plugin_rst(
                obj, category_plugin.label, type_required
            )
        return rst

    def generate_plugin_rst(self, plugin, strategy_name,
                            type_required=True):
        rst_anchor = f".. _{strategy_name}{self._ANCHOR_SEP}{plugin.name}:"
        rst = f"{rst_anchor}\n\n{plugin.name}\n{'-' * len(plugin.name)}\n\n"
        if plugin.description:
            rst += plugin.description + "\n\n"
        if type_required:
            type_param = Parameter(
                "type",
                json_type="",
                loader=None,
                description=(f"type identifier; must exactly match the "
                             f"string ``{plugin.name}``"),
            )
            rst += self.format_parameter(
                type_param, type_str=""
            )

        name_param = Parameter(
            "name",
            json_type="string",
            loader=None,
            default="",
            description="name this object in order to reuse it",
        )
        rst += self.format_parameter(name_param, type_str=" (*string*)")
        for param in plugin.parameters:
            type_str = f" ({json_type_to_string(param.json_type)})"
            rst += self.format_parameter(param, type_str)

        rst += "\n\n"
        return rst

    def _get_filename(self, cat_info):
        fname = str(cat_info.header).lower()
        fname = fname.translate(str.maketrans(' ', '_'))
        return f"{fname}.rst"

    def generate(self, category_plugins, stdout=False):
        for plugin in category_plugins:
            rst = self.generate_category_rst(plugin)
            if stdout:
                sys.stdout.write(rst)
                sys.stdout.flush()
            else:
                cat_info = self._get_cat_info(plugin)
                filename = self._get_filename(cat_info)
                with open(filename, 'w') as f:
                    f.write(rst)
