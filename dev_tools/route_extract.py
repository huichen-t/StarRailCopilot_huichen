"""
路由提取工具

功能：
1. 从代码中提取路由信息
2. 生成路由配置文件
3. 处理模拟宇宙和饰品相关的路由数据

使用方法：
    python -m dev_tools.route_extract
"""

import os
import re
from typing import Iterator

import numpy as np
from tqdm import tqdm

from module.base.code_generator import CodeGenerator, MarkdownGenerator
from module.base.decorator import cached_property
from module.base.utils import SelectedGrids, load_image
from module.config.utils import iter_folder
from tasks.map.route.model import RouteModel
from tasks.rogue.route.model import RogueRouteListModel, RogueRouteModel, RogueWaypointListModel, RogueWaypointModel


class RouteExtract:
    """
    路由提取器
    
    功能：
    1. 遍历指定文件夹下的所有Python文件
    2. 提取文件中的路由定义
    3. 生成路由配置文件
    """
    
    def __init__(self, folder):
        """
        初始化路由提取器
        
        Args:
            folder: 要处理的文件夹路径
        """
        self.folder = folder

    def iter_files(self) -> Iterator[str]:
        """
        遍历文件夹下的所有Python文件
        
        Yields:
            str: Python文件的完整路径
        """
        for path, folders, files in os.walk(self.folder):
            path = path.replace('\\', '/')
            for file in files:
                if file.endswith('.py'):
                    yield f'{path}/{file}'

    def extract_route(self, file) -> Iterator[RouteModel]:
        """
        从文件中提取路由信息
        
        提取规则：
        1. 查找包含map_init的函数定义
        2. 解析plane、floor和position参数
        3. 生成路由模型
        
        Args:
            file: 要处理的文件路径
            
        Yields:
            RouteModel: 路由模型实例
        """
        print(f'Extract {file}')
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()

        """
        def route_item_enemy(self):
            self.enter_himeko_trial()
            self.map_init(plane=Jarilo_BackwaterPass, position=(519.9, 361.5))
        """
        regex = re.compile(
            r'def (?P<func>[a-zA-Z0-9_]*?)\(self\):.*?'
            r'self\.map_init\((.*?)\)',
            re.DOTALL)
        file = file.replace(self.folder, '').replace('.py', '').replace('/', '_').strip('_')
        module = f"{self.folder.strip('./').replace('/', '.')}.{file}"

        for result in regex.findall(content):
            func, data = result

            res = re.search(r'plane=([a-zA-Z_]*)', data)
            if res:
                plane = res.group(1)
            else:
                # Must contain plane
                continue
            res = re.search(r'floor=([\'"a-zA-Z0-9_]*)', data)
            if res:
                floor = res.group(1).strip('"\'')
            else:
                floor = 'F1'
            res = re.search(r'position=\(([0-9.]*)[, ]+([0-9.]*)', data)
            if res:
                position = (float(res.group(1)), float(res.group(2)))
            else:
                position = None

            name = f'{file}__{func}'
            yield RouteModel(
                name=name,
                route=f'{module}:{func}',
                plane=plane,
                floor=floor,
                position=position,
            )

    def iter_route(self):
        """
        遍历所有路由
        
        Yields:
            RouteModel: 路由模型实例
        """
        for f in self.iter_files():
            for row in self.extract_route(f):
                yield row

    def write(self, file):
        """
        将提取的路由信息写入文件
        
        Args:
            file: 输出文件路径
        """
        gen = CodeGenerator()
        gen.Import("""
        from tasks.map.route.model import RouteModel
        """)
        gen.CommentAutoGenerage('dev_tools.route_extract')

        for row in self.iter_route():
            with gen.Object(key=row.name, object_class='RouteModel'):
                for key, value in row.__iter__():
                    gen.ObjectAttr(key, value)
        gen.write(file)


def model_to_json(model, file):
    """
    将模型转换为JSON格式并保存
    
    Args:
        model: 要转换的模型
        file: 输出文件路径
    """
    content = model.model_dump_json(indent=2)
    with open(file, 'w', encoding='utf-8', newline='') as f:
        f.write(content)


regex_posi = re.compile(r'_?X(\d+)Y(\d+)')


def get_position_from_name(name):
    """
    从名称中提取坐标
    
    Args:
        name: 包含坐标的名称
        
    Returns:
        tuple: (x, y)坐标
    """
    res = regex_posi.search(name)
    if res:
        position = int(res.group(1)), int(res.group(2))
    else:
        position = (0, 0)
    return position


def position2direction(target, origin):
    """
    计算从起点到目标点的方向角度
    
    Args:
        target: 目标位置 (x, y)
        origin: 起点位置 (x, y)

    Returns:
        float: 方向角度 (0~360)
    """
    diff = np.subtract(target, origin)
    distance = np.linalg.norm(diff)
    if distance < 0.05:
        return 0
    theta = np.rad2deg(np.arccos(-diff[1] / distance))
    if diff[0] < 0:
        theta = 360 - theta
    theta = round(theta, 3)
    return theta


def swap_exit(exit_, exit1, exit2):
    """
    根据角度关系交换两个出口的顺序
    
    Args:
        exit_: 主出口
        exit1: 第一个出口
        exit2: 第二个出口
        
    Returns:
        tuple: 排序后的出口对
    """
    diff = position2direction(exit1.position, exit_.position) - position2direction(exit2.position, exit_.position)
    diff = diff % 360
    if diff > 180:
        diff -= 360
    if diff < 0:
        return exit1, exit2
    else:
        return exit2, exit1


class RouteDetect:
    """
    路由检测器
    
    功能：
    1. 处理模拟宇宙和饰品的路由数据
    2. 预测路径点位置和方向
    3. 生成路由代码
    """
    
    GEN_END = '===== End of generated waypoints ====='

    def __init__(self, folder):
        """
        初始化路由检测器
        
        Args:
            folder: 路由数据文件夹路径
        """
        self.folder = os.path.abspath(folder)
        print(self.folder)
        self.waypoints = SelectedGrids(list(self.iter_image()))
        self.is_ornament = 'ornament' in folder

    @cached_property
    def detector(self):
        """获取小地图检测器"""
        from tasks.rogue.route.loader import MinimapWrapper
        return MinimapWrapper()

    def get_minimap(self, route: RogueWaypointModel):
        """
        获取指定路由的小地图
        
        Args:
            route: 路由模型
            
        Returns:
            MinimapWrapper: 小地图检测器实例
        """
        return self.detector.all_minimap[route.plane_floor]

    def iter_image(self) -> Iterator[RogueWaypointModel]:
        """
        遍历所有路径点图片
        
        Yields:
            RogueWaypointModel: 路径点模型实例
        """
        for domain_folder in iter_folder(self.folder, is_dir=True):
            domain = os.path.basename(domain_folder)
            for route_folder in iter_folder(domain_folder, is_dir=True):
                route = os.path.basename(route_folder)
                try:
                    for image_file in iter_folder(os.path.join(route_folder, 'route'), ext='.png'):
                        waypoint = os.path.basename(image_file[:-4])

                        parts = route.split('_', maxsplit=3)
                        if len(parts) == 4:
                            world, plane, floor, position = parts
                            position = get_position_from_name(position)
                        elif len(parts) == 3:
                            world, plane, floor = parts
                            position = (0, 0)
                        elif len(parts) == 2:
                            world, plane = parts
                            floor = 'F1'
                            position = (0, 0)
                        else:
                            continue

                        file = f'{self.folder}/{domain}/{route}/route/{waypoint}.png'
                        file_position = get_position_from_name(waypoint)
                        if file_position != (0, 0):
                            position = file_position
                        elif waypoint != 'spawn':
                            position = (0, 0)
                        model = RogueWaypointModel(
                            domain=domain,
                            route=route,
                            waypoint=waypoint,
                            index=0,
                            file=file,
                            plane=f'{world}_{plane}',
                            floor=floor,
                            position=position,
                            direction=0.,
                            rotation=0,
                        )
                        yield model
                except FileNotFoundError:
                    pass

    def predict(self):
        """
        预测路径点的位置和方向
        
        处理流程：
        1. 遍历所有路径点
        2. 使用小地图检测器更新位置和方向
        3. 检查位置变化
        4. 排序路径点
        5. 检查路径点间距
        """
        for waypoint in tqdm(self.waypoints.grids):
            waypoint: RogueWaypointModel = waypoint
            minimap = self.get_minimap(waypoint)
            im = load_image(waypoint.file)

            prev = waypoint.position
            minimap.init_position(waypoint.position, show_log=False)
            minimap.update(im, show_log=False)
            waypoint.position = minimap.position
            waypoint.direction = minimap.direction
            waypoint.rotation = minimap.rotation
            if prev != (0, 0) and np.linalg.norm(np.subtract(waypoint.position, prev)) > 1.5:
                if waypoint.is_spawn:
                    print(f'Position changed: {self.folder}/{waypoint.domain}/{waypoint.route}'
                          f' -> {waypoint.plane}_{waypoint.floor}_{waypoint.positionXY}')
                else:
                    name = regex_posi.sub('', waypoint.waypoint)
                    print(f'Position changed: {waypoint.file}'
                          f' -> {name}_{waypoint.positionXY}')

        self.waypoints.create_index('domain', 'route')
        # 按距离排序
        total = self.waypoints.filter(lambda x: (x.is_DomainCombat or x.is_DomainOccurrence) and x.is_spawn).count
        migrated = 0
        for waypoints in self.waypoints.indexes.values():
            if waypoints.select(is_exit_door=True).count == 2:
                migrated += 1
            waypoints = self.sort_waypoints(waypoints.grids)
            for index, waypoint in enumerate(waypoints):
                waypoint.index = index
            # 检查路径点间距
            diff = SelectedGrids(waypoints).get('position')
            diff = np.linalg.norm(np.diff(diff, axis=0), axis=1)
            for index in np.where(diff > 120)[0]:
                w1, w2 = waypoints[index], waypoints[index + 1]
                print(f'WARNING | Waypoint too far away in {w1.route}: {w1.position} -> {w2.position}')
        print(f'INFO | Domain exit migrated: {migrated}/{total}')
        self.waypoints = self.waypoints.sort('domain', 'route', 'index')

    @staticmethod
    def sort_waypoints(waypoints: list[RogueWaypointModel]) -> list[RogueWaypointModel]:
        """
        对路径点进行排序
        
        排序规则：
        1. 按路径点名称排序
        2. 处理中间路径点
        3. 处理出口路径点
        
        Args:
            waypoints: 要排序的路径点列表
            
        Returns:
            list: 排序后的路径点列表
        """
        waypoints = sorted(waypoints, key=lambda point: point.waypoint)
        middle = [point for point in waypoints if point.is_middle]
        if not middle:
            return waypoints

        try:
            spawn: RogueWaypointModel = [point for point in waypoints if point.is_spawn][0]
        except IndexError:
            return waypoints

        prev = spawn.position
        if prev == (0, 0):
            return waypoints

        sorted_middle = []
        while len(middle):
            distance = np.array([point.position for point in middle]) - prev
            distance = np.linalg.norm(distance, axis=1)
            index = np.argmin(distance)
            sorted_middle.append(middle[index])
            middle.pop(index)

        end = [point for point in waypoints if point.is_exit]
        door = [point for point in waypoints if point.is_exit_door]
        waypoints = [spawn] + sorted_middle + end + door
        return waypoints

    def write(self):
        """将路径点数据写入JSON文件"""
        waypoints = RogueWaypointListModel(self.waypoints.grids)
        model_to_json(waypoints, f'{self.folder}/data.json')

    def gen_route(self, waypoints: SelectedGrids):
        """
        生成路由代码
        
        Args:
            waypoints: 路径点集合
            
        Returns:
            str: 生成的路由代码
        """
        gen = CodeGenerator()

        spawn: RogueWaypointModel = waypoints.select(is_spawn=True).first_or_none()
        exit_: RogueWaypointModel = waypoints.select(is_exit=True).first_or_none()
        exit1: RogueWaypointModel = waypoints.select(is_exit1=True).first_or_none()
        exit2: RogueWaypointModel = waypoints.select(is_exit2=True).first_or_none()
        if not self.is_ornament:
            if spawn is None or exit_ is None:
                print(f'WARNING | No spawn point or no exit: {waypoints}')
                return ''

        class WaypointRepr:
            """路径点表示类"""
            def __init__(self, position):
                if isinstance(position, RogueWaypointModel):
                    position = position.position
                self.position = tuple(position)

            def __repr__(self):
                return f'Waypoint({self.position})'

            __str__ = __repr__

        def call(func, name):
            """生成函数调用代码"""
            ws = waypoints.filter(lambda x: x.waypoint.startswith(name)).get('waypoint')
            if ws:
                ws = ', '.join(ws)
                gen.add(f'self.{func}({ws})')

        with gen.tab():
            with gen.Def(name=spawn.route, args='self'):
                table = MarkdownGenerator(['Waypoint', 'Position', 'Direction', 'Rotation'])
                for waypoint in waypoints:
                    table.add_row([
                        waypoint.waypoint,
                        f'{WaypointRepr(waypoint)},',
                        waypoint.direction,
                        waypoint.rotation
                    ])
                gen.add('"""')
                for row in table.generate():
                    gen.add(row)
                gen.add('"""')
                position = tuple(spawn.position)
                gen.add(f'self.map_init(plane={spawn.plane}, floor="{spawn.floor}", position={position})')
                if spawn.is_DomainBoss or spawn.is_DomainElite or spawn.is_DomainRespite:
                    # Domain has only 1 exit
                    pass
                elif exit1 and exit2:
                    exit1, exit2 = swap_exit(exit_, exit1, exit2)
                    gen.add(f'self.register_domain_exit(')
                    gen.add(f'    {WaypointRepr(exit_)}, end_rotation={exit_.rotation},')
                    gen.add(f'    left_door={WaypointRepr(exit1)}, right_door={WaypointRepr(exit2)})')
                else:
                    if not self.is_ornament:
                        gen.add(f'self.register_domain_exit({WaypointRepr(exit_)}, end_rotation={exit_.rotation})')
                # Waypoint attributes
                for waypoint in waypoints:
                    if waypoint.is_spawn:
                        continue
                    if (waypoint.is_exit or waypoint.is_exit_door) \
                            and (spawn.is_DomainCombat or spawn.is_DomainOccurrence):
                        continue
                    gen.Value(key=waypoint.waypoint, value=WaypointRepr(waypoint))

                # Domain specific
                if spawn.is_DomainBoss or spawn.is_DomainElite:
                    gen.Empty()
                    call('clear_elite', 'enemy')
                    call('domain_reward', 'reward')
                if spawn.is_DomainRespite:
                    gen.Empty()
                    call('clear_item', 'item')
                    call('domain_herta', 'herta')
                if spawn.is_DomainOccurrence or spawn.is_DomainTransaction:
                    gen.Empty()
                    call('clear_item', 'item')
                    call('clear_event', 'event')
                if spawn.is_DomainBoss or spawn.is_DomainElite or spawn.is_DomainRespite:
                    # Domain has only 1 exit
                    call('domain_single_exit', 'exit')

                gen.Comment(self.GEN_END)

        return gen.generate()

    def insert(self, folder, base='tasks.map.route.base'):
        """
        将生成的路由代码插入到文件中
        
        Args:
            folder: 输出文件夹路径
            base: 基础路由类路径
        """
        # 创建文件夹
        self.waypoints.create_index('domain')
        for index, waypoints in self.waypoints.indexes.items():
            domain = index[0]
            os.makedirs(f'{folder}/{domain}', exist_ok=True)

        # 创建文件
        self.waypoints.create_index('domain', 'plane', 'floor')
        for index, waypoints in self.waypoints.indexes.items():
            domain, plane, floor = index
            file = f'{folder}/{domain}/{plane}_{floor}.py'
            if not os.path.exists(file):
                gen = CodeGenerator()
                gen.Import(f"""
                from {base} import RouteBase
                """)
                with gen.Class('Route', inherit='RouteBase'):
                    pass
                gen.write(file)

        for index, routes in self.waypoints.indexes.items():
            domain, plane, floor = index
            file = f'{folder}/{domain}/{plane}_{floor}.py'
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            # Add import
            if base != 'tasks.map.route.base':
                content = content.replace('tasks.map.route.base', base)
            p = '_'.join(plane.split('_', maxsplit=2)[:2])
            imp = [
                      'from tasks.map.control.waypoint import Waypoint',
                      f'from tasks.map.keywords.plane import {p}',
                      f'from {base} import RouteBase',
                  ][::-1]
            res = re.search(r'^(.*?)class Route', content, re.DOTALL)
            if res:
                head = res.group(1)
                for row in imp:
                    if row not in head:
                        content = row + '\n' + content
            content = content.replace(
                'from tasks.rogue.route.base import locked',
                'from tasks.map.route.base import locked')
            # Replace or add routes
            routes.create_index('route')
            for waypoints in routes.indexes.values():
                spawn = waypoints.select(is_spawn=True).first_or_none()
                if spawn is None:
                    continue
                regex = re.compile(rf'def {spawn.route}.*?{self.GEN_END}', re.DOTALL)
                res = regex.search(content)
                if res:
                    before = res.group(0).strip()
                    after = self.gen_route(waypoints).strip()
                    content = content.replace(before, after)
                else:
                    content += '\n' + self.gen_route(waypoints)

            # Sort routes
            regex = re.compile(
                r'(?=(\n    def ([a-zA-Z0-9_]+)\(.*?\n    def|\n    def ([a-zA-Z0-9_]+)\(.*?$))', re.DOTALL)
            funcs = regex.findall(content)

            known_routes = [route[0] for route in routes.indexes.keys()]
            routes = []
            for code, route1, route2 in funcs:
                if route1:
                    route = route1
                elif route2:
                    route = route2
                else:
                    continue
                if route not in known_routes:
                    continue
                code = code.removesuffix('\n    def').removeprefix('\n')
                routes.append((route, code))

            sorted_routes = sorted(routes, key=lambda x: get_position_from_name(x[0]))
            routes = [route[1] for route in routes]
            sorted_routes = [route[1] for route in sorted_routes]
            new = ''
            for before, after in zip(routes, sorted_routes):
                left = content.index(before)
                right = left + len(before)
                new += content[:left]
                new += after
                content = content[right:]
            new += content
            content = new

            # Format
            content = re.sub(r'[\n ]+    def', '\n\n    def', content)
            content = content.rstrip('\n') + '\n'
            content = re.sub(r'    (@[a-zA-Z0-9_().]+)[\n ]+    def', r'    \1\n    def', content)
            # Write
            with open(file, 'w', encoding='utf-8', newline='') as f:
                f.write(content)


def rogue_extract(folder):
    """
    提取模拟宇宙路由
    
    Args:
        folder: 路由数据文件夹路径
    """
    print('rogue_extract')

    def iter_route():
        for row in RouteExtract(f'{folder}').iter_route():
            domain = row.name.split('_', maxsplit=1)[0]
            row = RogueRouteModel(domain=domain, **row.model_dump())
            row.name = f'{row.domain}_{row.route.split(":")[1]}'
            row.route = row.route.replace('_', '.', 1)
            yield row

    routes = RogueRouteListModel(list(iter_route()))
    model_to_json(routes, f'{folder}/route.json')


if __name__ == '__main__':
    # 处理日常路由
    os.chdir(os.path.join(os.path.dirname(__file__), '../'))
    RouteExtract('./route/daily').write('./tasks/map/route/route/daily.py')

    # 处理模拟宇宙路由
    self = RouteDetect('../SrcRoute/rogue')
    self.predict()
    self.write()
    self.insert('./route/rogue', base='tasks.rogue.route.base')
    rogue_extract('./route/rogue')

    # 处理饰品路由
    self = RouteDetect('../SrcRoute/ornament')
    self.predict()
    self.write()
    self.insert('./route/ornament', base='tasks.ornament.route_base')
    rogue_extract('./route/ornament')
