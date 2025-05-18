import traceback

from tasks.base.assets.assets_base_page import *


class Page:
    """
    页面类，用于管理游戏中的各个页面及其导航关系
    实现了A*寻路算法来找到页面间的最短路径
    """
    # 存储所有页面实例的字典
    # Key: str, 页面名称，如 "page_main"
    # Value: Page, 页面实例
    all_pages = {}

    @classmethod
    def clear_connection(cls):
        """清除所有页面之间的连接关系"""
        for page in cls.all_pages.values():
            page.parent = None

    @classmethod
    def init_connection(cls, destination):
        """
        初始化页面间的A*寻路算法
        从目标页面开始，为每个页面找到最短路径

        Args:
            destination (Page): 目标页面
        """
        cls.clear_connection()

        visited = [destination]
        visited = set(visited)
        while 1:
            new = visited.copy()
            for page in visited:
                for link in cls.iter_pages():
                    if link in visited:
                        continue
                    if page in link.links:
                        link.parent = page
                        new.add(link)
            if len(new) == len(visited):
                break
            visited = new

    @classmethod
    def iter_pages(cls):
        """遍历所有页面实例"""
        return cls.all_pages.values()

    @classmethod
    def iter_check_buttons(cls):
        """遍历所有页面的检查按钮"""
        for page in cls.all_pages.values():
            yield page.check_button

    def __init__(self, check_button):
        """
        初始化页面实例
        Args:
            check_button: 用于检查当前是否在该页面的按钮
        """
        self.check_button = check_button
        self.links = {}  # 存储页面间的导航关系
        # 从调用栈中获取页面名称
        (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
        self.name = text[:text.find('=')].strip()
        self.parent = None  # 用于A*寻路算法
        Page.all_pages[self.name] = self

    def __eq__(self, other):
        """判断两个页面是否相同"""
        return self.name == other.name

    def __hash__(self):
        """获取页面的哈希值，用于在集合中使用"""
        return hash(self.name)

    def __str__(self):
        """返回页面名称的字符串表示"""
        return self.name

    def link(self, button, destination):
        """
        建立页面间的导航关系
        Args:
            button: 用于导航的按钮
            destination: 目标页面
        """
        self.links[destination] = button


# 主页面
page_main = Page(MAIN_GOTO_CHARACTER)

# 菜单页面，从手机进入
page_menu = Page(MENU_CHECK)
page_menu.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_MENU, destination=page_menu)

# 角色页面
page_character = Page(CHARACTER_CHECK)
page_character.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_CHARACTER, destination=page_character)

# 队伍页面
page_team = Page(TEAM_CHECK)
page_team.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_TEAM, destination=page_team)

# 物品页面，仓库
page_item = Page(ITEM_CHECK)
page_item.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_ITEM, destination=page_item)

# 指南页面，包括新手引导、每日任务和副本
page_guide = Page(GUIDE_CHECK)
page_guide.link(GUIDE_CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_GUIDE, destination=page_guide)

# 抽卡页面
page_gacha = Page(GACHA_CHECK)
page_gacha.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_GACHA, destination=page_gacha)

# 战令页面
page_battle_pass = Page(BATTLE_PASS_CHECK)
page_battle_pass.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_BATTLE_PASS, destination=page_battle_pass)

# 活动页面
page_event = Page(EVENT_CHECK)
page_event.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_EVENT, destination=page_event)

# 地图页面
page_map = Page(MAP_CHECK)
page_map.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_MAP, destination=page_map)

# 世界页面，地图的子页面，用于选择世界/星球，如黑塔空间站
page_world = Page(WORLD_CHECK)
page_world.link(BACK, destination=page_map)
page_map.link(MAP_GOTO_WORLD, destination=page_world)

# 教程页面
page_tutorial = Page(TUTORIAL_CHECK)
page_tutorial.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_TUTORIAL, destination=page_tutorial)

# 任务页面
page_mission = Page(MISSION_CHECK)
page_mission.link(CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_MISSION, destination=page_mission)

# 消息页面
page_message = Page(MESSAGE_CLOSE)
page_message.link(MESSAGE_CLOSE, destination=page_main)
page_main.link(MAIN_GOTO_MESSAGE, destination=page_message)

# 相机页面
page_camera = Page(CAMERA_CHECK)
page_camera.link(CLOSE, destination=page_menu)
page_menu.link(MENU_GOTO_CAMERA, destination=page_camera)

# 合成页面
page_synthesize = Page(SYNTHESIZE_CHECK)
page_synthesize.link(CLOSE, destination=page_menu)
page_menu.link(MENU_GOTO_SYNTHESIZE, destination=page_synthesize)

# 委托页面
page_assignment = Page(ASSIGNMENT_CHECK)
page_assignment.link(CLOSE, destination=page_main)
page_menu.link(MENU_GOTO_ASSIGNMENT, destination=page_assignment)

# 忘却之庭页面
page_forgotten_hall = Page(FORGOTTEN_HALL_CHECK)
page_forgotten_hall.link(CLOSE, destination=page_main)

# 模拟宇宙页面
page_rogue = Page(ROGUE_CHECK)
page_rogue.link(CLOSE, destination=page_main)

# 规划器结果页面
page_planner = Page(PLANNER_CHECK)
page_planner.link(CLOSE, destination=page_menu)
