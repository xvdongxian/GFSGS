# -*- coding: utf-8 -*-

import maya.cmds as cmds
import maya.mel as mel
from WingRigTool import wing_rig


def wing_ctrl_list():
    return wing_rig.list_curve_transforms_in_hierarchy([
    "l_wingConLGrp", "l_wingIKControllersGrp", "l_wing_FK_All_Grp", "l_scapula_ConGrpA",
     "r_wingConLGrp", "r_wingIKControllersGrp", "r_wing_FK_All_Grp", "r_scapula_ConGrpA"
])


        
def create_sdk_group():
    ctrl_list=wing_ctrl_list()
    for ctrl in ctrl_list:
        if cmds.objExists(ctrl):
            # 获取控制器的原始父级
            parent = cmds.listRelatives(ctrl, parent=True)
            
            # 获取控制器的世界空间位置和旋转
            world_pos = cmds.xform(ctrl, q=True, ws=True, t=True)
            world_rot = cmds.xform(ctrl, q=True, ws=True, ro=True)
            
            # 创建组，位置和旋转与控制器对齐
            grp = cmds.group(empty=True, name=ctrl + "_sdk")
            cmds.xform(grp, ws=True, t=world_pos)
            cmds.xform(grp, ws=True, ro=world_rot)
            
            # 将控制器父级到组下（保持位置不变）
            cmds.parent(ctrl, grp)
            
            # 如果控制器有原始父级，将组放到原始父级下
            if parent:
                cmds.parent(grp, parent[0])




def get_ctrl_transform():
    """
    将控制器的局部变换值传递给 _sdk 组，并建立驱动关键帧
    左控制器只绑定左驱动属性，右控制器只绑定右驱动属性
    
    Args:
        ctrl_list: 控制器名称列表
    """
    ctrl_list=wing_ctrl_list()
    l_driver_attr = "l_wrist_Con.wing_close"
    r_driver_attr = "r_wrist_Con.wing_close"
    
    # 检查驱动属性是否存在
    l_driver_exists = cmds.objExists(l_driver_attr)
    r_driver_exists = cmds.objExists(r_driver_attr)
    
    # 输出驱动属性状态
    if l_driver_exists:
        print(f"✅ 左侧驱动属性存在: {l_driver_attr}")
    else:
        print(f"⚠️ 左侧驱动属性不存在: {l_driver_attr}，将跳过左侧控制器")
    
    if r_driver_exists:
        print(f"✅ 右侧驱动属性存在: {r_driver_attr}")
    else:
        print(f"⚠️ 右侧驱动属性不存在: {r_driver_attr}，将跳过右侧控制器")
    
    if not l_driver_exists and not r_driver_exists:
        cmds.warning("左右驱动属性都不存在，无法创建驱动关键帧")
        return

    for ctrl in ctrl_list:
        if not cmds.objExists(ctrl):
            print(f"警告: {ctrl} 不存在，已跳过")
            continue

        grp = f"{ctrl}_sdk"
        if not cmds.objExists(grp):
            print(f"警告: {grp} 不存在，已跳过")
            continue

        # 判断左右控制器，匹配对应驱动属性
        if ctrl.startswith("l_"):
            driver_attr = l_driver_attr
            if not l_driver_exists:
                print(f"⚠️ 左侧驱动属性不存在，跳过控制器: {ctrl}")
                continue
        elif ctrl.startswith("r_"):
            driver_attr = r_driver_attr
            if not r_driver_exists:
                print(f"⚠️ 右侧驱动属性不存在，跳过控制器: {ctrl}")
                continue
        else:
            print(f"警告: {ctrl} 无法区分左右前缀，跳过驱动创建")
            continue

        # 1. 获取控制器局部变换 os=True 消除缩放警告
        local_pos = cmds.xform(ctrl, q=True, t=True, os=True)
        local_rot = cmds.xform(ctrl, q=True, ro=True, os=True)
        local_scl = cmds.xform(ctrl, q=True, s=True, ws=True)

        # 2. 赋值给sdk组，同步os=True
        cmds.xform(grp, t=local_pos, os=True)
        cmds.xform(grp, ro=local_rot, os=True)
        cmds.xform(grp, s=local_scl, ws=True)

        # 3. 控制器归零归1
        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
            full_attr = f"{ctrl}.{attr}"
            if not cmds.getAttr(full_attr, lock=True):
                cmds.setAttr(full_attr, 0)

        for attr in ['sx', 'sy', 'sz']:
            full_attr = f"{ctrl}.{attr}"
            if not cmds.getAttr(full_attr, lock=True):
                cmds.setAttr(full_attr, 1)

        # 4. 只创建对应单侧驱动关键帧，不再左右都打
        # driver=0 时 sdk组归零归1
        set_driven_keyframes(grp, driver_attr, 0, [0, 0, 0], [0, 0, 0], [1, 1, 1])
        # driver=10 时 sdk组还原原始控制器位置
        set_driven_keyframes(grp, driver_attr, 10, local_pos, local_rot, local_scl)
        
        print(f"✅ 已处理: {ctrl} -> {grp} (驱动: {driver_attr})")

    
def set_driven_keyframes(obj, driver_attr, driver_value, pos, rot, scl):
    """
    为对象的所有变换属性统一设置驱动关键帧
    
    Args:
        obj: 被驱动对象名称
        driver_attr: 驱动属性（完整路径）
        driver_value: 驱动属性的值
        pos: 位移值 [tx, ty, tz]
        rot: 旋转值 [rx, ry, rz]
        scl: 缩放值 [sx, sy, sz]
    """
    # 所有变换属性分组
    
    attr_groups = [
        (['tx', 'ty', 'tz'], pos),
        (['rx', 'ry', 'rz'], rot),
        (['sx', 'sy', 'sz'], scl)
    ]
    
    for attrs, values in attr_groups:
        for i, attr in enumerate(attrs):
            cmds.setDrivenKeyframe(
                obj + '.' + attr,
                cd=driver_attr,
                dv=driver_value,
                v=values[i]
            )


    cmds.setAttr('l_wrist_Con.wing_close',0)
    cmds.setAttr('r_wrist_Con.wing_close',0)




def edit_driven():
    """
    编辑驱动关键帧：从 _sdk 组获取当前变换值，应用到控制器，然后重置 _sdk 组
    
    Args:
        ctrl_list: 控制器名称列表
    """
    ctrl_list=wing_ctrl_list()
    l_driver_attr = "l_wrist_Con.wing_close"
    r_driver_attr = "r_wrist_Con.wing_close"
    
    # 检查驱动属性是否存在
    l_driver_exists = cmds.objExists(l_driver_attr)
    r_driver_exists = cmds.objExists(r_driver_attr)
    
    # 输出驱动属性状态
    if l_driver_exists:
        print(f"✅ 左侧驱动属性存在: {l_driver_attr}")
        cmds.setAttr(l_driver_attr, 10)
    else:
        print(f"⚠️ 左侧驱动属性不存在: {l_driver_attr}，将跳过左侧控制器")
    
    if r_driver_exists:
        print(f"✅ 右侧驱动属性存在: {r_driver_attr}")
        cmds.setAttr(r_driver_attr, 10)
    else:
        print(f"⚠️ 右侧驱动属性不存在: {r_driver_attr}，将跳过右侧控制器")
    
    if not l_driver_exists and not r_driver_exists:
        cmds.warning("左右驱动属性都不存在，无法编辑")
        return
    
    processed_count = 0
    skipped_count = 0
    
    for ctrl in ctrl_list:
        if not cmds.objExists(ctrl):
            print(f"警告: {ctrl} 不存在")
            skipped_count += 1
            continue
        
        grp = ctrl + '_sdk'
        if not cmds.objExists(grp):
            print(f"警告: {grp} 不存在")
            skipped_count += 1
            continue
        
        # 判断左右控制器，匹配对应驱动属性
        if ctrl.startswith("l_"):
            if not l_driver_exists:
                print(f"⚠️ 左侧驱动属性不存在，跳过控制器: {ctrl}")
                skipped_count += 1
                continue
        elif ctrl.startswith("r_"):
            if not r_driver_exists:
                print(f"⚠️ 右侧驱动属性不存在，跳过控制器: {ctrl}")
                skipped_count += 1
                continue
        else:
            print(f"警告: {ctrl} 无法区分左右前缀，跳过")
            skipped_count += 1
            continue
        
        # 2. 获取 _sdk 组的当前变换值（此时 wing_close=10 状态）
        local_pos = cmds.xform(grp, q=True, t=True, os=True)
        local_rot = cmds.xform(grp, q=True, ro=True, os=True)
        local_scl = cmds.xform(grp, q=True, s=True, ws=True)
        
        # 3. 将变换值应用到控制器
        cmds.xform(ctrl, t=local_pos, os=True)
        cmds.xform(ctrl, ro=local_rot, os=True)
        cmds.xform(ctrl, s=local_scl, ws=True)
        
        # 4. 归零 _sdk 组的变换
        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
            full_attr = grp + "." + attr
            if not cmds.getAttr(full_attr, lock=True):
                cmds.setAttr(full_attr, 0)
        
        for attr in ['sx', 'sy', 'sz']:
            full_attr = grp + "." + attr
            if not cmds.getAttr(full_attr, lock=True):
                cmds.setAttr(full_attr, 1)
        
        
        processed_count += 1
    
    # 重置存在的驱动属性为 0
    if l_driver_exists:
        cmds.setAttr(l_driver_attr, 0)
    if r_driver_exists:
        cmds.setAttr(r_driver_attr, 0)
    
    
                
def remove_driven_keyframes(obj, attrs=None):
    """
    移除对象上的驱动关键帧
    
    Args:
        obj: 对象名称
        attrs: 属性列表，如果为 None 则移除所有变换属性
    """
    if attrs is None:
        attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    
    for attr in attrs:
        full_attr = obj + '.' + attr
        if cmds.objExists(full_attr):
            # 断开驱动连接并删除关键帧
            cmds.setAttr(full_attr, lock=False)
            # 断开属性连接
            if cmds.connectionInfo(full_attr, isDestination=True):
                cmds.disconnectAttr(full_attr)
            # 删除关键帧
            cmds.cutKey(full_attr)
            
    


def mirror_driven_values(source_side="l"):
    """
    镜像控制器的变换值：将一侧的数值镜像应用到另一侧
    
    Args:
        ctrl_list: 控制器名称列表
        source_side: 源侧标识 ("l" 或 "r")
    """
    # 确定源和目标侧

    ctrl_list=wing_ctrl_list()
    if source_side == "l":
        target_side = "r"
    else:
        target_side = "l"
    
    for ctrl in ctrl_list:
        # 只处理源侧的控制器
        if not ctrl.startswith(source_side + "_"):
            continue
        
        # 获取源和目标对象
        source_grp = ctrl + '_sdk'
        target_ctrl = ctrl.replace(source_side + "_", target_side + "_", 1)
        target_grp = target_ctrl + '_sdk'
        
        # 检查是否存在
        if not cmds.objExists(source_grp):
            print("警告: {} 不存在，跳过".format(source_grp))
            continue
        if not cmds.objExists(target_ctrl):
            print("警告: {} 不存在，跳过".format(target_ctrl))
            continue
        if not cmds.objExists(target_grp):
            print("警告: {} 不存在，跳过".format(target_grp))
            continue
        
        # 获取源 _sdk 组的变换值
        source_pos = cmds.xform(ctrl, q=True, t=True)
        source_rot = cmds.xform(ctrl, q=True, ro=True)
        source_scl = cmds.xform(ctrl, q=True, s=True,ws=True)
        
        # 计算镜像值（X轴翻转）
        mirror_pos = [-source_pos[0], -source_pos[1], -source_pos[2]]
        mirror_rot = [source_rot[0], source_rot[1], source_rot[2]]
        mirror_scl = [source_scl[0], source_scl[1], source_scl[2]]
        
        # 应用到目标 _sdk 组
        cmds.xform(target_ctrl, t=mirror_pos)
        cmds.xform(target_ctrl, ro=mirror_rot)
        cmds.xform(target_ctrl, s=mirror_scl,ws=True)


            