"""
代码生成器模块

功能：
1. 提供代码生成和格式化功能
2. 支持缩进管理
3. 支持注释生成
4. 支持变量和对象生成
5. 支持Markdown表格生成

主要组件：
- TabWrapper: 缩进包装器
- VariableWrapper: 变量包装器
- CodeGenerator: 代码生成器
- MarkdownGenerator: Markdown表格生成器
"""

import typing as t


class TabWrapper:
    """
    缩进包装器类
    
    用于管理代码块的缩进，支持上下文管理器语法
    
    属性：
        generator: 代码生成器实例
        prefix: 前缀字符串
        suffix: 后缀字符串
        newline: 是否添加换行
        nested: 是否为嵌套块
    """
    def __init__(self, generator, prefix='', suffix='', newline=True):
        """
        初始化缩进包装器
        
        Args:
            generator (CodeGenerator): 代码生成器实例
            prefix (str): 前缀字符串
            suffix (str): 后缀字符串
            newline (bool): 是否添加换行
        """
        self.generator = generator
        self.prefix = prefix
        self.suffix = suffix
        self.newline = newline
        self.nested = False

    def __enter__(self):
        """
        进入代码块时添加前缀并增加缩进
        
        Returns:
            TabWrapper: 当前实例
        """
        if not self.nested and self.prefix:
            self.generator.add(self.prefix, newline=self.newline)
        self.generator.tab_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出代码块时减少缩进并添加后缀
        """
        self.generator.tab_count -= 1
        if self.suffix:
            self.generator.add(self.suffix)

    def __repr__(self):
        """
        返回前缀字符串表示
        """
        return self.prefix

    def set_nested(self, suffix=''):
        """
        设置为嵌套块并添加后缀
        
        Args:
            suffix (str): 要添加的后缀
        """
        self.nested = True
        self.suffix += suffix


class VariableWrapper:
    """
    变量包装器类
    
    用于包装变量名，提供字符串表示
    """
    def __init__(self, name):
        """
        初始化变量包装器
        
        Args:
            name: 变量名
        """
        self.name = name

    def __repr__(self):
        """
        返回变量名的字符串表示
        """
        return str(self.name)

    __str__ = __repr__


class CodeGenerator:
    """
    代码生成器类
    
    提供代码生成和格式化的核心功能
    
    属性：
        tab_count: 当前缩进级别
        lines: 生成的代码行列表
    """
    def __init__(self):
        """
        初始化代码生成器
        """
        self.tab_count = 0
        self.lines = []

    def add(self, line, comment=False, newline=True):
        """
        添加代码行
        
        Args:
            line (str): 要添加的代码行
            comment (bool): 是否为注释行
            newline (bool): 是否添加换行
        """
        self.lines.append(self._line_with_tabs(line, comment=comment, newline=newline))

    def generate(self):
        """
        生成完整的代码字符串
        
        Returns:
            str: 生成的代码
        """
        return ''.join(self.lines)

    def print(self):
        """
        打印生成的代码
        """
        lines = self.generate()
        print(lines)

    def write(self, file: str = None):
        """
        将生成的代码写入文件
        
        Args:
            file (str): 目标文件路径
        """
        lines = self.generate()
        with open(file, 'w', encoding='utf-8', newline='') as f:
            f.write(lines)

    def _line_with_tabs(self, line, comment=False, newline=True):
        """
        为代码行添加缩进
        
        Args:
            line (str): 代码行
            comment (bool): 是否为注释行
            newline (bool): 是否添加换行
            
        Returns:
            str: 添加缩进后的代码行
        """
        if comment:
            line = '# ' + line
        out = '    ' * self.tab_count + line
        if newline:
            out += '\n'
        return out

    def _repr(self, obj):
        """
        获取对象的字符串表示
        
        Args:
            obj: 要转换的对象
            
        Returns:
            str: 对象的字符串表示
        """
        if isinstance(obj, str):
            if '\n' in obj:
                out = '"""\n'
                with self.tab():
                    for line in obj.strip().split('\n'):
                        line = line.strip()
                        out += self._line_with_tabs(line)
                out += self._line_with_tabs('"""', newline=False)
                return out
        return repr(obj)

    def tab(self):
        """
        创建新的缩进块
        
        Returns:
            TabWrapper: 缩进包装器实例
        """
        return TabWrapper(self)

    def Empty(self):
        """
        添加空行
        """
        self.lines.append('\n')

    def Pass(self):
        """
        添加pass语句
        """
        self.add('pass')

    def Import(self, text, empty=2):
        """
        添加导入语句
        
        Args:
            text (str): 导入语句文本
            empty (int): 添加的空行数
        """
        for line in text.strip().split('\n'):
            line = line.strip()
            self.add(line)
        for _ in range(empty):
            self.Empty()

    def Variable(self, name):
        """
        创建变量包装器
        
        Args:
            name: 变量名
            
        Returns:
            VariableWrapper: 变量包装器实例
        """
        return VariableWrapper(name)

    def Value(self, key=None, value=None, type_=None, **kwargs):
        """
        添加变量赋值语句
        
        Args:
            key: 变量名
            value: 变量值
            type_: 变量类型
            **kwargs: 其他变量赋值
        """
        if key is not None:
            if type_ is not None:
                self.add(f'{key}: {type_} = {self._repr(value)}')
            else:
                self.add(f'{key} = {self._repr(value)}')
        for key, value in kwargs.items():
            self.Value(key, value)

    def Comment(self, text):
        """
        添加注释
        
        Args:
            text (str): 注释文本
        """
        for line in text.strip().split('\n'):
            line = line.strip()
            self.add(line, comment=True)

    def CommentAutoGenerage(self, file):
        """
        添加自动生成注释
        
        Args:
            file: 生成文件的模块路径，如 'dev_tools.button_extract'
        """
        # 只保留一个空行
        if len(self.lines) >= 2:
            if self.lines[-2:] == ['\n', '\n']:
                self.lines.pop(-1)
        self.Comment('This file was auto-generated, do not modify it manually. To generate:')
        self.Comment(f'``` python -m {file} ```')
        self.Empty()

    def List(self, key=None):
        """
        创建列表生成块
        
        Args:
            key: 列表变量名
            
        Returns:
            TabWrapper: 列表生成块
        """
        if key is not None:
            return TabWrapper(self, prefix=str(key) + ' = [', suffix=']')
        else:
            return TabWrapper(self, prefix='[', suffix=']')

    def ListItem(self, value):
        """
        添加列表项
        
        Args:
            value: 列表项值
            
        Returns:
            TabWrapper: 如果value是TabWrapper则返回该实例
        """
        if isinstance(value, TabWrapper):
            value.set_nested(suffix=',')
            self.add(f'{self._repr(value)}')
            return value
        else:
            self.add(f'{self._repr(value)},')

    def Dict(self, key=None):
        """
        创建字典生成块
        
        Args:
            key: 字典变量名
            
        Returns:
            TabWrapper: 字典生成块
        """
        if key is not None:
            return TabWrapper(self, prefix=str(key) + ' = {', suffix='}')
        else:
            return TabWrapper(self, prefix='{', suffix='}')

    def DictItem(self, key=None, value=None):
        """
        添加字典项
        
        Args:
            key: 字典键
            value: 字典值
            
        Returns:
            TabWrapper: 如果value是TabWrapper则返回该实例
        """
        if isinstance(value, TabWrapper):
            value.set_nested(suffix=',')
            if key is not None:
                self.add(f'{self._repr(key)}: {self._repr(value)}')
            return value
        else:
            if key is not None:
                self.add(f'{self._repr(key)}: {self._repr(value)},')

    def Object(self, object_class, key=None):
        """
        创建对象生成块
        
        Args:
            object_class: 对象类名
            key: 对象变量名
            
        Returns:
            TabWrapper: 对象生成块
        """
        if key is not None:
            return TabWrapper(self, prefix=f'{key} = {object_class}(', suffix=')')
        else:
            return TabWrapper(self, prefix=f'{object_class}(', suffix=')')

    def ObjectAttr(self, key=None, value=None):
        """
        添加对象属性
        
        Args:
            key: 属性名
            value: 属性值
            
        Returns:
            TabWrapper: 如果value是TabWrapper则返回该实例
        """
        if isinstance(value, TabWrapper):
            value.set_nested(suffix=',')
            if key is None:
                self.add(f'{self._repr(value)}')
            else:
                self.add(f'{key}={self._repr(value)}')
            return value
        else:
            if key is None:
                self.add(f'{self._repr(value)},')
            else:
                self.add(f'{key}={self._repr(value)},')

    def Class(self, name, inherit=None):
        """
        创建类定义块
        
        Args:
            name: 类名
            inherit: 继承的类名
            
        Returns:
            TabWrapper: 类定义块
        """
        if inherit is not None:
            return TabWrapper(self, prefix=f'class {name}({inherit}):')
        else:
            return TabWrapper(self, prefix=f'class {name}:')

    def Def(self, name, args=''):
        """
        创建函数定义块
        
        Args:
            name: 函数名
            args: 函数参数
            
        Returns:
            TabWrapper: 函数定义块
        """
        return TabWrapper(self, prefix=f'def {name}({args}):')


# 创建全局代码生成器实例
generator = CodeGenerator()
Import = generator.Import
Value = generator.Value
Comment = generator.Comment
Dict = generator.Dict
DictItem = generator.DictItem


class MarkdownGenerator:
    """
    Markdown表格生成器类
    
    用于生成格式化的Markdown表格
    
    属性：
        rows: 表格行列表
    """
    def __init__(self, column: t.List[str]):
        """
        初始化Markdown表格生成器
        
        Args:
            column (List[str]): 表头列
        """
        self.rows = [column]

    def add_row(self, row):
        """
        添加表格行
        
        Args:
            row: 要添加的行数据
        """
        self.rows.append([str(ele) for ele in row])

    def product_line(self, row, max_width):
        """
        生成格式化的表格行
        
        Args:
            row: 行数据
            max_width: 每列的最大宽度
            
        Returns:
            str: 格式化后的表格行
        """
        row = [ele.ljust(width) for ele, width in zip(row, max_width)]
        row = ' | '.join(row)
        row = '| ' + row + ' |'
        return row

    def generate(self) -> t.List[str]:
        """
        生成完整的Markdown表格
        
        Returns:
            List[str]: 表格行列表
        """
        import numpy as np
        width = np.array([
            [len(ele) for ele in row] for row in self.rows
        ])
        max_width = np.max(width, axis=0)
        dash = ['-' * width for width in max_width]

        rows = [
                   self.product_line(self.rows[0], max_width),
                   self.product_line(dash, max_width),
               ] + [
                   self.product_line(row, max_width) for row in self.rows[1:]
               ]
        return rows
