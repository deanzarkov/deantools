import bpy
import sys
import os
import bpy.utils.previews
import addon_utils
from textwrap import wrap
from .dt_tools_data import DT_TOOLS_DATA

dt_preview_collections = {}

# Get all available tool IDs (e.g. 'EFS', 'SHP', etc.)
all_tools = []
for tool_id in DT_TOOLS_DATA.keys():
    all_tools.append(tool_id)

def dt_get_icon(icon_prefix):
    dt_pcoll = dt_preview_collections["main"]
    theme_bg = bpy.context.preferences.themes[0].user_interface.wcol_regular.inner
    bg_luminance = (0.299 * theme_bg[0] + 0.587 * theme_bg[1] + 0.114 * theme_bg[2])
    dt_icon_id = f"{icon_prefix}_dark" if bg_luminance > 0.5 else f"{icon_prefix}_light"
    return dt_pcoll[dt_icon_id].icon_id

# CUSTOM PROPS
def dt_get_tools_list(self, context):
    return [
        ('EFS', "Eye Features Set", DT_TOOLS_DATA['EFS']['description'], dt_get_icon("dt_efs") , 0),
        ('SHP', "Stylized Hair PRO", DT_TOOLS_DATA['SHP']['description'], dt_get_icon("dt_shp"), 1),
    ]

class DT_Props(bpy.types.PropertyGroup):
    context_tool: bpy.props.EnumProperty(
        name="Context Tool",
        description="Select which tool's UI is displayed",
        items=dt_get_tools_list,
        default=0
    ) # type: ignore
    
    auto_tool: bpy.props.BoolProperty(
        name="Tool Auto-Select",
        description="Automatically display the tool, based on the object in context",
        default=True
    ) # type: ignore


# FUNCTIONS
def dt_split_string(text, max_length=40, first_line_subtract=0):
    first_line = wrap(text, width=max(max_length - first_line_subtract, 1))[0]

    remaining_text = text[len(first_line):].lstrip()
    remaining_lines = wrap(remaining_text, width=40)

    return [first_line] + remaining_lines

def dt_draw_multiline_text(text, space, max_chars=40, first_line_subtract=0, enabled=False, icon=None):
    text_col = space.column(align=True)
    text_col.enabled = enabled

    text_list = dt_split_string(text, max_chars, first_line_subtract)
    
    for label_index, label in enumerate(text_list):
        if label_index == 0:
            text_col.label(text=label, icon=icon if icon else 'NONE')
        else:
            text_col.label(text=label)

def dt_get_addon_info(tool_id):
    """
    Get information for a specific add-on by its module name.
    
    Args:
        tool_id (str): The module name of the add-on
    
    Returns:
        dict: Dictionary containing add-on info
            {
                'name': 'Add-on Display Name',
                'version': (1, 0, 0),
                'state': 'ENABLED', 'NOT_ENABLED' or 'NOT_INSTALLED',
            }
    """
    tool_id_name = DT_TOOLS_DATA[tool_id]['id_name']
    
    # Search for tool add-on
    for mod in addon_utils.modules():
        if mod.__name__.endswith(tool_id_name):
            return {
                'name': mod.bl_info.get('name', ''),
                'version': mod.bl_info.get('version', (-1, -1, -1)),
                'state': 'ENABLED' if mod.__name__ in bpy.context.preferences.addons else 'NOT_ENABLED'
            }
    
    # No tool found - default state
    return {
        'name': '',
        'version': (-1, -1, -1),
        'state': 'NOT_INSTALLED'
    }

def dt_get_enabled_tools():
    enabled_tools = []
    for tool_id in all_tools:
        tool_id_name = DT_TOOLS_DATA[tool_id]['id_name']
        for mod in addon_utils.modules():
            if mod.__name__.endswith(tool_id_name) and mod.__name__ in bpy.context.preferences.addons:
                enabled_tools.append(tool_id)
    return enabled_tools

def dt_refresh_tools():
    for tool_id in all_tools:
        tool_id_name = DT_TOOLS_DATA[tool_id]['id_name']
        for mod in addon_utils.modules():
            if mod.__name__.endswith(tool_id_name) and mod.__name__ in bpy.context.preferences.addons:
                tool_module = mod.__name__
                if tool_module in sys.modules:
                    addon_utils.disable(module_name=tool_module)
                addon_utils.enable(module_name=tool_module)

def dt_enable_tool(tool_id):
    """Enable a tool's add-on if it is installed but not enabled"""
    tool_id_name = DT_TOOLS_DATA[tool_id]['id_name']
    for mod in addon_utils.modules():
        if mod.__name__.endswith(tool_id_name) and mod.__name__ not in bpy.context.preferences.addons:
            tool_module = mod.__name__
            addon_utils.enable(module_name=tool_module, default_set=True)

def dt_disable_tool(tool_id):
    """Disable a tool's add-on if it is installed"""
    tool_id_name = DT_TOOLS_DATA[tool_id]['id_name']
    for mod in addon_utils.modules():
        if mod.__name__.endswith(tool_id_name):
            if mod.__name__ in sys.modules:
                addon_utils.disable(mod.__name__, default_set=True)              

def dt_draw_missing_tool(space, tool_id, missing_type='NOT_INSTALLED'):
    # dt_pcoll = dt_preview_collections["main"]
    tool_data = DT_TOOLS_DATA[tool_id]
    box = space.box()
    if missing_type == 'NOT_INSTALLED':
        box.label(text=f'{tool_data['name']} ({tool_id}) not installed.')
        
        # Description
        if tool_data['description']:
            sub = box.column(align=True)
            sub.scale_y = 0.8
            dt_draw_multiline_text(tool_data['description'], sub, max_chars=40)
        
        # Links
        sub = box.column(align=False)
        sub.label(text='Find out more on:')
        if tool_data['gr_url']:
            sub.operator("wm.url_open", text="Gumroad", icon_value=dt_get_icon("dt_gr")).url = tool_data['gr_url']
        if tool_data['sh_url']:
            sub.operator("wm.url_open", text="Superhive (Blender Market)", icon_value=dt_get_icon("dt_sh")).url = tool_data['sh_url']
    
        row = sub.row()
        row.operator("wm.url_open", text="Overview", icon='URL').url = tool_data['overview_url']
        row.operator("wm.url_open", text="Docs", icon='DOCUMENTS').url = tool_data['docs_url']
        
        sub.label(text='Already have it?')
        sub.operator("extensions.package_install_files", text="Install from Disk...", icon='IMPORT')
    
    elif missing_type == 'NOT_ENABLED':
        sub = box.column(align=True)
        sub.enabled = False
        sub.scale_y = 0.8
        sub.label(text=f'"{tool_data['name']}" installed,')
        sub.label(text='but not enabled:')
        box.operator("scene.dt_enable_tool", text=f'Enable "{tool_data['name']}"').tool_id = tool_id


# OPERATORS
class DT_OT_TestOperator(bpy.types.Operator):
    bl_idname = "scene.dt_test_operator"
    bl_label = "TEST"
    bl_description = ""

    def execute(self, context):
        pass
        return {'FINISHED'}

class DT_OT_EnableTool(bpy.types.Operator):
    bl_idname = "scene.dt_enable_tool"
    bl_label = "Enable Tool"
    bl_description = "Enable the tool add-on to show it's UI"

    tool_id: bpy.props.StringProperty(name="Tool Addon ID") #type:ignore
    
    def execute(self, context):
        dt_enable_tool(self.tool_id)
        return {'FINISHED'}

class DT_OT_RefreshTools(bpy.types.Operator):
    bl_idname = "scene.dt_refresh_tools"
    bl_label = "Refresh DT Tools"
    bl_description = "Refresh the tools shown in the UI"

    def execute(self, context):
        dt_refresh_tools()
        return {'FINISHED'}


# MENUS
class DT_MT_DeanToolsOptionsMenu(bpy.types.Menu):
    bl_label = "Options"
    bl_idname = "DT_MT_options_menu"
    bl_description = "Tools options"

    def draw(self, context):
        dt_props = context.scene.dt_addon
        ctx_tool_id = dt_props.context_tool
        tool_data = DT_TOOLS_DATA[ctx_tool_id]
        tool_info = dt_get_addon_info(ctx_tool_id)
        
        layout = self.layout
        layout.operator("scene.dt_refresh_tools", icon='FILE_REFRESH')
        layout.separator(type='LINE')
        sub = layout.row()
        sub.enabled = False
        tool_version = tool_info['version']
        tool_version_str = f"v{tool_version[0]}.{tool_version[1]}.{tool_version[2]}"
        tool_state = "- not installed" if tool_info['state'] == 'NOT_INSTALLED' else tool_version_str
        sub.label(text=f"{tool_data['name']} {tool_state}")
        layout.operator("wm.url_open", text="Overview", icon='URL').url = tool_data['overview_url']
        layout.operator("wm.url_open", text="Docs", icon='DOCUMENTS').url = tool_data['docs_url']

# MAIN PANEL
class DT_PT_GeoToolsPanel(bpy.types.Panel):
    bl_label = "DeanTools"
    bl_idname = "DT_PT_geo_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DT"

    def draw(self, context):
        dt_props = context.scene.dt_addon
        dt_pcoll = dt_preview_collections["main"]
        layout = self.layout
        
        # TOOL SELECTOR
        row = layout.row(align=True)
        row.prop(dt_props, "context_tool", text="")
        row.separator(factor=0.5)
        sub = row.row()
        sub.alignment = 'LEFT'
        sub.menu("DT_MT_options_menu")
        
        # EYE FEATURES SET
        if dt_props.context_tool == 'EFS':
            tool_state = dt_get_addon_info('EFS')['state']
            if tool_state != 'ENABLED':
                dt_draw_missing_tool(layout, 'EFS', missing_type=tool_state)
        
        # STYLIZED HAIR PRO
        if dt_props.context_tool == 'SHP':
            tool_state = dt_get_addon_info('SHP')['state']
            if tool_state != 'ENABLED':
                dt_draw_missing_tool(layout, 'SHP', missing_type=tool_state)
        
        layout.separator(type='LINE')
        

# REGISTER
def get_icons_list():
    icons_folder_path = os.path.join(os.path.dirname(__file__), "icons")
    icons_list = []
    
    for filename in os.listdir(icons_folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.bmp')):
            icon_name = os.path.splitext(filename)[0]
            icons_list.append((icon_name, filename))
    
    return icons_list

ICONS_LIST = get_icons_list()

CLASSES_LIST = [
    DT_Props,
    DT_OT_TestOperator,
    DT_OT_EnableTool,
    DT_OT_RefreshTools,
    DT_MT_DeanToolsOptionsMenu,
    DT_PT_GeoToolsPanel,
]

def register():
    enabled_tools = dt_get_enabled_tools()
    
    for tool_id in enabled_tools:
        dt_disable_tool(tool_id)
    
    for cls in CLASSES_LIST:
        bpy.utils.register_class(cls)
    
    # Custom Properties
    bpy.types.Scene.dt_addon = bpy.props.PointerProperty(type=DT_Props)
    
    # For icons
    dt_pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")

    # Load a preview thumbnail of a file and store in the previews collection
    for icon_name, icon_file in ICONS_LIST:
        dt_pcoll.load(icon_name, os.path.join(icons_dir, icon_file), 'IMAGE')

    dt_preview_collections["main"] = dt_pcoll
    
    # Refresh any DT tool add-ons
    for tool_id in enabled_tools:
        dt_enable_tool(tool_id)
    
    dt_refresh_tools()

def unregister():
    enabled_tools = dt_get_enabled_tools()
    
    for tool_id in enabled_tools:
        dt_disable_tool(tool_id)
        
    for cls in CLASSES_LIST:
        bpy.utils.unregister_class(cls)

    # Custom Properties
    del bpy.types.Scene.dt_addon
    
    # For icons
    for dt_pcoll in dt_preview_collections.values():
        bpy.utils.previews.remove(dt_pcoll)
    dt_preview_collections.clear()
    
    # Refresh any DT tool add-ons
    for tool_id in enabled_tools:
        dt_enable_tool(tool_id)
        
    dt_refresh_tools()

if __name__ == "__main__":
    register()
