# Aubo i5 机械臂控制系统

基于笔记本的 Aubo i5 机械臂控制器，包含 Mujoco 物理仿真、Eye 3D 相机集成和真实机械臂通信控制。

## 项目结构

```
aubo_controller/
├── backend/
│   ├── src/robot_controller/
│   │   ├── robot_controller.py      # 机械臂控制接口
│   │   ├── mujoco_sim/
│   │   │   └── simulator.py         # Mujoco仿真器
│   │   ├── api/
│   │   │   └── main.py              # FastAPI服务
│   │   ├── camera_service.py         # 相机服务抽象层
│   │   ├── eye3d_camera_adapter.py   # Eye 3D相机适配器
│   │   └── config.py                # 配置管理
│   ├── pyproject.toml
│   └── .venv/                       # uv虚拟环境 (已创建)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SimulationView.tsx   # 3D仿真视图
│   │   │   ├── CameraView.tsx       # 相机视图
│   │   │   └── ControlConsole.tsx   # 控制台
│   │   ├── store/robotStore.ts
│   │   └── App.tsx
│   └── package.json
├── start_all.bat                     # 一键启动脚本
├── start_backend.bat                 # 仅启动后端
└── README.md
```

## 快速开始

### 1. 依赖已安装

后端虚拟环境已在 `backend/.venv` 创建。使用 uv 管理，核心依赖:

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
websockets>=12.0
numpy>=1.26.0
mujoco>=3.1.0
pydantic>=2.5.0
python-multipart>=0.0.6
pillow>=10.0.0
```

### 2. 一键启动 (推荐)

双击运行 `start_all.bat`，同时启动后端和前端。

### 3. 手动启动后端

```bash
cd backend
.venv\Scripts\activate.bat
set PYTHONPATH=.\src
python -m robot_controller.api.main
```

后端将在 http://localhost:8000 启动

### 4. 启动前端

```bash
cd frontend
npm install   # 首次运行需要
npm run dev
```

前端将在 http://localhost:3000 启动

### 5. 访问界面

打开浏览器访问 http://localhost:3000

## 功能说明

### 界面布局
- **左侧上部**: 相机视图 (Eye 3D相机或Mock)
- **左侧下部**: Mujoco 3D仿真视图
- **右侧**: 控制台 (连接、关节控制、配置、日志)

### Control (控制) 标签
- **连接**: 输入Robot IP，点击Connect连接或Test测试连接
- **关节控制**: 6个关节滑块调节角度
- **速度调节**: 10%-100%
- **快捷位置**: Home / Ready / Folded
- **状态显示**: 实时关节角度和末端位置

### Config (配置) 标签
- **Robot Settings**: IP地址、端口、仿真模式
- **Motion Settings**: 速度、加速度、碰撞检测
- **Simulator Settings**: GUI、重力等
- **Save Configuration**: 保存配置到config.json

### Console (控制台) 标签
- 日志输出

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 健康检查 |
| `/health` | GET | 详细状态 |
| `/config` | GET/POST | 配置管理 |
| `/connect` | POST | 连接机械臂 |
| `/disconnect` | POST | 断开连接 |
| `/stop` | POST | 紧急停止 |
| `/test-connection` | POST | 测试连接 |
| `/state` | GET | 机械臂状态 |
| `/move/joints` | POST | 关节运动 |
| `/move/cartesian` | POST | 笛卡尔运动 |
| `/camera/status` | GET | 相机状态 |
| `/camera/connect` | POST | 连接相机 |
| `/camera/disconnect` | POST | 断开相机 |
| `/camera/frame` | GET | 获取相机帧 |
| `/ws` | WebSocket | 实时状态 |

## 相机支持

### Eye 3D相机 (M2-EyePro系列)

支持型号:
- M2-EyePro-000: USB3.0 灰度相机
- M2-EyePro-001: USB3.0 彩色相机 (1280x720)
- M2-EyePro-002: USB3.0 深度相机

使用 Eye3DViewer SDK (Eye3DViewer_API.dll)，通过 ctypes 调用。

### Mock相机

无硬件时使用Mock模式，显示合成渐变帧用于开发测试。界面显示"Mock"标签区分。

## 仿真模式 vs 真实机械臂

- **仿真模式 (默认)**: 不需要连接真实机械臂，用于开发和测试
- **真实机械臂**: 取消勾选Simulation Mode，输入正确IP连接

## 注意事项

1. **Mujoco License**: 如需使用Mujoco仿真，需要从 https://www.roboti.us/license.html 获取免费许可证
2. **pyaubo_sdk**: 连接真实机械臂需要安装Aubo官方SDK
3. **Eye3DViewer SDK**: 连接Eye 3D相机需要安装厂商SDK并配置DLL路径
4. **Python版本**: 支持Python 3.6-3.11

## 参考资料

- Aubo SDK API文档: `../../AuboStudio_SDK_API.pdf`
- Eye 3D相机文档: `../../eye-3d-camera-v2.5.4-zh.pdf`
- 机械臂描述文件: `../../aubo_description-main/`
- [Aubo开发者官网](https://developer.aubo-robotics.cn/)
- [aubo_description GitHub](https://github.com/AuboRobot/aubo_description)
