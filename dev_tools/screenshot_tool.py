import os
from datetime import datetime

from PIL import Image

from pynput import keyboard
from module.config.config import AzurLaneConfig
from module.config.utils import alas_instance
from module.device.connection import Connection, ConnectionAttr
from module.device.device import Device
from module.logger import logger

"""
设备截图工具 (Screenshot Tool)

功能：
1. 自动检测并连接设备
2. 支持快捷键截图
3. 自动处理敏感信息
4. 按时间戳保存截图

使用方法：
    python -m dev_tools.screenshot_tool
"""


class EmptyConnection(Connection):
    def __init__(self):
        ConnectionAttr.__init__(self, AzurLaneConfig('template'))

        logger.hr('检测设备')
        print()
        print('正在检测可用模拟器...')
        devices = self.list_device()

        # 获取可用设备
        available = devices.select(status='device')
        
        # 如果只有一个可用设备，直接选择它
        if len(available) == 1:
            device = available[0]
            print(f'检测到单个可用设备: {device.serial}')
            print('正在连接设备...')
            try:
                # 创建Device实例
                config = AzurLaneConfig('template')
                config.override(
                    Emulator_Serial=device.serial,
                    Emulator_PackageName='com.miHoYo.hkrpg',
                    Emulator_ScreenshotMethod='adb_nc',
                )
                self.device = Device(config)
                # 验证设备连接
                self.device.screenshot()
                print('设备连接成功！')
            except Exception as e:
                print(f'设备连接失败: {e}')
                print('请检查设备状态后重试')
                self.device = None
            return
            
        # 显示所有可用设备
        if len(available) > 1:
            print('检测到多个可用设备:')
            for device in available:
                print(f'- {device.serial}')
        else:
            print('未检测到可用设备')

        # 显示不可用设备
        unavailable = devices.delete(available)
        if len(unavailable):
            print('\n检测到以下不可用设备:')
            for device in unavailable:
                print(f'- {device.serial} ({device.status})')


def init_device():
    """初始化设备连接"""
    _ = EmptyConnection()
    
    # 如果已经自动选择了设备，直接使用
    if hasattr(_, 'device'):
        print('使用自动检测到的设备')
        return _.device
        
    while True:
        name = input(
            '\n请输入以下信息之一:\n'
            '1. 配置文件名称 (例如: "src")\n'
            '2. 模拟器序列号 (例如: "127.0.0.1:16384")\n'
            '3. 模拟器端口号 (例如: "7555")\n'
            '直接回车默认使用 "src":\n'
        )
        name = name.strip().strip('"').strip()
        if not name:
            name = 'src'
        if name.isdigit():
            name = f'127.0.0.1:{name}'
            
        try:
            if name in alas_instance():
                print(f'使用配置文件: {name}')
                device = Device(name)
            else:
                print(f'使用设备序列号: {name}')
                config = AzurLaneConfig('template')
                config.override(
                    Emulator_Serial=name,
                    Emulator_PackageName='com.miHoYo.hkrpg',
                    Emulator_ScreenshotMethod='adb_nc',
                )
                device = Device(config)
            return device
        except Exception as e:
            print(f'设备连接失败: {e}')
            print('请重新输入设备信息')


def handle_sensitive_info(image):
    """
    处理截图中的敏感信息
    
    Args:
        image: 原始截图数据
        
    Returns:
        处理后的截图数据
    """
    # 将UID区域涂黑
    image[680:720, 0:180, :] = 0
    return image


def save_screenshot(image, output_dir):
    """
    保存截图
    
    Args:
        image: 截图数据
        output_dir: 输出目录
    """
    now = datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S-%f')
    file = f'{output_dir}/{now}.png'
    image = handle_sensitive_info(image)
    Image.fromarray(image).save(file)
    print(f'截图已保存: {file}')


def main():
    # 初始化设备
    device = init_device()
    
    # 创建输出目录
    output = './screenshots/dev_screenshots'
    os.makedirs(output, exist_ok=True)
    
    # 配置设备
    device.disable_stuck_detection()
    device.screenshot_interval_set(0.)
    print(f'\n截图将保存到: {output}')
    
    # 设置快捷键
    GLOBAL_KEY = 'F3'
    print(f'按 <{GLOBAL_KEY}> 键可以随时截图')
    
    def on_press(key):
        if str(key) == f'Key.{GLOBAL_KEY.lower()}':
            try:
                print('截图中...')
                image = device.screenshot()
                save_screenshot(image, output)
            except Exception as e:
                print(f'截图失败: {e}')
    
    # 启动快捷键监听
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    # 主循环
    while True:
        try:
            input('\n按回车键截图，或按F3键随时截图:')
            print('截图中...')
            image = device.screenshot()
            save_screenshot(image, output)
        except KeyboardInterrupt:
            print('\n程序已退出')
            break
        except Exception as e:
            print(f'截图失败: {e}')


if __name__ == '__main__':
    main()
