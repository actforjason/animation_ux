# Animation UX - Auto Expand Channels
[中文](#中文说明) | [English](#english-documentation)

---

## 中文说明

Blender 动画通道自动展开插件。当在动画编辑器（曲线编辑器 Graph Editor / 动画摄影表 Dope Sheet）开启 **仅显示所选 (Show Only Selected)** 时，点击视图中的动画对象或骨骼，自动展开对应的动画通道，并针对**单选**与**多选**提供完整的行为情景配置。

### 核心特性

1. **智能感应与零延迟响应**：
   - 监听场景选择变化，点击骨骼或物体瞬间同步通道展开状态。
   - 动画播放过程中自动暂停监测，确保播放帧率 100% 流畅不卡顿。
   - 仅在触发有效选择变化时执行，无冗余开销。

2. **单选情景配置**：
   - **展开所选，折叠其他** *(推荐默认)*：只展开当前点击选中的骨骼/物体通道，并自动折叠其他所有通道，使通道列表始终极致整洁、聚焦。
   - **仅展开所选，保持其他**：展开当前选中的通道，保留其他已展开的通道。
   - **不处理**：单选时不干预通道展开状态。
   - **自动展开父级槽位/对象**：确保父级 Slot 或骨架对象处于展开状态，保证子骨骼通道完全可见。

3. **多选情景配置**：
   - **展开全部所选**：多选（框选/加选）时，自动展开所有选中项对应的通道组。
   - **仅展开活动项，折叠其他**：多选时仅展开最后选中的活动骨骼/物体，其余所选骨骼折叠，防止视口和通道过多拥挤。
   - **仅展开活动项，保持其他**：多选时仅展开活动项，不改变其他通道状态。
   - **全部折叠**：多选时自动折叠全部通道，方便宏观查看关键帧概览。
   - **数量自适应阈值**：可自定义阈值（默认 4 个）。当多选项数超过阈值时，自动平滑切换至溢出策略（如仅展开活动项），防止一次框选大量骨骼导致面板被数百条曲线挤满。

4. **原生多语言自动切换**：
   - 接入 Blender 原生 i18n 翻译字典。
   - 全局切换为中文时显示纯中文界面，切换为英文时显示纯英文界面，无混杂括号附注。

5. **双向架构兼容 (Blender 4.x & Blender 5.x)**：
   - 完美适配 Blender 5.x 的层级/槽位动作系统（Layered / Slotted Actions、`ChannelBag`、`ActionSlot`）。
   - 向上向下兼容 Blender 4.x / 3.6+ 的经典动作与曲线组系统。

6. **便捷 UI 入口**：
   - **Graph Editor / Dope Sheet 顶部标题栏**：精准紧邻原生过滤漏斗按钮右侧，提供一键开关与单一无冗余下拉菜单。
   - **3D 视口 N 侧边栏**：`Animation UX` 面板。
   - **插件偏好设置**：完整的全局配置项与提示说明。

### 安装方法

1. 将 `animation_ux` 文件夹拷贝到 Blender 的插件目录（或打包为 `.zip` 后在 Blender 偏好设置中点击 `安装...`）。
2. 在 **编辑 -> 偏好设置 -> 插件** 中搜索并启用 `Animation UX - Auto Expand Channels`。
3. 打开曲线编辑器或动画摄影表，确保开启了顶部的“仅显示所选 (`show_only_selected`)”漏斗过滤项即可体验。

---

## English Documentation

A Blender animation workflow add-on that automatically unfolds animation channels in the Graph Editor and Dope Sheet when selecting animated objects or pose bones under **Only Show Selected** mode. Provides granular behavioral configurations for both **single selection** and **multiple selection** scenarios.

### Key Features

1. **Zero-Latency Smart Tracking**:
   - Immediately detects bone and object selection changes without manual hotkeys.
   - Automatically pauses during animation playback to preserve full 60+ FPS viewport performance.
   - Updates only upon actual selection changes with minimal computational overhead.

2. **Single Selection Scenarios**:
   - **Expand Selected & Collapse Others** *(Recommended)*: Expands only the newly clicked bone/object channel while collapsing all others to keep the editor clean and focused.
   - **Expand Selected & Keep Others**: Expands the target channel while leaving previously opened channels intact.
   - **Do Nothing**: Keeps channel hierarchy untouched on single selection.
   - **Auto Expand Parent Slot/Object**: Ensures the parent Armature/Slot channel is expanded so sub-channels remain visible.

3. **Multiple Selection Scenarios**:
   - **Expand All Selected**: Expands channels for all selected items when box-selecting or shift-selecting.
   - **Expand Active Only & Collapse Others**: Expands only the active (last selected) item and collapses the rest, preventing dozens of f-curves from pushing elements off screen.
   - **Expand Active Only & Keep Others**: Expands the active item without collapsing existing open channels.
   - **Collapse All Selected**: Folds all selected channels for a high-level summary overview.
   - **Adaptive Count Threshold**: Configurable limit (default 4). When selection exceeds the threshold, automatically switches to a fallback overflow strategy (e.g. active item only) to prevent UI clutter.

4. **Native Blender i18n Localization**:
   - Integrates cleanly with Blender's official translation framework (`bpy.app.translations`).
   - Automatically renders pure English when Blender is set to English, and pure Chinese when set to Simplified Chinese, without awkward mixed parenthetical labels.

5. **Full Version Compatibility (Blender 4.x & 5.x)**:
   - Native support for Blender 5.x layered and slotted actions (`ChannelBag`, `ActionSlot`).
   - Backward-compatible with Blender 4.x and 3.6+ legacy actions and action groups.

6. **Seamless Header & Panel Integration**:
   - **Header Bar (Graph Editor & Dope Sheet)**: Injected directly adjacent to the native filter funnel button (`FILTER`) with a toggle icon and a single clean dropdown arrow.
   - **3D Viewport Sidebar**: Dedicated `Animation UX` tab in the N-panel.
   - **Add-on Preferences**: Comprehensive options and parameter tuning.

### Installation

1. Copy the `animation_ux` directory into your Blender addons folder (or compress into `.zip` and use `Install from Disk...` in Preferences).
2. Enable **Animation UX - Auto Expand Channels** under **Edit -> Preferences -> Add-ons**.
3. In the Graph Editor or Dope Sheet header, make sure **Only Show Selected** is enabled to start using.
