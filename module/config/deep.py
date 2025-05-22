"""
深度字典操作模块

功能：
1. 提供嵌套字典的深度访问和操作功能
2. 支持高性能的字典操作
3. 支持字典差异比较和补丁生成
4. 支持深度迭代和值获取

性能说明：
- 当键存在时性能排序：
  try: dict[key] except KeyError < dict.get(key) < if key in dict: dict[key]
- 当键不存在时性能排序：
  if key in dict: dict[key] < dict.get(key) <<< try: dict[key] except KeyError

主要函数：
- deep_get: 安全获取嵌套字典值
- deep_get_with_error: 获取嵌套字典值（带错误抛出）
- deep_exist: 检查嵌套字典键是否存在
- deep_set: 安全设置嵌套字典值
- deep_default: 设置嵌套字典默认值
- deep_pop: 弹出嵌套字典值
- deep_iter: 深度迭代嵌套字典
- deep_values: 获取嵌套字典所有值
- deep_iter_diff: 比较两个嵌套字典的差异
- deep_iter_patch: 生成嵌套字典的补丁操作
"""

from collections import deque

# 操作类型常量
OP_ADD = 'add'  # 添加操作
OP_SET = 'set'  # 设置操作
OP_DEL = 'del'  # 删除操作


def deep_get(d, keys, default=None):
    """
    安全获取嵌套字典中的值
    
    性能：240 + 30 * 深度 (纳秒)
    
    Args:
        d (dict): 目标字典
        keys (list[str], str): 键路径，如 ['Scheduler', 'NextRun', 'value']
        default: 当键不存在时返回的默认值
        
    Returns:
        指定键路径的值，如果不存在则返回默认值
    """
    if type(keys) is str:
        keys = keys.split('.')

    try:
        for k in keys:
            d = d[k]
        return d
    # 键不存在
    except KeyError:
        return default
    # 索引不存在
    except IndexError:
        return default
    # 输入keys不可迭代或d不是字典
    # 列表索引必须是整数或切片，不能是字符串
    except TypeError:
        return default


def deep_get_with_error(d, keys):
    """
    获取嵌套字典中的值，如果键不存在则抛出KeyError
    
    性能：240 + 30 * 深度 (纳秒)
    
    Args:
        d (dict): 目标字典
        keys (list[str], str): 键路径，如 ['Scheduler', 'NextRun', 'value']
        
    Returns:
        指定键路径的值
        
    Raises:
        KeyError: 当键不存在时抛出
    """
    if type(keys) is str:
        keys = keys.split('.')

    try:
        for k in keys:
            d = d[k]
        return d
    # 键不存在
    # except KeyError:
    #     raise
    # 索引不存在
    except IndexError:
        raise KeyError
    # 输入keys不可迭代或d不是字典
    # 列表索引必须是整数或切片，不能是字符串
    except TypeError:
        raise KeyError


def deep_exist(d, keys):
    """
    检查嵌套字典中是否存在指定的键路径
    
    性能：240 + 30 * 深度 (纳秒)
    
    Args:
        d (dict): 目标字典
        keys (str, list): 键路径，如 'Scheduler.NextRun.value'
        
    Returns:
        bool: 键路径是否存在
    """
    if type(keys) is str:
        keys = keys.split('.')

    try:
        for k in keys:
            d = d[k]
        return True
    # 键不存在
    except KeyError:
        return False
    # 索引不存在
    except IndexError:
        return False
    # 输入keys不可迭代或d不是字典
    # 列表索引必须是整数或切片，不能是字符串
    except TypeError:
        return False


def deep_set(d, keys, value):
    """
    安全设置嵌套字典中的值
    
    性能：150 * 深度 (纳秒)
    只能设置字典类型的值
    
    Args:
        d (dict): 目标字典
        keys (list[str], str): 键路径
        value: 要设置的值
    """
    if type(keys) is str:
        keys = keys.split('.')

    first = True
    exist = True
    prev_d = None
    prev_k = None
    prev_k2 = None
    try:
        for k in keys:
            if first:
                prev_d = d
                prev_k = k
                first = False
                continue
            try:
                # if key in dict: dict[key] > dict.get > dict.setdefault > try dict[key] except
                if exist and prev_k in d:
                    prev_d = d
                    d = d[prev_k]
                else:
                    exist = False
                    new = {}
                    d[prev_k] = new
                    d = new
            except TypeError:
                # d不是字典
                exist = False
                d = {}
                prev_d[prev_k2] = {prev_k: d}

            prev_k2 = prev_k
            prev_k = k
            # prev_k2, prev_k = prev_k, k
    # 输入keys不可迭代
    except TypeError:
        return

    # 最后一个键，设置值
    try:
        d[prev_k] = value
        return
    # 最后一个值d不是字典
    except TypeError:
        prev_d[prev_k2] = {prev_k: value}
        return


def deep_default(d, keys, value):
    """
    安全设置嵌套字典中的默认值
    
    性能：150 * 深度 (纳秒)
    只能设置字典类型的值
    
    Args:
        d (dict): 目标字典
        keys (list[str], str): 键路径
        value: 要设置的默认值
    """
    if type(keys) is str:
        keys = keys.split('.')

    first = True
    exist = True
    prev_d = None
    prev_k = None
    prev_k2 = None
    try:
        for k in keys:
            if first:
                prev_d = d
                prev_k = k
                first = False
                continue
            try:
                # if key in dict: dict[key] > dict.get > dict.setdefault > try dict[key] except
                if exist and prev_k in d:
                    prev_d = d
                    d = d[prev_k]
                else:
                    exist = False
                    new = {}
                    d[prev_k] = new
                    d = new
            except TypeError:
                # d不是字典
                exist = False
                d = {}
                prev_d[prev_k2] = {prev_k: d}

            prev_k2 = prev_k
            prev_k = k
            # prev_k2, prev_k = prev_k, k
    # 输入keys不可迭代
    except TypeError:
        return

    # 最后一个键，设置默认值
    try:
        d.setdefault(prev_k, value)
        return
    # 最后一个值d不是字典
    except AttributeError:
        prev_d[prev_k2] = {prev_k: value}
        return


def deep_pop(d, keys, default=None):
    """
    从嵌套字典中弹出值
    
    Args:
        d (dict): 目标字典
        keys (list[str], str): 键路径
        default: 当键不存在时返回的默认值
        
    Returns:
        弹出的值，如果键不存在则返回默认值
    """
    if type(keys) is str:
        keys = keys.split('.')

    try:
        for k in keys[:-1]:
            d = d[k]
        # 不使用pop(k, default)以支持列表弹出
        return d.pop(keys[-1])
    # 键不存在
    except KeyError:
        return default
    # 输入keys不可迭代或d不是字典
    # 列表索引必须是整数或切片，不能是字符串
    except TypeError:
        return default
    # 输入keys超出索引范围
    except IndexError:
        return default
    # 最后一个d不是字典
    except AttributeError:
        return default


def deep_iter_depth1(data):
    """
    等效于data.items()，但如果data不是字典则抑制错误
    
    Args:
        data: 要迭代的数据
        
    Yields:
        Any: 键
        Any: 值
    """
    try:
        for k, v in data.items():
            yield k, v
        return
    except AttributeError:
        # data不是字典
        return


def deep_iter_depth2(data):
    """
    迭代深度为2的嵌套字典中的键和值
    简化版的deep_iter
    
    Args:
        data: 要迭代的数据
        
    Yields:
        Any: 第一层键
        Any: 第二层键
        Any: 值
    """
    try:
        for k1, v1 in data.items():
            if type(v1) is dict:
                for k2, v2 in v1.items():
                    yield k1, k2, v2
    except AttributeError:
        # data不是字典
        return


def deep_iter(data, min_depth=None, depth=3):
    """
    迭代嵌套字典中的键和值
    在depth=3的alas.json上性能为300微秒（530+行）
    只能迭代字典
    
    Args:
        data: 要迭代的数据
        min_depth: 最小迭代深度
        depth: 最大迭代深度
        
    Yields:
        list[str]: 键路径
        Any: 值
    """
    if min_depth is None:
        min_depth = depth
    assert 1 <= min_depth <= depth

    # 等效于dict.items()
    try:
        if depth == 1:
            for k, v in data.items():
                yield [k], v
            return
        # 迭代第一层
        elif min_depth == 1:
            q = deque()
            for k, v in data.items():
                key = [k]
                if type(v) is dict:
                    q.append((key, v))
                else:
                    yield key, v
        # 只迭代目标深度
        else:
            q = deque()
            for k, v in data.items():
                key = [k]
                if type(v) is dict:
                    q.append((key, v))
    except AttributeError:
        # data不是字典
        return

    # 迭代深度
    current = 2
    while current <= depth:
        new_q = deque()
        # 最大深度
        if current == depth:
            for key, data in q:
                for k, v in data.items():
                    yield key + [k], v
        # 在目标深度内
        elif min_depth <= current < depth:
            for key, data in q:
                for k, v in data.items():
                    subkey = key + [k]
                    if type(v) is dict:
                        new_q.append((subkey, v))
                    else:
                        yield subkey, v
        # 未达到最小深度
        else:
            for key, data in q:
                for k, v in data.items():
                    subkey = key + [k]
                    if type(v) is dict:
                        new_q.append((subkey, v))
        q = new_q
        current += 1


def deep_values(data, min_depth=None, depth=3):
    """
    迭代嵌套字典中的值
    在depth=3的alas.json上性能为300微秒（530+行）
    只能迭代字典
    
    Args:
        data: 要迭代的数据
        min_depth: 最小迭代深度
        depth: 最大迭代深度
        
    Yields:
        Any: 值
    """
    if min_depth is None:
        min_depth = depth
    assert 1 <= min_depth <= depth

    # 等效于dict.items()
    try:
        if depth == 1:
            for v in data.values():
                yield v
            return
        # 迭代第一层
        elif min_depth == 1:
            q = deque()
            for v in data.values():
                if type(v) is dict:
                    q.append(v)
                else:
                    yield v
        # 只迭代目标深度
        else:
            q = deque()
            for v in data.values():
                if type(v) is dict:
                    q.append(v)
    except AttributeError:
        # data不是字典
        return

    # 迭代深度
    current = 2
    while current <= depth:
        new_q = deque()
        # 最大深度
        if current == depth:
            for data in q:
                for v in data.values():
                    yield v
        # 在目标深度内
        elif min_depth <= current < depth:
            for data in q:
                for v in data.values():
                    if type(v) is dict:
                        new_q.append(v)
                    else:
                        yield v
        # 未达到最小深度
        else:
            for data in q:
                for v in data.values():
                    if type(v) is dict:
                        new_q.append(v)
        q = new_q
        current += 1


def deep_iter_diff(before, after):
    """
    迭代两个字典之间的差异
    比较两个深度嵌套的字典时性能很好，
    时间成本随差异数量增加而增加
    
    Args:
        before: 原始字典
        after: 目标字典
        
    Yields:
        list[str]: 键路径
        Any: before中的值，如果不存在则为None
        Any: after中的值，如果不存在则为None
    """
    if before == after:
        return
    if type(before) is not dict or type(after) is not dict:
        yield [], before, after
        return

    queue = deque([([], before, after)])
    while True:
        new_queue = deque()
        for path, d1, d2 in queue:
            keys1 = set(d1.keys())
            keys2 = set(d2.keys())
            for key in keys1.union(keys2):
                try:
                    val2 = d2[key]
                except KeyError:
                    # 可以安全访问d1[key]，因为key来自两个集合的并集
                    # 如果key不在d2中，那么它一定在d1中
                    yield path + [key], d1[key], None
                    continue
                try:
                    val1 = d1[key]
                except KeyError:
                    yield path + [key], None, val2
                    continue
                # 先比较字典，这样比较快
                if val1 != val2:
                    if type(val1) is dict and type(val2) is dict:
                        new_queue.append((path + [key], val1, val2))
                    else:
                        yield path + [key], val1, val2
        queue = new_queue
        if not queue:
            break


def deep_iter_patch(before, after):
    """
    迭代从before到after的补丁事件，类似创建json-patch
    比较两个深度嵌套的字典时性能很好，
    时间成本随差异数量增加而增加
    
    Args:
        before: 原始字典
        after: 目标字典
        
    Yields:
        str: OP_ADD, OP_SET, OP_DEL
        list[str]: 键路径
        Any: after中的值，如果是OP_DEL则为None
    """
    if before == after:
        return
    if type(before) is not dict or type(after) is not dict:
        yield OP_SET, [], after
        return

    queue = deque([([], before, after)])
    while True:
        new_queue = deque()
        for path, d1, d2 in queue:
            keys1 = set(d1.keys())
            keys2 = set(d2.keys())
            for key in keys1.union(keys2):
                try:
                    val2 = d2[key]
                except KeyError:
                    yield OP_DEL, path + [key], None
                    continue
                try:
                    val1 = d1[key]
                except KeyError:
                    yield OP_ADD, path + [key], val2
                    continue
                # 先比较字典，这样比较快
                if val1 != val2:
                    if type(val1) is dict and type(val2) is dict:
                        new_queue.append((path + [key], val1, val2))
                    else:
                        yield OP_SET, path + [key], val2
        queue = new_queue
        if not queue:
            break
