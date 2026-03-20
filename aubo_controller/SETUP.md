# Aubo i5 机械臂控制系统 - 项目设置

## 项目概述

基于笔记本的 Aubo i5 机械臂控制器，包含：
- Mujoco 物理仿真环境
- 真实机械臂通信控制
- Web 前端示教器界面

## 系统要求

- Python 3.6 - 3.11
- Node.js 18+
- ROS2 (仅用于真实机械臂控制)
- Mujoco (仿真用)

## 安装步骤

### 1. 安装 Python 依赖

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装基础依赖
pip install -e .

# 安装 Aubo SDK (必须)
pip install pyaubo_sdk
```

**注意**: `pyaubo_sdk` 是 Aubo 官方提供的 Python SDK，必须单独下载安装。

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. Mujoco 安装

```bash
# 使用 pip 安装 mujoco
pip install mujoco

# 下载 Mujoco 许可证 (免费)
# 访问 https://www.roboti.us/license.html
# 将 license.txt 放在 ~/.mujoco/mjkey.txt
```

## 运行

### 启动后端服务

```bash
cd backend
python -m robot_controller.api.main
```

API 服务将在 http://localhost:8000 启动。

### 启动前端

```bash
cd frontend
npm run dev
```

前端将在 http://localhost:3000 启动。

### 访问界面

打开浏览器访问 http://localhost:3000

## 功能说明

### 仿真模式 (默认)

默认运行在仿真模式，不需要连接真实机械臂：

1. 启动后端和前端
2. 点击 "Connect" 连接仿真器
3. 使用关节控制滑块调整机械臂姿态
4. 点击 "Move to Position" 执行运动
5. 左侧 3D 视图实时显示机械臂状态

### 真实机械臂模式

1. 确保笔记本与机械臂在同一网络
2. 修改 `robot_ip` 为机械臂实际 IP
3. 取消勾选 simulation 模式
4. 点击 "Connect" 连接真实机械臂

## 目录结构

```
aubo_controller/
├── backend/
│   ├── src/
│   │   ├── robot_controller/
│   │   │   ├── robot_controller.py    # 机械臂控制封装
│   │   │   └── api/
│   │   │       └── main.py            # FastAPI 服务
│   │   └── mujoco_sim/
│   │       └── simulator.py           # Mujoco 仿真器
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SimulationView.tsx     # 3D 仿真视图
│   │   │   └── ControlConsole.tsx     # 控制台
│   │   ├── store/
│   │   │   └── robotStore.ts          # 状态管理
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 健康检查 |
| `/health` | GET | 详细状态 |
| `/connect` | POST | 连接机械臂 |
| `/disconnect` | POST | 断开连接 |
| `/state` | GET | 获取机械臂状态 |
| `/move/joints` | POST | 关节运动 |
| `/move/cartesian` | POST | 笛卡尔运动 |
| `/simulator/state` | GET | 获取仿真状态 |
| `/ws` | WS | WebSocket 实时更新 |

## 参考资料

- Aubo SDK API 文档: `../../AuboStudio_SDK_API.pdf`
- 机械臂描述文件: `../../aubo_description-main/`
- [Aubo 开发者官网](https://developer.aubo-robotics.cn/)
- [aubo_description GitHub](https://github.com/AuboRobot/aubo_description)
