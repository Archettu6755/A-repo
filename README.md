# 像素风肉鸽射击游戏

一款使用 Python 和 Pygame 开发的轻量俯视角射击游戏。玩家扮演进入军事隔离区的士兵，在黑暗房间中寻找照明机关、清理僵尸、收集金币并购买永久强化。一局共三关：第一关包含 2 至 3 个普通房间，第二关和第三关各包含 2 至 4 个普通房间。第三关商店之后进入空 Boss 房，Boss 内容待后续讨论。

正式版采用 32px 网格、房间模板池和 3/4 俯视像素画。游戏以软件渲染可运行、普通电脑稳定 60 FPS 为目标。

## 文档

- `docs/proposal.md`：正式需求与验收标准
- `docs/map.md`：地图结构、模板和校验规则
- `docs/art.md`：美术方向、资源清单和导出规范
- `docs/rules.md`：玩家可读的玩法说明

## 视觉母版

- `assets/concepts/art_direction_board_v1.png`：整体风格板
- `assets/characters/character_turnarounds_v1.png`：角色四方向母版
- `assets/environment/environment_props_master_v1.png`：场景与物件母版
- `assets/ui/ui_master_v1.png`：UI 母版

## 运行

```bash
uv run game
```

项目使用 uv 管理 Python 环境和依赖。
