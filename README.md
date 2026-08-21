# Serial UDP Bridge

基于 PyQt6 开发的串口数据监测与 UDP 转发上位机。

程序接收其他设备或软件通过串口发送的中文字符串。当串口连续一段时间没有收到新字节时，将当前缓冲区判定为一条完整消息，然后解码、显示并封装为 JSON，通过 UDP 转发给目标软件。

## 功能

- 自动检测和刷新串口
- 波特率选择
- 数据位选择
- 停止位选择
- 校验位选择
- UTF-8 和 GBK 编码选择
- 可配置串口静默分帧时间
- 串口读取后台线程
- 中文字符串实时显示
- JSON 数据包封装
- UDP 数据转发
- 接收成功和失败统计
- UDP 发送成功和失败统计
- 运行日志显示

## 消息分帧规则

串口是连续字节流，本项目不依赖换行符或特殊结束符。

每次收到新字节时，程序都会重新启动静默计时器。连续达到指定时间没有新字节后，才将缓冲区中的内容判定为一条完整消息。

默认静默时间：

```text
1000 ms
```

## UDP 数据格式

UDP 数据统一使用 UTF-8 编码的 JSON：

```json
{
  "protocol_version": 1,
  "message_id": "唯一消息标识",
  "received_at": "接收时间",
  "serial_port": "/dev/cu.usbserial-110",
  "source_encoding": "utf-8",
  "byte_count": 24,
  "text": "上海设备运行正常"
}
```

即使串口数据使用 GBK，生成的 UDP JSON 仍统一使用 UTF-8。

## 项目结构

```text
.
├── main.py
├── requirements.txt
├── app
│   ├── controllers
│   │   └── main_controller.py
│   ├── models
│   │   ├── config.py
│   │   ├── packet.py
│   │   └── statistics.py
│   ├── services
│   │   ├── frame_assembler.py
│   │   ├── message_decoder.py
│   │   └── udp_sender.py
│   ├── ui
│   │   └── main_window.py
│   └── workers
│       └── serial_worker.py
└── tests
```

## 环境要求

- Python 3.9 或更高版本
- PyQt6
- pyserial
- macOS 或 Windows

## 安装依赖

```bash
python -m pip install -r requirements.txt
```

## 运行软件

```bash
python main.py
```

## 运行测试

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 串口名称

macOS 通常显示为：

```text
/dev/cu.usbserial-*
/dev/cu.usbmodem-*
```

Windows 通常显示为：

```text
COM3
COM4
COM5
```

程序通过 pyserial 自动检测串口，不在代码中固定具体设备名称。

## UDP 发送统计说明

“UDP 发送成功”表示操作系统成功接受了本次 UDP 发送请求。UDP 本身不提供接收确认，因此该统计不能证明目标软件一定已经收到数据。

如果需要可靠确认，接收方需要增加 ACK 应答协议。

## Windows 部署

Windows 可执行文件需要在 Windows 环境中使用 PyInstaller 构建，不能直接在 macOS 上生成。

建议先使用目录模式测试：

```bash
python -m PyInstaller --noconfirm --clean --windowed --name SerialUdpBridge main.py
```

测试稳定后再生成单文件：

```bash
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SerialUdpBridge main.py
```

## 开发状态

项目目前处于开发和硬件联调阶段。

## License

MIT License

## 创建虚拟环境  当前文件夹

在当前文件夹创建 Python 虚拟环境：
python -m venv .venv
激活虚拟环境（PowerShell）：
.\.venv\Scripts\Activate.ps1
成功后，命令行前面会出现：
(.venv)
然后安装依赖：
pip install 包名
退出虚拟环境：
deactivate
在 VS Code 中可按 Ctrl+Shift+P，搜索 Python: Select Interpreter，选择 .venv 中的 Python。通常还应将 .venv/ 加进 .gitignore。

## 可以查看当前使用的是哪个解释器

python -c "import sys; print(sys.executable)"

## 创建虚拟环境  其他文件夹

方法二：在当前位置，直接指定虚拟环境路径
python -m venv D:\你的项目文件夹\.venv
D:\你的项目文件夹\.venv\Scripts\Activate.ps1
激活后检查当前使用的 Python：
python -c "import sys; print(sys.executable)"

## windows上编译成为EXE文件

先激活当前项目的虚拟环境，然后在 VS Code 终端执行：
python -m PyInstaller --version

可以使用 PyInstaller 把 PyQt6 项目打包成 Windows 的 .exe。严格来说这是“打包”，不是完全编译。
先在 VS Code 终端进入项目目录，并激活虚拟环境：
.\.venv\Scripts\Activate.ps1
安装 PyInstaller：
pip install pyinstaller
假设程序入口文件是 main.py，执行：
python -m PyInstaller --onefile --windowed --name 我的上位机 main.py
参数含义：
--onefile：打包成单个 EXE
--windowed：运行时不显示黑色命令行窗口
--name：设置 EXE 文件名
main.py：程序入口文件
打包成功后，EXE 通常位于：
你的项目目录\dist\我的上位机.exe
同时还会生成：
build\             临时打包文件
dist\              最终程序
我的上位机.spec     打包配置文件

## 快捷键打开终端 

Cmd + `

## windows 禁止启动项

方法二：Windows 设置
按 Win + I
进入“应用”→“启动”
关闭目标软件右侧的开关

## 共享热点

ncpa.cpl
服务设置
services.msc
注册表
regedit

## git上面克隆

在 Windows + VS Code 中，可以这样克隆 GitHub 项目：
先在 GitHub 项目页面点击绿色 Code 按钮，复制 HTTPS 地址，例如：
https://github.com/用户名/项目名.git
在 VS Code 中打开终端，进入你想保存项目的文件夹：
cd D:\Projects
执行克隆命令：
git clone https://github.com/用户名/项目名.git
进入项目：
cd 项目名 
用 VS Code 打开：
code .
克隆指定分支可以使用：
git clone -b 分支名 https://github.com/用户名/项目名.git

## 修改检测路径
主要只需要修改一个文件：
[origin_monitor.py (line 35)](/D:/111/haishi_pyqt_mac/app/services/origin_monitor.py:35)
1. 修改文件夹检测地址
ROOT_DIRECTORY = Path(
    r"D:\origin"
)
它负责检测该目录直接下一层新增/删除的文件夹。
例如改为：
ROOT_DIRECTORY = Path(
    r"E:\data\folders"
)
2. 修改文件检测地址
FILE_DIRECTORY = Path(
    r"D:\origin\Origin 2022(64bit)"
)
它负责检测该目录直接下一层新增/删除的文件。
例如改为：
FILE_DIRECTORY = Path(
    r"E:\data\files"
)
两个地址可以不同，不要求第二个必须位于第一个目录中。
3. 更新日志中的固定文字
在 origin_monitor.py 中搜索：
D:\origin
Origin 2022(64bit)
把固定日志改成动态路径更合适。例如：
messages.append(
    (
        f"已建立 {self.ROOT_DIRECTORY} "
        "直接子文件夹基准",
        "INFO",
    )
)
文件基准日志改为：
messages.append(
    (
        f"已建立 {self.FILE_DIRECTORY} "
        "直接文件基准",
        "INFO",
    )
)
这样以后只需修改顶部两个路径常量，日志会自动跟随变化。
4. 更换路径后重新建立基准
关闭软件，然后备份旧状态：
$statePath = Join-Path `
  $env:LOCALAPPDATA `
  "SerialUdpBridge\origin_monitor_state.json"

if (Test-Path $statePath) {
    Move-Item `
      -LiteralPath $statePath `
      -Destination "$statePath.old-path.backup"
}

## 编译成软件
1. 进入项目根目录
进入包含 main.py 的目录：
cd D:\sea_test\2026.9
如果项目在下一层，请进入实际目录。
2. 激活虚拟环境
.\.venv\Scripts\Activate.ps1
确认使用的是项目Python：
python -c "import sys; print(sys.executable)"
3. 安装PyInstaller
python -m pip install pyinstaller
验证：
python -m PyInstaller --version
4. 先生成目录版
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name SerialUdpBridge `
  main.py
生成位置：
dist\SerialUdpBridge\SerialUdpBridge.exe
运行测试：
.\dist\SerialUdpBridge\SerialUdpBridge.exe
目录版需要保留整个：
dist\SerialUdpBridge
不能只复制里面的EXE。目录版更方便排查依赖问题。
5. 确认正常后生成单文件版
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name SerialUdpBridge `
  main.py
最终文件：
dist\SerialUdpBridge.exe
--onefile 表示生成一个EXE，--windowed 表示启动时不显示黑色控制台。PyInstaller官方说明可参考命令参数和目录版与单文件版区别。
6. 放到最终运行位置
例如创建：
D:\SerialUdpBridge
把EXE复制为：
D:\SerialUdpBridge\SerialUdpBridge.exe
然后从最终位置运行一次：
& "D:\SerialUdpBridge\SerialUdpBridge.exe"
这一步很重要：软件会把当前EXE的绝对路径写入开机自启动注册表。之后不要随意移动或删除这个EXE。
检查自启动路径：
Get-ItemPropertyValue `
  -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
  -Name "SerialUdpBridge"
预期结果：
"D:\SerialUdpBridge\SerialUdpBridge.exe"
打包后的软件仍然监控：
D:\origin
D:\origin\Origin 2022(64bit)



## windows自带的远控如何打开

1. 基础启动（弹出连接窗口）
按下 Win+R 输入 cmd 打开命令提示符，直接输入命令回车：
cmd
mstsc
即可调出远程桌面连接界面，手动输入对方 IP / 计算机名发起连接。
2. 常用带参数命令（一步直达）
结合参数可以直接指定连接目标、启动模式，无需手动点选：
直接连接指定电脑（替换为被控端 IP / 计算机名，支持指定端口）
cmd
mstsc /v:192.168.1.100
全屏模式启动连接
cmd
mstsc /v:192.168.1.100 /f
管理员 / 控制台会话连接（连接服务器常用，不占用多用户授权）
cmd
mstsc /v:192.168.1.100 /admin
自定义窗口分辨率连接
cmd
mstsc /v:192.168.1.100 /w:1920 /h:1080
打开并编辑已保存的 rdp 配置文件
cmd
mstsc /edit "D:\MyServer.rdp"


192.168.135.99
名字 pc  
密码 666666