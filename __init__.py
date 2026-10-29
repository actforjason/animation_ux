bl_info = {
    "name": "Animation UX - 通道自动展开",
    "author": "Antigravity",
    "version": (1, 0, 2),
    "blender": (3, 6, 0),
    "location": "曲线编辑器与摄影表标题栏（过滤漏斗旁） / 3D 视图侧边栏",
    "description": "在仅显示所选时，选择动画对象或骨骼后自动展开对应通道，支持单选与多选情景配置",
    "category": "Animation",
}

import bpy
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
# 工具函数：兼容 Blender 4.x / 5.x 动作结构
# ============================================================================

def get_action_groups_and_slots(obj):
    """
    获取对象的动画槽位和曲线组列表。
    兼容：
      - Blender 5.x 分层/槽位动作 (strip.channelbags -> groups)
      - Blender 4.x / 3.x 传统动作结构 (action.groups)
    """
    slots = []
    groups = []
    if not obj or not obj.animation_data or not obj.animation_data.action:
        return slots, groups

    act = obj.animation_data.action
    slot = getattr(obj.animation_data, "action_slot", None)
    if slot:
        slots.append(slot)

    # Blender 5.x 分层动作
    if hasattr(act, "layers"):
        slot_handle = slot.handle if slot else None
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    if slot_handle is None or bag.slot_handle == slot_handle:
                        groups.extend(bag.groups)
    # Blender 4.x 传统动作
    elif hasattr(act, "groups"):
        groups.extend(act.groups)

    return slots, groups


def is_show_only_selected_active(context):
    """
    检查可见的曲线编辑器或摄影表是否开启了【仅显示所选】过滤。
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
    """即时重绘动画编辑器以刷新通道折叠/展开外观。"""
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
# 配置选项定义（纯中文无杂合）
# ============================================================================

SINGLE_MODE_ITEMS = (
    ("EXPAND_COLLAPSE_OTHERS", "展开所选，折叠其他", "展开当前选中项并自动折叠其他所有通道，保持面板最精简"),
    ("EXPAND_KEEP_OTHERS", "仅展开所选，保持其他", "展开当前选中项，保留之前已展开的通道"),
    ("DO_NOTHING", "不处理", "单选时不自动改变通道展开状态"),
)

MULTI_MODE_ITEMS = (
    ("EXPAND_ALL", "展开全部所选", "展开所有被选中的骨骼或对象通道组"),
    ("EXPAND_ACTIVE_ONLY", "仅展开活动项，折叠其他", "多选时只展开最后选中的活动项，其余保持折叠"),
    ("EXPAND_ACTIVE_KEEP", "仅展开活动项，保持其他", "多选时展开活动项，不改变其他项已展开状态"),
    ("COLLAPSE_ALL", "全部折叠", "多选时折叠所有通道以提供全局概览"),
    ("DO_NOTHING", "保持现状", "多选时不自动修改通道展开状态"),
)

OVERFLOW_MODE_ITEMS = (
    ("EXPAND_ACTIVE_ONLY", "仅展开活动项", "超过阈值时仅展开当前活动项"),
    ("COLLAPSE_ALL", "全部折叠", "超过阈值时全部折叠以防止屏幕被大量曲线挤爆"),
    ("DO_NOTHING", "保持现状", "超过阈值时不修改"),
)

ON_DESELECT_ITEMS = (
    ("KEEP", "保持现状", "全部取消选择时保持通道现有展开状态"),
    ("COLLAPSE_ALL", "全部折叠", "全部取消选择时自动折叠所有通道"),
)


class AnimUXSettings(PropertyGroup):
    enabled: BoolProperty(
        name="自动展开通道",
        description="当点击选择动画对象或骨骼时，自动展开对应的动画通道",
        default=True,
    )

    require_show_only_selected: BoolProperty(
        name="仅在【仅显示所选】开启时生效",
        description="只有当动画编辑器开启【仅显示所选】过滤时才触发自动展开",
        default=True,
    )

    # 单选配置
    single_mode: EnumProperty(
        name="单选行为",
        description="单个对象或骨骼被选中时的通道展开行为",
        items=SINGLE_MODE_ITEMS,
        default="EXPAND_COLLAPSE_OTHERS",
    )

    single_expand_slot: BoolProperty(
        name="自动展开父级槽位/对象",
        description="确保父级 Slot 或骨架对象通道也处于展开状态，保证子通道直接可见",
        default=True,
    )

    # 多选配置
    multi_mode: EnumProperty(
        name="多选行为",
        description="多个对象或骨骼被选中时的通道展开行为",
        items=MULTI_MODE_ITEMS,
        default="EXPAND_ALL",
    )

    use_multi_threshold: BoolProperty(
        name="启用数量阈值自适应",
        description="当同时选中的骨骼或对象过多时，自动切换策略以防止通道列表爆炸",
        default=True,
    )

    multi_threshold_count: IntProperty(
        name="阈值数量",
        description="选中数量超过此数值时，自动切换到降级策略",
        default=4,
        min=2,
        max=50,
    )

    multi_overflow_mode: EnumProperty(
        name="超出阈值时的策略",
        description="选中数量超出阈值时执行的行为",
        items=OVERFLOW_MODE_ITEMS,
        default="EXPAND_ACTIVE_ONLY",
    )

    # 生效编辑器
    target_graph_editor: BoolProperty(
        name="曲线编辑器",
        description="是否对曲线编辑器的通道列表生效",
        default=True,
    )

    target_dopesheet: BoolProperty(
        name="动画摄影表",
        description="是否对动画摄影表/动作编辑器的通道列表生效",
        default=True,
    )

    on_deselect: EnumProperty(
        name="全不选时",
        description="当没有任何对象或骨骼被选中时的行为",
        items=ON_DESELECT_ITEMS,
        default="KEEP",
    )


class AnimUXPreferences(AddonPreferences):
    bl_idname = __package__ or "animation_ux"

    def draw(self, context):
        layout = self.layout
        settings = getattr(context.scene, "anim_ux_settings", None)
        if not settings:
            layout.label(text="设置将在打开场景后初始化")
            return

        box = layout.box()
        box.label(text="全局配置", icon="SETTINGS")
        row = box.row()
        row.prop(settings, "enabled")
        row.prop(settings, "require_show_only_selected")

        row = box.row()
        row.label(text="生效编辑器:")
        row.prop(settings, "target_graph_editor")
        row.prop(settings, "target_dopesheet")

        # 单选情景面板
        box_single = layout.box()
        box_single.label(text="单个对象/骨骼选中情景", icon="USER")
        box_single.prop(settings, "single_mode")
        box_single.prop(settings, "single_expand_slot")

        # 多选情景面板
        box_multi = layout.box()
        box_multi.label(text="多个对象/骨骼选中情景", icon="COMMUNITY")
        box_multi.prop(settings, "multi_mode")
        box_multi.prop(settings, "use_multi_threshold")
        if settings.use_multi_threshold:
            col = box_multi.column(align=True)
            col.prop(settings, "multi_threshold_count")
            col.prop(settings, "multi_overflow_mode")

        box_misc = layout.box()
        box_misc.label(text="其他行为", icon="PREFERENCES")
        box_misc.prop(settings, "on_deselect")


# ============================================================================
# 核心处理逻辑
# ============================================================================

def process_channel_expansion(context):
    """
    根据当前上下文与配置应用通道展开/折叠规则。
    """
    if not context or not context.scene:
        return
    settings = getattr(context.scene, "anim_ux_settings", None)
    if not settings or not settings.enabled:
        return

    # 检查【仅显示所选】过滤开关
    if settings.require_show_only_selected and not is_show_only_selected_active(context):
        return

    mode = context.mode
    apply_graph = settings.target_graph_editor
    apply_ds = settings.target_dopesheet

    # -------------------------------------------------------------------------
    # 情景 1：姿态模式（骨骼）
    # -------------------------------------------------------------------------
    if mode == "POSE":
        sel_bones = [b.name for b in context.selected_pose_bones]
        active_bone_name = context.active_pose_bone.name if context.active_pose_bone else None
        active_obj = context.active_object

        # 全部取消选择
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

        # 展开父级槽位
        if settings.single_expand_slot:
            for s in slots:
                s.show_expanded = True

        count = len(sel_bones)

        # 单个骨骼选中情景
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

        # 多个骨骼选中情景
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
    # 情景 2：物体模式（普通物体）
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

        # 单个物体选中情景
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

        # 多个物体选中情景
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
# 选择监听器：Depsgraph 更新与定时器分发
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
            print(f"[Animation UX] 错误: {e}")
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
# 操作符定义
# ============================================================================

class ANIMUX_OT_ExpandChannelsNow(Operator):
    bl_idname = "anim_ux.expand_channels_now"
    bl_label = "立即执行通道展开"
    bl_description = "根据当前单选/多选配置立即刷新动画通道展开状态"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        process_channel_expansion(context)
        self.report({"INFO"}, "已按规则刷新通道展开状态")
        return {"FINISHED"}


class ANIMUX_OT_ToggleEnabled(Operator):
    bl_idname = "anim_ux.toggle_enabled"
    bl_label = "开关通道自动展开"
    bl_description = "快速开启或关闭选择对象/骨骼时自动展开通道的功能"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.anim_ux_settings
        settings.enabled = not settings.enabled
        state_str = "已开启" if settings.enabled else "已关闭"
        self.report({"INFO"}, f"通道自动展开: {state_str}")
        if settings.enabled:
            process_channel_expansion(context)
        return {"FINISHED"}


# ============================================================================
# 界面定义（标题栏挂载、弹出框与侧边栏）
# ============================================================================

class ANIMUX_PT_Popover(Panel):
    bl_idname = "ANIMUX_PT_popover"
    bl_label = "通道自动展开配置"
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
        col_single.label(text="单选情景", icon="USER")
        col_single.prop(settings, "single_mode", text="")
        col_single.prop(settings, "single_expand_slot")

        col_multi = layout.box()
        col_multi.label(text="多选情景", icon="COMMUNITY")
        col_multi.prop(settings, "multi_mode", text="")
        col_multi.prop(settings, "use_multi_threshold")
        if settings.use_multi_threshold:
            row = col_multi.row(align=True)
            row.prop(settings, "multi_threshold_count", text="阈值")
            row.prop(settings, "multi_overflow_mode", text="")

        layout.separator()
        row = layout.row(align=True)
        row.prop(settings, "target_graph_editor", toggle=True, text="曲线编辑器")
        row.prop(settings, "target_dopesheet", toggle=True, text="摄影表")

        layout.operator("anim_ux.expand_channels_now", icon="FILE_REFRESH")


def draw_header_button(layout, context):
    """
    绘制标题栏开关与单一原生下拉箭头。
    """
    settings = getattr(context.scene, "anim_ux_settings", None)
    if not settings:
        return

    row = layout.row(align=True)
    # 动作图标开关（开启时高亮）
    row.prop(settings, "enabled", text="", icon="CON_ACTION")
    # 下拉按钮：无额外图标参数，仅显示单一原生下拉箭头 ▼
    row.popover(panel="ANIMUX_PT_popover", text="")


# ----------------------------------------------------------------------------
# 标题栏拦截器：紧邻原生过滤漏斗按钮
# ----------------------------------------------------------------------------

class HeaderLayoutProxy:
    def __init__(self, real_layout, context):
        self._layout = real_layout
        self._context = context

    def popover(self, *args, **kwargs):
        res = self._layout.popover(*args, **kwargs)
        panel = kwargs.get("panel") or (args[0] if args else None)
        # 紧邻原生过滤漏斗按钮
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
    """在原生过滤漏斗弹窗内同样注入配置入口。"""
    settings = getattr(context.scene, "anim_ux_settings", None)
    if not settings:
        return
    layout = self.layout
    layout.separator()
    box = layout.box()
    box.label(text="通道自动展开", icon="CON_ACTION")
    row = box.row()
    row.prop(settings, "enabled")
    row.popover(panel="ANIMUX_PT_popover", text="", icon="PREFERENCES")


class ANIMUX_PT_SidebarPanel(Panel):
    bl_idname = "ANIMUX_PT_sidebar_panel"
    bl_label = "通道自动展开"
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
        box_s.label(text="单选情景", icon="USER")
        box_s.prop(settings, "single_mode")
        box_s.prop(settings, "single_expand_slot")

        box_m = layout.box()
        box_m.label(text="多选情景", icon="COMMUNITY")
        box_m.prop(settings, "multi_mode")
        box_m.prop(settings, "use_multi_threshold")
        if settings.use_multi_threshold:
            sub = box_m.column(align=True)
            sub.prop(settings, "multi_threshold_count")
            sub.prop(settings, "multi_overflow_mode")

        box_t = layout.box()
        box_t.label(text="生效编辑器与杂项", icon="WINDOW")
        row = box_t.row()
        row.prop(settings, "target_graph_editor")
        row.prop(settings, "target_dopesheet")
        box_t.prop(settings, "on_deselect")

        layout.operator("anim_ux.expand_channels_now", icon="FILE_REFRESH")


# ============================================================================
# 注册与反注册
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
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.anim_ux_settings = PointerProperty(type=AnimUXSettings)

    # 拦截标题栏以精准插入在原生漏斗按钮旁
    hook_header_draw(bpy.types.GRAPH_HT_header)
    hook_header_draw(bpy.types.DOPESHEET_HT_header)

    # 注入原生过滤漏斗弹窗
    bpy.types.GRAPH_PT_filters.append(draw_into_native_filters)
    bpy.types.DOPESHEET_PT_filters.append(draw_into_native_filters)

    # 注册事件监听
    if SelectionTracker.on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(SelectionTracker.on_depsgraph_update)

    if not bpy.app.timers.is_registered(SelectionTracker.periodic_poll):
        bpy.app.timers.register(SelectionTracker.periodic_poll, first_interval=0.05, persistent=True)


def unregister():
    # 注销定时器与事件
    if bpy.app.timers.is_registered(SelectionTracker.periodic_poll):
        bpy.app.timers.unregister(SelectionTracker.periodic_poll)

    if SelectionTracker.on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(SelectionTracker.on_depsgraph_update)

    # 恢复标题栏与原生面板
    unhook_header_draw(bpy.types.GRAPH_HT_header)
    unhook_header_draw(bpy.types.DOPESHEET_HT_header)

    bpy.types.GRAPH_PT_filters.remove(draw_into_native_filters)
    bpy.types.DOPESHEET_PT_filters.remove(draw_into_native_filters)

    del bpy.types.Scene.anim_ux_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
