import bpy
import os
import bpy.utils.previews
import addon_utils
from .dt_tools_data import DT_TOOLS_DATA

dt_preview_collections = {}

# Get all available tool IDs (e.g. 'EFS', 'SHP', etc.)
all_tools = []
for tool_id in DT_TOOLS_DATA.keys():
    all_tools.append(tool_id)


# CUSTOM PROPS
class DT_Props(bpy.types.PropertyGroup):
    context_tool: bpy.props.EnumProperty(
        name="Context Tool",
        description="Select which tool's UI is displayed",
        items=[('EFS', "Eye Features Set", ""),
               ('SHP', "Stylized Hair PRO", ""),
               ],
        default='EFS'
    ) # type: ignore
    
    auto_tool: bpy.props.BoolProperty(
        name="Tool Auto-Select",
        description="Automatically display the tool, based on the object in context",
        default=True
    ) # type: ignore


# FUNCTIONS
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
        if mod.__name__.endswith(tool_id_name) and mod.__name__ in bpy.context.preferences.addons:
            tool_module = mod.__name__
            addon_utils.disable(module_name=tool_module, default_set=True)

def dt_draw_missing_tool(space, tool_id, missing_type='NOT_INSTALLED'):
    dt_pcoll = dt_preview_collections["main"]
    tool_data = DT_TOOLS_DATA[tool_id]
    box = space.box()
    if missing_type == 'NOT_INSTALLED':
        sub = box.column(align=True)
        sub.enabled = False
        sub.scale_y = 0.8
        sub.label(text=f'"{tool_data['name']}" not installed.')
        if tool_data['description']:
            sub.label(tool_data['description'])
        sub.label(text='Find out more on:')
        
        sub = box.column(align=False)
        if tool_data['gr_url']:
            sub.operator("wm.url_open", text="Gumroad", icon_value=dt_pcoll["dt_gr_icon"].icon_id).url = tool_data['gr_url']
        if tool_data['sh_url']:
            sub.operator("wm.url_open", text="Superhive (Blender Market)", icon_value=dt_pcoll["dt_sh_icon"].icon_id).url = tool_data['sh_url']
    
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
        layout = self.layout
        layout.prop(dt_props, "auto_tool")
        layout.operator("scene.dt_refresh_tools", icon='FILE_REFRESH')

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
        sub = row.row()
        sub.alignment = 'LEFT'
        sub.ui_units_x = 1.5
        sub.label(text="Tool")
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
