# Aubo i5 机械臂控制系统

基于笔记本的 Aubo i5 机械臂控制器，包含 Mujoco 物理仿真和真实机械臂通信控制。

## 项目结构

```
aubo_controller/
├── backend/
│   ├── src/robot_controller/
│   │   ├── robot_controller.py   # 机械臂控制接口
│   │   ├── mujoco_sim/
│   │   │   └── simulator.py     # Mujoco仿真器
│   │   ├── api/
│   │   │   └── main.py          # FastAPI服务
│   │   └── config.py            # 配置管理
│   ├── pyproject.toml
│   └── .venv/                   # uv虚拟环境 (已创建)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SimulationView.tsx  # 左侧: 3D仿真视图
│   │   │   └── ControlConsole.tsx  # 右侧: 控制台
│   │   ├── store/robotStore.ts
│   │   └── App.tsx
│   └── package.json
├── run_backend.py
├── start_backend.bat            # Windows启动脚本
└── README.md
```

## 快速开始

### 1. 依赖已安装

后端虚拟环境已在 `backend/.venv` 创建，核心依赖已安装:
- fastapi, uvicorn, websockets
- numpy, pydantic
- mujoco

### 2. 启动后端

**方式一**: 双击运行
```
start_backend.bat
```

**方式二**: 命令行
```bash
cd backend
call .venv\Scripts\activate.bat
set PYTHONPATH=.\src
python -m robot_controller.api.main
```

**方式三**: Python脚本
```bash
python run_backend.py
```

后端将在 http://localhost:8000 启动

### 3. 启动前端

```bash
cd frontend
npm install   # 首次运行需要
npm run dev
```

前端将在 http://localhost:3000 启动

### 4. 访问界面

打开浏览器访问 http://localhost:3000

## 功能说明

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
| `/test-connection` | POST | 测试连接 |
| `/state` | GET | 机械臂状态 |
| `/move/joints` | POST | 关节运动 |
| `/move/cartesian` | POST | 笛卡尔运动 |
| `/ws` | WebSocket | 实时状态 |

## 仿真模式 vs 真实机械臂

- **仿真模式 (默认)**: 不需要连接真实机械臂，用于开发和测试
- **真实机械臂**: 取消勾选Simulation Mode，输入正确IP连接

## 注意事项

1. **Mujoco License**: 如需使用Mujoco仿真，需要从 https://www.roboti.us/license.html 获取免费许可证
2. **pyaubo_sdk**: 连接真实机械臂需要安装Aubo官方SDK
3. **Python版本**: 支持Python 3.6-3.11

## 参考资料

- Aubo SDK API文档: `../../AuboStudio_SDK_API.pdf`
- 机械臂描述文件: `../../aubo_description-main/`
- [Aubo开发者官网](https://developer.aubo-robotics.cn/)
- [aubo_description GitHub](https://github.com/AuboRobot/aubo_description)
