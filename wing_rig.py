# -*- coding: utf-8 -*-

import maya.cmds as cmds
import maya.mel as mel
from WingRigTool import ctrl_shape
from WingRigTool import wing_loc


def get_joints_sorted_by_x_distance_descending():
    """
    获取列表中骨骼的位置信息，按X轴距离中心的距离排序（从远到近）
    """
    select_joints = cmds.ls(selection=True)
    
    if not select_joints:
        cmds.warning("请先选择骨骼！")
        return []
    
    joint_info = []
    for joint in select_joints:
        pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)
        joint_info.append({
            'name': joint,
            'position': pos,
            'x_distance': abs(pos[0])
        })
    
    sorted_info = sorted(joint_info, key=lambda x: x['x_distance'], reverse=True)
    joints = [info['name'] for info in sorted_info]
    
    
    for i, name in enumerate(joints, 1):
        pos = sorted_info[i-1]['position']
        dist = sorted_info[i-1]['x_distance']
    
    cmds.select(joints)
    
    return joints


def attach_objects_to_surface(surface=None, keep_position=True, constraint_type="point"):
    """
    将选中的物体附着到模型表面（毛囊附着）
    
    参数:
        surface: 目标表面名称，如果为None则使用第一个选中的物体作为表面
        keep_position: 是否保持原位置 (True=保持, False=移动到表面)
        constraint_type: 约束类型 ("parent"=父子约束, "point"=点约束)
    """
    # 获取选中的物体
    selection = cmds.ls(selection=True)
    
    if not selection:
        cmds.warning("请先选择物体！")
        return
    
    # 如果没有指定表面，使用第一个选中的作为表面
    if surface is None:
        surface = selection[0]
        objects = selection[1:] if len(selection) > 1 else []
        
        if not objects:
            cmds.warning("请选择要附着的物体！\n提示：第一个选中的作为表面，其余作为附着物体")
            return
    else:
        # 使用指定的表面
        if not cmds.objExists(surface):
            cmds.error(f"表面不存在: {surface}")
            return
        objects = selection
    
    # 检查表面类型
    shapes = cmds.listRelatives(surface, shapes=True)
    if not shapes:
        cmds.error(f"表面 '{surface}' 没有形状节点")
        return
    
    shape_type = cmds.objectType(shapes[0])
    if shape_type not in ["mesh", "nurbsSurface"]:
        cmds.error(f"需要多边形或NURBS曲面，但得到: {shape_type}")
        return
    
    # 创建组
    group_name = f"{surface}follicleGrp"
    if not cmds.objExists(group_name):
        cmds.group(empty=True, name=group_name)
    
  
    success_count = 0
    
    for i, obj in enumerate(objects):
        try:
            # 获取物体世界空间位置
            pos = cmds.xform(obj, query=True, worldSpace=True, translation=True)
            
            # 创建closestPoint节点
            if shape_type == "mesh":
                cp_type = "closestPointOnMesh"
            else:
                cp_type = "closestPointOnSurface"
            
            cp_name = f"{obj}_cp"
            if cmds.objExists(cp_name):
                cmds.delete(cp_name)
            cp = cmds.createNode(cp_type, name=cp_name)
            
            # 连接输入
            if shape_type == "mesh":
                cmds.connectAttr(f"{surface}.outMesh", f"{cp}.inMesh", force=True)
            else:
                cmds.connectAttr(f"{shapes[0]}.worldSpace", f"{cp}.inputSurface", force=True)
            
            # 设置位置
            cmds.setAttr(f"{cp}.inPositionX", pos[0])
            cmds.setAttr(f"{cp}.inPositionY", pos[1])
            cmds.setAttr(f"{cp}.inPositionZ", pos[2])
            
            # 强制更新以获取正确的UV
            cmds.currentTime(cmds.currentTime(query=True), update=True)
            
            # 获取UV参数
            u = cmds.getAttr(f"{cp}.parameterU")
            v = cmds.getAttr(f"{cp}.parameterV")
            
            # 检查UV是否有效
            if u < 0 or u > 1 or v < 0 or v > 1:
                u = max(0, min(1, u))
                v = max(0, min(1, v))
            
            
            
            # 创建follicle
            follicle_shape_name = f"{obj}follicle_shape"
            if cmds.objExists(follicle_shape_name):
                cmds.delete(follicle_shape_name)
            follicle_shape = cmds.createNode("follicle", name=follicle_shape_name)
            
            # 获取follicle的transform并重命名
            follicle = cmds.listRelatives(follicle_shape, parent=True)[0]
            follicle_new_name = f"{obj}follicle"
            if cmds.objExists(follicle_new_name):
                cmds.delete(follicle_new_name)
            follicle = cmds.rename(follicle, follicle_new_name)
            
            # 连接表面几何
            if shape_type == "mesh":
                cmds.connectAttr(f"{surface}.outMesh", f"{follicle_shape}.inputMesh", force=True)
            else:
                cmds.connectAttr(f"{shapes[0]}.local", f"{follicle_shape}.inputSurface", force=True)
            
            # 连接世界矩阵
            cmds.connectAttr(f"{surface}.worldMatrix[0]", f"{follicle_shape}.inputWorldMatrix", force=True)
            
            # 连接输出到transform
            cmds.connectAttr(f"{follicle_shape}.outTranslate", f"{follicle}.translate", force=True)
            cmds.connectAttr(f"{follicle_shape}.outRotate", f"{follicle}.rotate", force=True)
            
            # 设置UV参数
            cmds.setAttr(f"{follicle_shape}.parameterU", u)
            cmds.setAttr(f"{follicle_shape}.parameterV", v)

           
            cmds.parent(follicle, group_name)
            
            # 删除closestPoint节点
            cmds.delete(cp)
            
            # ===== 根据约束类型创建不同的约束 =====
            
            # 先删除物体上现有的约束
            
            if constraint_type == "parent":
                # 父子约束（包含位置和旋转）
                if keep_position:
                    cmds.parentConstraint(follicle, obj, maintainOffset=True)
                    
                else:
                    cmds.parentConstraint(follicle, obj, maintainOffset=False)
                    
                    
            elif constraint_type == "point":
                # 仅点约束（只有位置）
                if keep_position:
                    cmds.pointConstraint(follicle, obj, maintainOffset=True)
                
                else:
                    cmds.pointConstraint(follicle, obj, maintainOffset=False)
                  
            
            
            else:
                # 默认使用父子约束
                if keep_position:
                    cmds.parentConstraint(follicle, obj, maintainOffset=True)
                
                else:
                    cmds.parentConstraint(follicle, obj, maintainOffset=False)
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ {obj} 附着失败: {e}")
    
    
    return success_count
    

    
def reparent_skin0_bones_to_body(parentJoint='l_scapula'):
    """
    将蒙皮骨骼父级到翅膀骨骼上
    """
    group_name = parentJoint+'_followGrp'
    target_parent = parentJoint
    
    # 检查节点是否存在
    if not cmds.objExists(group_name):
        
        return
    if not cmds.objExists(target_parent):
        
        return

    # 获取组下所有骨骼

    all_joints = cmds.listRelatives(group_name, children=True, type='joint') or []
    
    # 过滤出以 _0Skin0 结尾的骨骼（包括 a_0Skin0, b_0Skin0, c_0Skin0...）

    for j in all_joints:
        cmds.parent(j+'Skin0', target_parent, absolute=True)
        


def setup_wing_fk_groups(root_joint):
    """
    设置翅膀FK组
    
    参数:
        root_joint: 根关节名称 (如 "l_scapula" 或 "r_scapula")
    
    返回:
        处理后的关节列表
    """
    # 自动生成FK组名
    # 从关节名提取前缀 (l_ 或 r_)
    if root_joint.startswith("l_"):
        prefix = "l_"
    elif root_joint.startswith("r_"):
        prefix = "r_"
    else:
        prefix = ""
        print(f"⚠️ 无法识别前缀: {root_joint}")
    
    fk_grp_name = f"{prefix}wing_FK_All_Grp"
    
    # 获取根关节及其所有子关节
    joints = cmds.ls(root_joint, type='joint') or []
    joints += cmds.listRelatives(root_joint, allDescendents=True, type='joint') or []
    
    # 只保留有子关节的关节（排除末端）
    joints = [j for j in joints if cmds.listRelatives(j, children=True, type='joint')]
    
    # 创建FK组
    if not cmds.objExists(fk_grp_name):
        cmds.group(empty=True, name=fk_grp_name)
        
    # 执行 re-parent 函数
    for joint in joints:
        reparent_skin0_bones_to_body(joint)
    
    # 将 followGrp 父级到 FK 组
    for joint in joints:
        group = joint + '_followGrp'
        if cmds.objExists(group):
            cmds.parent(group, fk_grp_name)

    
    return joints


def gt_create_con_fk_con(root_jnt,con_size=1):
    """
    为骨骼链创建FK控制器
    
    参数:
        root_jnt: 根骨骼名称
    """
    if not cmds.objExists(root_jnt):
        cmds.warning(f"骨骼不存在: {root_jnt}")
        return
    
    # 获取所有子关节
    cmds.listRelatives(root_jnt, allDescendents=True, type="joint") or []
    
    # 构建关节链（从根到末端）
    joint_chain = [root_jnt]
    current = root_jnt
    while True:
        child = cmds.listRelatives(current, children=True, type="joint")
        if not child:
            break
        current = child[0]
        joint_chain.append(current)
    
    # 移除末端关节（最后一个）
    if joint_chain:
        joint_chain.pop()
    
    
    # 创建控制器
    con_list = []
    for jnt in joint_chain:
        base_name = jnt.replace("_jnt", "")
        
        con = ctrl_shape.create_controller(base_name + "_Con", size=2.5*con_size, shape_type="Square", color=18, orientation=(0, 0, 90))
        wing_loc.lock_and_hide_transform(con,lock_translate=True, lock_rotate=False, lock_scale=True)
        
        
        grp1 = cmds.group(con, name=f"{base_name}_ConGrp")
        grp2 = cmds.group(grp1, name=f"{base_name}_ConGrpA")
        con_list.append(con)
        
        shape = cmds.listRelatives(con, shapes=True)[0]
        cmds.rename(shape, f"{base_name}_ConShape")
        
        cmds.delete(cmds.parentConstraint(jnt, grp2, maintainOffset=False)[0])
        cmds.parentConstraint(con, jnt, maintainOffset=True)
        cmds.scaleConstraint(con, jnt, maintainOffset=True)
    
    # 父子级连接
    for i in range(len(con_list) - 1):
        # 子控制器的组父级到父控制器
        child_base = joint_chain[i + 1].replace("_jnt", "")
        child_grp = f"{child_base}_ConGrpA"
        cmds.parent(child_grp, con_list[i])



    # 添加全局属性
    last_con = con_list[-1]
    cmds.addAttr(last_con, longName="rotx", attributeType="double", keyable=True)
    cmds.addAttr(last_con, longName="roty", attributeType="double", keyable=True)
    cmds.addAttr(last_con, longName="rotz", attributeType="double", keyable=True)
    cmds.addAttr(last_con, longName="wing_close", attributeType="double", dv=0,min=0,max=10, keyable=True)
    
        
        # 连接属性
    for con in con_list:
        cmds.connectAttr(f"{last_con}.rotx", f"{con}Grp.rotateX", force=True)
        cmds.connectAttr(f"{last_con}.roty", f"{con}Grp.rotateY", force=True)
        cmds.connectAttr(f"{last_con}.rotz", f"{con}Grp.rotateZ", force=True)
        
    
    

    return con_list


def list_curve_transforms_in_hierarchy(objects):
    """
    列出物体层级下所有曲线的父级transform
    """
    if isinstance(objects, str):
        objects = [objects]
    
    curve_transforms = []
    
    for obj in objects:
        if not cmds.objExists(obj):
            print(f"❌ 物体不存在: {obj}")
            continue
        
        all_objects = [obj]
        children = cmds.listRelatives(obj, allDescendents=True) or []
        all_objects.extend(children)
        
        for item in all_objects:
            if cmds.nodeType(item) == 'transform':
                shapes = cmds.listRelatives(item, shapes=True, type='nurbsCurve')
                if shapes:
                    curve_transforms.append(item)
    
    # 去重
    curve_transforms = list(set(curve_transforms))
    
   
    
    return curve_transforms



def feather_binding(side="l", chiyuNum=4, con_size=1):
    """
    主函数：执行羽毛绑定
    
    参数:
        side: 左右标识 ("l" 或 "r")
        chiyuNum: 翅膀骨骼数量（默认4）
        con_size: 控制器大小（默认0.5）
    """
    
    
    # ===== 根据左右设置变量 =====
    if side == "l":
        prefix = "l_"
        wing_mesh = "l_wingMesh"
        wing_curve = "l_wingCurve"
        wing_tangent_curve = "l_wingTangentCurve"
        curve_grp = "l_wingCurveGrp"
        dyn_grp = "l_wingDynGrp"
        cluster_lik_grp = "l_wingClusterLIKGrp"
        cluster_ldyn_grp = "l_wingClusterLDynGrp"
        con_l_grp = "l_wingConLGrp"
        ik_con_grp = "l_wingIKConGrp"
        ik_all_grp = "l_wing_IK_All_Grp"
        ik_grp = "l_wingIkGrp"
        not_move_grp ='l_wingNotMoveGrp'
        wing_surf ='l_wingLoftSurface'
    else:
        prefix = "r_"
        wing_mesh = "r_wingMesh"
        wing_curve = "r_wingCurve"
        wing_tangent_curve = "r_wingTangentCurve"
        curve_grp = "r_wingCurveGrp"
        dyn_grp = "r_wingDynGrp"
        cluster_lik_grp = "r_wingClusterLIKGrp"
        cluster_ldyn_grp = "r_wingClusterLDynGrp"
        con_l_grp = "r_wingConLGrp"
        ik_con_grp = "r_wingIKConGrp"
        ik_all_grp = "r_wing_IK_All_Grp"
        ik_grp = "r_wingIkGrp"
        not_move_grp ='r_wingNotMoveGrp'
        wing_surf ='r_wingLoftSurface'
    

    # ===== 1. 初始化 =====

    joints = get_joints_sorted_by_x_distance_descending()
    cmds.parent(world=True)
    if not joints:
        cmds.error("请先选择关节!")
        return
    
    end_bn = {}
    
    wing_loc.auto_parent_branches(f"{prefix}scapula")

    #======创建翅膀控制器======

    gt_create_con_fk_con(f"{prefix}scapula",con_size)


    
    # ===== 创建翅膀切线 =====
    
    
    positions = []
    

    for joint in joints:
        pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)
        positions.append(pos)
    
    if cmds.objExists(wing_tangent_curve):
        cmds.delete(wing_tangent_curve)
    
    curve = cmds.curve(
        degree=3,
        point=positions,
        name=wing_tangent_curve
    )
    shapes = cmds.listRelatives(curve, shapes=True)
    if shapes:
        cmds.rename(shapes[0], f"{wing_tangent_curve}Shape")
    if not cmds.objExists(curve_grp):
        cmds.group(empty=True, n=curve_grp)

    cmds.parent(wing_tangent_curve, curve_grp)

    # ===== 创建附着曲面 =====
    cmds.duplicate(wing_tangent_curve,rr=True,n=f"{prefix}wingloftCurveA")
    cmds.duplicate(wing_tangent_curve,rr=True,n=f"{prefix}wingloftCurveB")
    cmds.setAttr(f"{prefix}wingloftCurveB.tz",-0.1)
    cmds.setAttr(f"{prefix}wingloftCurveA.tz",0.1)
    cmds.rebuildCurve(
    f"{prefix}wingloftCurveA",
    ch=1,
    rpo=1,
    rt=0,
    end=1,
    kr=0,
    kcp=0,
    kep=1,
    kt=0,
    s=len(joints),
    d=3,
    tol=0.01)
    cmds.rebuildCurve(
    f"{prefix}wingloftCurveB",
    ch=1,
    rpo=1,
    rt=0,
    end=1,
    kr=0,
    kcp=0,
    kep=1,
    kt=0,
    s=len(joints),
    d=3,
    tol=0.01)
    cmds.loft(f"{prefix}wingloftCurveA",f"{prefix}wingloftCurveB", name=f"{prefix}wingLoftSurface")
    cmds.delete(f"{prefix}wingloftCurveA",f"{prefix}wingloftCurveB")
    cmds.skinCluster(
                    f"{prefix}scapula",f"{prefix}shoulder",f"{prefix}ebow",f"{prefix}wrist", wing_surf,
                    toSelectedBones=True,
                    bindMethod=0,
                    skinMethod=0,
                    normalizeWeights=1,
                    weightDistribution=0,
                    maximumInfluences=1,
                    dropoffRate=4,
                    obeyMaxInfluences=False
                )[0]
    


    # ===== 创建跟随毛囊 =====
    
    cmds.select(joints)
    attach_objects_to_surface(f"{prefix}wingLoftSurface", keep_position=True, constraint_type="point")
    
    if cmds.objExists(f"{wing_surf}follicleGrp"):
        if not cmds.objExists(not_move_grp):
            cmds.group(empty=True, n=not_move_grp)
        cmds.parent(f"{wing_surf}follicleGrp", not_move_grp)
        cmds.parent(wing_surf, not_move_grp)
    
    
    # ===== 创建控制曲线 =====
    
    wing_curve_ik = f"{prefix}wingCurveIK"
    wing_curve_dyn = f"{prefix}wingCurveDyn"
    
    if cmds.objExists(wing_curve):
        cmds.select(wing_curve)
        cmds.duplicate(rr=True)
        cmds.rename(f"{prefix}wingCurveIK")
        cmds.duplicate(rr=True)
        cmds.rename(f"{prefix}wingCurveDyn")
        
    
    if cmds.objExists(wing_tangent_curve):
        cmds.select(wing_tangent_curve)
        cmds.duplicate(rr=True)
        cmds.rename(f"{prefix}wingTangentCurvePos")
        
    
    cmds.select(cl=True)
    curve_aim_loc_grp_name = f"{prefix}CurveAimLocGrp"
    if not cmds.objExists(curve_aim_loc_grp_name):
        cmds.group(empty=True, n=curve_aim_loc_grp_name)
        cmds.setAttr(curve_aim_loc_grp_name+'.visibility',0)
    
    # ===== 创建切线曲线定位器 =====
    
    tang_curve_a = f"{prefix}wingTangentCurvePos"
    tang_curve = wing_tangent_curve
    loc_grp = curve_aim_loc_grp_name
    
    if cmds.objExists(tang_curve_a):
        cmds.select(tang_curve_a + ".cv[0:1000]")
        tan_cv = cmds.ls(sl=True, fl=True)
        
        if tan_cv and cmds.objExists(tang_curve_a) and cmds.objExists(tang_curve):
            shap_curve_t = cmds.listRelatives(tang_curve_a, s=True)
            shap_tan = cmds.listRelatives(tang_curve, s=True)
            
            if shap_curve_t and shap_tan:
                for i, cv in enumerate(tan_cv):
                    loc_name = tang_curve_a + "Loc" + str(i)
                    cmds.spaceLocator(p=(0,0,0), n=loc_name)
                    cmds.parent(loc_name, loc_grp)
                    
                    cv_pos = cmds.xform(cv, q=True, ws=True, t=True)
                    cmds.setAttr(loc_name + ".tx", cv_pos[0])
                    cmds.setAttr(loc_name + ".ty", cv_pos[1])
                    cmds.setAttr(loc_name + ".tz", cv_pos[2])
                    
                    npoc = cmds.createNode('nearestPointOnCurve', n=tang_curve + "nearestPointOnCurve" + str(i))
                    cmds.connectAttr(shap_tan[0] + ".worldSpace[0]", npoc + ".inputCurve", f=True)
                    cmds.connectAttr(loc_name + ".t", npoc + ".inPosition", f=True)
                    param = cmds.getAttr(npoc + ".parameter")
                    cmds.delete(npoc)
                    
                    poci = cmds.createNode('pointOnCurveInfo', n=tang_curve_a + "wingTangCurvePointOnCurveInfo" + str(i))
                    cmds.connectAttr(shap_tan[0] + ".worldSpace[0]", poci + ".inputCurve", f=True)
                    cmds.setAttr(poci + ".parameter", param)
                    cmds.connectAttr(poci + ".position", loc_name + ".t", f=True)
                    
                    loc_shapes = cmds.listRelatives(loc_name, s=True)
                    if loc_shapes:
                        cmds.connectAttr(loc_shapes[0] + ".worldPosition[0]", shap_curve_t[0] + ".controlPoints[" + str(i) + "]", f=True)
    
    # ===== 获取末端关节和添加属性 =====
    for joint in joints:
        children = cmds.listRelatives(joint, c=True, type="joint")
        if children:
            end_bn[joint] = children[0]
            tx = cmds.getAttr(children[0] + ".tx")
            cmds.addAttr(joint, ln="oldTx", at="double", dv=tx)
    
    # ===== 创建位置和切线定位器 =====
        
    for joint in joints:
        pos_loc = joint + "CurvePosLoc"
        tan_loc = joint + "CurveTanLoc"
        
        cmds.spaceLocator(p=(0,0,0), n=pos_loc)
        cmds.spaceLocator(p=(0,0,0), n=tan_loc)
        
        constr = cmds.parentConstraint(joint, pos_loc)
        cmds.delete(constr)
        constr = cmds.parentConstraint(joint, tan_loc)
        cmds.delete(constr)
        
        parents = cmds.listRelatives(joint, p=True)
       
        if parents:
            wing_grp = parents[0] + "WingAlocGrp"
            if not cmds.objExists(wing_grp):
                cmds.select(cl=True)
                wing_grp = cmds.group(empty=True, n=wing_grp)
                constr = cmds.parentConstraint(parents[0], wing_grp)
                cmds.delete(constr)
                cmds.parent(wing_grp, parents[0])
            cmds.parent(pos_loc, wing_grp)
            cmds.parent(tan_loc, wing_grp)
            cmds.setAttr(wing_grp+'.visibility',0)
        
        
        constraints = cmds.listConnections(joint + ".tx", s=1, d=0)
        if constraints:
            inputs = cmds.listConnections(constraints[0] + ".target[0].targetTranslate", s=1, d=0)
            if inputs:
                cmds.pointConstraint(inputs[0], pos_loc, mo=True)
                cmds.pointConstraint(inputs[0], tan_loc, mo=True)
    
    # ===== 切线约束 =====
    
    tange_curve_a = f"{prefix}wingTangentCurvePos"
    
    for joint in joints:
        if cmds.objExists(tange_curve_a) and cmds.objExists(joint + "CurvePosLoc"):
            cmds.select(tange_curve_a)
            cmds.select(joint + "CurvePosLoc", add=True)
            cmds.tangentConstraint(weight=1, aimVector=(0,0,1), upVector=(0,1,0),
                                   worldUpType="objectrotation", worldUpVector=(0,1,0),
                                   worldUpObject=(joint + "CurveTanLoc"))
    
    # ===== 连接切线控制点 =====
    
    tange_curve = wing_tangent_curve
    if cmds.objExists(tange_curve):
        shap_tan = cmds.listRelatives(tange_curve, s=True)
        if shap_tan:
            for i, joint in enumerate(joints):
                loc_shapes = cmds.listRelatives(joint + "CurveTanLoc", s=True)
                if loc_shapes:
                    cmds.connectAttr(loc_shapes[0] + ".worldPosition[0]", shap_tan[0] + ".controlPoints[" + str(i) + "]", f=True)
    
    # ===== 创建目标定位器 =====
    
    wing_curve_ik = f"{prefix}wingCurveIK"
    if cmds.objExists(wing_curve_ik):
        curve_shape = cmds.listRelatives(wing_curve_ik, s=True)
        if curve_shape:
            for joint in joints:
                aim_loc = joint + "CurveAimLoc"
                cmds.spaceLocator(p=(0,0,0), n=aim_loc)
                
                children = cmds.listRelatives(joint, c=True, type="joint")
                if children:
                    pos_loc_a = joint + "CurvePosLocA"
                    cmds.spaceLocator(p=(0,0,0), n=pos_loc_a)
                    constr = cmds.parentConstraint(children[0], pos_loc_a)
                    cmds.delete(constr)
                    
                    npoc = cmds.createNode('nearestPointOnCurve', n=joint + "nearestPointOnCurve")
                    cmds.connectAttr(curve_shape[0] + ".worldSpace[0]", npoc + ".inputCurve", f=True)
                    cmds.connectAttr(pos_loc_a + ".t", npoc + ".inPosition", f=True)
                    param = cmds.getAttr(npoc + ".parameter")
                    cmds.delete(npoc, pos_loc_a)
                    
                    poci = cmds.createNode('pointOnCurveInfo', n=joint + "pointOnCurveInfoAim")
                    cmds.connectAttr(curve_shape[0] + ".worldSpace[0]", poci + ".inputCurve", f=True)
                    cmds.setAttr(poci + ".parameter", param)
                    cmds.connectAttr(poci + ".position", aim_loc + ".t", f=True)
    
    # ===== 目标约束 =====
    
    for joint in joints:
        if cmds.objExists(joint + "CurveAimLoc") and cmds.objExists(joint + "CurvePosLoc"):
            cmds.select(joint + "CurveAimLoc")
            cmds.select(joint, add=True)
            cmds.aimConstraint(mo=True, weight=1, aimVector=(1,0,0), upVector=(0,1,0),
                              worldUpType="objectrotation", worldUpVector=(0,1,0),
                              worldUpObject=(joint + "CurvePosLoc"))
    
    cmds.select(cl=True)
    for joint in joints:
        cmds.select(joint + "CurveAimLoc", add=True)
    cmds.select(curve_aim_loc_grp_name, add=True)
    cmds.parent()
    
    # ===== 创建 wingCurveIK 的簇 =====
    
    point_num = 0
    if cmds.objExists(wing_curve_ik):
        cmds.select(wing_curve_ik + ".cv[0:1000]")
        points = cmds.ls(sl=True)
        
        if points:
            first_point = points[0]
            parts = first_point.split(":")[1].split("]")[0]
            point_num = int(parts)
            
            cluster_nodes = []
            for i in range(point_num + 1):
                cmds.select(wing_curve_ik + ".cv[" + str(i) + "]")
                cluster_node = cmds.cluster(envelope=1)
                cluster_name = wing_curve_ik + "cluster" + str(i)
                cmds.rename(cluster_node[1], cluster_name)
                cluster_nodes.append(cluster_name)
            
            cmds.select(cluster_nodes)
    
    # ===== 为 IK 簇创建控制器 =====
    
    selected = cmds.ls(sl=True)
    for sel in selected:
        ctrl =  ctrl_shape.create_controller(sel + "Con", size=1.5*con_size, shape_type="Diamond", color=14)
        wing_loc.lock_and_hide_transform(ctrl,lock_translate=False, lock_rotate=True, lock_scale=True)
        grp = cmds.group(empty=True, n=sel + "ConGrp")
        grp_a = cmds.group(empty=True, n=sel + "ConGrpA")
        cmds.parent(ctrl,grp)
        cmds.parent(grp,grp_a)
        
        temp_constraint = cmds.parentConstraint(sel,grp_a,mo=False)
        cmds.delete(temp_constraint)
        cmds.parentConstraint(ctrl,sel)
        cmds.connectAttr('wing_follow_Grp.scale',grp_a+'.scale')
        


    # ===== 创建 wingCurveDyn 的簇 =====
    
    wing_curve_dyn = f"{prefix}wingCurveDyn"
    if cmds.objExists(wing_curve_dyn):
        cmds.select(wing_curve_dyn + ".cv[0:1000]")
        points_b = cmds.ls(sl=True)
        
        if points_b:
            first_point = points_b[0]
            parts = first_point.split(":")[1].split("]")[0]
            point_num = int(parts)
            
            cluster_nodes = []
            for i in range(point_num + 1):
                cmds.select(wing_curve_dyn + ".cv[" + str(i) + "]")
                cluster_node = cmds.cluster(envelope=1)
                cluster_name = wing_curve_dyn + "cluster" + str(i)
                cmds.rename(cluster_node[1], cluster_name)
                cluster_nodes.append(cluster_name)
            
            cmds.select(cluster_nodes)
    
    # ===== 为动力学簇创建圆形控制器 =====
    
    selected_b = cmds.ls(sl=True)
    for sel in selected_b:
        ctrl =  ctrl_shape.create_controller(sel + "Con", size=5*con_size, shape_type="A_Arrow", color=17,orientation=(90, 0, 0))
        wing_loc.lock_and_hide_transform(ctrl,lock_translate=False, lock_rotate=True, lock_scale=True)
        grp = cmds.group(empty=True, n=sel + "ConGrp")
        grp_a = cmds.group(empty=True, n=sel + "ConGrpA")
        cmds.parent(ctrl,grp)
        cmds.parent(grp,grp_a)
        
        temp_constraint = cmds.parentConstraint(sel,grp_a,mo=False)
        cmds.delete(temp_constraint)
        cmds.parentConstraint(ctrl,sel)
        
        
    
    # ===== 整理控制器组和簇 =====
    
    
    if not cmds.objExists(cluster_lik_grp):
        cmds.group(empty=True, n=cluster_lik_grp)
    
    for i in range(point_num + 1):
        cluster_name = wing_curve_ik + "cluster" + str(i)
        if cmds.objExists(cluster_name):
            cmds.parent(cluster_name, cluster_lik_grp)
    
    if not cmds.objExists(cluster_ldyn_grp):
        cmds.group(empty=True, n=cluster_ldyn_grp)
    
    for i in range(point_num + 1):
        cluster_name = wing_curve_dyn + "cluster" + str(i)
        if cmds.objExists(cluster_name):
            cmds.parent(cluster_name, cluster_ldyn_grp)
    
    cmds.parent(cluster_lik_grp, cluster_ldyn_grp)
    
    if not cmds.objExists(con_l_grp):
        cmds.group(empty=True, n=con_l_grp)
    
    for i in range(point_num + 1):
        grp_name = wing_curve_ik + "cluster" + str(i) + "ConGrpA"
        if cmds.objExists(grp_name):
            cmds.parent(grp_name, con_l_grp)
    
    for i in range(point_num + 1):
        dyn_cluster_grp = wing_curve_dyn + "cluster" + str(i) + "ConGrpA"
        ik_cluster_ctrl = wing_curve_ik + "cluster" + str(i) + "Con"
        
        if cmds.objExists(dyn_cluster_grp) and cmds.objExists(ik_cluster_ctrl):
            cmds.parent(dyn_cluster_grp, ik_cluster_ctrl)
    
    # ===== 曲线位置约束 =====
    
    con_sel = [wing_curve_ik + "cluster" + str(i) + "ConGrpA" for i in range(point_num + 1)]
    
    curve_shape = cmds.listRelatives(wing_curve, s=True)
    
    if curve_shape:
        for con in con_sel:
            if not cmds.objExists(con):
                continue
            
            pos = cmds.xform(con, q=True, a=True, ws=True, t=True)
            
            npoc = cmds.createNode('nearestPointOnCurve', n=con + "nearestPointOnCurve")
            cmds.connectAttr(curve_shape[0] + ".worldSpace[0]", npoc + ".inputCurve", f=True)
            cmds.connectAttr(con + ".t", npoc + ".inPosition", f=True)
            
            param = cmds.getAttr(npoc + ".parameter")
            cmds.delete(npoc)
            
            poci = cmds.createNode('pointOnCurveInfo', n=con + "pointOnCurveInfo")
            cmds.connectAttr(curve_shape[0] + ".worldSpace[0]", poci + ".inputCurve", f=True)
            cmds.setAttr(poci + ".parameter", param)
            cmds.connectAttr(poci + ".position", con + ".t", f=True)
    
    # ===== 创建羽毛骨骼 =====
    for joint in joints:
        cmds.setAttr(joint + ".drawStyle",2)
        joint_children = cmds.listRelatives(joint, children=True)[0]

        cmds.setAttr(joint_children + ".drawStyle", 2)

    for joint in joints:
        if joint not in end_bn:
            continue
        
        dis = cmds.getAttr(joint + ".oldTx")
        perdis = dis / chiyuNum
        
        cmds.select(cl=True)
        cmds.joint(p=(0,0,0), n=joint + "Skin0")
        for j in range(1, chiyuNum + 1):
            cmds.joint(p=(j * perdis, 0, 0), n=joint + "Skin" + str(j))
        
        constr = cmds.parentConstraint(joint, joint + "Skin0")
        cmds.delete(constr)
        cmds.select(joint + "Skin0")
        cmds.makeIdentity(apply=True, t=0, r=1, s=0, n=0)
        cmds.parent(joint + "Skin0", joint)


    
    # ===== 复制骨骼用于 FK/IK =====
    
    for joint in joints:
        cmds.select(joint + "Skin0")
        cmds.duplicate(rr=True, n=joint + "FK0")
        for j in range(1, chiyuNum + 1):
            cmds.pickWalk(d='down')
            sel = cmds.ls(sl=True)[0]
            cmds.rename(joint + "FK" + str(j))
            
        
        cmds.select(joint + "Skin0")
        cmds.duplicate(rr=True, n=joint + "IK0")
        for j in range(1, chiyuNum + 1):
            cmds.pickWalk(d='down')
            sel = cmds.ls(sl=True)[0]
            cmds.rename(joint + "IK" + str(j))
            
        
        for suffix in ["FKRotA", "FKRotB", "FKRotC"]:
            cmds.select(joint + "Skin0")
            cmds.duplicate(rr=True, n=joint + suffix + "0")
            
            for j in range(1, chiyuNum + 1):
                cmds.pickWalk(d='down')
                sel = cmds.ls(sl=True)[0]
                cmds.rename(sel, joint + suffix + str(j))

        for j in range(0,chiyuNum + 1):
            cmds.setAttr(joint + 'FKRotA' + str(j)+".drawStyle",2)
            cmds.setAttr(joint + 'FKRotB' + str(j)+".drawStyle",2)
            cmds.setAttr(joint + 'FKRotC' + str(j)+".drawStyle",2)
            cmds.setAttr(joint + "IK" + str(j)+".drawStyle",2)
            cmds.setAttr(joint + "FK" + str(j)+".drawStyle",2)
        
    # ===== 创建 FK 控制器 约束蒙皮骨骼======
        
    for joint in joints:
        for j in range(chiyuNum):
            
            ctrl =  ctrl_shape.create_controller(joint + "FKCon"+ str(j) , size=0.6*con_size, shape_type="Circle", color=20,orientation=(0, 0, 90))
            
            temp_constraint = cmds.parentConstraint(joint + "FK"+ str(j),ctrl,mo=False)
            cmds.delete(temp_constraint)

            
            cmds.parent(ctrl, joint + 'FKRotC' + str(j))
            
            
            
            
            cmds.parentConstraint(joint + "FK"+ str(j), joint + "Skin"+ str(j))[0]
            cmds.scaleConstraint(joint + "FK"+ str(j), joint + "Skin"+ str(j))[0]
            
  

    # ===== 建立旋转层级和连接 =====
        
    for joint in joints:
        for j in range(chiyuNum):
            if j + 1 <= chiyuNum:
                cmds.parent(joint + "FKRotB" + str(j), joint + "FKRotA" + str(j))
                cmds.parent(joint + "FKRotA" + str(j+1), joint + "FKRotB" + str(j))
        
        for j in range(chiyuNum):
            if j + 1 <= chiyuNum:
                cmds.parent(joint + "FKRotC" + str(j), joint + "FKRotB" + str(j))
                cmds.parent(joint + "FKRotA" + str(j+1), joint + "FKRotC" + str(j))
        
        for j in range(chiyuNum):
            if j + 1 <= chiyuNum:
                cmds.parent(joint + "FKRotA" + str(j+1), joint + "FK" + str(j))
                cmds.parent(joint + "FK" + str(j), joint + "FKCon" + str(j))

        
        for j in range(chiyuNum):
            cmds.connectAttr(joint + "IK" + str(j) + ".t", joint + "FKRotA" + str(j) + ".t", f=True)
            cmds.connectAttr(joint + "IK" + str(j) + ".r", joint + "FKRotA" + str(j) + ".r", f=True)
            cmds.connectAttr(joint + "IK" + str(j) + ".s", joint + "FKRotA" + str(j) + ".s", f=True)
        
        last_fk = joint + "FK" + str(chiyuNum - 1)
        cmds.addAttr(last_fk, ln="rootRotx", at="double", k=True)
        cmds.addAttr(last_fk, ln="rootRoty", at="double", k=True)
        cmds.addAttr(last_fk, ln="rootRotz", at="double", k=True)
        cmds.connectAttr(last_fk + ".rootRotx", joint + "FKRotB0.rx", f=True)
        cmds.connectAttr(last_fk + ".rootRoty", joint + "FKRotB0.ry", f=True)
        cmds.connectAttr(last_fk + ".rootRotz", joint + "FKRotB0.rz", f=True)
        
        cmds.addAttr(last_fk, ln="rotx", at="double", k=True)
        cmds.addAttr(last_fk, ln="roty", at="double", k=True)
        cmds.addAttr(last_fk, ln="rotz", at="double", k=True)
        
        for j in range(chiyuNum):
            cmds.connectAttr(last_fk + ".rotx", joint + "FKRotC" + str(j) + ".rx", f=True)
            cmds.connectAttr(last_fk + ".roty", joint + "FKRotC" + str(j) + ".ry", f=True)
            cmds.connectAttr(last_fk + ".rotz", joint + "FKRotC" + str(j) + ".rz", f=True)
    
    # ===== 动力学曲线定位 =====
    
    
    ik_curve = f"{prefix}wingCurveDyn"
    
    if cmds.objExists(ik_curve):
        shap_curve_ik = cmds.listRelatives(ik_curve, s=True)
        
        if shap_curve_ik:
            for joint in joints:
                end_pbn = cmds.listRelatives(joint, c=True, type="joint")
                
                if not end_pbn:
                    print(f"警告: {joint} 没有子关节")
                    continue
                
                aim_loc = joint + "IkCurveAimLoc"
                aim_loc_grp = joint + "IkCurveAimLocGrp"
                
                cmds.spaceLocator(p=(0,0,0), n=aim_loc)
                cmds.group(n=aim_loc_grp)
                
                temp_constraint = cmds.parentConstraint(end_pbn[0], aim_loc_grp)[0]
                cmds.delete(temp_constraint)
                cmds.parent(aim_loc_grp, joint)
                
                aim_loc_b = joint + "IkCurveAimLocB"
                cmds.spaceLocator(p=(0,0,0), n=aim_loc_b)
                
                temp_constraint = cmds.parentConstraint(end_pbn[0], aim_loc_b)[0]
                cmds.delete(temp_constraint)
                
                npoc = cmds.createNode('nearestPointOnCurve', n=joint + "nearestPointOnCurveIK")
                cmds.connectAttr(shap_curve_ik[0] + ".worldSpace[0]", npoc + ".inputCurve", f=True)
                cmds.connectAttr(aim_loc_b + ".t", npoc + ".inPosition", f=True)
                param = cmds.getAttr(npoc + ".parameter")
                cmds.delete(npoc)
                
                poci = cmds.createNode('pointOnCurveInfo', n=joint + "pointOnCurveInfoAimIK")
                cmds.connectAttr(shap_curve_ik[0] + ".worldSpace[0]", poci + ".inputCurve", f=True)
                cmds.setAttr(poci + ".parameter", param)
                cmds.connectAttr(poci + ".position", aim_loc_b + ".t", f=True)
                
                cmds.pointConstraint(aim_loc_b, aim_loc)
                cmds.setAttr(aim_loc_grp+'.visibility',0)
    cmds.select(cl=True)
    for joint in joints:
        aim_loc_b = joint + "IkCurveAimLocB"
        if cmds.objExists(aim_loc_b):
            cmds.select(aim_loc_b, add=True)
    
    if cmds.objExists(curve_aim_loc_grp_name):
        selected = cmds.ls(sl=True)
        if selected:
            cmds.parent(selected, curve_aim_loc_grp_name)
    
    # ===== 创建 IK 曲线 =====
        
    for joint in joints:
        base_bn = joint + "IK0"
        end_bn = joint + "IK" + str(chiyuNum)
        
        joint_positions = []
        current_joint = base_bn
        
        cmds.select(base_bn)
        while current_joint != end_bn:
            pos = cmds.joint(current_joint, q=True, p=True, a=True)
            joint_positions.append(pos)
            
            cmds.pickWalk(d='down')
            sel = cmds.ls(sl=True)
            if not sel:
                break
            current_joint = sel[0]
        
        sel = cmds.ls(sl=True)
        if sel:
            current_joint = sel[0]
            pos = cmds.joint(current_joint, q=True, p=True, a=True)
            joint_positions.append(pos)
        
        if len(joint_positions) >= 2:
            point_list = [(pos[0], pos[1], pos[2]) for pos in joint_positions]
            curve = cmds.curve(d=3, p=point_list)
            curve = cmds.rename(curve, base_bn + "CurveA")
    
    # ===== 创建动力学系统 =====
        
    curves = []
    for joint in joints:
        curve_name = joint + "IK0CurveA"
        if cmds.objExists(curve_name):
            curves.append(curve_name)
            cmds.select(curve_name, add=True)
    
    if curves:
        cmds.MakeCurvesDynamic()
        cmds.rename("hairSystem1", f"{prefix}wing_hairSystem")
        cmds.rename("hairSystem1Follicles", f"{prefix}wing_hairSystem1Follicles")
        cmds.rename("hairSystem1OutputCurves", f"{prefix}wing_hairSystem1OutputCurves")
        cmds.rename("nucleus1", f"{prefix}wing_nucleus")
        output_curves = cmds.listRelatives(f"{prefix}wing_hairSystem1OutputCurves", children=True)
                      
        if output_curves:
            for i, curve in enumerate(output_curves):
                if i < len(joints):
                    new_name = f"{joints[i]}_outputCurve"
                    cmds.rename(curve, new_name)
        

        cmds.select(f"{prefix}wing_hairSystem1Follicles", replace=True)
        cmds.select(f"{prefix}wing_nucleus", add=True)
        cmds.select(f"{prefix}wing_hairSystem", add=True)
        cmds.select(f"{prefix}wing_hairSystem1OutputCurves", add=True)

        group = cmds.group(name=dyn_grp)
    
    follicles = cmds.listRelatives(f"{prefix}wing_hairSystem1Follicles", children=True)
    for follicle in follicles:
        cmds.setAttr(follicle+'.pointLock',1)

    
    cmds.disconnectAttr("time1.outTime",f"{side}_wing_hairSystemShape.currentTime")
    cmds.disconnectAttr("time1.outTime",f"{side}_wing_nucleus.currentTime")

    # ===== 创建 IK 手柄 =====
        
    for joint in joints:
        base_bn = joint + "IK0"
        end_bn = joint + "IK" + str(chiyuNum)
        
        cmds.select(base_bn + ".rotatePivot")
        cmds.select(end_bn + ".rotatePivot", add=True)
        cmds.select(joint + "_outputCurve", add=True)
        
        ik_handle = cmds.ikHandle(sol="ikSplineSolver", ccv=False, pcv=False)[0]
        cmds.rename(ik_handle, joint + "ikhandle")
    
    if not cmds.objExists(ik_grp):
        cmds.select([joint + "ikhandle" for joint in joints])
        cmds.group(n=ik_grp)
    
    # ===== 创建曲线簇和定位器（前2个控制点） =====
    
    
    for joint in joints:
        curve_ika = joint + "IK0CurveA"
        
        for a in range(2):
            cmds.select(curve_ika + ".cv[" + str(a) + "]")
            cluster_node = cmds.cluster(envelope=1)
            cluster_name = curve_ika + "cluster" + str(a)
            cmds.rename(cluster_node[1], cluster_name)
            
            loc_name = curve_ika + "loc" + str(a)
            cmds.spaceLocator(p=(0,0,0), n=loc_name)
            
            constraint = cmds.parentConstraint(cluster_name, loc_name)[0]
            cmds.delete(constraint)
            
            cmds.parent(cluster_name, loc_name)
            cmds.parent(loc_name, joint)
            cmds.setAttr(loc_name+'.visibility',0)
            
    
    # ===== 创建曲线簇（chiyuNum-1个控制点） =====
    
    
    for joint in joints:
        curve_ika = joint + "IK0CurveA"
        
        # 从第2个控制点开始，到 chiyuNum 结束（共 chiyuNum-1 个点）
        for a in range(2, chiyuNum + 1):
            cmds.select(curve_ika + ".cv[" + str(a) + "]")
            cluster_node = cmds.cluster(envelope=1)
            cluster_name = curve_ika + "cluster" + str(a)
            cmds.rename(cluster_node[1], cluster_name)
    
    # ===== 为后 chiyuNum-1 个簇创建控制器 =====
    
    
    for joint in joints:
        for a in range(2, chiyuNum + 1):
            cmds.select(joint + "IK0CurveAcluster" + str(a), add=True)
    
    selected_clusters = cmds.ls(sl=True)
    
    for sel in selected_clusters:
        ctrl = ctrl_shape.create_controller(sel + "Con", size=0.5*con_size, shape_type="Sphere", color=13)
        wing_loc.lock_and_hide_transform(ctrl,lock_translate=False, lock_rotate=False, lock_scale=True)
        grp = cmds.group(empty=True, n=sel + "ConGrp")
        grp_a = cmds.group(empty=True, n=sel + "ConGrpA")
        cmds.parent(grp,grp_a)
        cmds.parent(ctrl,grp)
        
        temp_con = cmds.parentConstraint(sel,grp_a,mo=False)
        cmds.delete(temp_con)
        cmds.parentConstraint(ctrl, sel, mo=False)
        
        cmds.connectAttr('wing_follow_Grp.scale',grp_a+'.scale')
    # ===== 整理簇组 =====
    
    
    cmds.select(cl=True)
    for joint in joints:
        for a in range(2, chiyuNum + 1):
            cmds.select(joint + "IK0CurveAcluster" + str(a), add=True)
    
    wing_cluster_grp = cmds.group(n=f"{prefix}wingClusterGrp")
    
    if cmds.objExists(cluster_lik_grp):
        cmds.parent(wing_cluster_grp,cluster_lik_grp)
    
    # ===== 隐藏部分控制器组 =====
    
    
    cmds.select(cl=True)
    for joint in joints:
        for a in range(2, chiyuNum ):
            grp_name = joint + "IK0CurveAcluster" + str(a) + "ConGrpA"
            if cmds.objExists(grp_name):
                cmds.select(grp_name, add=True)
                cmds.setAttr(grp_name + ".visibility", 0)
    
    if not cmds.objExists(ik_con_grp):
        cmds.group(n=ik_con_grp)
    
    # ===== 目标约束 =====

    for joint in joints:
        cmds.select(joint)
        cmds.select(joint + "IK0CurveAcluster" + str(chiyuNum) + "ConGrpA", add=True)
        cmds.aimConstraint(offset=(0,0,0), weight=1, aimVector=(1,0,0), 
                        upVector=(0,1,0), worldUpType="objectrotation",
                        worldUpVector=(0,1,0), worldUpObject=(joint + "CurvePosLoc"))
        

    # ====打组添加属性=======   
    selected = []
    for joint in joints:
        obj = joint + "IK0CurveAcluster" + str(chiyuNum) + "ConGrpA"
        
        if cmds.objExists(obj):
            selected.append(obj)
    
    if selected:
        # 直接打组选中的物体
        group = cmds.group(selected, n=f"{prefix}wingIKControllersGrp")
        
    else:
        print("⚠️ 没有找到任何物体")

    for joint in joints:
        cmds.addAttr(joint + "IK0CurveAcluster" + str(chiyuNum) + "Con", longName='follow', attributeType='float', 
                     defaultValue=1, minValue=0, maxValue=10, keyable=True)
    # ===== 权重约束 =====
    
    
    for joint in joints:
        # 计算权重步长
        weight_step = 1.0 / (chiyuNum - 1)
        
        obj_a = joint + "IK0CurveAloc1"
        obj_b = joint + "IK0CurveAcluster" + str(chiyuNum) + "Con"
        
        
        # 为每个中间簇创建约束（从 cluster2 到 cluster(chiyuNum-1)）
        for i in range(2, chiyuNum):
            obj_x = joint + "IK0CurveAcluster" + str(i) + "Con"
            
            # 计算权重：从 cluster2 到最后一个簇均匀过渡
            # cluster2: avalue最大，bvalue最小
            # 最后一个簇: avalue最小，bvalue最大
            avalue = 1.0 - weight_step * (i - 1)
            bvalue = weight_step * (i - 1)
            
            cmds.select(obj_a)
            cmds.select(obj_b, toggle=True)
            cmds.select(obj_x, toggle=True)
            constraint = cmds.parentConstraint(mo=True)[0]
            mult = cmds.createNode('multiplyDivide', name=constraint + '_mult')
            
            mult 
            cmds.setAttr(mult  + ".input2X", avalue)
            cmds.setAttr(constraint + "." + obj_b + "W1", bvalue)
            cmds.connectAttr(mult + '.outputX',constraint + "." + obj_a + "W0")
            cmds.connectAttr(joint + "IK0CurveAcluster" + str(chiyuNum) + "Con.follow",mult + '.input1X')
            
    
    # ===== 整理 IK 组 =====

    
    cmds.select(ik_con_grp)
    cmds.select(con_l_grp, add=True)
    wing_ik_all_grp = cmds.group(n=ik_all_grp)
    cmds.parent(f"{prefix}wingIKControllersGrp",f"{prefix}wing_IK_All_Grp")
    cmds.setAttr(cluster_lik_grp + ".visibility", 0)
    
    cmds.select(dyn_grp)
    cmds.select(cluster_lik_grp, add=True)
    cmds.select(curve_aim_loc_grp_name, add=True)
    if cmds.objExists(curve_grp):
        cmds.select(curve_grp, add=True)
    cmds.select(ik_grp, add=True)
    if cmds.objExists(not_move_grp):
        cmds.select(not_move_grp, add=True)
    cmds.parent()
    
    # ===== 创建动力学控制点 =====
    
    
    for joint in joints:
        dyncon_grp = joint + "IK0CurveAcluster" + str(chiyuNum) + "ConGrpA"
        
        cmds.select(cl=True)
        pos_grp = cmds.group(empty=True, n=joint + "IkCurveAimLocPos")
        
        temp_con = cmds.parentConstraint(dyncon_grp, pos_grp)[0]
        cmds.delete(temp_con)
        
        cmds.parent(pos_grp, joint + "IkCurveAimLoc")
        cmds.pointConstraint(pos_grp, dyncon_grp)

    
    
    # ===== 整理大纲 =====
    
    cmds.parent(f'{prefix}wingClusterLDynGrp',not_move_grp)
    cmds.setAttr(f'{prefix}wing_hairSystemShape.simulationMethod', 1);
    setup_wing_fk_groups(f'{prefix}scapula')
    cmds.group(empty=True, n=f"{prefix}wing_All_Grp")
    

    
    cmds.parent(f"{prefix}wing_IK_All_Grp",f"{prefix}scapula_ConGrpA",f"{prefix}wing_FK_All_Grp",f"{prefix}wing_All_Grp")
    cmds.parentConstraint("wing_follow_Grp",f"{prefix}scapula_ConGrpA",maintainOffset=True, weight=1)
    cmds.scaleConstraint("wing_follow_Grp",f"{prefix}scapula_ConGrpA",maintainOffset=True, weight=1)

    cmds.orientConstraint(f"{prefix}wrist",f"{prefix}wingCurveIKcluster4ConGrpA",maintainOffset=True, weight=1)
    cmds.orientConstraint(f"{prefix}wrist",f"{prefix}wingCurveIKcluster3ConGrpA",maintainOffset=True, weight=1)
    cmds.orientConstraint(f"{prefix}ebow",f"{prefix}wingCurveIKcluster2ConGrpA",maintainOffset=True, weight=1)
    cmds.orientConstraint(f"{prefix}shoulder",f"{prefix}wingCurveIKcluster1ConGrpA",maintainOffset=True, weight=1)
    cmds.orientConstraint(f"{prefix}scapula",f"{prefix}wingCurveIKcluster0ConGrpA",maintainOffset=True, weight=1)
    




    if not cmds.objExists("wingNotMoveGrp"):
        cmds.group(empty=True, n="wingNotMoveGrp")

    # 安全地设置父级，避免警告
    try:
        current_parent = cmds.listRelatives("wing_follow_Grp", parent=True)
        if not current_parent or current_parent[0] != "wingNotMoveGrp":
            cmds.parent("wing_follow_Grp", "wingNotMoveGrp")
            
        # 如果已经是子物体，什么也不做
        cmds.parent(f"{prefix}wingNotMoveGrp", "wingNotMoveGrp")
    except Exception as e:
        print(f"Warning: Could not parent wing_follow_Grp: {e}")

    cmds.setAttr('wingNotMoveGrp.visibility', 0)    
    

    # 创建或获取显示控制控制器
    if not cmds.objExists("wing_showCon"):
        vis_ctrl = ctrl_shape.create_controller("wing_showCon", size=5*con_size, shape_type="PointyLocal", color=9)
        wing_loc.lock_and_hide_transform(vis_ctrl,lock_translate=True, lock_rotate=True, lock_scale=True)
        vis_ctrl_grp = cmds.group(empty=True, name="wing_showConGrp")
        cmds.parent(vis_ctrl, vis_ctrl_grp)
        
        # 添加属性
        attrs = ["ik_con_show", "fk_con_show", "ik_all_show"]
        for attr in attrs:
            cmds.addAttr(vis_ctrl, longName=attr, attributeType="bool")
            cmds.setAttr(vis_ctrl + "." + attr, edit=True, channelBox=True)
            cmds.setAttr(vis_ctrl + "." + attr, 1)
        cmds.setAttr(vis_ctrl_grp + ".ty", 25 * con_size)
    else:
        vis_ctrl = "wing_showCon"

    # 连接可见性（使用 force=True 自动处理已有连接）
    if cmds.objExists(f"{prefix}wing_FK_All_Grp"):
        cmds.connectAttr(vis_ctrl + '.ik_con_show', f"{prefix}wing_FK_All_Grp.visibility", force=True)

    if cmds.objExists(f"{prefix}wingIKControllersGrp"):
        cmds.connectAttr(vis_ctrl + '.fk_con_show', f"{prefix}wingIKControllersGrp.visibility", force=True)

    if cmds.objExists(f"{prefix}wingConLGrp"):
        cmds.connectAttr(vis_ctrl + '.ik_all_show', f"{prefix}wingConLGrp.visibility", force=True)

    cmds.parentConstraint("wing_follow_Grp","wing_showConGrp",maintainOffset=True, weight=1)
    cmds.scaleConstraint("wing_follow_Grp","wing_showConGrp",maintainOffset=True, weight=1)

    
    
    print(f" {prefix}侧羽毛绑定完成！")
    


def add_to_existing_expression(wing_joints,side='l_',do_mirror=True,con_size=1):
    """
    添加实时动力学表达式


    
    """

    # ===== 创建动力学控制面板 =====
    dyn_con = "DynCon"
    reverse_node="Dyn_rev"
    condition_node="Dyn_cond"
    exp_name = "dynControlEXP"
    side_mirror = 'r' if side == 'l' else 'l'
    if not cmds.objExists(dyn_con):
    
        dyn_con = ctrl_shape.create_controller("DynCon", size=3.0*con_size, shape_type="Star", color=22)
        dyn_con_grp = cmds.group(empty=True, n="DynConGrp")
        wing_loc.lock_and_hide_transform(dyn_con,lock_translate=True, lock_rotate=True, lock_scale=True)
        cmds.parent(dyn_con, dyn_con_grp)
        cmds.parent(dyn_con_grp, 'wing_showCon')
        cmds.setAttr(dyn_con_grp+'.ty',0)

        cmds.addAttr('wing_showConGrp',ln="dyn_con_show", at="bool")
        cmds.setAttr('wing_showConGrp' + ".dyn_con_show", e=True, channelBox=True)
        cmds.setAttr('wing_showConGrp' + ".dyn_con_show", 1)

        cmds.addAttr(dyn_con, ln="dynSimulate", at="bool")
        cmds.setAttr(dyn_con + ".dynSimulate", e=True, channelBox=True)
        
        cmds.addAttr(dyn_con, ln="ctime", at="double", dv=0)
        cmds.setAttr(dyn_con + ".ctime", e=True, keyable=True)
        
        cmds.addAttr(dyn_con, ln="startFrame", at="double", dv=0)
        cmds.setAttr(dyn_con + ".startFrame", e=True, channelBox=True)
        
        cmds.addAttr(dyn_con, ln="playStyle", at="enum", en="autoDyn:realTimeDyn:")
        cmds.setAttr(dyn_con + ".playStyle", e=True, channelBox=True)
        
        cmds.addAttr(dyn_con, ln="motionDrag", at="double", dv=0)
        cmds.setAttr(dyn_con + ".motionDrag", e=True, keyable=True)
        
        cmds.addAttr(dyn_con, ln="startCurveAttract", at="double", dv=0)
        cmds.setAttr(dyn_con + ".startCurveAttract", e=True, keyable=True)

        
        cmds.setAttr(dyn_con + ".startFrame", 1)
        cmds.setAttr(dyn_con + ".motionDrag", 0.5)
        cmds.setAttr(dyn_con + ".startCurveAttract", 0.1)
        cmds.setAttr(dyn_con + ".dynSimulate", 0)

        reverse_node = cmds.createNode('reverse', name='Dyn_rev')
        condition_node= cmds.createNode('condition', name='Dyn_cond')
        cmds.setAttr(condition_node + ".colorIfTrueR", 1)
        cmds.setAttr(condition_node + ".colorIfFalseR", 3)
        cmds.connectAttr(dyn_con+'.dynSimulate',condition_node+'.firstTerm')
        cmds.connectAttr(dyn_con+'.dynSimulate',reverse_node+'.inputX')


    cmds.connectAttr(condition_node + '.outColorR', f"{side_mirror}_wing_hairSystem.simulationMethod")
    for cv in wing_joints:
        cmds.blendShape(cv+'IK0CurveA',cv+'_outputCurve',name=cv+"cvBs")[0]
        cmds.connectAttr(reverse_node+'.outputX',cv+"cvBs."+cv+'IK0CurveA')

    

    
    # 获取选中的物体
    if do_mirror == True:
        
        cmds.connectAttr(dyn_con+'.startCurveAttract',"l_wing_hairSystemShape.startCurveAttract")
        cmds.connectAttr(dyn_con+'.motionDrag',"l_wing_hairSystemShape.motionDrag")
        cmds.connectAttr(dyn_con+'.startCurveAttract',"r_wing_hairSystemShape.startCurveAttract")
        cmds.connectAttr(dyn_con+'.motionDrag',"r_wing_hairSystemShape.motionDrag")

        cmds.connectAttr(condition_node + '.outColorR', f"{side}_wing_hairSystem.simulationMethod")
        selected = list_curve_transforms_in_hierarchy([
            "l_wingIKControllersGrp", "l_scapula_ConGrpA", "l_wingConLGrp",
            "r_wingIKControllersGrp", "r_scapula_ConGrpA", "r_wingConLGrp"
        ])
        
        # 构建基础表达式 - 镜像模式
        exp_string = f'''float $autotime = time1.outTime;
        if(frame <= {dyn_con}.startFrame)
            {dyn_con}.ctime = $autotime;
        else
            {dyn_con}.ctime += 1;

        if({dyn_con}.playStyle == 0)
        {{
            l_wing_nucleus.currentTime = $autotime;
            r_wing_nucleus.currentTime = $autotime;
        }}
        else
        {{
            l_wing_nucleus.currentTime = {dyn_con}.ctime;
            r_wing_nucleus.currentTime = {dyn_con}.ctime;
        }}

        l_wing_nucleus.startFrame = {dyn_con}.startFrame;
        r_wing_nucleus.startFrame = {dyn_con}.startFrame;
        l_wing_hairSystemShape.currentTime = l_wing_nucleus.currentTime;
        r_wing_hairSystemShape.currentTime = r_wing_nucleus.currentTime;

        // ===== 选择物体关联表达式 =====
        float $tx, $ty, $tz, $rx, $ry, $rz;
        '''
    else:

        
        cmds.connectAttr(dyn_con+'.startCurveAttract',f"{side}_wing_hairSystemShape.startCurveAttract")
        cmds.connectAttr(dyn_con+'.motionDrag',f"{side}_wing_hairSystemShape.motionDrag")
        selected = list_curve_transforms_in_hierarchy([
            f"{side}_wingIKControllersGrp", 
            f"{side}_scapula_ConGrpA",
            f"{side}_wingConLGrp"
        ])
        
        nucleus = f"{side}_wing_nucleus"
        hair_system = f"{side}_wing_hairSystemShape"
        
        # 构建基础表达式 - 单侧模式
        exp_string = f'''float $autotime = time1.outTime;
if(frame <= {dyn_con}.startFrame)
    {dyn_con}.ctime = $autotime;
else
    {dyn_con}.ctime += 1;

if({dyn_con}.playStyle == 0)
    {nucleus}.currentTime = $autotime;
else
    {nucleus}.currentTime = {dyn_con}.ctime;

{nucleus}.startFrame = {dyn_con}.startFrame;
{hair_system}.currentTime = {nucleus}.currentTime;

// ===== 选择物体关联表达式  =====
float $tx, $ty, $tz, $rx, $ry, $rz;
'''
    
    # 检查是否找到了物体
    if not selected:
        return None
    
    # 添加物体属性读取
    for i, obj in enumerate(selected):
        exp_string += f'''
// {i+1}: {obj}
$tx = {obj}.tx;
$ty = {obj}.ty;
$tz = {obj}.tz;
$rx = {obj}.rx;
$ry = {obj}.ry;
$rz = {obj}.rz;
'''
    
    # 如果表达式已存在，先删除再创建
    if cmds.objExists(exp_name):
        cmds.delete(exp_name)
    
    # 创建新表达式
    cmds.expression(
        string=exp_string,
        alwaysEvaluate=True,
        unitConversion="all",
        name=exp_name
    )
    
    print(f"成功创建表达式: {exp_name}")
    return exp_name





def feather_rig(root_joint, base_joint, wing_joints, side="l",do_mirror=True,  chiyuNum=4, get_con_size=1,dynCrete=True):
    """
    羽毛/翅膀绑定系统
    
    Args:
        root_joint: 翅膀根部骨骼
        base_joint: 基础骨骼（用于镜像定位）
        wing_joints: 翅膀骨骼列表
        do_mirror: 是否镜像
        side: 当前侧标识 ('l' 或 'r')
        chiyuNum: 羽毛数量
        con_size: 控制器大小
    """
    con_size=wing_loc.get_x_distance(root_joint)/30*get_con_size


    # 检查输入
    if not wing_joints:
        cmds.error("wing_joints 列表不能为空！")
        return
    
    # 整理骨骼
    cmds.select(wing_joints)
    wing_loc.auto_parent_branches_by_x_threshold(root_joint)
    
    # 镜像骨骼 
    
    wing_loc.mirror_wing(root_joint, base_joint, do_mirror)
    
    # 自动判断并生成镜像列表
    first_joint = wing_joints[0]
    if first_joint.startswith('l_'):
        wing_joints_mirr = [name.replace('l_', 'r_') for name in wing_joints]
        mirror_side = "r"
    elif first_joint.startswith('r_'):
        wing_joints_mirr = [name.replace('r_', 'l_') for name in wing_joints]
        mirror_side = "l"
    else:
        # 如果没有标准前缀，根据 side 参数判断
        if side == "l":
            wing_joints_mirr = [name.replace('l_', 'r_', 1) for name in wing_joints]
            mirror_side = "r"
        elif side == "r":
            wing_joints_mirr = [name.replace('r_', 'l_', 1) for name in wing_joints]
            mirror_side = "l"
        else:
            cmds.warning(f"无法识别侧标识: {first_joint}，使用 side 参数: {side}")
            wing_joints_mirr = []
            mirror_side = "r" if side == "l" else "l"
    

    # 创建绑定 - 当前侧
    cmds.select(wing_joints)
    feather_binding(side, chiyuNum, con_size)
    
    # 创建绑定 - 镜像侧（如果存在镜像骨骼）
    if  do_mirror:
        cmds.select(wing_joints_mirr)
        feather_binding(mirror_side, chiyuNum, con_size)

    
    # 添加动力学表达式
    if dynCrete==True:
        add_to_existing_expression(wing_joints,side, do_mirror,con_size)
    
    # 返回镜像列表以便后续使用
    return wing_joints_mirr


