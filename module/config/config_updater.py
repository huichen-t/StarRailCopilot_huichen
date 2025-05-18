import typing
from module.base.timer import timer
from module.config.convert import *
from module.config.deep import deep_get, deep_iter, deep_set
from module.config.utils import *
from cached_property import cached_property

class ConfigUpdater:
    """
    配置更新器类
    负责处理配置文件的读取、更新和写入，以及配置项之间的关联关系
    """

    def save_callback(self, key: str, value: typing.Any) -> typing.Iterable[typing.Tuple[str, typing.Any]]:
        """
        配置保存回调函数
        处理配置项之间的关联关系，当一个配置项改变时，可能需要同步更新其他相关配置项
        
        Args:
            key (str): 配置JSON中的键路径，如"Main.Emotion.Fleet1Value"
            value (Any): 用户设置的值，如"98"
            
        Yields:
            Tuple[str, Any]: 需要设置的配置项键值对
                str: 配置JSON中的键路径，如"Main.Emotion.Fleet1Record"
                any: 要设置的值，如"2020-01-01 00:00:00"
        """
        # 处理副本相关配置
        if key.startswith('Dungeon.Dungeon') or key.startswith('Dungeon.DungeonDaily'):
            from tasks.dungeon.keywords.dungeon import DungeonList
            from module.exception import ScriptError
            try:
                dungeon = DungeonList.find(value)
            except ScriptError:
                return
            if key.endswith('Name'):
                if dungeon.is_Calyx_Golden:
                    yield 'Dungeon.Dungeon.NameAtDoubleCalyx', value
                elif dungeon.is_Calyx_Crimson:
                    yield 'Dungeon.Dungeon.NameAtDoubleCalyx', value
                elif dungeon.is_Cavern_of_Corrosion:
                    yield 'Dungeon.Dungeon.NameAtDoubleRelic', value
            elif key.endswith('CavernOfCorrosion'):
                yield 'Dungeon.Dungeon.NameAtDoubleRelic', value

        # 处理模拟宇宙相关配置
        if key == 'Rogue.RogueWorld.UseImmersifier' and value is False:
            yield 'Rogue.RogueWorld.UseStamina', False
        if key == 'Rogue.RogueWorld.UseStamina' and value is True:
            yield 'Rogue.RogueWorld.UseImmersifier', True
        if key == 'Rogue.RogueWorld.DoubleEvent' and value is True:
            yield 'Rogue.RogueWorld.UseImmersifier', True

        # 处理云游戏相关配置
        if key == 'Alas.Emulator.GameClient' and value == 'cloud_android':
            yield 'Alas.Emulator.PackageName', 'CN-Official'
            yield 'Alas.Optimization.WhenTaskQueueEmpty', 'close_game'

        # 同步副本和饰品之间的开拓力配置
        if key == 'Dungeon.TrailblazePower.ExtractReservedTrailblazePower':
            yield 'Ornament.TrailblazePower.ExtractReservedTrailblazePower', value
        if key == 'Dungeon.TrailblazePower.UseFuel':
            yield 'Ornament.TrailblazePower.UseFuel', value
        if key == 'Dungeon.TrailblazePower.FuelReserve':
            yield 'Ornament.TrailblazePower.FuelReserve', value
        if key == 'Ornament.TrailblazePower.ExtractReservedTrailblazePower':
            yield 'Dungeon.TrailblazePower.ExtractReservedTrailblazePower', value
        if key == 'Ornament.TrailblazePower.UseFuel':
            yield 'Dungeon.TrailblazePower.UseFuel', value
        if key == 'Ornament.TrailblazePower.FuelReserve':
            yield 'Dungeon.TrailblazePower.FuelReserve', value

    def get_hidden_args(self, data) -> typing.Set[str]:
        """
        获取需要隐藏的配置项
        
        Args:
            data (dict): 配置数据
            
        Returns:
            Set[str]: 需要隐藏的配置项路径集合
        """
        out = list(self._iter_hidden_args(data))
        return set(out)

    def read_file(self, config_name, is_template=False):
        """
        读取并更新配置文件
        
        Args:
            config_name (str): 配置文件路径，如 ./config/{file}.json
            is_template (bool): 是否为模板配置
            
        Returns:
            dict: 更新后的配置数据
        """
        old = read_file(filepath_config(config_name))
        new = self._config_update(old, is_template=is_template)
        # 更新后的配置不会写入文件，虽然这并不重要
        # 由于性能问题，已注释掉写入操作
        # self.write_file(config_name, new)
        return new

    @staticmethod
    def write_file(config_name, data, mod_name='alas'):
        """
        写入配置文件
        
        Args:
            config_name (str): 配置文件路径，如 ./config/{file}.json
            data (dict): 要写入的配置数据
            mod_name (str): 模块名称
        """
        write_file(filepath_config(config_name, mod_name), data)

    @timer
    def test_update_file(self, config_name, is_template=False):
        """
        读取、更新并写入配置文件（用于测试）
        
        Args:
            config_name (str): 配置文件路径，如 ./config/{file}.json
            is_template (bool): 是否为模板配置
            
        Returns:
            dict: 更新后的配置数据
        """
        data = self.read_file(config_name, is_template=is_template)
        self.write_file(config_name, data)
        return data


    @cached_property
    def args(self):
        """
        配置参数缓存属性

        这是一个关键的缓存属性，用于存储和访问配置参数定义。
        使用cached_property装饰器确保参数定义只被读取一次，后续访问直接使用缓存值。

        功能：
        1. 读取 ./module/config/argument/args.json 文件中的配置参数定义
        2. 缓存读取结果，避免重复IO操作
        3. 提供统一的配置参数访问接口

        参数定义文件结构：
        {
            "Alas": {
                "Emulator": {
                    "GameClient": {
                        "type": "select",
                        "value": "CN-Official",
                        "option": ["CN-Official", "CN-Bilibili", "OVERSEA-America", ...]
                    },
                    ...
                },
                ...
            },
            ...
        }

        使用场景：
        1. 配置更新时获取参数定义
        2. 配置界面生成时获取参数选项
        3. 配置验证时获取参数类型
        4. 配置转换时获取参数映射关系

        Returns:
            dict: 配置参数定义字典，包含所有配置项的类型、默认值、选项等信息
        """
        return read_file(filepath_args())

    def _config_update(self, old, is_template=False):
        """
        更新配置数据
        
        Args:
            old (dict): 旧的配置数据
            is_template (bool): 是否为模板配置
            
        Returns:
            dict: 更新后的配置数据
        """
        new = {}

        # 遍历参数文件中的所有配置项
        for keys, data in deep_iter(self.args, depth=3):
            value = deep_get(old, keys=keys, default=data['value'])
            typ = data['type']
            display = data.get('display')
            # 如果是模板配置或值为空，使用默认值
            if is_template or value is None or value == '' \
                    or typ in ['lock', 'state'] or (display == 'hide' and typ != 'stored'):
                value = data['value']
            value = parse_value(value, data=data)
            deep_set(new, keys=keys, value=value)

        # 如果不是模板配置，进行配置重定向
        if not is_template:
            new = self._config_redirect(old, new)
        new = self._update_state(new)

        return new

    @staticmethod
    def _update_state(data):
        """
        更新配置状态
        限制某些配置项的组合
        
        Args:
            data (dict): 配置数据
            
        Returns:
            dict: 更新后的配置数据
        """
        # 限制模拟宇宙相关配置的组合
        if deep_get(data, keys='Rogue.RogueWorld.UseImmersifier') is False:
            deep_set(data, keys='Rogue.RogueWorld.UseStamina', value=False)
        if deep_get(data, keys='Rogue.RogueWorld.UseStamina') is True:
            deep_set(data, keys='Rogue.RogueWorld.UseImmersifier', value=True)
        if deep_get(data, keys='Rogue.RogueWorld.DoubleEvent') is True:
            deep_set(data, keys='Rogue.RogueWorld.UseImmersifier', value=True)
        # 在副本任务中存储沉浸器
        if deep_get(data, keys='Rogue.RogueWorld.UseImmersifier') is True:
            deep_set(data, keys='Dungeon.Scheduler.Enable', value=True)
        # 云游戏设置
        if deep_get(data, keys='Alas.Emulator.GameClient') == 'cloud_android':
            deep_set(data, keys='Alas.Emulator.PackageName', value='CN-Official')

        return data

    def _config_redirect(self, old, new):
        """
        将旧配置转换为新配置
        
        Args:
            old (dict): 旧的配置数据
            new (dict): 新的配置数据
            
        Returns:
            dict: 转换后的配置数据
        """
        # 源配置项、目标配置项、（可选）转换函数
        redirection = [
            # 3.1版本
            ('Dungeon.Dungeon.Name', 'Dungeon.Dungeon.Name', convert_31_dungeon),
            ('Dungeon.Dungeon.NameAtDoubleCalyx', 'Dungeon.Dungeon.NameAtDoubleCalyx', convert_31_dungeon),
            ('Dungeon.DungeonDaily.CalyxGolden', 'Dungeon.DungeonDaily.CalyxGolden', convert_31_dungeon),
            ('Dungeon.DungeonDaily.CalyxCrimson', 'Dungeon.DungeonDaily.CalyxCrimson', convert_31_dungeon),
            # 3.2版本
            ('Weekly.Weekly.Name', 'Weekly.Weekly.Name', convert_32_weekly),
        ]

        for row in redirection:
            if len(row) == 2:
                source, target = row
                update_func = None
            elif len(row) == 3:
                source, target, update_func = row
            else:
                continue

            # 处理多个源配置项的情况
            if isinstance(source, tuple):
                value = []
                error = False
                for attribute in source:
                    tmp = deep_get(old, keys=attribute)
                    if tmp is None:
                        error = True
                        continue
                    value.append(tmp)
                if error:
                    continue
            else:
                value = deep_get(old, keys=source)
                if value is None:
                    continue

            # 应用转换函数
            if update_func is not None:
                value = update_func(value)

            # 处理多个目标配置项的情况
            if isinstance(target, tuple):
                for k, v in zip(target, value):
                    # 允许更新相同的键
                    if (deep_get(old, keys=k) is None) or (source == target):
                        deep_set(new, keys=k, value=v)
            elif (deep_get(old, keys=target) is None) or (source == target):
                deep_set(new, keys=target, value=value)

        return new

    def _iter_hidden_args(self, data) -> typing.Iterator[str]:
        """
        迭代需要隐藏的配置项
        
        Args:
            data (dict): 配置数据
            
        Yields:
            str: 需要隐藏的配置项路径
        """
        # 根据开拓力配置决定是否隐藏燃料储备
        if deep_get(data, 'Dungeon.TrailblazePower.UseFuel') == False:
            yield 'Dungeon.TrailblazePower.FuelReserve'
        if deep_get(data, 'Ornament.TrailblazePower.UseFuel') == False:
            yield 'Ornament.TrailblazePower.FuelReserve'
            
        # 根据模拟宇宙祝福配置决定是否隐藏自定义过滤器
        if deep_get(data, 'Rogue.RogueBlessing.PresetBlessingFilter') != 'custom':
            yield 'Rogue.RogueBlessing.CustomBlessingFilter'
        if deep_get(data, 'Rogue.RogueBlessing.PresetResonanceFilter') != 'custom':
            yield 'Rogue.RogueBlessing.CustomResonanceFilter'
        if deep_get(data, 'Rogue.RogueBlessing.PresetCurioFilter') != 'custom':
            yield 'Rogue.RogueBlessing.CustomCurioFilter'
            
        # 根据模拟宇宙周常配置决定是否隐藏模拟宇宙农场
        if deep_get(data, 'Rogue.RogueWorld.WeeklyFarming', default=False) is False:
            yield 'Rogue.RogueWorld.SimulatedUniverseFarm'

