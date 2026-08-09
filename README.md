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