# 地图生成算法调研报告

> 调研对象：类《以撒的结合》2D 俯视角射击 roguelike（Python + Pygame）
> 现状：1~3 个水平排列的固定 1024x576 房间、门连接、障碍物随机生成
> 调研重点：**单房间内部障碍布局**（非房间拓扑）
> 状态：调研文档，非需求协议。结论待与需求文档同步确认后实施。

## 一、以撒式"房间拼接型"地图的关键设计思路

来源：Isaac 官方 Lua API 文档（Level / RoomDescriptor）+ 社区分析。

1. **楼层 = 13×13 房间网格**。每个房间占据 1~4 个网格单元（1x1 / 1x2 / 2x1 / 2x2 / L 形）。
2. **两步生成**：先决定"哪些格子有房间、什么类型"，再为每个房间挑选预制布局（房间内部是固定 tile 布局 + 内部 13×13 网格实体槽）。即**拓扑随机、内容预制**——房间内容不过程序生成，只做选择。
3. **特殊房间按规则放置**：出生房、Boss 房（远离出生点/在边缘）、宝库、商店等，有最小距离约束和数量上限。
4. **门 = 邻接关系的产物**。两格相邻即生成门洞；以撒**没有走廊**，房间直接贴邻，门就是通道。
5. **每个房间带独立种子**：实体/掉落、装饰、清房奖励各一个种子，可复现关卡。

**对"单房间"的启示**：以撒房间内部本质上是固定尺寸的 tile 网格，障碍生成就是"在这个网格上按规则放柱子/坑/刺"。

## 二、算法对比

### 1. BSP（二叉空间分割）— 房间+走廊

- 原理：把整块地图递归二分成矩形子区域，直到叶子大小≈房间；每个叶子内放一个随机大小房间（天然不重叠）；自底向上用 L/Z 形走廊连接兄弟区域，保证全连通。
- 优点：实现简单（约 50 行）、房间永不重叠、天然连通、可控制密度。
- 缺点：全是矩形房间，风格单调；难以表达以撒式"网格房间+门"。
- 适用：经典俯视角地牢；可降级用于单房间内分区。

### 2. WFC（波函数坍缩）— tile 级约束生成

- 原理：把地图看作 tile 网格，每格是候选 tile 集合的叠加态；反复取熵最小格"坍缩"，再用邻接约束传播。两个模型：Overlapping（从样例图学习模式）和 Simple Tiled（手写 tile 邻接规则）。支持约束合成。
- 优点：风格统一、有局部结构的室内布局；对"房间内网格"天然契合。
- 缺点：可能坍缩失败需回溯/重试；效果依赖 tile 集和邻接表设计。
- 适用：**单房间内部障碍布局**；已被《Caves of Qud》《Bad North》使用。

### 3. 房间拼接 / 圆形布局（TinyKeep 式）

- 原理：随机撒矩形（允许重叠）→ 物理分离 → Delaunay 三角剖分建邻接图 → 取最小生成树(MST)做主通路 + 随机回几条边 → 沿图边生成走廊。
- 优点：房间位置/大小自由度最高。
- 缺点：实现量最大；对"水平排列 1~3 个房间"的现状是杀鸡用牛刀。
- 适用：整层拓扑生成；其"网格图 + MST"思路可复用于以撒式门图。

| | BSP | WFC | 房间拼接(TinyKeep) |
|---|---|---|---|
| 实现成本 | ★ | ★★★ | ★★★★ |
| 风格 | 矩形地牢 | 样式丰富、统一 | 自由蜂巢 |
| 失败处理 | 无 | 可能冲突需重试 | 无 |
| 最佳场景 | 整层 | **单房间 tile 布局** | 整层拓扑/环形图 |

## 三、开源项目参考

| 项目 | 链接 | 说明 | 技术栈 |
|---|---|---|---|
| WaveFunctionCollapse | https://github.com/mxgmn/WaveFunctionCollapse | WFC 鼻祖，25k★，overlapping/tiled 双模型，README 含算法详解与语言移植清单 | C# |
| wfc_python | https://github.com/ikarth/wfc_python | mxgmn 官方清单收录的 overlapping 模型 Python 移植，纯 Python 易读 | Python |
| python-tcod | https://github.com/libtcod/python-tcod | 经典 roguelike 库（BSP、FOV、A*），配套教程有完整 Python 房间+走廊生成代码 | Python |
| DungeonGenerator | https://github.com/jongallant/DungeonGenerator | TinyKeep 算法完整实现（分离 + Delaunay + MST + 回边） | C#/Unity |
| Procedural-Cave-Generation | https://github.com/SebLague/Procedural-Cave-Generation | 元胞自动机生成洞穴 + 连通分量后处理（对"生成障碍后保证可达"思路可抄） | C#/Unity |
| tutorial-dungeon-generation | https://github.com/Tiendil/tutorial-dungeon-generation | 极简 Python 地牢生成教程 | Python |

## 四、针对本项目的建议（按性价比排序）

1. **网格化 + 规则放障碍（先做）**：房间内部划分 tile 网格（如 64px → 16×9 或 32px → 32×18），障碍只在格子上。规则：出生点和门附近 1~2 格净空；房间中央留 1/3 空间（保证走位）；柱子不贴墙、不与门正对。成本最低、稳定性最高，也是以撒的真实做法。
2. **对称布局（强烈推荐）**：随机生成左半边障碍，然后镜像到右半边（或上下镜像），天然平衡、好看、可读性好。可混入少量非对称点缀。
3. **WFC Simple Tiled 生成室内 tilemap（中期）**：定义 tile 集（空/柱子/平面墙/坑/不可达地块）和邻接表，在网格上跑 WFC。失败就换种子重试。
4. **迷宫式障碍（可选）**：递归回溯/最小生成树迷宫生成"不完全墙"（留缺口），或轻量 BSP 分区填障碍区，营造绕行空间。
5. **连通性后处理（必须）**：生成后做可达性检查（BFS 从出生点到门、到全图空地），不达标则重生成或打开障碍。
6. **以"房间模板池"为终态**：把生成器产出的优秀布局落盘为模板（每类房间 20~50 个），运行时随机抽。可控、可调、可平衡，最接近以撒手感。

**结论**：先做"网格化 + 规则 + 对称 + 可达性校验"（一两天工作量，立刻见效）；WFC 作为下一个迭代目标；整层拓扑算法（BSP/TinyKeep）当前需求不大，等做多房间树状地图时再引入，届时参考 TinyKeep 的 MST 方案。

## 五、待深入调研的方向

- WFC Simple Tiled 的 tile 集与邻接表设计实例
- 以撒房间布局"对称生成"的具体实现细节
- 房间模板池的模板数据结构与存储格式
- 可达性校验的轻量实现（BFS 在网格上的成本）
- 迷宫生成（递归回溯/MST）在矩形房间内的适配

## 六、深入调研：固定尺寸房间内墙壁/障碍/坑布局生成

> 补充调研（第二轮），针对固定 1024x576 房间（约 16x9 格 @64px 或 32x18 格 @32px）的生成逻辑。

### 6.1 关键发现：以撒的房间内部布局不是程序生成的

- 每个房间是**关卡设计师手工画好的静态布局**（.stb 文件），`rooms.xml` 只存元数据，运行时按权重抽取一个房间。
- `RoomConfig_Room` 字段：StageID / Type / Variant / Difficulty / Shape / Width / Height / Doors（8 门槽位掩码）/ Weight / Spawns。**无任何"障碍生成算法"字段**。
- 1x1 房间格子索引 0–134（15x9 网格 + 周边一圈墙，每格 64px）。

### 6.2 GridEntity 类型（对应"墙壁/障碍/坑"）

`GridEntityType`（0–27）按项目对应关系分类：

| 分类 | 枚举值 | 说明 |
|---|---|---|
| 不可破坏 | GRID_WALL (15) | 房间边框墙 |
| 可破坏 | GRID_ROCK (2)、GRID_ROCKB (3)、GRID_PILLAR (24)、GRID_TNT (12)、GRID_STATUE (21) 等 | 被炸弹/弹幕摧毁 |
| 不可达 | GRID_PIT (7)、GRID_GRAVITY (19) | 坑有碰撞，弹幕落入消失 |
| 危险地板 | GRID_SPIKES (8)、GRID_SPIKES_ONOFF (9)、GRID_SPIDERWEB (10) | 可走但造成伤害 |
| 功能格 | GRID_DOOR (16)、GRID_TRAPDOOR (17)、GRID_STAIRS (18)、GRID_PRESSURE_PLATE (20) | |

### 6.3 可考证的放置规则（编辑器/设计约定）

- **出生点净化**：出生点格及周围一圈必须为空。
- **门区域净化**：门内 2–3 格无实体障碍。
- **坑不贴墙**：坑至少与墙留 1 格走道。
- **不封死**：保证从出生点到所有门连通（编辑器自动检查）。
- **对称**：大量普通房间左右对称（视觉规整 + 视野公平）。

### 6.4 WFC Simple Tiled 邻接表设计指南

- **Simple Tiled Model**：瓦片列表 + 显式邻接规则，传播即邻接约束传播。对称系统用二面体群 D4：`X`(恒等 1 变换)、`I`(180° 旋转 2)、`T`(90° 旋转 4)、`L`(旋转+反射 4)。
- 官方 `tilesets/Castle.xml` 是"坑+桥+障碍+墙"的现成范本：river/riverturn（不可达水域）、road/roadturn、bridge（桥上可走）、wall/wallriver/wallroad、ground、tower 共 11 种瓦片，邻接规则实现"river 只能与 river/riverturn/bridge 相邻；bridge 必须两端接 road 或 ground"。
- **约束过松则无趣**：所有瓦片都能互相相邻时生成结果毫无全局结构；要有硬约束（如"坑不能单独出现"）。
- **约束合成**：预先固定某些格子（正好用于固定出生点/门旁为空）。
- **失败重试**：矛盾时整局重试，小房间毫秒级，重试 10 次几乎必然成功（官方 samples 有 limit=25/120 参数）。
- **WFC 不保证连通**（Caves of Qud 的 Brian Bucklew GDC 演讲明确讨论），必须在瓦片规则或后处理层保证。

### 6.5 坑/水域放置最佳实践（Brogue）

> 来源：Rock Paper Shotgun 对 Brogue 作者 Brian Walker 的访谈。

- 坑以**簇**生成（2–6 格连片，扩展概率递减）。
- 放置后**连通性检查**："把所有湖画在透明胶片上滑动到随机位置，检查未被覆盖的可走部分是否仍完全连通，20 次失败就画小一号的湖再试"。
- **打洞回路**：房间连接后是树形（无环），扫描墙找两侧可行走且路径距离远的墙打洞，形成环路改善探索。

### 6.6 对称布局生成

- 以撒的对称是**手工画的**，无公开程序化实现；工程做法：垂直中轴镜像（默认）、只生成左半再镜像、中轴格特殊处理、镜像后跑连通性校验。
- 16 列网格中轴在第 8/9 列之间（偶数宽干净）；9 列网格中轴在第 5 列（奇数宽需特殊处理）。

### 6.7 连通性保证（四层次）

1. **放置时避免封死**（预防）：障碍/坑不贴墙不贴门，沿墙至少 1 格走道。
2. **生成后校验**：BFS（出生点→所有门）或并查集（出生点与门同集合）。
3. **打洞形成回路**（改善体验）。
4. **必经之路**（可选进阶）：Boris the Brave 的 chiseling 凿刻法（DFS 求割点，只删非割点格）。

### 6.8 落地建议（1024x576 房间）

| 项 | 推荐 |
|---|---|
| 网格尺寸 | **32x18 @32px** 逻辑格（障碍实体占 2x2=64px，对齐现有美术） |
| 墙壁 | 仅周边墙（1 格逻辑厚），**不生成内墙** |
| 障碍密度 | 以撒 1x1 房约 6–15 个岩石/柱子 = 内格面积 **5%–12%**；普通房 8%–12%，禁成排/2x2 块，单格间距 ≥1 |
| 坑 | 簇状 2–6 格，不贴墙/门，不横穿房间，两端留桥 |
| 净化区 | 出生点 3x3 绝对净化；门内 2 格净化 |
| 连通性 | BFS 出生点→所有门，失败移除堵路障碍或重试 |
| WFC vs 规则 | **先规则后 WFC**：规则生成做主方案，WFC 后期作为变体生成器（瓦片集 6–10 种） |

### 6.9 优先实现顺序

1. **手工模板库**：5–10 个精心设计模板（含对称模板、带坑模板），按权重抽取。
2. **规则随机生成 + 净化区**：模板上随机增删 2–4 个障碍，出生点/门净化。
3. **对称镜像生成**：随机画左半 → 镜像 → 校验。
4. **坑簇生成 + BFS 连通性校验 + 修复**。
5. **（可选）WFC 瓦片集**：参照 Castle.xml 定义坑/桥/障碍/墙邻接表，接入 Python WFC 实现。

---

## 七、参考资料清单

### 7.1 以撒官方 API 文档

| 参考对象 | 链接 |
|---|---|
| GridEntity 类（格子实体类型、碰撞类） | https://wofsauge.github.io/IsaacDocs/rep/GridEntity.html |
| GridEntityType 枚举（28 种网格实体） | https://wofsauge.github.io/IsaacDocs/rep/enums/GridEntityType.html |
| RoomConfig_Room（房间元数据字段） | https://wofsauge.github.io/IsaacDocs/rep/RoomConfig_Room.html |
| RoomShape 枚举（房间形状与格子索引） | https://wofsauge.github.io/IsaacDocs/rep/enums/RoomShape.html |
| Level（楼层生成 API） | https://wofsauge.github.io/IsaacDocs/rep/Level.html |
| RoomDescriptor（房间描述 API） | https://wofsauge.github.io/IsaacDocs/rep/RoomDescriptor.html |

### 7.2 WFC 相关

| 参考对象 | 链接 |
|---|---|
| WFC 原版仓库（Simple Tiled、对称系统、约束合成、失败策略） | https://github.com/mxgmn/WaveFunctionCollapse |
| 官方瓦片集示例 Rooms.xml / Castle.xml（邻接表格式范本） | https://github.com/mxgmn/WaveFunctionCollapse/tree/master/tilesets |
| marian42 城市生成实践（邻接建模、回溯、错误处理） | https://marian42.de/article/wfc/ |
| Boris the Brave 连通路径 chiseling 凿刻法 | https://www.boristhebrave.com/2018/04/28/random-paths-via-chiseling/ |
| Caves of Qud 用 WFC 的演讲（Brian Bucklew，GDC 2019，讨论连通性） | https://www.youtube.com/watch?v=AdCgi9E90jw |

### 7.3 WFC Python 实现

| 参考对象 | 链接 |
|---|---|
| wfc_python（overlapping 模型 Python 移植，官方清单收录） | https://github.com/ikarth/wfc_python |
| py-wfc-estm（Even Simpler Tile Model，纯 Python 瓦片模型，最贴合 simple tiled） | https://github.com/antigones/py-wfc-estm |
| wave-function-collapse（纯 Python 实现） | https://github.com/Coac/wave-function-collapse |
| GraphWaveFunctionCollapse（图上的 WFC，任意局部结构） | https://github.com/lamelizard/GraphWaveFunctionCollapse |
| gpWFC（PyOpenCL GPU 瓦片模型） | https://github.com/s-ol/gpWFC |
| DeBroglie（C# 参考实现，支持约束/回溯/hex 网格，Python 可参考其约束 API） | https://boristhebrave.github.io/DeBroglie |

### 7.4 Roguelike 生成算法文章与教程

| 参考对象 | 链接 |
|---|---|
| RogueBasin: Basic BSP Dungeon generation | https://www.roguebasin.com/index.php?title=Basic_BSP_Dungeon_generation |
| RogueBasin: 元胞自动机洞穴 + flood fill 连通性修复 | https://www.roguebasin.com/index.php/Cellular_Automata_Method_for_Generating_Random_Cave-Like_Levels |
| RogueBasin: Python 房间+走廊生成器 | https://www.roguebasin.com/index.php/A_Simple_Dungeon_Generator_for_Python_2_or_3 |
| RogueBasin: Shattered Pixel Dungeon 地图生成流程 | https://www.roguebasin.com/index.php/Introducing_the_map_generation_algorithm_in_Shattered_Pixel_Dungeon |
| RogueBasin: 文章总索引（Map 分类 30+ 篇） | https://www.roguebasin.com/index.php/Articles |
| Brogue 关卡生成全流程访谈（房间贴合、打洞回路、湖的连通性放置） | https://www.rockpapershotgun.com/2015/07/28/how-do-roguelikes-generate-levels/ |
| Gamasutra: Procedural_Dungeon_Generation_Algorithm（TinyKeep，房间拼接/MST） | http://www.gamasutra.com/blogs/AAdonaac/20150903/252889/Procedural_Dungeon_Generation_Algorithm.php |

### 7.5 开源项目参考（两轮调研汇总）

| 项目 | 链接 | 参考对象 | 技术栈 |
|---|---|---|---|
| WaveFunctionCollapse | https://github.com/mxgmn/WaveFunctionCollapse | WFC 鼻祖，README 含算法详解与移植清单 | C# |
| wfc_python | https://github.com/ikarth/wfc_python | overlapping 模型 Python 移植，学习首选 | Python |
| python-tcod | https://github.com/libtcod/python-tcod | roguelike 库（BSP、FOV、A*），教程含房间+走廊生成代码 | Python |
| DungeonGenerator | https://github.com/jongallant/DungeonGenerator | TinyKeep 算法完整实现（分离+Delaunay+MST+回边） | C#/Unity |
| Procedural-Cave-Generation | https://github.com/SebLague/Procedural-Cave-Generation | 元胞自动机洞穴 + 连通分量后处理（"生成障碍后保证可达"思路） | C#/Unity |
| tutorial-dungeon-generation | https://github.com/Tiendil/tutorial-dungeon-generation | 极简 Python 地牢生成教程 | Python |
| The-Binding-of-Isaac-Python | https://github.com/K1rL3s/The-Binding-of-Isaac-Python | Pygame 的以撒复刻（规模小，作参考） | Python |
