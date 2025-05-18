from typing import Callable

from module.base.base import ModuleBase
from module.base.utils import color_similarity_2d
from module.logger import logger
from tasks.base.assets.assets_base_page import BACK, CLOSE
from tasks.base.assets.assets_base_popup import *


class PopupHandler(ModuleBase):
    """弹窗处理器，用于处理游戏中出现的各种弹窗"""

    def reward_appear(self) -> bool:
        """
        检查是否出现奖励弹窗
        Returns:
            bool: 是否出现奖励弹窗
        """
        for button in GET_REWARD.buttons:
            image = self.image_crop(button.search, copy=False)
            image = color_similarity_2d(image, color=(203, 181, 132))
            if button.match_template(image, direct_match=True):
                return True
        return False

    def handle_reward(self, interval=5, click_button: ButtonWrapper = None) -> bool:
        """
        处理奖励弹窗
        Args:
            interval: 检查间隔时间
            click_button: 指定要点击的按钮，如果为None则点击默认的GET_REWARD按钮

        Returns:
            bool: 是否处理了弹窗
        """
        self.device.stuck_record_add(GET_REWARD)

        if interval and not self.interval_is_reached(GET_REWARD, interval=interval):
            return False

        appear = self.reward_appear()

        if click_button is None:
            if appear:
                self.device.click(GET_REWARD)
        else:
            if appear:
                logger.info(f'{GET_REWARD} -> {click_button}')
                self.device.click(click_button)

        if appear and interval:
            self.interval_reset(GET_REWARD, interval=interval)

        return appear

    def handle_battle_pass_notification(self, interval=5) -> bool:
        """
        处理战斗通行证通知弹窗
        当首次进入战斗通行证时出现的弹窗

        Args:
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了弹窗
        """
        if self.appear_then_click(BATTLE_PASS_NOTIFICATION, interval=interval):
            return True
        if self.appear(POPUP_BATTLE_PASS_UPDATE, interval=interval):
            logger.info(f'{POPUP_BATTLE_PASS_UPDATE} -> {BATTLE_PASS_NOTIFICATION}')
            self.device.click(BATTLE_PASS_NOTIFICATION)
            return True

        return False

    def handle_monthly_card_reward(self, interval=1) -> bool:
        """
        处理月卡奖励弹窗
        在服务器时间04:00时，如果购买了月卡会弹出此窗口

        Args:
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了弹窗
        """
        if self.appear_then_click(MONTHLY_CARD_REWARD, interval=interval):
            # 每天第一次登录时的语言检查可能因为弹窗而失败
            # 稍后重试
            from tasks.base.main_page import MainPage
            if not MainPage._lang_check_success:
                MainPage._lang_checked = False
            return True
        if self.appear_then_click(MONTHLY_CARD_GET_ITEM, interval=interval):
            from tasks.base.main_page import MainPage
            if not MainPage._lang_check_success:
                MainPage._lang_checked = False
            return True

        return False

    def handle_popup_cancel(self, interval=2) -> bool:
        """
        处理带有取消按钮的弹窗

        Args:
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了弹窗
        """
        if self.appear_then_click(POPUP_CANCEL, interval=interval):
            return True

        return False

    def handle_popup_confirm(self, interval=2) -> bool:
        """
        处理带有确认按钮的弹窗

        Args:
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了弹窗
        """
        if self.appear_then_click(POPUP_CONFIRM, interval=interval):
            return True

        return False

    def handle_popup_single(self, interval=2) -> bool:
        """
        处理只有一个确认按钮的弹窗（按钮在中间）

        Args:
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了弹窗
        """
        if self.appear_then_click(POPUP_SINGLE, interval=interval):
            return True

        return False

    def handle_get_light_cone(self, interval=2) -> bool:
        """
        处理获得光锥的弹窗
        从战争回响中获得光锥时出现的弹窗

        Args:
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了弹窗
        """
        if self.appear(GET_LIGHT_CONE, interval=interval):
            logger.info(f'{GET_LIGHT_CONE} -> {GET_REWARD}')
            self.device.click(GET_REWARD)
            return True

        return False

    def handle_get_character(self, interval=2) -> bool:
        """
        处理获得角色的弹窗
        从模拟宇宙奖励中获得角色时出现的弹窗

        Args:
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了弹窗
        """
        if self.appear(GET_CHARACTER, interval=interval):
            logger.info(f'{GET_CHARACTER} -> {GET_REWARD}')
            self.device.click(GET_REWARD)
            return True

        return False

    def handle_ui_close(self, appear_button: ButtonWrapper | Callable, interval=2) -> bool:
        """
        处理需要点击关闭按钮的UI界面

        Args:
            appear_button: 要检查的按钮或检查函数
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了界面
        """
        if callable(appear_button):
            if self.interval_is_reached(appear_button, interval=interval) and appear_button():
                logger.info(f'{appear_button.__name__} -> {CLOSE}')
                self.device.click(CLOSE)
                self.interval_reset(appear_button, interval=interval)
                return True
        else:
            if self.appear(appear_button, interval=interval):
                logger.info(f'{appear_button} -> {CLOSE}')
                self.device.click(CLOSE)
                return True

        return False

    def handle_ui_back(self, appear_button: ButtonWrapper | Callable, interval=2) -> bool:
        """
        处理需要点击返回按钮的UI界面

        Args:
            appear_button: 要检查的按钮或检查函数
            interval: 检查间隔时间

        Returns:
            bool: 是否处理了界面
        """
        if callable(appear_button):
            if self.interval_is_reached(appear_button, interval=interval) and appear_button():
                logger.info(f'{appear_button.__name__} -> {BACK}')
                self.device.click(BACK)
                self.interval_reset(appear_button, interval=interval)
                return True
        else:
            if self.appear(appear_button, interval=interval):
                logger.info(f'{appear_button} -> {BACK}')
                self.device.click(BACK)
                return True

        return False
