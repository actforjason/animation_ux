bl_info = {
    "name": "Animation UX - Auto Expand Channels",
    "author": "Antigravity",
    "version": (1, 0, 3),
    "blender": (3, 6, 0),
    "location": "Graph Editor & Dope Sheet Header (next to filter funnel) / 3D View Sidebar",
    "description": "Auto expand channels when selecting animated objects/bones under show_only_selected with configurable single & multi selection rules.",
    "category": "Animation",
}

import bpy
from bpy.app.translations import pgettext_iface
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import (
    AddonPreferences,
    Header,
    Operator,
    Panel,
    PropertyGroup,
)


# ============================================================================
# i18n / 多语言字典 (原生国际化支持：切英文显示纯英文，切中文显示纯中文)
# ============================================================================

TRANSLATIONS_TABLE = {
    "Auto Expand Channels": "自动展开通道",
    "Only on Show Only Selected": "仅在【仅显示所选】开启时生效",
    "Only auto-expand when 'Only Show Selected' is active in Dope Sheet or Graph Editor": "只有当动画编辑器开启【仅显示所选】过滤时才触发自动展开",
    "Automatically expand animation channels when clicking/selecting animated objects or bones": "当点击选择动画对象或骨骼时，自动展开对应的动画通道",
    "Single Selection Scenario": "单选情景",
    "Single Selection Mode": "单选行为",
    "Action when a single object or bone is selected": "单个对象或骨骼被选中时的通道展开行为",
    "Expand Selected & Collapse Others": "展开所选，折叠其他",
    "Expand target and collapse all other channels": "展开当前选中项并自动折叠其他所有通道，保持面板最精简",
    "Expand Selected & Keep Others": "仅展开所选，保持其他",
    "Expand target while keeping existing open channels": "展开当前选中项，保留之前已展开的通道",
    "Do Nothing": "不处理",
    "Do not auto-expand when single item is selected": "单选时不自动改变通道展开状态",
    "Auto Expand Parent Slot/Object": "自动展开父级槽位/对象",
    "Ensure parent slot or armature object channel is also expanded": "确保父级 Slot 或骨架对象通道也处于展开状态，保证子通道直接可见",
    "Multi Selection Scenario": "多选情景",
    "Multi Selection Mode": "多选行为",
    "Action when multiple objects or bones are selected": "多个对象或骨骼被选中时的通道展开行为",
    "Expand All Selected": "展开全部所选",
    "Expand channel groups for all selected bones/objects": "展开所有被选中的骨骼或对象通道组",
    "Expand Active Only & Collapse Others": "仅展开活动项，折叠其他",
    "Expand only the active item and collapse other selected items": "多选时只展开最后选中的活动项，其余保持折叠",
    "Expand Active Only & Keep Others": "仅展开活动项，保持其他",
    "Expand active item without changing other items": "多选时展开活动项，不改变其他项已展开状态",
    "Collapse All Selected": "全部折叠",
    "Collapse all selected items for an uncluttered overview": "多选时折叠所有通道以提供全局概览",
    "Do not modify channel expansion on multi-selection": "多选时不自动修改通道展开状态",
    "Use Count Threshold": "启用数量阈值自适应",
    "Limit channel expansion when selecting many bones/objects at once": "当同时选中的骨骼或对象过多时，自动切换策略以防止通道列表爆炸",
    "Threshold Count": "阈值数量",
    "Maximum number of selected items before falling back to overflow mode": "选中数量超过此数值时，自动切换到降级策略",
    "Overflow Mode": "超出阈值时的策略",
    "Mode applied when selected items exceed threshold count": "选中数量超出阈值时执行的行为",
    "Expand Active Only": "仅展开活动项",
    "Switch to active item only when selection exceeds threshold": "超过阈值时仅展开当前活动项",
    "Collapse All": "全部折叠",
    "Collapse all selected channels when selection exceeds threshold": "超过阈值时全部折叠以防止屏幕被大量曲线挤爆",
    "Keep current expansion states when selection exceeds threshold": "超过阈值时不修改",
    "Graph Editor": "曲线编辑器",
    "Apply expansion to Graph Editor channels": "是否对曲线编辑器的通道列表生效",
    "Dope Sheet / Action Editor": "动画摄影表",
    "Apply expansion to Dope Sheet / Timeline / Action Editor channels": "是否对动画摄影表/动作编辑器的通道列表生效",
    "On Deselect All": "全不选时",
    "Behavior when no objects or bones are selected": "当没有任何对象或骨骼被选中时的行为",
    "Keep Current State": "保持现状",
    "Do not alter channels when everything is deselected": "全部取消选择时保持通道现有展开状态",
    "Collapse channels when everything is deselected": "全部取消选择时自动折叠所有通道",
    "Auto Expand Channels Now": "立即执行通道展开",
    "Manually trigger auto expansion logic according to current settings": "根据当前单选/多选配置立即刷新动画通道展开状态",
    "Toggle Channel Auto-Expansion": "开关通道自动展开",
    "Quickly enable or disable auto-expansion on click": "快速开启或关闭选择对象/骨骼时自动展开通道的功能",
    "Auto Expand Channels Settings": "通道自动展开配置",
    "Global Configuration": "全局配置",
    "Target Editors": "生效编辑器",
    "Target Editors & Misc": "生效编辑器与杂项",
    "Other Behaviors": "其他行为",
    "Threshold": "阈值",
    "Trigger Now": "立即执行",
    "Settings will be initialized after opening a scene.": "设置将在打开场景后初始化",
    "Channels expanded according to rules": "已按规则刷新通道展开状态",
    "Auto Expand Channels: Enabled": "通道自动展开: 已开启",
    "Auto Expand Channels: Disabled": "通道自动展开: 已关闭",
}

TRANSLATIONS_DICT = {
    "zh_HANS": {("*", k): v for k, v in TRANSLATIONS_TABLE.items()},
    "zh_CN": {("*", k): v for k, v in TRANSLATIONS_TABLE.items()},
}


# ============================================================================
# Helpers: Compatibility for Blender 4.x / 5.x Slotted & Layered Actions
# ============================================================================

def get_action_groups_and_slots(obj):
    """
    Retrieve all relevant action slots and action groups for an object.
    Supports:
      - Blender 5.x layered and slotted actions (strip.channelbags -> groups)
      - Blender 4.x / legacy single-action structures (action.groups)
    """
    slots = []
    groups = []
    if not obj or not obj.animation_data or not obj.animation_data.action:
        return slots, groups

    act = obj.animation_data.action
    slot = getattr(obj.animation_data, "action_slot", None)
    if slot:
        slots.append(slot)

    # Blender 5.x layered actions
    if hasattr(act, "layers"):
        slot_handle = slot.handle if slot else None
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    if slot_handle is None or bag.slot_handle == slot_handle:
                        groups.extend(bag.groups)
    # Blender 4.x / legacy actions
    elif hasattr(act, "groups"):
        groups.extend(act.groups)

    return slots, groups


def is_show_only_selected_active(context):
    """
    Check if any visible Graph Editor or Dope Sheet has 'show_only_selected' enabled.
    """
    wm = getattr(context, "window_manager", None)
    if not wm:
        return False
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type in {"GRAPH_EDITOR", "DOPESHEET_EDITOR"}:
                space = area.spaces.active
                if space and hasattr(space, "dopesheet") and space.dopesheet:
                    if space.dopesheet.show_only_selected:
                        return True
    return False


def request_editor_redraws(context, target_graph=True, target_dopesheet=True):
    """Redraw animation editors to show updated channel collapse/expand states immediately."""
    wm = getattr(context, "window_manager", None)
    if not wm:
        return
    target_types = set()
    if target_graph:
        target_types.add("GRAPH_EDITOR")
    if target_dopesheet:
        target_types.add("DOPESHEET_EDITOR")

    for window in wm.windows:
        for area in window.screen.areas:
            if area.type in target_types:
                area.tag_redraw()


# ============================================================================
# Settings: Property Group & Addon Preferences
# ============================================================================

SINGLE_MODE_ITEMS = (
    ("EXPAND_COLLAPSE_OTHERS", "Expand Selected & Collapse Others", "Expand target and collapse all other channels"),
    ("EXPAND_KEEP_OTHERS", "Expand Selected & Keep Others", "Expand target while keeping existing open channels"),
    ("DO_NOTHING", "Do Nothing", "Do not auto-expand when single item is selected"),
)

MULTI_MODE_ITEMS = (
    ("EXPAND_ALL", "Expand All Selected", "Expand channel groups for all selected bones/objects"),
    ("EXPAND_ACTIVE_ONLY", "Expand Active Only & Collapse Others", "Expand only the active item and collapse other selected items"),
    ("EXPAND_ACTIVE_KEEP", "Expand Active Only & Keep Others", "Expand active item without changing other items"),
    ("COLLAPSE_ALL", "Collapse All Selected", "Collapse all selected items for an uncluttered overview"),
    ("DO_NOTHING", "Do Nothing", "Do not modify channel expansion on multi-selection"),
)

OVERFLOW_MODE_ITEMS = (
    ("EXPAND_ACTIVE_ONLY", "Expand Active Only", "Switch to active item only when selection exceeds threshold"),
    ("COLLAPSE_ALL", "Collapse All", "Collapse all selected channels when selection exceeds threshold"),
    ("DO_NOTHING", "Do Nothing", "Keep current expansion states when selection exceeds threshold"),
)

ON_DESELECT_ITEMS = (
    ("KEEP", "Keep Current State", "Do not alter channels when everything is deselected"),
    ("COLLAPSE_ALL", "Collapse All", "Collapse channels when everything is deselected"),
)


class AnimUXSettings(PropertyGroup):
    enabled: BoolProperty(
        name="Auto Expand Channels",
        description="Automatically expand animation channels when clicking/selecting animated objects or bones",
        default=True,
    )

    require_show_only_selected: BoolProperty(
        name="Only on Show Only Selected",
        description="Only auto-expand when 'Only Show Selected' is active in Dope Sheet or Graph Editor",
        default=True,
    )

    # Single item scenario
    single_mode: EnumProperty(
        name="Single Selection Mode",
        description="Action when a single object or bone is selected",
        items=SINGLE_MODE_ITEMS,
        default="EXPAND_COLLAPSE_OTHERS",
    )

    single_expand_slot: BoolProperty(
        name="Auto Expand Parent Slot/Object",
        description="Ensure parent slot or armature object channel is also expanded",
        default=True,
    )

    # Multi item scenario
    multi_mode: EnumProperty(
        name="Multi Selection Mode",
        description="Action when multiple objects or bones are selected",
        items=MULTI_MODE_ITEMS,
        default="EXPAND_ALL",
    )

    use_multi_threshold: BoolProperty(
        name="Use Count Threshold",
        description="Limit channel expansion when selecting many bones/objects at once",
        default=True,
    )

    multi_threshold_count: IntProperty(
        name="Threshold Count",
        description="Maximum number of selected items before falling back to overflow mode",
        default=4,
        min=2,
        max=50,
    )

    multi_overflow_mode: EnumProperty(
        name="Overflow Mode",
        description="Mode applied when selected items exceed threshold count",
        items=OVERFLOW_MODE_ITEMS,
        default="EXPAND_ACTIVE_ONLY",
    )

    # Target editors
    target_graph_editor: BoolProperty(
        name="Graph Editor",
        description="Apply expansion to Graph Editor channels",
        default=True,
    )

    target_dopesheet: BoolProperty(
        name="Dope Sheet / Action Editor",
        description="Apply expansion to Dope Sheet / Timeline / Action Editor channels",
        default=True,
    )

    on_deselect: EnumProperty(
        name="On Deselect All",
        description="Behavior when no objects or bones are selected",
        items=ON_DESELECT_ITEMS,
        default="KEEP",
    )


class AnimUXPreferences(AddonPreferences):
    bl_idname = __package__ or "animation_ux"

    def draw(self, context):
        layout = self.layout
        settings = getattr(context.scene, "anim_ux_settings", None)
        if not settings:
            layout.label(text=pgettext_iface("Settings will be initialized after opening a scene."))
            return

        box = layout.box()
        box.label(text=pgettext_iface("Global Configuration"), icon="SETTINGS")
        row = box.row()
        row.prop(settings, "enabled")
        row.prop(settings, "require_show_only_selected")

        row = box.row()
        row.label(text=pgettext_iface("Target Editors") + ":")
        row.prop(settings, "target_graph_editor")
        row.prop(settings, "target_dopesheet")

        # Single selection box
        box_single = layout.box()
        box_single.label(text=pgettext_iface("Single Selection Scenario"), icon="USER")
        box_single.prop(settings, "single_mode")
        box_single.prop(settings, "single_expand_slot")

        # Multi selection box
        box_multi = layout.box()
        box_multi.label(text=pgettext_iface("Multi Selection Scenario"), icon="COMMUNITY")
        box_multi.prop(settings, "multi_mode")
        box_multi.prop(settings, "use_multi_threshold")
        if settings.use_multi_threshold:
            col = box_multi.column(align=True)
            col.prop(settings, "multi_threshold_count")
            col.prop(settings, "multi_overflow_mode")

        box_misc = layout.box()
        box_misc.label(text=pgettext_iface("Other Behaviors"), icon="PREFERENCES")
        box_misc.prop(settings, "on_deselect")


# ============================================================================
# Core Logic: Channel Expansion Processor
# ============================================================================

def process_channel_expansion(context):
    """
    Applies single / multi selection expansion logic based on current context.
    """
    if not context or not context.scene:
        return
    settings = getattr(context.scene, "anim_ux_settings", None)
    if not settings or not settings.enabled:
        return

    # Check 'show_only_selected' gate if enabled
    if settings.require_show_only_selected and not is_show_only_selected_active(context):
        return

    mode = context.mode
    apply_graph = settings.target_graph_editor
    apply_ds = settings.target_dopesheet

    # -------------------------------------------------------------------------
    # Case 1: Pose Mode (Bones in Armatures)
    # -------------------------------------------------------------------------
    if mode == "POSE":
        sel_bones = [b.name for b in context.selected_pose_bones]
        active_bone_name = context.active_pose_bone.name if context.active_pose_bone else None
        active_obj = context.active_object

        # If deselected all
        if not sel_bones:
            if settings.on_deselect == "COLLAPSE_ALL" and active_obj:
                slots, groups = get_action_groups_and_slots(active_obj)
                for g in groups:
                    if apply_ds:
                        g.show_expanded = False
                    if apply_graph:
                        g.show_expanded_graph = False
                request_editor_redraws(context, apply_graph, apply_ds)
            return

        if not active_obj or not active_obj.animation_data:
            return

        slots, groups = get_action_groups_and_slots(active_obj)

        # Ensure parent slot is expanded if configured
        if settings.single_expand_slot:
            for s in slots:
                s.show_expanded = True

        count = len(sel_bones)

        # Single Bone Selection
        if count == 1:
            target_bone = sel_bones[0]
            mode_choice = settings.single_mode

            if mode_choice == "EXPAND_COLLAPSE_OTHERS":
                for g in groups:
                    match = (g.name == target_bone)
                    if apply_ds:
                        g.show_expanded = match
                    if apply_graph:
                        g.show_expanded_graph = match

            elif mode_choice == "EXPAND_KEEP_OTHERS":
                for g in groups:
                    if g.name == target_bone:
                        if apply_ds:
                            g.show_expanded = True
                        if apply_graph:
                            g.show_expanded_graph = True

        # Multiple Bones Selection
        else:
            multi_choice = settings.multi_mode
            if settings.use_multi_threshold and count > settings.multi_threshold_count:
                multi_choice = settings.multi_overflow_mode

            sel_bone_set = set(sel_bones)

            if multi_choice == "EXPAND_ALL":
                for g in groups:
                    match = (g.name in sel_bone_set)
                    if apply_ds:
                        g.show_expanded = match
                    if apply_graph:
                        g.show_expanded_graph = match

            elif multi_choice == "EXPAND_ACTIVE_ONLY":
                for g in groups:
                    match = (g.name == active_bone_name)
                    if apply_ds:
                        g.show_expanded = match
                    if apply_graph:
                        g.show_expanded_graph = match

            elif multi_choice == "EXPAND_ACTIVE_KEEP":
                for g in groups:
                    if g.name == active_bone_name:
                        if apply_ds:
                            g.show_expanded = True
                        if apply_graph:
                            g.show_expanded_graph = True

            elif multi_choice == "COLLAPSE_ALL":
                for g in groups:
                    if g.name in sel_bone_set:
                        if apply_ds:
                            g.show_expanded = False
                        if apply_graph:
                            g.show_expanded_graph = False

        request_editor_redraws(context, apply_graph, apply_ds)

    # -------------------------------------------------------------------------
    # Case 2: Object Mode (Standard Objects)
    # -------------------------------------------------------------------------
    elif mode == "OBJECT":
        sel_objs = [o for o in context.selected_objects if o.animation_data and o.animation_data.action]
        active_obj = context.active_object
        count = len(sel_objs)

        if count == 0:
            if settings.on_deselect == "COLLAPSE_ALL":
                for o in context.scene.objects:
                    if o.animation_data and o.animation_data.action:
                        slots, groups = get_action_groups_and_slots(o)
                        for s in slots:
                            s.show_expanded = False
                        for g in groups:
                            if apply_ds:
                                g.show_expanded = False
                            if apply_graph:
                                g.show_expanded_graph = False
                request_editor_redraws(context, apply_graph, apply_ds)
            return

        # Single Object Selection
        if count == 1:
            target_obj = sel_objs[0]
            mode_choice = settings.single_mode

            if mode_choice == "EXPAND_COLLAPSE_OTHERS":
                for o in context.scene.objects:
                    if o.animation_data and o.animation_data.action:
                        slots, groups = get_action_groups_and_slots(o)
                        is_target = (o == target_obj)
                        for s in slots:
                            s.show_expanded = is_target
                        for g in groups:
                            if apply_ds:
                                g.show_expanded = is_target
                            if apply_graph:
                                g.show_expanded_graph = is_target

            elif mode_choice == "EXPAND_KEEP_OTHERS":
                slots, groups = get_action_groups_and_slots(target_obj)
                for s in slots:
                    s.show_expanded = True
                for g in groups:
                    if apply_ds:
                        g.show_expanded = True
                    if apply_graph:
                        g.show_expanded_graph = True

        # Multiple Objects Selection
        else:
            multi_choice = settings.multi_mode
            if settings.use_multi_threshold and count > settings.multi_threshold_count:
                multi_choice = settings.multi_overflow_mode

            sel_obj_set = set(sel_objs)

            if multi_choice == "EXPAND_ALL":
                for o in sel_objs:
                    slots, groups = get_action_groups_and_slots(o)
                    for s in slots:
                        s.show_expanded = True
                    for g in groups:
                        if apply_ds:
                            g.show_expanded = True
                        if apply_graph:
                            g.show_expanded_graph = True

            elif multi_choice == "EXPAND_ACTIVE_ONLY":
                for o in context.scene.objects:
                    if o.animation_data and o.animation_data.action:
                        slots, groups = get_action_groups_and_slots(o)
                        is_active = (o == active_obj)
                        for s in slots:
                            s.show_expanded = is_active
                        for g in groups:
                            if apply_ds:
                                g.show_expanded = is_active
                            if apply_graph:
                                g.show_expanded_graph = is_active

            elif multi_choice == "EXPAND_ACTIVE_KEEP":
                if active_obj and active_obj in sel_obj_set:
                    slots, groups = get_action_groups_and_slots(active_obj)
                    for s in slots:
                        s.show_expanded = True
                    for g in groups:
                        if apply_ds:
                            g.show_expanded = True
                        if apply_graph:
                            g.show_expanded_graph = True

            elif multi_choice == "COLLAPSE_ALL":
                for o in sel_objs:
                    slots, groups = get_action_groups_and_slots(o)
                    for s in slots:
                        s.show_expanded = False
                    for g in groups:
                        if apply_ds:
                            g.show_expanded = False
                        if apply_graph:
                            g.show_expanded_graph = False

        request_editor_redraws(context, apply_graph, apply_ds)


# ============================================================================
# Observer: Depsgraph Update & Timer Dispatcher
# ============================================================================

class SelectionTracker:
    last_state = None
    is_executing = False

    @classmethod
    def get_selection_fingerprint(cls, context):
        if not context or not context.scene:
            return None
        mode = context.mode
        if mode == "POSE":
            sel = tuple(sorted(b.name for b in context.selected_pose_bones))
            act = context.active_pose_bone.name if context.active_pose_bone else None
            return (mode, getattr(context.active_object, "name", None), act, sel)
        elif mode == "OBJECT":
            sel = tuple(sorted(o.name for o in context.selected_objects))
            act = context.active_object.name if context.active_object else None
            return (mode, act, sel)
        return (mode,)

    @classmethod
    def handle_selection_change(cls, context):
        if cls.is_executing:
            return
        cls.is_executing = True
        try:
            process_channel_expansion(context)
        except Exception as e:
            print(f"[Animation UX] Error: {e}")
        finally:
            cls.is_executing = False

    @classmethod
    def on_depsgraph_update(cls, scene, depsgraph):
        context = bpy.context
        if not context or not context.scene:
            return
        if context.screen and context.screen.is_animation_playing:
            return
        settings = getattr(context.scene, "anim_ux_settings", None)
        if not settings or not settings.enabled:
            return

        fp = cls.get_selection_fingerprint(context)
        if fp != cls.last_state:
            cls.last_state = fp
            cls.handle_selection_change(context)

    @classmethod
    def periodic_poll(cls):
        context = bpy.context
        if not context or not context.scene:
            return 0.1
        if context.screen and context.screen.is_animation_playing:
            return 0.2
        settings = getattr(context.scene, "anim_ux_settings", None)
        if not settings or not settings.enabled:
            return 0.1

        fp = cls.get_selection_fingerprint(context)
        if fp != cls.last_state:
            cls.last_state = fp
            cls.handle_selection_change(context)
        return 0.05


# ============================================================================
# Operators
# ============================================================================

class ANIMUX_OT_ExpandChannelsNow(Operator):
    bl_idname = "anim_ux.expand_channels_now"
    bl_label = "Auto Expand Channels Now"
    bl_description = "Manually trigger auto expansion logic according to current settings"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        process_channel_expansion(context)
        self.report({"INFO"}, pgettext_iface("Channels expanded according to rules"))
        return {"FINISHED"}


class ANIMUX_OT_ToggleEnabled(Operator):
    bl_idname = "anim_ux.toggle_enabled"
    bl_label = "Toggle Channel Auto-Expansion"
    bl_description = "Quickly enable or disable auto-expansion on click"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.anim_ux_settings
        settings.enabled = not settings.enabled
        msg = "Auto Expand Channels: Enabled" if settings.enabled else "Auto Expand Channels: Disabled"
        self.report({"INFO"}, pgettext_iface(msg))
        if settings.enabled:
            process_channel_expansion(context)
        return {"FINISHED"}


# ============================================================================
# User Interface (Header Injection & Popover & Sidebar)
# ============================================================================

class ANIMUX_PT_Popover(Panel):
    bl_idname = "ANIMUX_PT_popover"
    bl_label = "Auto Expand Channels Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        settings = getattr(context.scene, "anim_ux_settings", None)
        if not settings:
            return

        layout.prop(settings, "enabled")
        layout.prop(settings, "require_show_only_selected")

        layout.separator()
        col_single = layout.box()
        col_single.label(text=pgettext_iface("Single Selection Scenario"), icon="USER")
        col_single.prop(settings, "single_mode", text="")
        col_single.prop(settings, "single_expand_slot")

        col_multi = layout.box()
        col_multi.label(text=pgettext_iface("Multi Selection Scenario"), icon="COMMUNITY")
        col_multi.prop(settings, "multi_mode", text="")
        col_multi.prop(settings, "use_multi_threshold")
        if settings.use_multi_threshold:
            row = col_multi.row(align=True)
            row.prop(settings, "multi_threshold_count", text=pgettext_iface("Threshold"))
            row.prop(settings, "multi_overflow_mode", text="")

        layout.separator()
        row = layout.row(align=True)
        row.prop(settings, "target_graph_editor", toggle=True)
        row.prop(settings, "target_dopesheet", toggle=True)

        layout.operator("anim_ux.expand_channels_now", icon="FILE_REFRESH", text=pgettext_iface("Trigger Now"))


def draw_header_button(layout, context):
    """
    Renders the toggle icon + single clean dropdown popover arrow.
    No extra icons on popover so exactly ONE dropdown triangle appears.
    """
    settings = getattr(context.scene, "anim_ux_settings", None)
    if not settings:
        return

    row = layout.row(align=True)
    # Action toggle icon (highlights blue when active)
    row.prop(settings, "enabled", text="", icon="CON_ACTION")
    # Popover button: text="" and NO icon argument so Blender draws only its single native dropdown arrow
    row.popover(panel="ANIMUX_PT_popover", text="")


# ----------------------------------------------------------------------------
# Header Interceptor: Places our button tightly adjacent to the filter funnel
# ----------------------------------------------------------------------------

class HeaderLayoutProxy:
    def __init__(self, real_layout, context):
        self._layout = real_layout
        self._context = context

    def popover(self, *args, **kwargs):
        res = self._layout.popover(*args, **kwargs)
        panel = kwargs.get("panel") or (args[0] if args else None)
        # Directly adjacent to native filter funnel button in Graph Editor and Dope Sheet
        if panel in {"GRAPH_PT_filters", "DOPESHEET_PT_filters"}:
            draw_header_button(self._layout, self._context)
        return res

    def __getattr__(self, name):
        return getattr(self._layout, name)


class HeaderProxy:
    def __init__(self, real_header, context):
        self._real = real_header
        self.layout = HeaderLayoutProxy(real_header.layout, context)

    def __getattr__(self, name):
        return getattr(self._real, name)


_original_header_draws = {}

def hook_header_draw(header_cls):
    if not hasattr(header_cls, "draw") or not hasattr(header_cls.draw, "_draw_funcs"):
        header_cls._dyn_ui_initialize()
    draw_funcs = header_cls.draw._draw_funcs
    if not draw_funcs:
        return
    orig_func = draw_funcs[0]
    _original_header_draws[header_cls] = orig_func

    def wrapped_draw(self, context):
        proxy = HeaderProxy(self, context)
        return orig_func(proxy, context)

    draw_funcs[0] = wrapped_draw


def unhook_header_draw(header_cls):
    orig_func = _original_header_draws.pop(header_cls, None)
    if orig_func and hasattr(header_cls, "draw") and hasattr(header_cls.draw, "_draw_funcs"):
        header_cls.draw._draw_funcs[0] = orig_func


def draw_into_native_filters(self, context):
    """Also inject a settings section inside the native filter funnel popover panel."""
    settings = getattr(context.scene, "anim_ux_settings", None)
    if not settings:
        return
    layout = self.layout
    layout.separator()
    box = layout.box()
    box.label(text=pgettext_iface("Auto Expand Channels"), icon="CON_ACTION")
    row = box.row()
    row.prop(settings, "enabled")
    row.popover(panel="ANIMUX_PT_popover", text="", icon="PREFERENCES")


class ANIMUX_PT_SidebarPanel(Panel):
    bl_idname = "ANIMUX_PT_sidebar_panel"
    bl_label = "Auto Expand Channels"
    bl_category = "Animation UX"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        settings = getattr(context.scene, "anim_ux_settings", None)
        if not settings:
            return

        box = layout.box()
        box.prop(settings, "enabled")
        box.prop(settings, "require_show_only_selected")

        box_s = layout.box()
        box_s.label(text=pgettext_iface("Single Selection Scenario"), icon="USER")
        box_s.prop(settings, "single_mode")
        box_s.prop(settings, "single_expand_slot")

        box_m = layout.box()
        box_m.label(text=pgettext_iface("Multi Selection Scenario"), icon="COMMUNITY")
        box_m.prop(settings, "multi_mode")
        box_m.prop(settings, "use_multi_threshold")
        if settings.use_multi_threshold:
            sub = box_m.column(align=True)
            sub.prop(settings, "multi_threshold_count")
            sub.prop(settings, "multi_overflow_mode")

        box_t = layout.box()
        box_t.label(text=pgettext_iface("Target Editors & Misc"), icon="WINDOW")
        row = box_t.row()
        row.prop(settings, "target_graph_editor")
        row.prop(settings, "target_dopesheet")
        box_t.prop(settings, "on_deselect")

        layout.operator("anim_ux.expand_channels_now", icon="FILE_REFRESH")


# ============================================================================
# Registration
# ============================================================================

classes = (
    AnimUXSettings,
    AnimUXPreferences,
    ANIMUX_OT_ExpandChannelsNow,
    ANIMUX_OT_ToggleEnabled,
    ANIMUX_PT_Popover,
    ANIMUX_PT_SidebarPanel,
)


def register():
    # Register i18n dictionary
    try:
        bpy.app.translations.register(__name__, TRANSLATIONS_DICT)
    except Exception as e:
        print(f"[Animation UX] i18n register note: {e}")

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.anim_ux_settings = PointerProperty(type=AnimUXSettings)

    # Hook headers to place button tightly adjacent to the filter funnel popover
    hook_header_draw(bpy.types.GRAPH_HT_header)
    hook_header_draw(bpy.types.DOPESHEET_HT_header)

    # Also append to the filter funnel panels if the user expands the funnel popover
    bpy.types.GRAPH_PT_filters.append(draw_into_native_filters)
    bpy.types.DOPESHEET_PT_filters.append(draw_into_native_filters)

    # Register handlers
    if SelectionTracker.on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(SelectionTracker.on_depsgraph_update)

    if not bpy.app.timers.is_registered(SelectionTracker.periodic_poll):
        bpy.app.timers.register(SelectionTracker.periodic_poll, first_interval=0.05, persistent=True)


def unregister():
    # Unregister timer & handlers
    if bpy.app.timers.is_registered(SelectionTracker.periodic_poll):
        bpy.app.timers.unregister(SelectionTracker.periodic_poll)

    if SelectionTracker.on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(SelectionTracker.on_depsgraph_update)

    # Unhook headers & native panels
    unhook_header_draw(bpy.types.GRAPH_HT_header)
    unhook_header_draw(bpy.types.DOPESHEET_HT_header)

    bpy.types.GRAPH_PT_filters.remove(draw_into_native_filters)
    bpy.types.DOPESHEET_PT_filters.remove(draw_into_native_filters)

    del bpy.types.Scene.anim_ux_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    try:
        bpy.app.translations.unregister(__name__)
    except Exception:
        pass


if __name__ == "__main__":
    register()
