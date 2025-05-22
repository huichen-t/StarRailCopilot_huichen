"""
配置转换模块

功能：
1. 提供游戏内各种名称和标识符的转换功能
2. 支持日常任务名称转换
3. 支持副本名称转换
4. 支持模拟宇宙相关转换
5. 支持物品名称转换
6. 支持周常任务名称转换

主要函数：
- convert_daily: 日常任务名称转换
- convert_20_dungeon: 20级副本名称转换
- convert_rogue_farm: 模拟宇宙相关转换
- convert_Item_Moon_Madness_Fang: 物品名称转换
- convert_31_dungeon: 31级副本名称转换
- convert_32_weekly: 32级周常任务名称转换
"""

def convert_daily(value):
    """
    转换日常任务名称
    
    Args:
        value: 原始任务名称
        
    Returns:
        str: 转换后的任务名称
    """
    if value == "Calyx_Crimson_Hunt":
        value = "Calyx_Crimson_The_Hunt"
    return value


def convert_20_dungeon(value):
    """
    转换20级副本名称
    
    支持的转换：
    1. 金色回忆副本 -> 雅利洛VI金色回忆
    2. 金色以太副本 -> 雅利洛VI金色以太
    3. 金色宝藏副本 -> 雅利洛VI金色宝藏
    4. 赤色毁灭副本 -> 黑塔存储区赤色毁灭
    5. 赤色追猎副本 -> 雅利洛外围雪原赤色追猎
    6. 赤色智识副本 -> 雅利洛铆钉镇赤色智识
    7. 赤色谐乐副本 -> 雅利洛机器人定居点赤色谐乐
    8. 赤色虚无副本 -> 雅利洛大矿场赤色虚无
    9. 赤色存护副本 -> 黑塔补给区赤色存护
    10. 赤色丰饶副本 -> 雅利洛后巷赤色丰饶
    
    Args:
        value: 原始副本名称
        
    Returns:
        str: 转换后的副本名称
    """
    if value == 'Calyx_Golden_Memories':
        return 'Calyx_Golden_Memories_Jarilo_VI'
    if value == 'Calyx_Golden_Aether':
        return 'Calyx_Golden_Aether_Jarilo_VI'
    if value == 'Calyx_Golden_Treasures':
        return 'Calyx_Golden_Treasures_Jarilo_VI'
    if value == 'Calyx_Golden_Memories':
        return 'Calyx_Golden_Memories_Jarilo_VI'

    if value == 'Calyx_Crimson_Destruction':
        return 'Calyx_Crimson_Destruction_Herta_StorageZone'
    if value == 'Calyx_Crimson_The_Hunt':
        return 'Calyx_Crimson_The_Hunt_Jarilo_OutlyingSnowPlains'
    if value == 'Calyx_Crimson_Erudition':
        return 'Calyx_Crimson_Erudition_Jarilo_RivetTown'
    if value == 'Calyx_Crimson_Harmony':
        return 'Calyx_Crimson_Harmony_Jarilo_RobotSettlement'
    if value == 'Calyx_Crimson_Nihility':
        return 'Calyx_Crimson_Nihility_Jarilo_GreatMine'
    if value == 'Calyx_Crimson_Preservation':
        return 'Calyx_Crimson_Preservation_Herta_SupplyZone'
    if value == 'Calyx_Crimson_Abundance':
        return 'Calyx_Crimson_Abundance_Jarilo_BackwaterPass'

    return value


def convert_rogue_farm(value):
    """
    转换模拟宇宙相关数值
    
    功能：
    1. 将进度值转换为剩余值
    2. 设置总值为100
    
    Args:
        value: 包含进度的字典，格式为{'value': int}
        
    Returns:
        dict: 转换后的字典，格式为{'value': int, 'total': 100}
    """
    if isinstance(value, dict) and 'value' in value.keys():
        value['value'] = 100 - value['value']
        value['total'] = 100
        return value


def convert_Item_Moon_Madness_Fang(value):
    """
    转换物品名称
    
    功能：
    将"Moon_Madness_Fang"转换为"Moon_Rage_Fang"
    
    Args:
        value: 包含物品名称的字典，格式为{'item': str}
        
    Returns:
        dict: 转换后的字典
    """
    if isinstance(value, dict):
        value['item'] = 'Moon_Rage_Fang'
    return value


def convert_31_dungeon(value):
    """
    转换31级副本名称
    
    功能：
    将"Calyx_Crimson_Remembrance_Special_StrifeRuinsCastrumKremnos"
    转换为"Calyx_Crimson_Remembrance_Amphoreus_StrifeRuinsCastrumKremnos"
    
    Args:
        value: 原始副本名称
        
    Returns:
        str: 转换后的副本名称
    """
    if value == 'Calyx_Crimson_Remembrance_Special_StrifeRuinsCastrumKremnos':
        return 'Calyx_Crimson_Remembrance_Amphoreus_StrifeRuinsCastrumKremnos'
    return value


def convert_32_weekly(value):
    """
    转换32级周常任务名称
    
    功能：
    将"Echo_of_War_Borehole_Planet_Old_Crater"
    转换为"Echo_of_War_Borehole_Planet_Past_Nightmares"
    
    Args:
        value: 原始任务名称
        
    Returns:
        str: 转换后的任务名称
    """
    if value == 'Echo_of_War_Borehole_Planet_Old_Crater':
        return 'Echo_of_War_Borehole_Planet_Past_Nightmares'
    return value
