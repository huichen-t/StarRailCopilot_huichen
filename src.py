# 导入基础模块
from module.alas import AzurLaneAutoScript
from module.logger import logger


class StarRailCopilot(AzurLaneAutoScript):
    """
    星穹铁道自动脚本主类
    继承自AzurLaneAutoScript，用于实现星穹铁道的自动化功能
    """
    
    def restart(self):
        """
        重启游戏应用
        通过Login类实现游戏的重启操作
        """
        from tasks.login.login import Login
        Login(self.config, device=self.device).app_restart()

    def start(self):
        """
        启动游戏应用
        通过Login类实现游戏的启动操作
        """
        from tasks.login.login import Login
        Login(self.config, device=self.device).app_start()

    def stop(self):
        """
        停止游戏应用
        通过Login类实现游戏的停止操作
        """
        from tasks.login.login import Login
        Login(self.config, device=self.device).app_stop()

    def goto_main(self):
        """
        跳转到游戏主界面
        如果游戏已经在运行，直接跳转到主界面
        如果游戏未运行，先启动游戏再跳转到主界面
        """
        from tasks.login.login import Login
        from tasks.base.ui import UI
        if self.device.app_is_running():
            logger.info('App is already running, goto main page')
            UI(self.config, device=self.device).ui_goto_main()
        else:
            logger.info('App is not running, start app and goto main page')
            Login(self.config, device=self.device).app_start()
            UI(self.config, device=self.device).ui_goto_main()

    def error_postprocess(self):
        """
        错误后处理
        如果是云游戏，则停止游戏以减少额外费用
        """
        if self.config.is_cloud_game:
            from tasks.login.login import Login
            Login(self.config, device=self.device).app_stop()

    def dungeon(self):
        """
        执行副本任务
        通过Dungeon类实现副本的自动化
        """
        from tasks.dungeon.dungeon import Dungeon
        Dungeon(config=self.config, device=self.device).run()

    def weekly(self):
        """
        执行周常副本任务
        通过WeeklyDungeon类实现周常副本的自动化
        """
        from tasks.dungeon.weekly import WeeklyDungeon
        WeeklyDungeon(config=self.config, device=self.device).run()

    def daily_quest(self):
        """
        执行每日任务
        通过DailyQuestUI类实现每日任务的自动化
        """
        from tasks.daily.daily_quest import DailyQuestUI
        DailyQuestUI(config=self.config, device=self.device).run()

    def battle_pass(self):
        """
        执行战斗通行证相关任务
        通过BattlePassUI类实现战斗通行证的自动化
        """
        from tasks.battle_pass.battle_pass import BattlePassUI
        BattlePassUI(config=self.config, device=self.device).run()

    def assignment(self):
        """
        执行委托任务
        通过Assignment类实现委托任务的自动化
        """
        from tasks.assignment.assignment import Assignment
        Assignment(config=self.config, device=self.device).run()

    def data_update(self):
        """
        更新游戏数据
        通过DataUpdate类实现游戏数据的更新
        """
        from tasks.item.data_update import DataUpdate
        DataUpdate(config=self.config, device=self.device).run()

    def freebies(self):
        """
        领取免费奖励
        通过Freebies类实现免费奖励的自动领取
        """
        from tasks.freebies.freebies import Freebies
        Freebies(config=self.config, device=self.device).run()

    def rogue(self):
        """
        执行模拟宇宙任务
        通过Rogue类实现模拟宇宙的自动化
        """
        from tasks.rogue.rogue import Rogue
        Rogue(config=self.config, device=self.device).run()

    def ornament(self):
        """
        执行遗器相关任务
        通过Ornament类实现遗器系统的自动化
        """
        from tasks.ornament.ornament import Ornament
        Ornament(config=self.config, device=self.device).run()

    def benchmark(self):
        """
        执行性能测试
        通过benchmark模块进行性能测试
        """
        from module.daemon.benchmark import run_benchmark
        run_benchmark(config=self.config)

    def daemon(self):
        """
        执行守护进程任务
        通过Daemon类实现守护进程功能
        """
        from tasks.base.daemon import Daemon
        Daemon(config=self.config, device=self.device, task="Daemon").run()

    def planner_scan(self):
        """
        执行规划器扫描任务
        通过PlannerScan类实现规划器的扫描功能
        """
        from tasks.planner.scan import PlannerScan
        PlannerScan(config=self.config, device=self.device, task="PlannerScan").run()


if __name__ == '__main__':
    # 创建StarRailCopilot实例并启动主循环
    src = StarRailCopilot('src')
    src.loop()
