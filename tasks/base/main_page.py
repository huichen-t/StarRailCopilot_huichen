import re

import module.config.server as server
from module.config.server import VALID_LANG
from module.exception import RequestHumanTakeover, ScriptError
from module.logger import logger
from module.ocr.ocr import OcrWhiteLetterOnComplexBackground
from tasks.base.assets.assets_base_main_page import OCR_MAP_NAME
from tasks.base.page import Page, page_main
from tasks.base.popup import PopupHandler
from tasks.map.keywords import KEYWORDS_MAP_PLANE, MapPlane


class OcrPlaneName(OcrWhiteLetterOnComplexBackground):
    """地图名称OCR识别类，用于处理各种地图名称的识别和修正"""
    
    def after_process(self, result):
        """
        对OCR识别结果进行后处理，修正各种可能的识别错误
        Args:
            result: OCR识别结果

        Returns:
            str: 处理后的结果
        """
        # 处理机器人定居点1
        result = re.sub(r'-[Ii1]$', '', result)
        result = re.sub(r'I$', '', result)
        result = re.sub(r'\d+$', '', result)
        # 处理黑塔办公室Y/
        result = re.sub(r'Y/?$', '', result)
        # 修正观星者导航名称
        result = result.replace('avatia', 'avalia')
        # 处理苏乐达™热砂海选会场
        result = re.sub(r'(苏乐达|蘇樂達|SoulGlad|スラーダ|FelizAlma)[rtT]*M*', r'\1', result)
        # 处理SoulGladtM Scorchsand Audition Ven
        if 'Audition' in result:
            right = result.find('Audition') + len('Audition')
            result = result[:right] + ' Venue'
        # 处理The Radiant Feldspar
        result = re.sub(r'The\s*Rad', 'Rad', result)
        # 修正幽囚狱
        result = result.replace('幽因狱', '幽囚狱')
        result = result.replace('幽因獄', '幽囚獄')
        # 修正DomainiRespite
        result = result.replace('omaini', 'omain')
        # 修正Domain=Combat
        result = result.replace('=', '')
        # 修正各种Domain相关错误
        result = result.replace('cunr', 'cur').replace('uren', 'urren').replace('Qcc', 'Occ')
        # 修正Domain-Elit相关错误
        result = re.sub(r'[Ee]lit$', 'Elite', result)
        result = result.replace('tite', 'lite')

        # 修正区域战斗相关错误
        result = re.sub(r'区域.*战$', '区域战斗', result)
        # 修正区域事件相关错误
        result = re.sub(r'区域.*[事件]$', '区域事件', result)
        # 修正区域交易相关错误
        result = re.sub(r'区域.*交$', '区域交易', result)
        # 修正区域精英相关错误
        result = re.sub(r'区域.*[精英]$', '区域精英', result)
        # 修正区域事件相关错误
        result = re.sub(r'事[伴祥]', '事件', result)
        # 修正医域错误
        result = result.replace('医域', '区域')
        # 修正区域战斗相关错误
        result = re.sub(r'战[半头卒三]', '战斗', result)
        # 统一区域分隔符
        result = re.sub(r'区域[\-—－一=]', '区域-', result)
        # 修正黑塔办公室
        result = result.replace('累塔', '黑塔')
        if '星港' in result:
            result = '迴星港'
        result = result.replace('太司', '太卜司')
        # 修正Radiant Feldspar相关错误
        result = re.sub('[Ii1|]\s*Radiant', 'Radiant', result)

        # 移除空格
        result = result.replace(' ', '')

        return super().after_process(result)


class MainPage(PopupHandler):
    """主页面处理类，用于处理主界面的各种操作和状态"""
    # 与BigmapPlane类相同
    # 当前所在的地图
    plane: MapPlane = KEYWORDS_MAP_PLANE.Herta_ParlorCar

    _lang_checked = False
    _lang_check_success = True

    def update_plane(self, lang=None) -> MapPlane | None:
        """
        更新当前所在的地图信息
        Args:
            lang: 语言，如果为None则使用服务器语言

        Returns:
            MapPlane | None: 当前地图，如果无法识别则返回None

        Pages:
            in: page_main
        """
        if lang is None:
            lang = server.lang
        ocr = OcrPlaneName(OCR_MAP_NAME, lang=lang)
        result = ocr.ocr_single_line(self.device.image)
        # 尝试匹配
        keyword = ocr._match_result(result, keyword_classes=MapPlane, lang=lang)
        if keyword is not None:
            self.plane = keyword
            logger.attr('CurrentPlane', keyword)
            return keyword
        # 尝试移除后缀后匹配
        for suffix in range(1, 5):
            keyword = ocr._match_result(result[:-suffix], keyword_classes=MapPlane, lang=lang)
            if keyword is not None:
                self.plane = keyword
                logger.attr('CurrentPlane', keyword)
                return keyword

        return None

    def check_lang_from_map_plane(self) -> str | None:
        """
        通过地图名称检查游戏语言
        Returns:
            str | None: 检测到的语言，如果无法检测则返回None
        """
        logger.info('check_lang_from_map_plane')
        lang_unknown = self.config.Emulator_GameLanguage == 'auto'

        if lang_unknown:
            lang_list = VALID_LANG
        else:
            # 优先尝试当前语言
            lang_list = [server.lang] + [lang for lang in VALID_LANG if lang != server.lang]

        for lang in lang_list:
            logger.info(f'Try ocr in lang {lang}')
            keyword = self.update_plane(lang)
            if keyword is not None:
                logger.info(f'check_lang_from_map_plane matched lang: {lang}')
                if lang_unknown or lang != server.lang:
                    self.config.Emulator_GameLanguage = lang
                    server.set_lang(lang)
                MainPage._lang_checked = True
                MainPage._lang_check_success = True
                return lang

        if lang_unknown:
            logger.critical('Cannot detect in-game text language, please set it to 简体中文 or English')
            raise RequestHumanTakeover
        else:
            logger.warning(f'Cannot detect in-game text language, assume current lang={server.lang} is correct')
            MainPage._lang_checked = True
            MainPage._lang_check_success = False
            return server.lang

    def handle_lang_check(self, page: Page):
        """
        处理语言检查
        Args:
            page: 当前页面

        Returns:
            bool: 是否进行了语言检查
        """
        if MainPage._lang_checked:
            return False
        if page != page_main:
            return False

        self.check_lang_from_map_plane()
        return True

    def acquire_lang_checked(self):
        """
        获取语言检查状态
        Returns:
            bool: 是否进行了语言检查
        """
        if MainPage._lang_checked:
            return False

        logger.info('acquire_lang_checked')
        try:
            self.ui_goto(page_main)
        except AttributeError:
            logger.critical('Method ui_goto() not found, class MainPage must be inherited by class UI')
            raise ScriptError

        self.handle_lang_check(page=page_main)
        return True
