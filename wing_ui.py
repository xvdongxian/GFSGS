# -*- coding: utf-8 -*-
"""
羽毛绑定工具UI
根据导入的定位器自动识别左右方向
"""

import maya.cmds as cmds
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# 导入你的模块
from WingRigTool import wing_rig
from WingRigTool import wing_loc
from WingRigTool import wing_sdk


class FeatherRigUI(QWidget):
    def __init__(self, parent=None):
        super(FeatherRigUI, self).__init__(parent)
        
        self.setObjectName("FeatherRigUI")
        self.setWindowTitle("Wing_Rig_Tool")
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
        self.setMinimumHeight(580)
        
        # 设置窗口属性
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        
        # 初始化变量
        self.wing_joints = []
        self.base_joint = ""
        self.current_side = "l_"
        self.root_joint = ""
        
        # 配色方案
        self.setStyleSheet("""
            QWidget {
                background-color: #2B2B2B;
                color: #E0E0E0;
                font-family: "Microsoft YaHei";
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
            QLineEdit {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px;
                color: #E0E0E0;
            }
            QLineEdit:read-only {
                background-color: #333333;
                color: #999999;
            }
            QListWidget {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                border-radius: 3px;
                color: #E0E0E0;
            }
            QListWidget::item:selected {
                background-color: #555555;
                color: #FFFFFF;
            }
            QListWidget::item:hover {
                background-color: #4A4A4A;
            }
            QComboBox {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px;
                color: #E0E0E0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A;
                color: #E0E0E0;
                selection-background-color: #555555;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px;
                color: #E0E0E0;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                border: none;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                border: none;
            }
            QCheckBox {
                color: #CCCCCC;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3A3A3A;
                border: 1px solid #666666;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #666666;
                border: 1px solid #888888;
                border-radius: 2px;
            }
            QGroupBox {
                color: #CCCCCC;
            }
            
            /* 基础灰色按钮 */
            QPushButton {
                background-color: #4A4A4A;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 5px 10px;
                color: #E0E0E0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
                border: 1px solid #888888;
            }
            QPushButton:pressed {
                background-color: #3A3A3A;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
            
            /* ===== 灰蓝 - 导入定位器 ===== */
            #importBtn {
                background-color: #4A5A6A;
                border: 1px solid #5A6A7A;
            }
            #importBtn:hover {
                background-color: #5A6A7A;
            }
            #importBtn:pressed {
                background-color: #3A4A5A;
            }
            
            /* ===== 灰蓝 - 创建翅膀骨骼 ===== */
            #skelBtn {
                background-color: #4A5A6A;
                border: 1px solid #5A6A7A;
            }
            #skelBtn:hover {
                background-color: #5A6A7A;
            }
            #skelBtn:pressed {
                background-color: #3A4A5A;
            }
            
            /* ===== 灰蓝 - 创建羽毛骨骼 ===== */
            #featherBtn {
                background-color: #4A5A6A;
                border: 1px solid #5A6A7A;
            }
            #featherBtn:hover {
                background-color: #5A6A7A;
            }
            #featherBtn:pressed {
                background-color: #3A4A5A;
            }
            
            /* ===== 灰黄 - 创建绑定 ===== */
            #buildBtn {
                background-color: #6A6A4A;
                border: 1px solid #7A7A5A;
                font-size: 14px;
                padding: 10px;
            }
            #buildBtn:hover {
                background-color: #7A7A5A;
                border: 1px solid #8A8A6A;
            }
            #buildBtn:pressed {
                background-color: #5A5A3A;
            }
            #buildBtn:disabled {
                background-color: #555555;
                color: #888888;
                border: 1px solid #666666;
            }
            
            /* ===== 灰蓝 - 创建驱动组 ===== */
            #sdkBtn {
                background-color: #4A5A6A;
                border: 1px solid #5A6A7A;
            }
            #sdkBtn:hover {
                background-color: #5A6A7A;
            }
            #sdkBtn:pressed {
                background-color: #3A4A5A;
            }
            
            /* ===== 灰红 - 编辑驱动 ===== */
            #editBtn {
                background-color: #6A4A4A;
                border: 1px solid #7A5A5A;
            }
            #editBtn:hover {
                background-color: #7A5A5A;
            }
            #editBtn:pressed {
                background-color: #5A3A3A;
            }
            
            /* ===== 灰绿 - 镜像驱动值 L→R 和 R→L ===== */
            #mirrorBtn {
                background-color: #4A6A5A;
                border: 1px solid #5A7A6A;
            }
            #mirrorBtn:hover {
                background-color: #5A7A6A;
            }
            #mirrorBtn:pressed {
                background-color: #3A5A4A;
            }
            
            /* ===== 灰蓝 - 设置驱动 ===== */
            #getCtrlBtn {
                background-color: #4A5A6A;
                border: 1px solid #5A6A7A;
            }
            #getCtrlBtn:hover {
                background-color: #5A6A7A;
            }
            #getCtrlBtn:pressed {
                background-color: #3A4A5A;
            }
            
            /* ===== 灰蓝 - 加载父对象 ===== */
            #baseBtn {
                background-color: #4A5A6A;
                border: 1px solid #5A6A7A;
            }
            #baseBtn:hover {
                background-color: #5A6A7A;
            }
            #baseBtn:pressed {
                background-color: #3A4A5A;
            }
            
            /* ===== 灰绿 - 使用说明按钮（居中，宽度与创建绑定一致） ===== */
            #helpBtn {
                background-color: #4A6A5A;
                border: 1px solid #5A7A6A;
                color: #E0E0E0;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 3px;
            }
            #helpBtn:hover {
                background-color: #5A7A6A;
            }
            #helpBtn:pressed {
                background-color: #3A5A4A;
            }
        """)
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """创建UI界面"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== 标题（使用说明按钮居中，宽度与创建绑定一致） =====
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧弹性空间
        title_layout.addStretch()
        
        # 使用说明按钮 - 固定宽度，与创建绑定按钮宽度一致
        self.help_btn = QPushButton("使用说明")
        self.help_btn.setObjectName("helpBtn")
        self.help_btn.setFixedWidth(300)  # 与创建绑定按钮宽度一致
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.setToolTip("查看使用说明")
        title_layout.addWidget(self.help_btn)
        
        # 右侧弹性空间
        title_layout.addStretch()
        
        main_layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #555555;")
        main_layout.addWidget(line)
        
        # ===== 骨骼设置 =====
        bone_group = QGroupBox("骨骼设置")
        bone_layout = QVBoxLayout()
        bone_layout.setSpacing(6)
        
        # 第1行：导入定位器 + 左翼/右翼下拉
        loc_layout = QHBoxLayout()
        self.import_loc_btn = QPushButton("导入定位器")
        self.import_loc_btn.setObjectName("importBtn")
        self.import_loc_btn.setFixedWidth(120)
        loc_layout.addWidget(self.import_loc_btn)
        loc_layout.addStretch()
        self.loc_side_combo = QComboBox()
        self.loc_side_combo.addItems(["左 (l_)", "右 (r_)"])
        self.loc_side_combo.setCurrentIndex(0)
        self.loc_side_combo.setFixedWidth(60)
        loc_layout.addWidget(self.loc_side_combo)
        bone_layout.addLayout(loc_layout)
        
        # 第2行：创建翅膀骨骼（靠左）
        skel_layout = QHBoxLayout()
        self.create_skel_btn = QPushButton("创建翅膀骨骼")
        self.create_skel_btn.setObjectName("skelBtn")
        self.create_skel_btn.setFixedWidth(120)
        skel_layout.addWidget(self.create_skel_btn)
        skel_layout.addStretch()
        bone_layout.addLayout(skel_layout)
        
        # 第3行：创建羽毛骨骼 + 数量
        feather_layout = QHBoxLayout()
        self.create_feather_btn = QPushButton("创建羽毛骨骼")
        self.create_feather_btn.setObjectName("featherBtn")
        self.create_feather_btn.setFixedWidth(120)
        feather_layout.addWidget(self.create_feather_btn)
        feather_layout.addStretch()
        feather_layout.addWidget(QLabel("数量:"))
        self.feather_num_spin = QSpinBox()
        self.feather_num_spin.setRange(3, 30)
        self.feather_num_spin.setValue(10)
        self.feather_num_spin.setFixedWidth(45)
        self.feather_num_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        feather_layout.addWidget(self.feather_num_spin)
        bone_layout.addLayout(feather_layout)
        
        # 第4行：加载父对象
        base_layout = QHBoxLayout()
        self.base_btn = QPushButton("加载父对象")
        self.base_btn.setObjectName("baseBtn")
        self.base_btn.setFixedWidth(120)
        base_layout.addWidget(self.base_btn)
        base_layout.addStretch()
        self.base_line = QLineEdit()
        self.base_line.setPlaceholderText("例如: chest")
        self.base_line.setFixedWidth(130)
        base_layout.addWidget(self.base_line)
        bone_layout.addLayout(base_layout)
        
        # 翅膀骨骼列表
        wing_label_layout = QHBoxLayout()
        wing_label_layout.addWidget(QLabel("羽毛骨骼列表:"))
        wing_label_layout.addStretch()
        self.wing_count_label = QLabel("0 个")
        self.wing_count_label.setStyleSheet("color: #999999; font-size: 10px;")
        wing_label_layout.addWidget(self.wing_count_label)
        bone_layout.addLayout(wing_label_layout)
        
        self.wing_list = QListWidget()
        self.wing_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.wing_list.setMinimumHeight(100)
        bone_layout.addWidget(self.wing_list)
        
        # 翅膀骨骼操作按钮
        wing_btn_layout = QHBoxLayout()
        self.load_wing_btn = QPushButton("加载")
        self.clear_wing_btn = QPushButton("清空")
        self.load_wing_btn.setStyleSheet("background-color: #4A4A4A; color: #E0E0E0;")
        self.clear_wing_btn.setStyleSheet("background-color: #4A4A4A; color: #E0E0E0;")
        wing_btn_layout.addWidget(self.load_wing_btn)
        wing_btn_layout.addWidget(self.clear_wing_btn)
        wing_btn_layout.addStretch()
        bone_layout.addLayout(wing_btn_layout)
        
        bone_group.setLayout(bone_layout)
        main_layout.addWidget(bone_group)
        
        # ===== 绑定参数 =====
        param_group = QGroupBox("绑定参数")
        param_layout = QGridLayout()
        param_layout.setVerticalSpacing(6)
        
        # 羽毛数量
        param_layout.addWidget(QLabel("羽毛骨骼数量:"), 0, 0)
        self.chiyu_spin = QSpinBox()
        self.chiyu_spin.setRange(2, 20)
        self.chiyu_spin.setValue(4)
        self.chiyu_spin.setFixedWidth(45)
        self.chiyu_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        param_layout.addWidget(self.chiyu_spin, 0, 1)
        
        # 是否镜像（默认勾选）
        self.mirror_check = QCheckBox("创建镜像绑定")
        self.mirror_check.setChecked(True)
        param_layout.addWidget(self.mirror_check, 1, 0, 1, 2)
        
        # 是否创建动力学（默认不勾选）
        self.dyn_check = QCheckBox("创建动力学表达式 ")
        self.dyn_check.setChecked(False)
        param_layout.addWidget(self.dyn_check, 2, 0, 1, 2)
        
        param_group.setLayout(param_layout)
        main_layout.addWidget(param_group)
        
        # ===== 执行绑定 =====
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)
        
        self.build_btn = QPushButton("创建绑定")
        self.build_btn.setObjectName("buildBtn")
        self.build_btn.setFixedWidth(300)  # 固定宽度300
        btn_layout.addWidget(self.build_btn)
        
        main_layout.addLayout(btn_layout)
        
        # ===== SDL驱动控制 =====
        sdk_group = QGroupBox("SDK驱动收翅控制(驱动物体为l/r_writs_Con)")
        sdk_layout = QGridLayout()
        sdk_layout.setVerticalSpacing(6)
        
        # 第1行：创建驱动组 + 编辑驱动
        self.create_sdk_btn = QPushButton("创建驱动组")
        self.create_sdk_btn.setObjectName("sdkBtn")
        sdk_layout.addWidget(self.create_sdk_btn, 0, 0)
        
        self.edit_sdk_btn = QPushButton("编辑驱动")
        self.edit_sdk_btn.setObjectName("editBtn")
        sdk_layout.addWidget(self.edit_sdk_btn, 0, 1)
        
        # 第2行：镜像驱动值 (L→R) + 镜像驱动值 (R→L)
        self.mirror_sdk_btn = QPushButton("镜像驱动值 (L→R)")
        self.mirror_sdk_btn.setObjectName("mirrorBtn")
        sdk_layout.addWidget(self.mirror_sdk_btn, 1, 0)
        
        self.mirror_sdk_btn_r = QPushButton("镜像驱动值 (R→L)")
        self.mirror_sdk_btn_r.setObjectName("mirrorBtn")
        sdk_layout.addWidget(self.mirror_sdk_btn_r, 1, 1)
        
        # 第3行：设置驱动（独占一行）
        self.get_ctrl_btn = QPushButton("设置驱动")
        self.get_ctrl_btn.setObjectName("getCtrlBtn")
        sdk_layout.addWidget(self.get_ctrl_btn, 2, 0, 1, 2)
        
        sdk_group.setLayout(sdk_layout)
        main_layout.addWidget(sdk_group)
        
        self.setLayout(main_layout)
        
    def connect_signals(self):
        """连接信号与槽"""
        # 定位器与骨骼创建
        self.import_loc_btn.clicked.connect(self.import_locators)
        self.create_skel_btn.clicked.connect(self.create_skeleton)
        self.create_feather_btn.clicked.connect(self.create_feather_skeleton)
        
        # 骨骼设置
        self.base_btn.clicked.connect(self.load_base_joint)
        self.load_wing_btn.clicked.connect(self.load_wing_joints)
        self.clear_wing_btn.clicked.connect(self.clear_wing_joints)
        
        # 绑定
        self.build_btn.clicked.connect(self.build_rig)
        
        # SDL驱动控制
        self.create_sdk_btn.clicked.connect(self.create_sdk_group)
        self.get_ctrl_btn.clicked.connect(self.get_ctrl_transform)
        self.mirror_sdk_btn.clicked.connect(lambda: self.mirror_driven_values('l'))
        self.mirror_sdk_btn_r.clicked.connect(lambda: self.mirror_driven_values('r'))
        self.edit_sdk_btn.clicked.connect(self.edit_driven)
        
        # 帮助按钮
        self.help_btn.clicked.connect(self.show_help)
        
        # 更新信息
        self.base_line.textChanged.connect(self.update_info)
        self.wing_list.model().rowsInserted.connect(self.update_info)
        self.wing_list.model().rowsRemoved.connect(self.update_info)
        
    def show_help(self):
        """显示帮助文档"""
        help_text = """
<h2 style="color:#E0E0E0; margin-bottom:10px;">使用说明</h2>
</p>
<h3 style="color:#CCCCCC; margin-top:10px; margin-bottom:5px;">一、骨骼创建</h3>
</p>
<p style="color:#AAAAAA; margin:3px 0;">
<b>1. 导入左侧或者右侧定位器，匹配定位器位置</b><br>

</p>
<p style="color:#AAAAAA; margin:3px 0;">
<b>2. 创建翅膀骨骼，然后创建羽毛骨骼(自行创建骨骼可以忽略)</b><br>


</p>
<p style="color:#AAAAAA; margin:3px 0;">
<b>3. 加载父对象和羽毛骨骼（自动创建的羽毛骨骼会自动载入，手动创建的需要手动载入）</b><br>


</p>


<h3 style="color:#CCCCCC; margin-top:10px; margin-bottom:5px;">二、绑定参数</h3>
</p>
<p style="color:#AAAAAA; margin:3px 0;">
<b>羽毛骨骼数：设置羽毛的骨骼段数。</b><br>

</p>
<p style="color:#AAAAAA; margin:3px 0;">
<b>创建镜像绑定：勾选后自动创建对称侧的绑定。</b><br>

</p>
<p style="color:#AAAAAA; margin:3px 0;">
<b>创建动力学表达式：勾选后添加风力/飘动的动力学效果</b><br>

</p>

<h3 style="color:#CCCCCC; margin-top:10px; margin-bottom:5px;">三、执行绑定</h3>
<p style="color:#AAAAAA; margin:3px 0;">
完成所有设置后，点击<b style="color:#E0E0E0;">创建绑定</b>执行完整的羽毛绑定系统。
</p>

<h3 style="color:#CCCCCC; margin-top:10px; margin-bottom:5px;">四、SDL驱动控制</h3>
<p style="color:#AAAAAA; margin:3px 0;">
<b>创建驱动：首先创建驱动组,然后直接用控制器去调整收翅的pose,然后镜像一下驱动值,最后设置驱动即可(驱动控制器属性为l/r_wrist_Con.wing_close)</b><br>

</p>
<p style="color:#AAAAAA; margin:3px 0;">
<b>编辑驱动: 会回退到控制器的pose,此时调整完pose后,镜像驱动值,再设置驱动即可</b><br>






</p>
        """
        
        # 创建帮助对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("使用说明")
        dialog.setMinimumWidth(380)
        dialog.setMinimumHeight(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
            }
            QScrollArea {
                background-color: #2B2B2B;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #3A3A3A;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 布局
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #2B2B2B; border: none;")
        
        # 内容容器
        content = QWidget()
        content.setStyleSheet("background-color: #2B2B2B;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 文本标签
        label = QLabel(help_text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                background-color: transparent;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        content_layout.addWidget(label)
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A4A4A;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 8px;
                color: #E0E0E0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def get_loc_side(self):
        """获取定位器侧标识"""
        return 'l_' if self.loc_side_combo.currentIndex() == 0 else 'r_'
    
    def get_side(self):
        """获取方向字符"""
        return 'l' if self.loc_side_combo.currentIndex() == 0 else 'r'
    
    def get_root_name(self):
        """获取根骨骼名称"""
        side = self.get_loc_side()
        return f"{side}scapula"
    
    # ===== 定位器与骨骼创建功能 =====
    
    def import_locators(self):
        """导入定位器"""
        side = self.get_loc_side()
        try:
            result = wing_loc.import_locators(side)
            if result:
                root_name = self.get_root_name()
                if cmds.objExists(root_name):
                    self.root_joint = root_name
                    self.current_side = side
                    print(f"✅ 成功导入 {side}定位器，已识别根骨骼: {root_name}")
                    self.auto_load_wing_joints()
                else:
                    print(f"⚠️ 导入成功，但未找到根骨骼 {root_name}")
            else:
                print("❌ 导入失败，请检查文件路径")
        except Exception as e:
            print(f"❌ 导入失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def create_skeleton(self):
        """创建主骨骼"""
        side = self.get_loc_side()
        try:
            result = wing_loc.create_wing_skeleton(side=side)
            if result:
                root_name = self.get_root_name()
                if cmds.objExists(root_name):
                    self.root_joint = root_name
                    self.current_side = side
                    print(f"✅ 成功创建主骨骼: {root_name}")
                    self.auto_load_wing_joints()
                else:
                    print("⚠️ 创建骨骼成功，但未找到根骨骼")
            else:
                print("❌ 创建骨骼失败")
        except Exception as e:
            print(f"❌ 创建失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def create_feather_skeleton(self):
        """创建羽毛骨骼"""
        side = self.get_loc_side()
        num_joints = self.feather_num_spin.value()
        try:
            result = wing_loc.create_wing_joints_and_aim(num_joints=num_joints, side=side)
            if result:
                print(f"✅ 成功创建 {num_joints} 个羽毛骨骼")
                self.auto_load_wing_joints()
            else:
                print("❌ 创建羽毛骨骼失败")
        except Exception as e:
            print(f"❌ 创建失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def auto_load_wing_joints(self):
        """自动加载翅膀骨骼（只识别 _0，排除 _1 和末端）"""
        side = self.get_loc_side()
        prefix = side
        
        all_joints = cmds.ls(type='joint')
        wing_joints = []
        for j in all_joints:
            if j.startswith(prefix) and 'wing' in j:
                if j.endswith('_0'):
                    wing_joints.append(j)
        
        if wing_joints:
            wing_joints.sort()
            self.wing_list.clear()
            self.wing_list.addItems(wing_joints)
            self.wing_joints = wing_joints
            self.update_info()
            print(f"✅ 自动加载 {len(wing_joints)} 个翅膀骨骼")
        else:
            print(f"⚠️ 未找到以 '{prefix}' 开头的翅膀骨骼 (_0)")
    
    # ===== SDL驱动控制功能 =====
    
    def create_sdk_group(self):
        """创建驱动组"""
        try:
            wing_sdk.create_sdk_group()
            print("✅ 成功创建驱动组")
        except Exception as e:
            print(f"❌ 创建驱动组失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def get_ctrl_transform(self):
        """设置控制器变换"""
        try:
            wing_sdk.get_ctrl_transform()
            print("✅ 成功设置控制器变换")
        except Exception as e:
            print(f"❌ 设置控制器变换失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def mirror_driven_values(self, source_side):
        """镜像驱动值"""
        try:
            wing_sdk.mirror_driven_values(source_side=source_side)
            target = '右' if source_side == 'l' else '左'
            print(f"✅ 成功镜像驱动值 {source_side.upper()}→{target}")
        except Exception as e:
            print(f"❌ 镜像驱动值失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def edit_driven(self):
        """编辑驱动"""
        try:
            wing_sdk.edit_driven()
            print("✅ 已进入驱动编辑模式")
        except Exception as e:
            print(f"❌ 编辑驱动失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # ===== 骨骼加载功能 =====
    
    def load_base_joint(self):
        """从选择加载基础骨骼"""
        sel = cmds.ls(sl=True, type='joint')
        if sel:
            self.base_line.setText(sel[0])
            print(f"✅ 已加载基础骨骼: {sel[0]}")
        else:
            print("⚠️ 请选择一个关节作为基础骨骼")
    
    def load_wing_joints(self):
        """从选择加载翅膀骨骼"""
        sel = cmds.ls(sl=True, type='joint')
        if sel:
            side = self.get_side()
            prefix = f"{side}_"
            filtered = [j for j in sel if j.startswith(prefix) and 'wing' in j and j.endswith('_0')]
            if filtered:
                self.wing_list.clear()
                self.wing_list.addItems(filtered)
                self.wing_joints = filtered
                self.update_info()
                print(f"✅ 已加载 {len(filtered)} 个翅膀骨骼")
            else:
                print(f"⚠️ 未找到符合条件的翅膀骨骼 (_0)")
        else:
            print("⚠️ 请选择翅膀骨骼")
    
    def clear_wing_joints(self):
        """清空翅膀骨骼列表"""
        self.wing_list.clear()
        self.wing_joints = []
        self.update_info()
        print("🗑 已清空翅膀骨骼列表")
    
    def update_info(self):
        """更新信息"""
        count = self.wing_list.count()
        self.wing_count_label.setText(f"{count} 个")
    
    def build_rig(self):
        """执行绑定"""
        root = self.root_joint
        base = self.base_line.text()
        chiyuNum = self.chiyu_spin.value()
        get_con_size = 1.0  # 固定为1
        do_mirror = self.mirror_check.isChecked()
        dynCrete = self.dyn_check.isChecked()
        
        if not root:
            print("❌ 请先导入定位器或创建骨骼")
            return
        if not base:
            print("❌ 请设置基础骨骼")
            return
        
        side = self.get_side()
        side_name = '左翼' if side == 'l' else '右翼'
        
        wing_joints = []
        for i in range(self.wing_list.count()):
            wing_joints.append(self.wing_list.item(i).text())
        
        if not wing_joints:
            print("❌ 请加载翅膀骨骼")
            return
        
        if not cmds.objExists(root):
            print(f"❌ 根骨骼不存在: {root}")
            return
        if not cmds.objExists(base):
            print(f"❌ 基础骨骼不存在: {base}")
            return
        
        missing = [j for j in wing_joints if not cmds.objExists(j)]
        if missing:
            print(f"❌ 以下骨骼不存在: {missing[:3]}...")
            return
        
        try:
            print(f"⏳ 正在执行绑定 ({side_name})，请稍候...")
            self.build_btn.setEnabled(False)
            QApplication.processEvents()
            
            result = wing_rig.feather_rig(
                root_joint=root,
                base_joint=base,
                wing_joints=wing_joints,
                do_mirror=do_mirror,
                side=side,
                chiyuNum=chiyuNum,
                get_con_size=get_con_size,
                dynCrete=dynCrete
            )
            
            if result:
                print(f"✅ 绑定完成！共处理 {len(wing_joints)} 个骨骼 ({side_name})")
            else:
                print("⚠️ 绑定完成，但未创建镜像")
                
        except Exception as e:
            print(f"❌ 绑定失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.build_btn.setEnabled(True)
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()


# ===== 全局变量保持窗口引用 =====
_feather_ui_instance = None


def show():
    """显示UI面板"""
    global _feather_ui_instance
    
    try:
        if _feather_ui_instance is not None:
            try:
                _feather_ui_instance.show()
                _feather_ui_instance.raise_()
                _feather_ui_instance.activateWindow()
                return _feather_ui_instance
            except:
                _feather_ui_instance = None
    except:
        _feather_ui_instance = None
    
    for widget in QApplication.allWidgets():
        if widget.objectName() == "FeatherRigUI":
            widget.close()
            widget.deleteLater()
    
    try:
        from shiboken2 import wrapInstance
        import maya.OpenMayaUI as omui
        maya_main = wrapInstance(int(omui.MQtUtil.mainWindow()), QWidget)
    except:
        maya_main = None
    
    _feather_ui_instance = FeatherRigUI(maya_main)
    _feather_ui_instance.show()
    
    return _feather_ui_instance


def close():
    """关闭UI面板"""
    global _feather_ui_instance
    if _feather_ui_instance is not None:
        _feather_ui_instance.close()
        _feather_ui_instance = None


if __name__ == "__main__":
    show()