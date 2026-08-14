import maya.cmds as cmds
import os

def auto_parent_branches(root_joint):
    """
    根据X轴位置分配分支骨骼到主骨骼
    左侧：按X从小到大分配（负X到正X）
    右侧：按X从大到小分配（正X到负X）
    自动检测左右侧
    """
    if not cmds.objExists(root_joint):
        print(f"❌ 根骨不存在: {root_joint}")
        return
    
    # ===== 1. 获取主骨骼链 =====
    all_children = cmds.listRelatives(root_joint, allDescendents=True, type='joint')
    if not all_children:
        print(f"❌ {root_joint} 没有子骨骼")
        return
    
    # 找出主链
    main_chain = [root_joint]
    current = root_joint
    
    while True:
        children = cmds.listRelatives(current, children=True, type='joint')
        if not children:
            break
        
        if len(children) > 1:
            current_pos = cmds.xform(current, q=True, ws=True, t=True)
            closest_child = None
            min_dist = float('inf')
            for child in children:
                child_pos = cmds.xform(child, q=True, ws=True, t=True)
                dist = abs(child_pos[0] - current_pos[0])
                if dist < min_dist:
                    min_dist = dist
                    closest_child = child
            current = closest_child
        else:
            current = children[0]
        
        if current:
            main_chain.append(current)
        else:
            break
    
    # 获取主骨骼的X坐标
    main_data = []
    for joint in main_chain:
        pos = cmds.xform(joint, q=True, ws=True, t=True)
        main_data.append((joint, pos[0]))
    
    # 根据X坐标排序（从小到大）
    main_data.sort(key=lambda x: x[1])
    main_joints = [m[0] for m in main_data]
    
    for i, j in enumerate(main_joints):
        pos = cmds.xform(j, q=True, ws=True, t=True)
       
    
    # 判断左右侧（根据根骨骼的X坐标）
    root_x = cmds.xform(root_joint, q=True, ws=True, t=True)[0]
    if root_x < 0:
        side = 'r'
        
    else:
        side = 'l'
    
    # ===== 2. 获取分支骨骼 =====
    branch_joints = cmds.ls(selection=True)
    branch_joints = [j for j in branch_joints if cmds.nodeType(j) == 'joint']
    
    if not branch_joints:
        cmds.warning("请先选择分支骨骼！")
        return
    
  
    for j in branch_joints:
        pos = cmds.xform(j, q=True, ws=True, t=True)
        
    # ===== 3. 按主骨骼分组 =====
    groups_dict = {main: [] for main in main_joints}
    
    for branch in branch_joints:
        pos = cmds.xform(branch, q=True, ws=True, t=True)
        branch_x = pos[0]
        
        parent = None
        
        if side == 'l':
            # 左侧：分支X > A 且 分支X <= B → 分配给 A
            for i in range(len(main_data) - 1, -1, -1):
                main_x = main_data[i][1]
                if branch_x > main_x:
                    parent = main_data[i][0]
                    break
            if parent is None:
                parent = main_data[0][0]
        else:
            # 右侧：分支X < A 且 分支X >= B → 分配给 A
            for i in range(len(main_data)):
                main_x = main_data[i][1]
                if branch_x < main_x:
                    parent = main_data[i][0]
                    break
            if parent is None:
                parent = main_data[-1][0]
        
        groups_dict[parent].append(branch)
       
    
    # ===== 4. 创建组和约束 =====
    created_groups = []
    created_constraints = []
    
    for main_joint, branches in groups_dict.items():
        if not branches:
            continue
        
        group_name = main_joint + '_followGrp'
        if cmds.objExists(group_name):
            cmds.delete(group_name)
        
        group = cmds.createNode('transform', name=group_name)
        
        main_pos = cmds.xform(main_joint, q=True, ws=True, t=True)
        main_rot = cmds.xform(main_joint, q=True, ws=True, rotation=True)
        main_scale = cmds.getAttr(main_joint + '.scale')[0]
        
        cmds.setAttr(group + '.translate', main_pos[0], main_pos[1], main_pos[2])
        cmds.setAttr(group + '.rotate', main_rot[0], main_rot[1], main_rot[2])
        cmds.setAttr(group + '.scale', main_scale[0], main_scale[1], main_scale[2])
        
        for branch in branches:
            current_parent = cmds.listRelatives(branch, parent=True)
            if current_parent:
                cmds.parent(branch, world=True)
            cmds.parent(branch, group)
        
        cmds.parentConstraint(main_joint, group, maintainOffset=True)[0]
        cmds.connectAttr('wing_follow_Grp.scale',group+'.scale')
        
        
        
        
       

    return created_groups, created_constraints



def auto_parent_branches_by_x_threshold(root_joint):
    """
    根据X轴阈值分配分支骨骼到主骨骼
    分配逻辑：分支骨骼X位置在 A < X <= B 之间，分配给 A（左边的主骨骼）
    
    使用方法：
        1. 先选择分支骨骼
        2. 运行: auto_parent_branches_by_x_threshold("wing_root")
    """
    # ===== 1. 从根骨获取主骨骼链 =====
    if not cmds.objExists(root_joint):
        print(f"❌ 根骨不存在: {root_joint}")
        return
    
    # 获取所有子骨骼
    all_children = cmds.listRelatives(root_joint, allDescendents=True, type='joint')
    
    if not all_children:
        print(f"❌ {root_joint} 没有子骨骼")
        return
    
    # 找出主链
    main_chain = [root_joint]
    current = root_joint
    
    while True:
        children = cmds.listRelatives(current, children=True, type='joint')
        if not children:
            break
        
        if len(children) > 1:
            current_pos = cmds.xform(current, q=True, ws=True, t=True)
            closest_child = None
            min_dist = float('inf')
            for child in children:
                child_pos = cmds.xform(child, q=True, ws=True, t=True)
                dist = abs(child_pos[0] - current_pos[0])
                if dist < min_dist:
                    min_dist = dist
                    closest_child = child
            current = closest_child
        else:
            current = children[0]
        
        if current:
            main_chain.append(current)
        else:
            break
    
    # 按X轴排序主骨骼
    main_data = []
    for joint in main_chain:
        pos = cmds.xform(joint, q=True, ws=True, t=True)
        main_data.append((joint, pos[0]))
    
    main_data.sort(key=lambda x: x[1])
    main_joints = [m[0] for m in main_data]
    
    
    
    # ===== 2. 获取选中的分支骨骼 =====
    branch_joints = cmds.ls(selection=True)
    branch_joints = [j for j in branch_joints if cmds.nodeType(j) == 'joint']
    
    if not branch_joints:
        cmds.warning("请先选择分支骨骼！")
        return
    
    
    # ===== 3. 分配逻辑（基于X轴距离） =====
    assignment_count = {main: 0 for main in main_joints}
    assigned = 0
    
    for branch in branch_joints:
        pos = cmds.xform(branch, q=True, ws=True, t=True)
        branch_x = pos[0]
        
        # 分配逻辑：分支X > A 且 分支X <= B → 分配给 A
        # 即：分支X落在哪个主骨骼的右侧，就分配给那个主骨骼
        parent = None
        
        # 从右往左找（从最外侧开始）
        for i in range(len(main_data) - 1, -1, -1):
            main_x = main_data[i][1]
            # 如果分支X大于主骨骼X，分配给这个主骨骼
            if branch_x > main_x:
                parent = main_data[i][0]
                break
        
        # 如果分支X小于所有主骨骼（在最左边），分配给第一个主骨骼
        if parent is None:
            parent = main_data[0][0]
        
        try:
            # 断开当前父级
            current_parent = cmds.listRelatives(branch, parent=True)
            if current_parent:
                cmds.parent(branch, world=True)
            
            cmds.parent(branch, parent)
            
            assignment_count[parent] += 1
            assigned += 1
            
            
        except Exception as e:
            print(f"  ❌ {branch} 父级失败: {e}")
    


def mirror_wing(root_joint, base_joint, do_mirror=True):
    """
    自动检测前缀并镜像骨骼和网格，自动蒙皮和权重清理
    
    参数:
        root_joint: 翅膀根骨骼名称 (如 "l_scapula" 或 "r_scapula")
        base_joint: 主骨骼/父级骨骼名称 (如 "base_joint" 或 "pelvis")
        do_mirror: 是否执行镜像操作
                   True - 执行完整镜像（骨骼+网格+蒙皮+权重镜像+清理）
                   False - 只将翅膀根骨骼P给base_joint，不镜像
    
    使用方法:
        # 镜像（自动执行蒙皮和权重清理）
        mirror_wing("l_scapula", "base_joint", do_mirror=True)
        
        # 不镜像，只P给主骨骼
        mirror_wing("l_scapula", "base_joint", do_mirror=False)
    """
    # ===== 检查根骨骼是否存在 =====
    if not cmds.objExists(root_joint):
        print(f"❌ 根骨骼不存在: {root_joint}")
        return False
    
    # ===== 检查父骨骼是否存在 =====
    if not cmds.objExists("wing_follow_Grp"):
        cmds.group(empty=True, name="wing_follow_Grp")
    base_exists = cmds.objExists(base_joint)
    

    if  base_exists:
        cmds.parentConstraint(base_joint,"wing_follow_Grp")
        cmds.scaleConstraint(base_joint,"wing_follow_Grp")
    else:
        print(f"⚠️ 父骨骼不存在: {base_joint}")




    # ===== 自动检测前缀 =====
    if root_joint.startswith("l_"):
        search = "l_"
        replace = "r_"
        mesh_name = "l_wingMesh"
        mirror_mesh_name = "r_wingMesh"
        prefix = "左侧"
    elif root_joint.startswith("r_"):
        search = "r_"
        replace = "l_"
        mesh_name = "r_wingMesh"
        mirror_mesh_name = "l_wingMesh"
        prefix = "右侧"
    else:
        print(f"❌ 无法检测前缀: {root_joint}")
        return False
    
        
    # ===== 保存原始选择 =====
    original_selection = cmds.ls(selection=True)
    
    # ===== 1. 镜像操作 =====
    if do_mirror:
        
        
        # 1.1 镜像骨骼
        if cmds.objExists(root_joint):
            cmds.select(root_joint)
            try:
                cmds.mirrorJoint(
                    root_joint,
                    mirrorYZ=True,
                    mirrorBehavior=True,
                    searchReplace=[search, replace]
                )
            except Exception as e:
                print(f"   ❌ 镜像骨骼失败: {e}")
                return False
        
        # 1.2 镜像网格
        if cmds.objExists(mesh_name):
            if cmds.objExists(mirror_mesh_name):
                cmds.delete(mirror_mesh_name)
                print(f"   删除已存在的网格: {mirror_mesh_name}")
            
            cmds.select(mesh_name)
            duplicated = cmds.duplicate(returnRootsOnly=True)[0]
            duplicated = cmds.rename(duplicated, mirror_mesh_name)
            
            # 解锁并镜像
            attrs = [".tx", ".ty", ".tz", ".rx", ".ry", ".rz", ".sx", ".sy", ".sz"]
            for attr in attrs:
                try:
                    cmds.setAttr(f"{mirror_mesh_name}{attr}", lock=False)
                except:
                    pass
            
            cmds.setAttr(f"{mirror_mesh_name}.scaleX", -1)
            cmds.select(mirror_mesh_name)
            cmds.makeIdentity(apply=True, t=1, r=1, s=1, n=0)
            

            
            
            # 创建曲线
            create_wing_curve(mirror_mesh_name, replace)
    
    # ===== 2. 蒙皮和权重处理 =====
    if do_mirror:
        
        # 确定镜像后的骨骼
        if search == "l_":
            mirrored_root = root_joint.replace("l_", "r_")
            source_root = root_joint
            source_mesh = mesh_name
            target_mesh = mirror_mesh_name
        else:
            mirrored_root = root_joint.replace("r_", "l_")
            source_root = root_joint
            source_mesh = mesh_name
            target_mesh = mirror_mesh_name
        
        # 获取所有骨骼
        
        # 创建目标蒙皮
        if cmds.objExists(mirrored_root) and cmds.objExists(target_mesh):
            
            skin_node = cmds.skinCluster(
                mirrored_root, target_mesh,
                toSelectedBones=False,
                bindMethod=0,
                skinMethod=1,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=8,
                dropoffRate=4,
                obeyMaxInfluences=True
            )[0]
            
            # 查询蒙皮节点
            source_shape = cmds.listRelatives(source_mesh, shapes=True)[0]
            source_skin= cmds.listConnections(source_shape, type='skinCluster')

            target_shape = cmds.listRelatives(target_mesh, shapes=True)[0]
            target_skin = cmds.listConnections(target_shape, type='skinCluster')
           
            
            cmds.copySkinWeights(
            sourceSkin=source_skin[0],
            destinationSkin=target_skin[0],
            mirrorMode="YZ",
            surfaceAssociation="closestPoint",
            influenceAssociation="closestJoint",
            normalize=True
        )

            cmds.skinCluster(target_skin[0], edit=True, removeUnusedInfluence=True)
    
    # ===== 3. 父级操作 =====
    
    if do_mirror:
        if search == "l_":
            mirrored_root = root_joint.replace("l_", "r_")
        else:
            mirrored_root = root_joint.replace("r_", "l_")
        
        if base_exists:
            if cmds.objExists(root_joint):
                cmds.parent(root_joint, base_joint)
            if do_mirror and cmds.objExists(mirrored_root):
                cmds.parent(mirrored_root, base_joint)
        else:
            print(f"   ⚠️ 跳过父级: {base_joint} 不存在")
    else:
        if base_exists and cmds.objExists(root_joint):
            cmds.parent(root_joint, base_joint)
            print(f"   ✅ {root_joint} -> {base_joint}")
    
    # ===== 恢复选择 =====
    if original_selection:
        cmds.select(original_selection)
    


def create_wing_curve(mesh_name, prefix):
    """ 
    从网格边缘创建曲线
    
    参数:
        mesh_name: 网格名称
        prefix: 曲线名称前缀
    """
    try:
        edges = [
            f"{mesh_name}.e[9]", f"{mesh_name}.e[10]", 
            f"{mesh_name}.e[11]", f"{mesh_name}.e[8]"
        ]
        valid_edges = [e for e in edges if cmds.objExists(e)]
        if valid_edges:
            cmds.select(valid_edges, replace=True)
            cmds.polyToCurve(form=2, degree=1, conformToSmoothMeshPreview=1)
            curve_name = f"{prefix}wingCurve"
            if cmds.objExists("polyToCurve1"):
                if cmds.objExists(curve_name):
                    cmds.delete(curve_name)
                cmds.rename("polyToCurve1", curve_name)
        cmds.group(empty=True, n=f"{prefix}wingCurveGrp")
        cmds.parent(curve_name, f"{prefix}wingCurveGrp")
    except Exception as e:
        print(f"   ⚠️ 创建曲线失败: {e}")



def get_skin_cluster(mesh):
    """
    获取网格的蒙皮节点
    
    参数:
        mesh: 网格名称
    
    返回:
        str: 蒙皮节点名称，未找到返回None
    """
    for skin in cmds.ls(type='skinCluster'):
        outputs = cmds.listConnections(skin, type='transform')
        if outputs and mesh in outputs:
            return skin
    return None



def get_x_distance(root_joint):
    """计算指定骨骼到其末端关节的X轴绝对距离,设置控制器大小"""
    # 找末端
    end = root_joint
    while cmds.listRelatives(end, children=True, type='joint'):
        end = cmds.listRelatives(end, children=True, type='joint')[0]
    
    # 计算X轴距离
    start_pos = cmds.xform(root_joint, q=True, ws=True, t=True)
    end_pos = cmds.xform(end, q=True, ws=True, t=True)
    
    return abs(end_pos[0] - start_pos[0])
    
        

def create_wing_skeleton(side="l_"):
    """
    根据四个定位器创建翅膀骨骼
    
    参数:
        side: 前缀 ("l_" 或 "r_")
    """
    # 根据side设置定位器名称和骨骼名称
    locators = [f"{side}wing_loc0", f"{side}wing_loc1", f"{side}wing_loc2", f"{side}wing_loc3"]
    joint_names = [f"{side}scapula", f"{side}shoulder", f"{side}ebow", f"{side}wrist"]
    
    # 检查定位器
    positions = []
    for loc in locators:
        if not cmds.objExists(loc):
            print(f"❌ 定位器不存在: {loc}")
            return None
        pos = cmds.xform(loc, query=True, worldSpace=True, translation=True)
        positions.append(pos)
        print(f"  {loc}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
    
    # 删除已存在的骨骼
    for name in joint_names:
        if cmds.objExists(name):
            # 解除子级关系
            children = cmds.listRelatives(name, children=True)
            if children:
                for child in children:
                    cmds.parent(child, world=True)
            cmds.delete(name)
            print(f"  删除已存在的骨骼: {name}")
    
    # 先创建所有骨骼（不连接）
    created_joints = []
    for i, pos in enumerate(positions):
        cmds.select(clear=True)
        joint = cmds.joint(name=joint_names[i], position=pos)
        created_joints.append(joint)
    
    # 然后建立父子关系
    for i in range(len(created_joints) - 1):
        cmds.parent(created_joints[i + 1], created_joints[i])
    
    # 选择根骨骼
    cmds.select(joint_names[0])

    for name in joint_names:
        print(f"  - {name}")
    
    # 创建末端骨骼（复制wrist）
    end_joint_name = f"{side}wrist_end"
    
    # 删除已存在的末端骨骼
    if cmds.objExists(end_joint_name):
        cmds.delete(end_joint_name)
    
    # 复制wrist骨骼
    dup = cmds.duplicate(joint_names[3], returnRootsOnly=True)[0]
    end_joint = cmds.rename(dup, end_joint_name)
    
    # 父级到wrist
    cmds.parent(end_joint, joint_names[3])
    
    # 获取wrist的X轴位置
    wrist_x = cmds.getAttr(joint_names[3] + '.tx')
    
    # 设置末端骨骼的X轴位置（在局部空间）
    cmds.setAttr(end_joint + '.tx', wrist_x)
    cmds.select(clear=True)
    

    
    cmds.delete(f"{side}wingMesh",constructionHistory=True)
    cmds.delete(f"{side}wing_move")

    create_wing_curve(f"{side}wingMesh", side)

    skin_node = cmds.skinCluster(
                    joint_names, f"{side}wingMesh",
                    toSelectedBones=False,
                    bindMethod=0,
                    skinMethod=1,
                    normalizeWeights=1,
                    weightDistribution=0,
                    maximumInfluences=1,
                    dropoffRate=4,
                    obeyMaxInfluences=False
                )[0]
    
    cmds.skinPercent(skin_node, f"{side}wingMesh.vtx[1]", tv=[(f"{side}shoulder", 1)])
    cmds.skinPercent(skin_node, f"{side}wingMesh.vtx[2]", tv=[(f"{side}ebow", 1)])
    cmds.skinPercent(skin_node, f"{side}wingMesh.vtx[3]", tv=[(f"{side}wrist", 1)])

    cmds.skinPercent(skin_node, f"{side}wingMesh.vtx[5]", tv=[(f"{side}scapula", 0.730),(f"{side}shoulder", 0.270)])

    cmds.skinPercent(skin_node, f"{side}wingMesh.vtx[6]", tv=[(f"{side}scapula", 0.63),(f"{side}shoulder", 0.37)])

    cmds.skinPercent(skin_node, f"{side}wingMesh.vtx[7]", tv=[(f"{side}ebow", 0.52),(f"{side}shoulder", 0.48)])

    cmds.skinPercent(skin_node, f"{side}wingMesh.vtx[8]", tv=[(f"{side}wrist", 0.52), (f"{side}ebow", 0.48)])

    cmds.select([f"{side}wingMesh.e[0]", f"{side}wingMesh.e[2]", f"{side}wingMesh.e[4]"], replace=True)
    cmds.polyToCurve(form=2, degree=1, conformToSmoothMeshPreview=1)
    curve_name = f"{side}AimwingCurve"
    cmds.rename("polyToCurve1", curve_name) 
    cmds.reverseCurve(curve_name, constructionHistory=False, replaceOriginal=True) 
    cmds.setAttr(curve_name+".tz",-0.5)          
    if cmds.objExists(f"{side}wingCurveGrp"):
        cmds.parent(curve_name, f"{side}wingCurveGrp")
       
    return joint_names + [end_joint_name]



def create_joints_from_curve(curve_name, num_joints=10, suffix="0",side="l_"):
    """
    根据曲线创建骨骼
    
    参数:
        curve_name: 曲线名称
        num_joints: 骨骼数量
        suffix: 骨骼后缀 ("0" 或 "1")
    """
    if not cmds.objExists(curve_name):
        print(f"❌ 曲线不存在: {curve_name}")
        return None
    
    # 复制曲线
    dup_curve = cmds.duplicate(curve_name, returnRootsOnly=True)[0]
    dup_curve = cmds.rename(dup_curve, f"{curve_name}_temp")
    
    # 重建曲线
    rebuilt = cmds.rebuildCurve(
        dup_curve,
        constructionHistory=False,
        replaceOriginal=True,
        spans=num_joints - 1,
        degree=3,
        keepRange=0,
        keepTangents=0
    )[0]
    cmds.reverseCurve(dup_curve, constructionHistory=False, replaceOriginal=True)   
    # 获取曲线形状
    curve_shape = cmds.listRelatives(rebuilt, shapes=True)[0]
    
    # 创建 pointOnCurveInfo 节点
    poci = cmds.createNode('pointOnCurveInfo', name=f"{curve_name}_poci")
    cmds.connectAttr(f"{curve_shape}.worldSpace[0]", f"{poci}.inputCurve", force=True)
    
    # 创建骨骼
    joints = []
    for i in range(1, num_joints + 1):
        joint_name = f"{side}wing{i:02d}_{suffix}"
        if cmds.objExists(joint_name):
            cmds.delete(joint_name)
        joints.append(joint_name)
    
    cmds.select(clear=True)
    
    for i in range(num_joints):
        param = i / (num_joints - 1) if num_joints > 1 else 0
        
        cmds.setAttr(f"{poci}.parameter", param)
        pos = cmds.getAttr(f"{poci}.position")[0]
        
        cmds.select(clear=True)
        joint = cmds.joint(name=joints[i], position=pos)
    
    # 删除临时节点和曲线
    cmds.delete(poci)
    cmds.delete(dup_curve)
    
    return joints


def create_wing_joints_and_aim(num_joints=3,side='l_'):
    """
    创建翅膀骨骼和aim约束
    
    参数:
        num_joints: 骨骼数量
    """
    # 1. 从 l_AimwingCurve 创建骨骼 (后缀 _0)
    joints_0 = create_joints_from_curve(f"{side}AimwingCurve", num_joints, "0",side)
    
    # 2. 从 l_wingCurve 创建骨骼 (后缀 _1)
    joints_1 = create_joints_from_curve(f"{side}wingCurve", num_joints, "1",side)
    
    if not joints_0 or not joints_1:
        print("❌ 骨骼创建失败")
        return
    
    # 3. 创建 aim 约束: wingXX_0 -> wingXX_1
    for i in range(num_joints):
        joint_0 = f"{side}wing{i+1:02d}_0"
        joint_1 = f"{side}wing{i+1:02d}_1"
        
        if cmds.objExists(joint_0) and cmds.objExists(joint_1):
            aim_constranintA=cmds.aimConstraint(
                joint_1, joint_0,
                offset=[0, 0, 0],
                weight=1,
                aimVector=[1, 0, 0],
                upVector=[0, 1, 0],
                worldUpType="vector",
                worldUpVector=[0, 1, 0]
            )
            cmds.delete(aim_constranintA)

        
            aim_constranintB=cmds.aimConstraint(
                joint_0, joint_1,
                offset=[0, 0, 0],
                weight=1,
                aimVector=[-1, 0, 0],
                upVector=[0, 1, 0],
                worldUpType="vector",
                worldUpVector=[0, 1, 0]
            )
            cmds.delete(aim_constranintB)


            cmds.parent(joint_1,joint_0)
            
         
        
    return joints_0, joints_1



def import_locators(side="l_"):
    """
    从当前用户路径导入定位器
    """
    # 获取当前用户
    user = os.getenv("USERNAME") or os.getenv("USER")
    
    # 构建路径
    script_dir = f"C:/Users/{user}/Documents/maya/2022/scripts/WingRigTool/loc"
    
    if side == "l_":
        file_name = "l_wing_loc.ma"
    else:
        file_name = "r_wing_loc.ma"
    
    file_path = os.path.join(script_dir, file_name)
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    cmds.file(file_path, i=True, type="mayaAscii", 
          ignoreVersion=True, ra=True, 
          mergeNamespacesOnClash=True,  # 改为 True
          namespace=":",  # 使用根命名空间
          options="v=0;")
    
    print(f"✅ 导入定位器: {file_name}")
    return file_path



def lock_and_hide_transform(obj, lock_translate=True, lock_rotate=True, lock_scale=True,lock_visibility=True):
    """
    锁定并隐藏位移、旋转、缩放属性
    
    参数:
        obj: 物体名称
        lock_translate: 是否锁定位移
        lock_rotate: 是否锁定旋转
        lock_scale: 是否锁定缩放
    """
    if not cmds.objExists(obj):
        return
    
    attrs = []
    if lock_translate:
        attrs.extend([".tx", ".ty", ".tz"])
    if lock_rotate:
        attrs.extend([".rx", ".ry", ".rz"])
    if lock_scale:
        attrs.extend([".sx", ".sy", ".sz"])
    if lock_visibility:
        attrs.append(".v")
    for attr in attrs:
        try:
            cmds.setAttr(obj + attr, 
                         lock=True,        # 锁定，无法编辑
                         keyable=False,    # 不在通道盒显示
                         channelBox=False) # 不在通道盒显示
        except:
            pass