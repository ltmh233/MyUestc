import json
import re
import os
import datetime
import time
from kivy.animation import Animation
import threading
from kivy.properties import ListProperty
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from get_course import get_course_schedule, get_current_week

# 定义颜色
PRIMARY_COLOR = [0.20, 0.60, 0.86, 1]      # 主色调蓝色
SECONDARY_COLOR = [0.95, 0.95, 0.95, 1]    # 次色调浅灰色
BUTTON_COLOR = [0.20, 0.60, 0.86, 1]       # 按钮蓝色
BUTTON_TEXT_COLOR = [1, 1, 1, 1]           # 按钮白色文本
LABEL_TEXT_COLOR_DARK = [0, 0, 0, 1]       # 标签黑色文本
LABEL_TEXT_COLOR_LIGHT = [1, 1, 1, 1]      # 标签白色文本      
INPUT_BACKGROUND_COLOR = [1, 1, 1, 1]      # 输入框白色背景
INPUT_TEXT_COLOR = [0, 0, 0, 1]            # 输入框黑色文本
POPUP_BACKGROUND_COLOR = [1, 1, 1, 1]      # 弹窗白色背景
POPUP_CONTENT_COLOR = [1, 1, 1, 1]         # 弹窗内容区域

CREDENTIALS_FILE = './data/credentials.json'      # 保存账号密码的文件
FONT_PATH = './font/MapleMono-SC-NF-Regular.ttf'  # 字体文件路径

# 定义字体大小
BASE_FONT_SIZE = 48
LABEL_FONT_SIZE = BASE_FONT_SIZE
BUTTON_FONT_SIZE = BASE_FONT_SIZE
SPINNER_FONT_SIZE = BASE_FONT_SIZE
POPUP_TITLE_FONT_SIZE = 32
POPUP_CONTENT_FONT_SIZE = 32

class FontScaler:
    @staticmethod
    def get_base_font_size():
        # 基于窗口宽度和高度的平均值计算基础字体大小
        return (Window.width * 0.01 + Window.height * 0.02) / 2
    
    @staticmethod
    def get_font_sizes():
        base = FontScaler.get_base_font_size()
        return {
            'base': base,
            'label': base,
            'button': base,
            'spinner': base,
            'popup_title': base * 1.2,
            'popup_content': base * 1.1
        }

class LimitedScrollView(ScrollView):
    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            # 获取当前的 scroll_y
            current_scroll = self.scroll_y
            # 计算新的 scroll_y
            new_scroll = current_scroll - touch.dy / self.height
            # 限制 scroll_y 在0到1之间
            new_scroll = max(0, min(1, new_scroll))
            self.scroll_y = new_scroll
            return True
        return super(LimitedScrollView, self).on_touch_move(touch)
    
    def on_scroll_y(self, instance, value):
        # 限制 scroll_y 在0到1之间
        self.scroll_y = max(0, min(1, value))
    
    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            return super(LimitedScrollView, self).on_touch_move(touch)
        return super(LimitedScrollView, self).on_touch_move(touch)

class CustomPopup(Popup):
    def __init__(self, title_text='', content_widget=None, **kwargs):
        super(CustomPopup, self).__init__(**kwargs)
        self.background = ''  # 移除默认背景
        self.title = ''  # 移除默认标题
        self.title_size = 0  # 移除标题空间

        self.size_hint = kwargs.get('size_hint', (0.5, 0.5))
        self.auto_dismiss = kwargs.get('auto_dismiss', True)
        self.background_color = [0, 0, 0, 0]  # 设置为完全透明

        # 创建一个纯白色带圆角的背景
        with self.canvas.before:
            Color(0.7, 0.7, 0.7, 1)  # 存在BUG
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[20])

        self.bind(size=self.update_canvas, pos=self.update_canvas)

        # 创建内容布局
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)

        if title_text:
            self.title_label = Label(
                text=title_text,
                font_name=FONT_PATH,
                font_size=POPUP_TITLE_FONT_SIZE,
                size_hint=(1, 0.3),
                halign='center',
                valign='middle'
            )
            self.title_label.bind(size=self.title_label.setter('text_size'))
            layout.add_widget(self.title_label)

        if content_widget:
            layout.add_widget(content_widget)

        self.content = layout

    def update_canvas(self, *args):
        # 更新圆角背景的位置和大小
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

    def on_open(self):
        """
        当弹窗打开时，调整标题标签以确保完整显示。
        """
        if hasattr(self, 'title_label'):
            self.title_label.bind(width=self.update_title_text_size)

    def update_title_text_size(self, instance, width):
        """
        更新标题标签的文本大小以适应弹窗宽度。

        参数:
            instance: 被绑定的实例。
            width (float): 当前弹窗的宽度。
        """
        instance.text_size = (width * 0.9, None)  # 设置文本宽度为弹窗宽度的90%

class ColoredBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        self.bg_color = kwargs.pop('bg_color', SECONDARY_COLOR)
        super(ColoredBoxLayout, self).__init__(**kwargs)
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update_rect, pos=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class CustomSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super(CustomSpinnerOption, self).__init__(**kwargs)
        self.font_name = FONT_PATH
        self.font_size = SPINNER_FONT_SIZE
        self.original_background_color = self.background_color  # 保存原始颜色
        self.original_size = self.size  # 保存原始大小

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # 增强背景颜色变化
            anim_bg = Animation(background_color=[0.4, 0.8, 1, 1], duration=0.1)
            # 添加缩放动画，通过改变size
            anim_size = Animation(size=(self.width * 1.1, self.height * 1.1), duration=0.1)
            anim = anim_bg & anim_size
            anim.start(self)
        return super(CustomSpinnerOption, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            # 恢复背景颜色
            anim_bg = Animation(background_color=self.original_background_color, duration=0.1)
            # 恢复大小
            anim_size = Animation(size=self.original_size, duration=0.1)
            anim = anim_bg & anim_size
            anim.start(self)
        return super(CustomSpinnerOption, self).on_touch_up(touch)

class BorderedLabel(ButtonBehavior, Label):
    background_color = ListProperty([1, 1, 1, 1])
    initial_background_color = ListProperty([1, 1, 1, 1])  # 添加初始化颜色属性
    row = 0
    col = 0

    def __init__(self, background_color=[1, 1, 1, 1], row=0, col=0, span=1, **kwargs):
        super(BorderedLabel, self).__init__(**kwargs)
        self.background_color = background_color
        self.initial_background_color = background_color  # 设置初始化颜色
        self.row = row
        self.col = col
        self.span = span  # 新增span属性，用于跨越多个节次
        self.bind(pos=self.update_rect, size=self.update_rect, background_color=self.update_background_color)
        self.bind(on_press=self.on_label_press)  # 绑定点击事件
        self.gradient_steps = 1  # 减少渐变步数
        
        with self.canvas.before:
            # 基础颜色层
            self.color_base = Color(*self.background_color)
            self.rect_base = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
            
            # 深色阴影层
            self.color_shadow = Color(0, 0, 0, 0.1)
            self.rect_shadow = RoundedRectangle(pos=(self.x, self.y - 2), size=self.size, radius=[10])
            
            # 增加渐变层以实现平滑渐变
            for i in range(self.gradient_steps):
                alpha = 0.2 * (1 - i / self.gradient_steps)
                Color(1, 1, 1, alpha)
                y_pos = self.y + (self.height / self.gradient_steps) * i
                height = self.height / self.gradient_steps
                setattr(self, f'rect_gradient{i}', RoundedRectangle(pos=(self.x, y_pos), size=(self.width, height), radius=[10]))
        self.update_border()
        Window.bind(size=self.on_window_resize)

    def update_rect(self, *args):
        # 更新所有背景层的位置和大小
        self.rect_base.pos = self.pos
        self.rect_base.size = self.size
        
        self.rect_shadow.pos = (self.x, self.y - 2)
        self.rect_shadow.size = self.size
        
        for i in range(self.gradient_steps):
            rect = getattr(self, f'rect_gradient{i}', None)
            if rect:
                rect.pos = (self.x, self.y + (self.height / self.gradient_steps) * i)
                rect.size = (self.width, self.height / self.gradient_steps)
        
        self.update_border()

    def on_window_resize(self, window, size):
        self.update_rect()

    def update_background_color(self, instance, value):
        # 更新基础颜色层的颜色
        self.color_base.rgba = value
        self.update_border()

    def update_border(self):
        # 移除所有现有的边框
        borders_to_remove = [instr for instr in self.canvas.before.children if isinstance(instr, Line)]
        for border in borders_to_remove:
            self.canvas.before.remove(border)

        with self.canvas.before:
            # 第一行和第一列的边框
            if self.row == 0:  # 第一行
                Color(0, 0, 0, 1)  # 黑色
                Line(points=[
                    self.x, self.y,  # 左
                    self.x + self.width, self.y  # 右
                ], width=2)

            if self.col == 0:  # 第一列
                Color(0, 0, 0, 1)  # 黑色
                Line(points=[
                    self.x + self.width, self.y,  # 下
                    self.x + self.width, self.y + self.height  # 上
                ], width=2)

            # 上午/下午/晚上分隔线
            if self.row in [4, 8]:  # 第4行和第8行后的分隔线
                Color(0.8, 0.8, 0.8, 1)  # 浅灰色
                Line(points=[
                    self.x, self.y,  # 左
                    self.x + self.width, self.y  # 右
                ], width=1.5)

    def on_label_press(self, instance):
        if self.text.strip():
            course_name = ''.join(self.text.split(' ')[0].split('\n')[0:-1])
            CourseDetailPopup(course_name=course_name).open()

class CourseDetailPopup(CustomPopup):
    def __init__(self, course_name, **kwargs):
        # 初始化详细信息为默认消息
        detail = '暂无详细信息'
        try:
            # 尝试从JSON文件中加载课程详细信息
            with open('./data/course_details.json', 'r', encoding='utf-8') as f:
                course_details = json.load(f)
            # 获取指定课程的详细信息
            detail = course_details.get(course_name, '暂无详细信息')
            if isinstance(detail, dict):
                detail = detail.get('detail', '暂无详细信息')
        except:
            pass  # 如果读取文件失败，保持默认消息

        # 创建一个可滚动的视图来显示详细信息
        content = ScrollView(size_hint=(1, 0.8))

        # 创建一个垂直布局，用于容纳详细信息标签
        label_container = BoxLayout(orientation='vertical', size_hint=(1, None))
        label_container.bind(minimum_height=label_container.setter('height'))

        # 创建详细信息标签
        detail_label = Label(
            text=detail,
            font_name=FONT_PATH,
            font_size=POPUP_CONTENT_FONT_SIZE,
            color=LABEL_TEXT_COLOR_LIGHT,
            size_hint_y=None,
            halign='left',
            valign='top',
            text_size=(self.width * 0.9, None),  # 设置文本宽度为弹窗宽度的90%
            padding=(10, 10)  # 添加内边距以防止文本紧贴边缘
        )
        # 绑定标签的宽度变化以自动调整文本区域
        detail_label.bind(
            width=lambda lb, w: lb.setter('text_size')(lb, (w, None)),
            texture_size=lambda lb, ts: setattr(lb, 'height', ts[1])
        )

        label_container.add_widget(detail_label)
        content.add_widget(label_container)

        # 创建关闭按钮
        btn_close = Button(
            text='关闭',
            size_hint=(0.3, 0.3),
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=PRIMARY_COLOR,
            color=BUTTON_TEXT_COLOR,
            font_name=FONT_PATH,
            font_size=BUTTON_FONT_SIZE
        )
        btn_close.bind(on_press=self.dismiss)  # 绑定按钮点击事件以关闭弹窗

        # 创建主内容布局，包含详细信息和关闭按钮
        main_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        main_content.add_widget(content)
        main_content.add_widget(btn_close)

        # 初始化父类CustomPopup
        super(CourseDetailPopup, self).__init__(
            title_text=f"{course_name} 详细信息",  # 设置弹窗标题为课程名称加详细信息
            content_widget=main_content,
            size_hint=(0.6, 0.5),  # 增加高度以确保标题显示完全
            auto_dismiss=True,
            #background_color=POPUP_BACKGROUND_COLOR
        )

    def on_open(self):
        """
        当弹窗打开时，调整标题标签以确保完整显示。
        """
        if hasattr(self, 'title_label'):
            self.title_label.bind(width=self.update_title_text_size)

    def update_title_text_size(self, instance, width):
        """
        更新标题标签的文本大小以适应弹窗宽度。

        参数:
            instance: 被绑定的实例。
            width (float): 当前弹窗的宽度。
        """
        instance.text_size = (width * 0.9, None)  # 设置文本宽度为弹窗宽度的90%

class SwipeScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super(SwipeScreenManager, self).__init__(**kwargs)
        self._touch_start = None

    def on_touch_down(self, touch):
        # 检查触摸点是否在按钮或交互式组件上
        for child in self.walk():
            if child.collide_point(*touch.pos) and isinstance(child, (Button, ButtonBehavior)):
                return super(SwipeScreenManager, self).on_touch_down(touch)
        self._touch_start = touch.x
        return super(SwipeScreenManager, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._touch_start:
            dx = touch.x - self._touch_start
            if abs(dx) > 50:  # 判定为滑动
                if dx < 0:
                    self.switch_next()
                else:
                    self.switch_previous()
        self._touch_start = None  # 重置触摸起点
        return super(SwipeScreenManager, self).on_touch_up(touch)

    def switch_next(self):
        current_index = self.screen_names.index(self.current)
        if current_index < len(self.screen_names) - 1:
            self.transition.direction = 'left'  # 设置为左滑动方向
            self.current = self.screen_names[current_index + 1]

    def switch_previous(self):
        current_index = self.screen_names.index(self.current)
        if current_index > 0:
            self.transition.direction = 'right'  # 设置为右滑动方向
            self.current = self.screen_names[current_index - 1]

class ScheduleScreen(Screen):
    def __init__(self, **kwargs):
        super(ScheduleScreen, self).__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', bg_color=SECONDARY_COLOR)
        Window.bind(size=self.on_window_resize)

        query_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=10, padding=10)
        self.days = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        self.sample_schedule = {day: [''] * 12 for day in self.days}
        self.operate_data()
        self.color_list = [
            [0.20, 0.60, 0.86, 1],   # 蓝色
            [0.46, 0.80, 0.45, 1],   # 绿色
            [0.93, 0.69, 0.13, 1],   # 橙色
            [0.89, 0.39, 0.28, 1],   # 红色
            [0.54, 0.17, 0.89, 1],   # 紫色
            [0.99, 0.63, 0.78, 1],   # 粉色
            [0.64, 0.08, 0.18, 1],   # 深红色
            [0.30, 0.75, 0.93, 1],   # 天蓝色
            [0.34, 0.93, 0.37, 1],   # 明亮绿色
            [0.98, 0.75, 0.28, 1],   # 黄橙色
            [0.27, 0.52, 0.96, 1],   # 皇家蓝
            [0.79, 0.13, 0.24, 1],   # 绯红色
            [0.85, 0.44, 0.84, 1],   # 薰衣草色
            [0.95, 0.85, 0.25, 1],   # 芥末色
            [0.75, 0.37, 0.62, 1],   # 淡紫色
            [0.60, 0.80, 0.20, 1],   # 石灰色
            [0.50, 0.50, 0.50, 1],   # 灰色
            [0.35, 0.70, 0.90, 1],   # 浅蓝色
            [0.90, 0.50, 0.80, 1],   # 洋红色
            [0.15, 0.75, 0.60, 1],   # 青色
            [0.60, 0.40, 0.80, 1],   # 靛色
            [0.70, 0.30, 0.30, 1],   # 棕红色
            [0.40, 0.80, 0.70, 1],   # 薄荷色
            [0.85, 0.60, 0.10, 1],   # 琥珀色
            [0.90, 0.10, 0.40, 1],   # 桃红色
            [0.50, 0.60, 0.80, 1],   # 石板蓝色
            [0.70, 0.80, 0.20, 1],   # 查特酒绿
            [0.85, 0.45, 0.55, 1],   # 玫瑰色
            [0.25, 0.65, 0.30, 1],   # 森林绿
            [0.80, 0.70, 0.30, 1],   # 橄榄色
            [0.95, 0.20, 0.60, 1],   # 热粉色
            [0.10, 0.60, 0.70, 1],   # 青绿色
        ]
            # 添加“上一周”按钮
        btn_prev_week = Button(
            text='上一周',
            font_name=FONT_PATH,
                # 移除固定的字体大小设置
                # font_size=SPINNER_FONT_SIZE,
            size_hint=(0.2, 1),
            background_color=BUTTON_COLOR,
            color=BUTTON_TEXT_COLOR
        )
        btn_prev_week.bind(on_press=self.prev_week)
     
            # 修改spinner_week的size_hint以适应新增按钮
        self.spinner_week = Spinner(
            text=f'第{self.current_week}周 (当前周)',
            values=[f'第{week}周' + (' (当前周)' if week == self.current_week else '') for week in range(1, 21)],
            font_name=FONT_PATH,
                # 移除固定的字体大小设置
                # font_size=SPINNER_FONT_SIZE,
            size_hint=(0.6, 1),
            option_cls=CustomSpinnerOption
        )
            # 绑定spinner_week的文本变化事件，自动查询
        self.spinner_week.bind(text=self.query_schedule)

            # 添加“下一周”按钮
        btn_next_week = Button(
            text='下一周',
            font_name=FONT_PATH,
                # 移除固定的字体大小设置
                # font_size=SPINNER_FONT_SIZE,
            size_hint=(0.2, 1),
            background_color=BUTTON_COLOR,
            color=BUTTON_TEXT_COLOR
        )
        btn_next_week.bind(on_press=self.next_week)

        query_layout.add_widget(btn_prev_week)
        query_layout.add_widget(self.spinner_week)
        query_layout.add_widget(btn_next_week)

        self.label = Label(
            text='请选择学期并查询',
            font_name=FONT_PATH,
            font_size=LABEL_FONT_SIZE,
            color=LABEL_TEXT_COLOR_DARK,
            size_hint=(1, 0.1),
            halign='center',
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))

        layout.add_widget(query_layout)
        
        scroll_view = LimitedScrollView(size_hint=(1, 0.8))
        self.table_layout = GridLayout(
            cols=8, 
            rows=13, 
            size_hint_y=None, 
            padding=10, 
            spacing=2
        )
        self.table_layout.bind(minimum_height=self.table_layout.setter('height'))

        # 设置最小单元格高度
        self.min_cell_height = 480  # 新增最小高度

        # 获取当前周的日期
        current_week_dates = self.get_week_dates(self.current_week)
        headers = ['时间/星期']
        for day in self.days:
            date_str = current_week_dates.get(day, '')
            headers.append(f'{day}\n{date_str}')

        # 初始化标题行并保存引用
        self.header_widgets = []  # 保存标题标签的列表
        for col, header in enumerate(headers):
            header_label = BorderedLabel(
                text=f'[b]{header}[/b]',
                font_name=FONT_PATH,
                color=LABEL_TEXT_COLOR_DARK,
                background_color=SECONDARY_COLOR,  # 指定初始背景颜色
                size_hint=(1, None),
                height=self.calculate_cell_height(),
                markup=True,
                halign='center',
                valign='middle',
                row=0,
                col=col
            )
            self.table_layout.add_widget(header_label)
            self.header_widgets.append(header_label)  # 保存标题标签引用

        courge_time = [
            '08:30\n09:15','09:20\n10:05','10:20\n11:05','11:10\n11:55',
            '14:30\n15:15','15:20\n16:05','16:20\n17:05','17:10\n17:55',
            '19:30\n20:15','20:20\n21:05','21:10\n21:55','22:00\n22:45'
        ]
                
        # 修改第一列的创建方式，指定初始背景颜色
        for row in range(1, 13):
            # 创建第一列的时间标签，添加文本大小自适应和换行
            time_label = BorderedLabel(
                text=f'第{row}节\n{courge_time[row-1]}',
                font_name=FONT_PATH,
                color=LABEL_TEXT_COLOR_DARK,
                background_color=SECONDARY_COLOR,  # 指定初始背景颜色
                size_hint=(1, None),
                height=self.calculate_cell_height(),
                halign='center',
                valign='middle',
                text_size=(Window.width * 0.06, None),  # 增加文本宽度比例
                padding=(2, 2),  # 添加内边距
                row=row,
                col=0
            )
            time_label.bind(
                width=lambda lb, w: setattr(lb, 'text_size', (lb.width, None)),
                height=lambda lb, h: self.adjust_time_label_font(lb)
            )
            self.table_layout.add_widget(time_label)
                    
            for col in range(1, 8): 
                self.table_layout.add_widget(BorderedLabel(
                    text='',
                    font_name=FONT_PATH,
                    color=LABEL_TEXT_COLOR_DARK,
                    background_color=SECONDARY_COLOR,  # 指定初始背景颜色
                    size_hint=(1, None),
                    height=self.calculate_cell_height(),
                    halign='center',
                    valign='middle',
                    row=row,
                    col=col
                ))
        
        scroll_view.add_widget(self.table_layout)
        layout.add_widget(scroll_view)
        self.add_widget(layout)
                
        self.query_schedule(None)

    def operate_data(self):
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            username = credentials.get('username', '')
            current_week = credentials.get('currentweek','')
            update_week = credentials.get('update_week','')
        
        if int(time.strftime('%W')) - int(update_week) > 0:
            current_week = get_current_week()
            credentials['currentweek'] = current_week
            credentials['update_week'] = time.strftime('%W')
            with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=4)
        
        self.current_week = current_week
        self.outstanding_current_week = current_week
        
        with open('./data/course.json', 'r', encoding='utf-8') as f:
            if f.read() == '':
                course_data = get_course_schedule(username)
                course_data.append({'username': username, 'update_time': time.time()})
                with open('./data/course.json', 'w', encoding='utf-8') as f_write:
                    json.dump(course_data, f_write, ensure_ascii=False, indent=4)
            else:
                f.seek(0)
                course_data = json.load(f)
                if not course_data or course_data[-1]['username'] != username or time.time() - course_data[-1]['update_time'] > 86400:
                    course_data = get_course_schedule(username)
                    course_data.append({'username': username, 'update_time': time.time()})
                    with open('./data/course.json', 'w', encoding='utf-8') as f_write:
                        json.dump(course_data, f_write, ensure_ascii=False, indent=4)
                    
        self.course_list = []
        with open('./data/course_details.json', 'r', encoding='utf-8') as f:
            if f.read() == '':
                course_details = {}
                course_details['update_time'] = 0
                course_details['username'] = username
            else:
                f.seek(0)
                course_details = json.load(f)
                if 'username' not in course_details:
                    course_details['username'] = ''
                elif 'usename' != course_details['username']:
                    course_details.clear()
                    course_details['username'] = ''
                if 'update_time' not in course_details:
                    course_details['update_time'] = 0
        course_data.pop(-1)
        self.course_data = course_data
        for course in course_data:
            course['c_name'] = course['c_name'].replace(' ', '').replace('Ⅱ', 'II').replace('Ⅰ', 'I').replace('Ⅲ', 'III').replace('–', '-')
            if time.time() - course_details['update_time'] > 86400 or course_details['username'] != username:
                if course['c_name'] not in course_details:
                    course_details[course['c_name']] = {}
                    course_details[course['c_name']]['detail'] =(
                        f'地点: {course["school"]}{course["room_name"]}\n'
                        f'教师: {course["teacher"]}\n上课周: '
                    )
                    course_details[course['c_name']]['rq'] = course['rq']
                else:
                    rq = ''
                    course_details[course['c_name']]['detail'] =(
                        f'地点: {course["school"]}{course["room_name"]}\n'
                        f'教师: {course["teacher"]}\n上课周: '
                    )
                    for i in range(len(course['rq'])):
                        if course['rq'][i] == '1' or course_details[course['c_name']]['rq'][i] == '1':
                            rq += '1'
                        else:
                            rq += '0'
                    course_details[course['c_name']]['rq'] = rq
                
            if course['c_name'] not in self.course_list:
                self.course_list.append(course['c_name'])
            if current_week < len(course['rq']) and course['rq'][current_week] == '1':  # 使用整数周数
                xqj = self.days[int(course['xqj']) - 1]
                ksjc = int(course['ksjc'])
                jsjc = int(course['jsjc'])
                for i in range(ksjc, jsjc + 1):
                    self.sample_schedule[xqj][i - 1] = self.coursename_add(course['c_name']) + '\n \n' + self.coursename_add(course['room_name'])

        for course in self.course_list:
            start = 0
            for i in range(1,len(course_details[course]['rq'])):
                if course_details[course]['rq'][i] == '1' and course_details[course]['rq'][start] == '1':
                    continue
                elif course_details[course]['rq'][i] == '1' and course_details[course]['rq'][start] == '0':
                    start = i
                    if '周\n' in course_details[course]['detail']:
                        course_details[course]['detail'] += ','
                    course_details[course]['detail'] += f'第{start}'
                elif course_details[course]['rq'][i] == '0' and course_details[course]['rq'][start] == '1':
                    if start != i - 1:
                        course_details[course]['detail'] += f'-{i - 1}周\n'
                    else:
                        course_details[course]['detail'] += f'周\n'
                    start = i
            if course_details[course]['rq'].endswith('1'):
                course_details[course]['detail'] += f'第{start}-{len(course_details[course]["rq"])}周\n'
        
        if time.time() - course_details['update_time']  > 86400 or username != course_details['username']:
            course_details['update_time'] = time.time()
            course_details['username'] = username
            with open('./data/course_details.json', 'w', encoding='utf-8') as f:
                json.dump(course_details, f, ensure_ascii=False, indent=4)
        
    
    def rebuild(self):
        self.operate_data()
        self.query_schedule(None)
    
    def prev_week(self, instance):
        if self.outstanding_current_week > 1:
            self.outstanding_current_week -= 1
            self.update_week()
            
    def next_week(self, instance):
        if self.outstanding_current_week < 20:
            self.outstanding_current_week += 1
            self.update_week()
            
    def update_week(self):
        # 更新spinner_week的文本
        self.spinner_week.text = f'第{self.outstanding_current_week}周'
        # 更新spinner_week的值列表
        self.spinner_week.values = [f'第{week}周' + (' (当前周)' if week == self.current_week else '') for week in range(1, 21)]
        # 调用查询方法刷新表格
        self.query_schedule(None)

    def get_week_dates(self, week_number):
        """获取指定周数每一天的日期，格式为MM月DD日"""
        today = datetime.date.today()
        current_week_number = self.current_week
        # 计算目标周与当前周的差值
        week_diff = week_number - current_week_number
        # 获取当前周的星期一
        start_of_current_week = today - datetime.timedelta(days=today.weekday())
        # 计算目标周的星期一
        target_start_of_week = start_of_current_week + datetime.timedelta(weeks=week_diff)
        week_dates = {}
        for i, day in enumerate(['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']):
            current_day = target_start_of_week + datetime.timedelta(days=i)
            date_str = current_day.strftime('%m月%d日')
            week_dates[day] = date_str
        return week_dates
            
    def calculate_cell_height(self):
        # 增加单元格高度比例
        table_height = Window.height * 0.9  # 从0.8增加到0.9
        cell_height = max(table_height / 13, self.min_cell_height)  # 使用最小高度
        return cell_height

    def update_cell_font_size(self, widget):
        # 已移除固定字体大小设置
        if not widget.text:
            return
        lines = len(widget.text.split('\n'))
        if widget.text.startswith('第') or widget.text == '时间/星期':
            widget.font_size = widget.height * 0.2 if lines > 1 else widget.height * 0.3
        else:
            widget.font_size = widget.height * 0.25 if lines > 1 else widget.height * 0.4

    def adjust_time_label_font(self, label):
        """调整时间标签的字体大小"""
        # 计算文本行数
        lines = len(label.text.split('\n'))
        # 根据行数和单元格高度计算合适的字体大小
        max_font_size = label.height * 0.2  # 最大字体大小为单元格高度的20%
        label.font_size = min(max_font_size, label.height / (lines * 1.5))

    def on_window_resize(self, instance, size):
        new_height = self.calculate_cell_height()
        for widget in self.table_layout.children[:]:
            if isinstance(widget, BorderedLabel):
                widget.height = new_height
                # 更新第一列的文本宽度
                if '第' in widget.text and '\n' in widget.text:
                    widget.text_size = (Window.width * 0.06, None)  # 调整为一致的宽度比例
                    self.adjust_time_label_font(widget)
                else:
                    self.update_cell_font_size(widget)

    def query_schedule(self, instance, value=None):
            selected_week = self.spinner_week.text
            # 提取周数
            match = re.search(r'\d+', selected_week)
            if match:
                week_number = int(match.group())
                self.outstanding_current_week = week_number
                # 使用 Clock.schedule_once 确保在主线程中执行动画
                Clock.schedule_once(lambda dt: self.populate_table(week_number))
    
    def coursename_add(self, coursename):
        coursename = [coursename[i:i+4] for i in range(0, len(coursename), 4)]
        # 使用换行符连接这些组
        return '\n'.join(coursename)
    
    def populate_table(self, week):
        # 获取指定周的日期
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            update_week = credentials.get('update_week','')
        
        if int(time.strftime('%W')) - int(update_week) > 0:
            current_week = get_current_week()
            self.current_week = current_week
            credentials['currentweek'] = current_week
            credentials['update_week'] = time.strftime('%W')
            with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=4)
        
        week_dates = self.get_week_dates(week)
        
        # 更新标题行的文本
        headers = ['时间/星期']
        for day in ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']:
            date_str = week_dates.get(day, '')
            headers.append(f'{day}\n{date_str}')
        
        for header_widget, header_text in zip(self.header_widgets, headers):
            header_widget.text = f'[b]{header_text}[/b]'
        
        # 清空现有内容和样式，仅重置课程单元格
        for widget in self.table_layout.children:
            if isinstance(widget, BorderedLabel):
                if widget.row != 0 and widget.col != 0:
                    widget.text = ''
                    widget.background_color = widget.initial_background_color  # 使用初始化的颜色
                    widget.update_background_color(widget, widget.background_color)  # 调用更新方法
        
        self.sample_schedule = {day: [''] * 12 for day in self.days}
        for course in self.course_data:
            if week < len(course['rq']) and course['rq'][week] == '1':  # 使用整数周数
                xqj = self.days[int(course['xqj']) - 1]
                ksjc = int(course['ksjc'])
                jsjc = int(course['jsjc'])
                for i in range(ksjc, jsjc + 1):
                    self.sample_schedule[xqj][i - 1] = self.coursename_add(course['c_name']) + '\n \n' + self.coursename_add(course['room_name'])
        
        # 填充课程信息
        
        for day_index, day in enumerate(self.days, 1):
            courses = self.sample_schedule.get(day, [])
            for period_index, course in enumerate(courses, 1):
                if course:
                    course_name = ''.join(course.split(' ')[0].split('\n')[0:-1])
                    widget_position = (12 - period_index) * 8 + (7 - day_index)
                    if widget_position < len(self.table_layout.children):
                        target_widget = self.table_layout.children[widget_position]
                        if target_widget.row != 0 and target_widget.col != 0:
                            target_widget.text = course
                            # 设置背景颜色并添加多层渐变效果
                            target_widget.background_color = self.color_list[self.course_list.index(course_name) % len(self.color_list)]
                            
class GradesScreen(Screen):
    def __init__(self, **kwargs):
        super(GradesScreen, self).__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', bg_color=SECONDARY_COLOR)
        self.label = Label(
            text='成绩查询界面',
            font_name=FONT_PATH,
            font_size=LABEL_FONT_SIZE,
            color=LABEL_TEXT_COLOR_DARK,
            halign='center',
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))
        layout.add_widget(self.label)
        self.add_widget(layout)

class NotificationsScreen(Screen):
    def __init__(self, **kwargs):
        super(NotificationsScreen, self).__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', bg_color=SECONDARY_COLOR)
        self.label = Label(
            text='通知中心',
            font_name=FONT_PATH,
            font_size=LABEL_FONT_SIZE,
            color=LABEL_TEXT_COLOR_DARK,
            halign='center',
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))
        layout.add_widget(self.label)
        self.add_widget(layout)


class SettingsScreen(Screen):
        def __init__(self, **kwargs):
            super(SettingsScreen, self).__init__(**kwargs)
            layout = ColoredBoxLayout(orientation='vertical', bg_color=SECONDARY_COLOR)
                
            self.loading_popup = CustomPopup(
                title_text='保存中...',
                content_widget=Label(
                    text='请稍候...',
                    font_name=FONT_PATH,
                    font_size=POPUP_CONTENT_FONT_SIZE,
                    halign='center',
                    valign='middle'
                ),
                size_hint=(0.3, 0.3),
                auto_dismiss=False
            )
            self.username_input = TextInput(
                hint_text='用户名',
                font_name=FONT_PATH,
                font_size=BASE_FONT_SIZE,  # 保持初始字体大小
                background_color=INPUT_BACKGROUND_COLOR,
                foreground_color=INPUT_TEXT_COLOR,
                size_hint=(1, 0.1)
            )
            self.password_input = TextInput(
                hint_text='密码',
                font_name=FONT_PATH,
                font_size=BASE_FONT_SIZE,  # 保持初始字体大小
                background_color=INPUT_BACKGROUND_COLOR,
                foreground_color=INPUT_TEXT_COLOR,
                password=True,
                size_hint=(1, 0.1)
            )
            save_btn = Button(
                text='保存',
                font_name=FONT_PATH,
                font_size=BUTTON_FONT_SIZE,  # 保持初始字体大小
                background_color=BUTTON_COLOR,
                color=BUTTON_TEXT_COLOR,
                size_hint=(1, 0.1)
            )
            save_btn.bind(on_press=self.save_credentials)
            self.save_btn = save_btn  # 保存按钮引用以便动画使用

            self.status_label = Label(
                text='',
                font_name=FONT_PATH,
                font_size=LABEL_FONT_SIZE,  # 保持初始字体大小
                color=LABEL_TEXT_COLOR_DARK,
                size_hint=(1, 0.1),
                halign='center',
                valign='middle'
            )
            self.status_label.bind(size=self.status_label.setter('text_size'))

            layout.add_widget(Label(
                text='设置界面',
                font_name=FONT_PATH,
                font_size=LABEL_FONT_SIZE,  # 保持初始字体大小
                color=LABEL_TEXT_COLOR_DARK,
                size_hint=(1, 0.1),
                halign='center',
                valign='middle'
            ))
            layout.add_widget(self.username_input)
            layout.add_widget(self.password_input)
            layout.add_widget(save_btn)
            layout.add_widget(self.status_label)
                
            self.add_widget(layout)
            self.load_credentials()

        def save_credentials(self, instance):
                # 显示加载弹窗
            self.loading_popup.open()
            self.save_btn.disabled = True

            # 在线程中执行保存操作
            threading.Thread(target=self._save_credentials_thread, daemon=True).start()
            
        def _save_credentials_thread(self):
            try:
                username = self.username_input.text
                password = self.password_input.text
                credentials = {'username': username,
                               'password': password,
                               'currentweek':get_current_week(),
                               'update_week':time.strftime('%W')
                               }
                    
                with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(credentials, f, ensure_ascii=False, indent=4)
                status_text = '账号和密码已保存'
                    
                app = App.get_running_app()
                schedule_screen = app.sm.get_screen('schedule')
                    
                # 重新初始化 ScheduleScreen
                def reinitialize_schedule_screen(dt):
                    schedule_screen.rebuild()
                    self.status_label.text = status_text
                    self.loading_popup.dismiss()
                    self.save_btn.disabled = False
                    # 不调用 update_font_sizes，以保持设置界面的字体大小不变
                
                Clock.schedule_once(reinitialize_schedule_screen)
            except Exception as e:
                status_text = f'保存失败: {e}'
                    
                def update_ui_error(dt):
                    self.status_label.text = status_text
                    # 关闭加载弹窗并恢复按钮状态
                    self.loading_popup.dismiss()
                    self.save_btn.disabled = False
                    
                Clock.schedule_once(update_ui_error)

        def _update_ui_after_save(self, status_text):
            self.status_label.text = status_text
            # 关闭加载弹窗并恢复按钮状态
            self.loading_popup.dismiss()
            self.save_btn.disabled = False
        
        def load_credentials(self):
            if os.path.exists(CREDENTIALS_FILE):
                try:
                    with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                        credentials = json.load(f)
                    self.username_input.text = credentials.get('username', '')
                    self.password_input.text = credentials.get('password', '')
                    
                except Exception as e:
                    self.status_label.text = f'加载失败: {e}'
                    
class ScheduleApp(App):
    screens_order = ['schedule', 'grades', 'notifications', 'settings']

    def build(self):
        Window.bind(size=self.on_window_resize)
        
        # 使用自定义的SwipeScreenManager
        self.sm = SwipeScreenManager(transition=SlideTransition())
        self.sm.bind(current=self.on_screen_change)
        # 定义所有页面及其顺序
        screens = [
            ('schedule', ScheduleScreen),
            ('grades', GradesScreen),
            ('notifications', NotificationsScreen), 
            ('settings', SettingsScreen)
        ]

        # 添加所有页面
        for name, screen_class in screens:
            self.sm.add_widget(screen_class(name=name))
        
        # 初始化 current_index
        self.current_index = 0  # 总是从第一个页面开始

        # 创建导航栏按钮
        nav_layout = ColoredBoxLayout(orientation='horizontal', size_hint=(1, 0.1), bg_color=PRIMARY_COLOR)
        
        # 修改导航按钮点击事件
        btn_schedule = Button(
            text='课表',
            font_name=FONT_PATH,
            background_color=BUTTON_COLOR,
            color=BUTTON_TEXT_COLOR,
            on_press=lambda x: self.switch_screen(0, 'schedule')
        )
        btn_grades = Button(
            text='成绩',
            font_name=FONT_PATH,
            background_color=BUTTON_COLOR,
            color=BUTTON_TEXT_COLOR,
            on_press=lambda x: self.switch_screen(1, 'grades')
        )
        btn_notifications = Button(
            text='通知',
            font_name=FONT_PATH,
            background_color=BUTTON_COLOR,
            color=BUTTON_TEXT_COLOR,
            on_press=lambda x: self.switch_screen(2, 'notifications')
        )
        btn_settings = Button(
            text='设置',
            font_name=FONT_PATH,
            background_color=BUTTON_COLOR,
            color=BUTTON_TEXT_COLOR,
            on_press=lambda x: self.switch_screen(3, 'settings')
        )

        nav_layout.add_widget(btn_schedule)
        nav_layout.add_widget(btn_grades)
        nav_layout.add_widget(btn_notifications)
        nav_layout.add_widget(btn_settings)
        
        main_layout = ColoredBoxLayout(orientation='vertical', bg_color=PRIMARY_COLOR)
        main_layout.add_widget(self.sm)
        main_layout.add_widget(nav_layout)

        # 延迟调用 update_font_sizes 以确保所有组件已加载
        Clock.schedule_once(lambda dt: self.update_font_sizes(), 0.1)

        return main_layout

    def switch_screen(self, index, screen_name):
        if index == self.current_index:
            return
        # 根据目标索引设置方向
        self.sm.transition.direction = 'left' if index > self.current_index else 'right'
        self.sm.current = screen_name

    def on_screen_change(self, instance, value):
        try:
            self.current_index = self.screens_order.index(value)
        except ValueError:
            self.current_index = 0

    def on_window_resize(self, instance, size):
        # 延迟更新字体大小,避免过于频繁刷新
        Clock.schedule_once(lambda dt: self.update_font_sizes(), 0.1)
    
    def update_font_sizes(self):
        font_sizes = FontScaler.get_font_sizes()
        
        # 更新需要的组件
        for widget in self.walk_widgets():
            if isinstance(widget, Label):
                widget.font_size = font_sizes['label']
            elif isinstance(widget, Button):
                widget.font_size = font_sizes['button']
            elif isinstance(widget, Spinner):
                widget.font_size = font_sizes['spinner']
            elif isinstance(widget, TextInput):
                widget.font_size = font_sizes['base']

    def walk_widgets(self):
        """辅助方法，遍历所有子组件"""
        for widget in self.root.walk():
            yield widget

if __name__ == '__main__':
    ScheduleApp().run()