import threading
import time
from datetime import datetime, timedelta

import inflection
from cached_property import cached_property

from module.base.decorator import del_cached_property
from module.config.config import AzurLaneConfig, TaskEnd
from module.config.deep import deep_get, deep_set
from module.exception import *
from module.logger import logger, save_error_log
from module.notify import handle_notify


class AzurLaneAutoScript:
    """
    碧蓝航线自动脚本基类
    提供基础的自动化功能框架，包括配置管理、设备控制、任务调度等
    """
    # 停止事件标志，用于控制脚本运行
    stop_event: threading.Event = None

    def __init__(self, config_name='alas'):
        """
        初始化自动脚本
        
        Args:
            config_name (str): 配置名称，默认为'alas'
        """
        logger.hr('Start', level=0)
        self.config_name = config_name
        # 跳过首次重启
        self.is_first_task = True
        # 任务失败记录
        # 键：任务名称(str)，值：失败次数(int)
        self.failure_record = {}

    @cached_property
    def config(self):
        """
        获取配置对象
        使用缓存属性装饰器，避免重复创建配置对象
        
        Returns:
            AzurLaneConfig: 配置对象
        """
        try:
            config = AzurLaneConfig(config_name=self.config_name)
            return config
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)

    @cached_property
    def device(self):
        """
        获取设备对象
        使用缓存属性装饰器，避免重复创建设备对象
        
        Returns:
            Device: 设备对象
        """
        try:
            from module.device.device import Device
            device = Device(config=self.config)
            return device
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)

    @cached_property
    def checker(self):
        """
        获取服务器检查器
        使用缓存属性装饰器，避免重复创建检查器对象
        
        Returns:
            ServerChecker: 服务器检查器对象
        """
        try:
            from module.server_checker import ServerChecker
            checker = ServerChecker(server=self.config.Emulator_PackageName)
            return checker
        except Exception as e:
            logger.exception(e)
            exit(1)

    def restart(self):
        """重启游戏，需要子类实现"""
        raise NotImplemented

    def start(self):
        """启动游戏，需要子类实现"""
        raise NotImplemented

    def stop(self):
        """停止游戏，需要子类实现"""
        raise NotImplemented

    def goto_main(self):
        """跳转到主界面，需要子类实现"""
        raise NotImplemented

    def run(self, command):
        """
        运行指定的命令
        
        Args:
            command (str): 要执行的命令名称
            
        Returns:
            bool: 命令执行是否成功
        """
        try:
            # 获取屏幕截图并清除跟踪记录
            self.device.screenshot()
            self.device.screenshot_tracking.clear()
            # 执行命令
            self.__getattribute__(command)()
            return True
        except TaskEnd:
            return True
        except GameNotRunningError as e:
            logger.warning(e)
            self.config.task_call('Restart')
            return False
        except (GameStuckError, GameTooManyClickError) as e:
            logger.error(e)
            self.save_error_log()
            logger.warning(f'Game stuck, {self.device.package} will be restarted in 10 seconds')
            logger.warning('If you are playing by hand, please stop Src')
            self.config.task_call('Restart')
            self.device.sleep(10)
            return False
        except GameBugError as e:
            logger.warning(e)
            self.save_error_log()
            logger.warning('An error has occurred in Star Rail game client, Src is unable to handle')
            logger.warning(f'Restarting {self.device.package} to fix it')
            self.config.task_call('Restart')
            self.device.sleep(10)
            return False
        except GamePageUnknownError:
            # 检查服务器状态
            self.checker.check_now()
            if self.checker.is_available():
                logger.critical('Game page unknown')
                self.save_error_log()
                handle_notify(
                    self.config.Error_OnePushConfig,
                    title=f"Src <{self.config_name}> crashed",
                    content=f"<{self.config_name}> GamePageUnknownError",
                )
                exit(1)
            else:
                self.checker.wait_until_available()
                return False
        except HandledError as e:
            logger.error(e)
            return False
        except ScriptError as e:
            logger.exception(e)
            self.error_postprocess()
            logger.critical('This is likely to be a mistake of developers, but sometimes just random issues')
            self.save_error_log()
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Src <{self.config_name}> crashed",
                content=f"<{self.config_name}> ScriptError",
            )
            exit(1)
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            self.error_postprocess()
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Src <{self.config_name}> crashed",
                content=f"<{self.config_name}> RequestHumanTakeover",
            )
            exit(1)
        except Exception as e:
            logger.exception(e)
            self.error_postprocess()
            self.save_error_log()
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Src <{self.config_name}> crashed",
                content=f"<{self.config_name}> Exception occured",
            )
            exit(1)

    def save_error_log(self):
        """
        保存错误日志
        保存最近60张截图到 ./log/error/<timestamp>
        保存日志到 ./log/error/<timestamp>/log.txt
        """
        save_error_log(config=self.config, device=self.device)

    def error_postprocess(self):
        """
        错误后处理
        在发生错误时执行的操作
        """
        pass

    def wait_until(self, future):
        """
        等待到指定时间
        
        Args:
            future (datetime): 目标时间
            
        Returns:
            bool: 如果等待完成返回True，如果配置改变返回False
        """
        future = future + timedelta(seconds=1)
        self.config.start_watching()
        while 1:
            if datetime.now() > future:
                return True
            if self.stop_event is not None:
                if self.stop_event.is_set():
                    logger.info("Update event detected")
                    logger.info(f"[{self.config_name}] exited. Reason: Update")
                    exit(0)

            time.sleep(5)

            if self.config.should_reload():
                return False

    def get_next_task(self):
        """
        获取下一个要执行的任务
        
        Returns:
            str: 下一个任务的名称
        """
        while 1:
            task = self.config.get_next()
            self.config.task = task
            self.config.bind(task)

            from module.base.resource import release_resources
            if self.config.task.command != 'Alas':
                release_resources(next_task=task.command)

            if task.next_run > datetime.now():
                logger.info(f'Wait until {task.next_run} for task `{task.command}`')
                self.is_first_task = False
                method = self.config.Optimization_WhenTaskQueueEmpty
                if method == 'close_game':
                    logger.info('Close game during wait')
                    self.run('stop')
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                    if task.command != 'Restart':
                        self.config.task_call('Restart')
                        del_cached_property(self, 'config')
                        continue
                elif method == 'goto_main':
                    logger.info('Goto main page during wait')
                    self.run('goto_main')
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                elif method == 'stay_there':
                    logger.info('Stay there during wait')
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                else:
                    logger.warning(f'Invalid Optimization_WhenTaskQueueEmpty: {method}, fallback to stay_there')
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
            break

        AzurLaneConfig.is_hoarding_task = False
        return task.command

    def loop(self):
        """
        主循环
        执行任务调度和错误处理
        
        主要功能：
        1. 初始化日志系统
        2. 检查GUI更新事件
        3. 监控服务器状态
        4. 执行任务队列
        5. 处理任务执行结果
        6. 错误处理和恢复
        
        执行流程：
        1. 设置日志记录器
        2. 进入无限循环，直到收到停止信号
        3. 检查服务器状态，确保游戏可访问
        4. 获取并执行下一个任务
        5. 处理任务执行结果，包括成功/失败处理
        6. 根据执行结果决定下一步操作
        """
        # 设置日志记录器，将日志写入文件
        logger.set_file_logger(self.config_name)
        logger.info(f'Start scheduler loop: {self.config_name}')

        while 1:
            # 检查GUI更新事件
            # 如果收到停止信号，退出循环
            if self.stop_event is not None:
                if self.stop_event.is_set():
                    logger.info("Update event detected")
                    logger.info(f"[{self.config_name}] exited.")
                    break

            # 检查游戏服务器维护状态
            # 等待服务器可用，如果服务器恢复，重启游戏客户端
            self.checker.wait_until_available()
            if self.checker.is_recovered():
                # 服务器恢复后，清除配置缓存并重启游戏
                del_cached_property(self, 'config')
                logger.info('Server or network is recovered. Restart game client')
                self.config.task_call('Restart')

            # 获取下一个要执行的任务
            task = self.get_next_task()
            
            # 初始化设备并更新配置
            # 确保设备配置与当前任务配置同步
            _ = self.device
            self.device.config = self.config

            # 跳过首次重启任务
            # 避免在调度器启动时立即重启游戏
            if self.is_first_task and task == 'Restart':
                logger.info('Skip task `Restart` at scheduler start')
                self.config.task_delay(server_update=True)
                del_cached_property(self, 'config')
                continue

            # 执行任务
            # 1. 记录任务开始
            # 2. 清除设备状态记录
            # 3. 执行任务
            # 4. 记录任务结束
            logger.info(f'Scheduler: Start task `{task}`')
            self.device.stuck_record_clear()  # 清除卡住记录
            self.device.click_record_clear()  # 清除点击记录
            logger.hr(task, level=0)
            success = self.run(inflection.underscore(task))  # 执行任务
            logger.info(f'Scheduler: End task `{task}`')
            self.is_first_task = False  # 标记首次任务已完成

            # 检查任务失败次数
            # 如果任务失败3次或以上，请求人工干预
            failed = deep_get(self.failure_record, keys=task, default=0)
            failed = 0 if success else failed + 1  # 更新失败次数
            deep_set(self.failure_record, keys=task, value=failed)
            
            # 处理任务失败
            if failed >= 3:
                # 记录错误信息
                logger.critical(f"Task `{task}` failed 3 or more times.")
                logger.critical("Possible reason #1: You haven't used it correctly. "
                                "Please read the help text of the options.")
                logger.critical("Possible reason #2: There is a problem with this task. "
                                "Please contact developers or try to fix it yourself.")
                logger.critical('Request human takeover')
                # 发送通知
                handle_notify(
                    self.config.Error_OnePushConfig,
                    title=f"Src <{self.config_name}> crashed",
                    content=f"<{self.config_name}> RequestHumanTakeover\nTask `{task}` failed 3 or more times.",
                )
                exit(1)

            # 处理任务执行结果
            if success:
                # 任务成功，清除配置缓存，继续下一个任务
                del_cached_property(self, 'config')
                continue
            else:
                # 任务失败，清除配置缓存，检查服务器状态
                del_cached_property(self, 'config')
                self.checker.check_now()
                continue


if __name__ == '__main__':
    # 创建实例并启动主循环
    alas = AzurLaneAutoScript()
    alas.loop()
