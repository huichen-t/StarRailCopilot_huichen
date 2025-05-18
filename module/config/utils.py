import json
import os
import random
import string
from datetime import datetime, timedelta, timezone

import yaml

import module.config.server as server_
from deploy.Windows.atomic import atomic_read_text, atomic_read_bytes, atomic_write

# 支持的语言列表
LANGUAGES = ['zh-CN', 'en-US', 'ja-JP', 'zh-TW', 'es-ES']

# 服务器时区映射表
SERVER_TO_TIMEZONE = {
    'CN-Official': timedelta(hours=8),    # 国服官方
    'CN-Bilibili': timedelta(hours=8),    # 国服B站
    'OVERSEA-America': timedelta(hours=-5), # 美服
    'OVERSEA-Asia': timedelta(hours=8),    # 亚服
    'OVERSEA-Europe': timedelta(hours=1),  # 欧服
    'OVERSEA-TWHKMO': timedelta(hours=8),  # 港澳台服
}

# 默认时间
DEFAULT_TIME = datetime(2020, 1, 1, 0, 0)


# 自定义YAML字符串表示器，用于处理多行字符串
def str_presenter(dumper, data):
    """
    自定义YAML字符串表示器
    如果字符串包含多行，使用'|'样式输出
    """
    if len(data.splitlines()) > 1:  # 检查是否为多行字符串
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


# 注册自定义字符串表示器
yaml.add_representer(str, str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)


def filepath_args(filename='args', mod_name='alas'):
    """
    获取参数文件路径
    
    Args:
        filename (str): 文件名
        mod_name (str): 模块名
        
    Returns:
        str: 参数文件路径
    """
    return f'./module/config/argument/{filename}.json'


def filepath_argument(filename):
    """
    获取参数YAML文件路径
    
    Args:
        filename (str): 文件名
        
    Returns:
        str: 参数文件路径
    """
    return f'./module/config/argument/{filename}.yaml'


def filepath_i18n(lang, mod_name='alas'):
    """
    获取国际化文件路径
    
    Args:
        lang (str): 语言代码
        mod_name (str): 模块名
        
    Returns:
        str: 国际化文件路径
    """
    return os.path.join('./module/config/i18n', f'{lang}.json')


def filepath_config(filename, mod_name='alas'):
    """
    获取配置文件路径
    
    Args:
        filename (str): 文件名
        mod_name (str): 模块名
        
    Returns:
        str: 配置文件路径
    """
    if mod_name == 'alas':
        return os.path.join('./config', f'{filename}.json')
    else:
        return os.path.join('./config', f'{filename}.{mod_name}.json')


def filepath_code():
    """
    获取生成的代码文件路径
    
    Returns:
        str: 代码文件路径
    """
    return './module/config/config_generated.py'


def read_file(file):
    """
    读取文件内容，支持YAML和JSON格式
    如果文件不存在则返回空字典
    
    Args:
        file (str): 文件路径
        
    Returns:
        dict, list: 文件内容
    """
    print(f'read: {file}')
    if file.endswith('.json'):
        content = atomic_read_bytes(file)
        if not content:
            return {}
        return json.loads(content)
    elif file.endswith('.yaml'):
        content = atomic_read_text(file)
        data = list(yaml.safe_load_all(content))
        if len(data) == 1:
            data = data[0]
        if not data:
            data = {}
        return data
    else:
        print(f'Unsupported config file extension: {file}')
        return {}


def write_file(file, data):
    """
    写入数据到文件，支持YAML和JSON格式
    
    Args:
        file (str): 文件路径
        data (dict, list): 要写入的数据
    """
    print(f'write: {file}')
    if file.endswith('.json'):
        content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False, default=str)
        atomic_write(file, content)
    elif file.endswith('.yaml'):
        if isinstance(data, list):
            content = yaml.safe_dump_all(
                data, default_flow_style=False, encoding='utf-8', allow_unicode=True, sort_keys=False)
        else:
            content = yaml.safe_dump(
                data, default_flow_style=False, encoding='utf-8', allow_unicode=True, sort_keys=False)
        atomic_write(file, content)
    else:
        print(f'Unsupported config file extension: {file}')


def iter_folder(folder, is_dir=False, ext=None):
    """
    遍历文件夹内容
    
    Args:
        folder (str): 文件夹路径
        is_dir (bool): 是否只遍历目录
        ext (str): 文件扩展名，如'.yaml'
        
    Yields:
        str: 文件的绝对路径
    """
    for file in os.listdir(folder):
        sub = os.path.join(folder, file)
        if is_dir:
            if os.path.isdir(sub):
                yield sub.replace('\\\\', '/').replace('\\', '/')
        elif ext is not None:
            if not os.path.isdir(sub):
                _, extension = os.path.splitext(file)
                if extension == ext:
                    yield os.path.join(folder, file).replace('\\\\', '/').replace('\\', '/')
        else:
            yield os.path.join(folder, file).replace('\\\\', '/').replace('\\', '/')


def alas_template():
    """
    获取所有Alas模板实例名称
    
    Returns:
        list[str]: 模板实例名称列表
    """
    out = []
    for file in os.listdir('./config'):
        name, extension = os.path.splitext(file)
        if name == 'template' and extension == '.json':
            out.append(f'{name}-src')
    return out


def alas_instance():
    """
    获取所有Alas实例名称（除template外）
    
    Returns:
        list[str]: 实例名称列表
    """
    out = []
    for file in os.listdir('./config'):
        name, extension = os.path.splitext(file)
        config_name, mod_name = os.path.splitext(name)
        mod_name = mod_name[1:]
        if name != 'template' and extension == '.json' and mod_name == '':
            out.append(name)

    if not len(out):
        out = ['src']

    return out


def parse_value(value, data):
    """
    将字符串转换为float、int、datetime等类型
    
    Args:
        value (str): 要转换的值
        data (dict): 包含选项的数据
        
    Returns:
        Any: 转换后的值
    """
    if 'option' in data:
        if value not in data['option']:
            return data['value']
    if isinstance(value, str):
        if value == '':
            return None
        if value == 'true' or value == 'True':
            return True
        if value == 'false' or value == 'False':
            return False
        if '.' in value:
            try:
                return float(value)
            except ValueError:
                pass
        else:
            try:
                return int(value)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

    return value


def data_to_type(data, **kwargs):
    """
    根据数据特征确定UI控件类型
    
    | 条件 | 类型 |
    | --- | --- |
    | value是bool | checkbox |
    | 有options | select |
    | 有stored | select |
    | 名称包含Filter | textarea |
    | 其他 | input |
    
    Args:
        data (dict): 数据
        **kwargs: 额外属性
        
    Returns:
        str: 控件类型
    """
    kwargs.update(data)
    if isinstance(kwargs.get('value'), bool):
        return 'checkbox'
    elif 'option' in kwargs and kwargs['option']:
        return 'select'
    elif 'stored' in kwargs and kwargs['stored']:
        return 'stored'
    elif 'Filter' in kwargs['arg']:
        return 'textarea'
    else:
        return 'input'


def data_to_path(data):
    """
    将数据转换为路径
    
    Args:
        data (dict): 数据
        
    Returns:
        str: 路径，格式为<func>.<group>.<arg>
    """
    return '.'.join([data.get(attr, '') for attr in ['func', 'group', 'arg']])


def path_to_arg(path):
    """
    将YAML文件中的字典键转换为配置中的参数名
    
    Args:
        path (str): 路径，如'Scheduler.ServerUpdate'
        
    Returns:
        str: 参数名，如'Scheduler_ServerUpdate'
    """
    return path.replace('.', '_')


def dict_to_kv(dictionary, allow_none=True):
    """
    将字典转换为键值对字符串
    
    Args:
        dictionary: 字典，如{'path': 'Scheduler.ServerUpdate', 'value': True}
        allow_none (bool): 是否允许None值
        
    Returns:
        str: 键值对字符串，如'path='Scheduler.ServerUpdate', value=True'
    """
    return ', '.join([f'{k}={repr(v)}' for k, v in dictionary.items() if allow_none or v is not None])


def server_timezone() -> timedelta:
    """
    获取服务器时区
    
    Returns:
        timedelta: 服务器时区偏移
    """
    return SERVER_TO_TIMEZONE.get(server_.server, SERVER_TO_TIMEZONE['CN-Official'])


def server_time_offset() -> timedelta:
    """
    获取服务器时间偏移
    
    将本地时间转换为服务器时间：
        server_time = local_time + server_time_offset()
    将服务器时间转换为本地时间：
        local_time = server_time - server_time_offset()
        
    Returns:
        timedelta: 时间偏移
    """
    return datetime.now(timezone.utc).astimezone().utcoffset() - server_timezone()


def random_normal_distribution_int(a, b, n=3):
    """
    生成区间内的正态分布整数
    使用多个随机数的平均值来模拟正态分布
    
    Args:
        a (int): 区间最小值
        b (int): 区间最大值
        n (int): 模拟使用的随机数数量，默认为3
        
    Returns:
        int: 正态分布整数
    """
    if a < b:
        output = sum([random.randint(a, b) for _ in range(n)]) / n
        return int(round(output))
    else:
        return b


def ensure_time(second, n=3, precision=3):
    """
    确保时间为正态分布
    
    Args:
        second (int, float, tuple): 时间，如10, (10, 30), '10, 30'
        n (int): 模拟使用的随机数数量，默认为5
        precision (int): 小数位数
        
    Returns:
        float: 正态分布时间
    """
    if isinstance(second, tuple):
        multiply = 10 ** precision
        return random_normal_distribution_int(second[0] * multiply, second[1] * multiply, n) / multiply
    elif isinstance(second, str):
        if ',' in second:
            lower, upper = second.replace(' ', '').split(',')
            lower, upper = int(lower), int(upper)
            return ensure_time((lower, upper), n=n, precision=precision)
        if '-' in second:
            lower, upper = second.replace(' ', '').split('-')
            lower, upper = int(lower), int(upper)
            return ensure_time((lower, upper), n=n, precision=precision)
        else:
            return int(second)
    else:
        return second


def get_os_next_reset():
    """
    获取下个月第一天
    
    Returns:
        datetime: 下个月第一天的日期时间
    """
    diff = server_time_offset()
    server_now = datetime.now() - diff
    server_reset = (server_now.replace(day=1) + timedelta(days=32)) \
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    local_reset = server_reset + diff
    return local_reset


def get_os_reset_remain():
    """
    获取距离下次重置的天数
    
    Returns:
        int: 距离下次重置的天数
    """
    from module.logger import logger

    next_reset = get_os_next_reset()
    now = datetime.now()
    logger.attr('OpsiNextReset', next_reset)

    remain = int((next_reset - now).total_seconds() // 86400)
    logger.attr('ResetRemain', remain)
    return remain


def get_server_next_update(daily_trigger):
    """
    获取下次服务器更新时间
    
    Args:
        daily_trigger (list[str], str): 每日触发时间列表，如["00:00", "12:00", "18:00"]
        
    Returns:
        datetime: 下次更新时间
    """
    if isinstance(daily_trigger, str):
        daily_trigger = daily_trigger.replace(' ', '').split(',')

    diff = server_time_offset()
    local_now = datetime.now()
    trigger = []
    for t in daily_trigger:
        h, m = [int(x) for x in t.split(':')]
        future = local_now.replace(hour=h, minute=m, second=0, microsecond=0) + diff
        s = (future - local_now).total_seconds() % 86400
        future = local_now + timedelta(seconds=s)
        trigger.append(future)
    update = sorted(trigger)[0]
    return update


def get_server_last_update(daily_trigger):
    """
    获取上次服务器更新时间
    
    Args:
        daily_trigger (list[str], str): 每日触发时间列表，如["00:00", "12:00", "18:00"]
        
    Returns:
        datetime: 上次更新时间
    """
    if isinstance(daily_trigger, str):
        daily_trigger = daily_trigger.replace(' ', '').split(',')

    diff = server_time_offset()
    local_now = datetime.now()
    trigger = []
    for t in daily_trigger:
        h, m = [int(x) for x in t.split(':')]
        future = local_now.replace(hour=h, minute=m, second=0, microsecond=0) + diff
        s = (future - local_now).total_seconds() % 86400 - 86400
        future = local_now + timedelta(seconds=s)
        trigger.append(future)
    update = sorted(trigger)[-1]
    return update


def get_server_last_monday_update(daily_trigger):
    """
    获取上次周一更新时间
    
    Args:
        daily_trigger (list[str], str): 每日触发时间列表，如["00:00", "12:00", "18:00"]
        
    Returns:
        datetime: 上次周一更新时间
    """
    update = get_server_last_update(daily_trigger)
    diff = update.weekday()
    update = update - timedelta(days=diff)
    return update


def get_server_next_monday_update(daily_trigger):
    """
    获取下次周一更新时间
    
    Args:
        daily_trigger (list[str], str): 每日触发时间列表，如["00:00", "12:00", "18:00"]
        
    Returns:
        datetime: 下次周一更新时间
    """
    update = get_server_next_update(daily_trigger)
    diff = (7 - update.weekday()) % 7
    update = update + timedelta(days=diff)
    return update


def nearest_future(future, interval=120):
    """
    获取最近的未来时间
    如果两个时间点间隔小于interval，返回最后一个
    
    Args:
        future (list[datetime]): 未来时间列表
        interval (int): 间隔秒数
        
    Returns:
        datetime: 最近的未来时间
    """
    future = [datetime.fromisoformat(f) if isinstance(f, str) else f for f in future]
    future = sorted(future)
    next_run = future[0]
    for finish in future:
        if finish - next_run < timedelta(seconds=interval):
            next_run = finish

    return next_run


def get_nearest_weekday_date(target):
    """
    获取最近的指定星期几的日期
    
    Args:
        target (int): 目标星期几
        
    Returns:
        datetime: 最近的指定星期几的日期
    """
    diff = server_time_offset()
    server_now = datetime.now() - diff

    days_ahead = target - server_now.weekday()
    if days_ahead <= 0:
        # 目标日期已经过去
        days_ahead += 7
    server_reset = (server_now + timedelta(days=days_ahead)) \
        .replace(hour=0, minute=0, second=0, microsecond=0)

    local_reset = server_reset + diff
    return local_reset


def get_server_weekday():
    """
    获取服务器当前星期几
    
    Returns:
        int: 服务器当前星期几
    """
    diff = server_time_offset()
    server_now = datetime.now() - diff
    result = server_now.weekday()
    return result


def random_id(length=32):
    """
    生成随机ID
    
    Args:
        length (int): ID长度
        
    Returns:
        str: 随机ID
    """
    return ''.join(random.sample(string.ascii_lowercase + string.digits, length))


def to_list(text, length=1):
    """
    将文本转换为列表
    
    Args:
        text (str): 文本，如'1, 2, 3'
        length (int): 如果只有一个数字，返回指定长度的列表
            如text='3', length=5, 返回[3, 3, 3, 3, 3]
            
    Returns:
        list[int]: 整数列表
    """
    if text.isdigit():
        return [int(text)] * length
    out = [int(letter.strip()) for letter in text.split(',')]
    return out


def type_to_str(typ):
    """
    将任何类型或对象转换为字符串
    移除<>以防止被解析为HTML标签
    
    Args:
        typ: 要转换的类型或对象
        
    Returns:
        str: 类型字符串，如'int', 'datetime.datetime'
    """
    if not isinstance(typ, type):
        typ = type(typ).__name__
    return str(typ)


if __name__ == '__main__':
    get_os_reset_remain()
