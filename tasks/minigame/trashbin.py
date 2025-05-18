import argparse

from module.base.button import ClickButton
from module.base.timer import Timer
from module.base.utils import color_similar, get_color
from tasks.base.daemon import Daemon

# 拍照按钮的位置和名称
TAKE_PHOTO = ClickButton((1101, 332, 1162, 387), name='TAKE_PHOTO')


class TrashBin(Daemon):
    """
    垃圾桶小游戏类，用于自动拍摄垃圾桶照片
    继承自Daemon类，实现自动拍照功能
    """
    def is_camera_active(self):
        """
        检查相机是否处于激活状态
        通过检测屏幕特定位置的颜色来判断

        Returns:
            bool: 相机是否激活
        """
        color = get_color(self.device.image, (568, 358, 588, 362))
        # 检查绿色激活状态
        if color_similar(color, (23, 254, 180), threshold=20):
            return True
        # 检查黄色激活状态
        if color_similar(color, (225, 214, 124), threshold=30):
            return True
        return False

    def is_in_camera(self):
        """
        检查是否在相机界面
        通过检测拍照按钮的颜色来判断

        Returns:
            bool: 是否在相机界面
        """
        # 检查绿色图标
        if self.image_color_count(TAKE_PHOTO, color=(134, 209, 187), threshold=221, count=200):
            # 检查白色背景
            if self.image_color_count(TAKE_PHOTO, color=(235, 233, 237), threshold=221, count=1000):
                return True
        return False

    # 拍照间隔计时器，防止连续拍照
    photo_interval = Timer(1)

    def handle_blessing(self):
        """
        处理拍照逻辑
        当相机激活且在相机界面时，自动点击拍照按钮
        """
        if self.photo_interval.reached():
            if self.is_in_camera() and self.is_camera_active():
                self.device.click(TAKE_PHOTO)
                self.photo_interval.reset()

    def run(self):
        """
        运行垃圾桶小游戏
        禁用卡死检测，设置截图间隔，并运行守护进程
        """
        self.device.disable_stuck_detection()  # 禁用卡死检测
        self.device.screenshot_interval_set(0.05)  # 设置截图间隔为0.05秒
        _ = self.device.maatouch_builder  # 初始化触摸构建器
        super().run()  # 运行父类的run方法


if __name__ == '__main__':
    """
    2.4版本(2024.08)的垃圾桶小游戏，自动拍摄垃圾桶照片
    
    运行方式：
        python -m tasks.minigame.trashbin
    或者：
        python -m tasks.minigame.trashbin <instance>
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('instance', nargs='?', default='src', help='SRC实例名称')

    args = parser.parse_args()
    instance = args.instance

    src = TrashBin(instance)
    src.run()
