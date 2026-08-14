import maya.cmds as cmds

# 用于存储删除的约束信息
deleted_constraints_history = []


def get_constraints_from_hierarchy():
    """获取选中物体层级下的所有约束"""
    selected = cmds.ls(selection=True)
    
    if not selected:
        cmds.warning("请先选择物体！")
        return []
    
    all_constraints = []
    
    for obj in selected:
        all_objects = [obj]
        children = cmds.listRelatives(obj, allDescendents=True)
        if children:
            all_objects.extend(children)
        
        for item in all_objects:
            constraints = cmds.listConnections(item, type='constraint')
            if constraints:
                all_constraints.extend(constraints)
    
    return list(set(all_constraints))


def select_constraints():
    """选择选中物体层级下的所有约束"""
    constraints = get_constraints_from_hierarchy()
    
    if constraints:
        cmds.select(constraints)
        cmds.text("constraint_count_text", edit=True, label=f"✅ 已选择 {len(constraints)} 个约束")
        print(f"✅ 已选择 {len(constraints)} 个约束节点")
    else:
        cmds.text("constraint_count_text", edit=True, label="⚠️ 没有找到约束节点")
        print("没有找到约束节点")


def delete_constraints():
    """删除选中物体层级下的所有约束"""
    global deleted_constraints_history
    
    constraints = get_constraints_from_hierarchy()
    
    if constraints:
        # 保存约束信息用于恢复
        deleted_constraints_history = []
        for const in constraints:
            info = {
                'name': const,
                'type': cmds.nodeType(const),
                'targets': cmds.listConnections(const + '.target', source=True) or [],
                'driver': None
            }
            # 获取被约束的物体
            outputs = cmds.listConnections(const, plugs=True, destination=True)
            if outputs:
                for out in outputs:
                    if '.constraint' not in out and '.target' not in out:
                        info['driver'] = out.split('.')[0]
                        break
            deleted_constraints_history.append(info)
        
        count = len(constraints)
        cmds.delete(constraints)
        cmds.text("constraint_count_text", edit=True, label=f"✅ 已删除 {count} 个约束")
        cmds.button("restore_constraints_btn", edit=True, enable=True)
        print(f"✅ 已删除 {count} 个约束节点")
    else:
        cmds.text("constraint_count_text", edit=True, label="⚠️ 没有找到约束节点")
        print("没有找到约束节点")


def restore_constraints():
    """恢复最近删除的约束"""
    global deleted_constraints_history
    
    if not deleted_constraints_history:
        cmds.text("constraint_count_text", edit=True, label="⚠️ 没有可恢复的约束")
        print("没有可恢复的约束")
        return
    
    restored = 0
    for info in deleted_constraints_history:
        try:
            const_name = info['name']
            const_type = info['type']
            targets = [t for t in info['targets'] if cmds.objExists(t)]
            driver = info['driver']
            
            if not targets or not driver or not cmds.objExists(driver):
                print(f"⚠️ 跳过 {const_name}: 目标或驱动不存在")
                continue
            
            # 根据类型重建约束
            const_map = {
                'parentConstraint': cmds.parentConstraint,
                'pointConstraint': cmds.pointConstraint,
                'orientConstraint': cmds.orientConstraint,
                'scaleConstraint': cmds.scaleConstraint,
                'aimConstraint': cmds.aimConstraint
            }
            
            if const_type in const_map:
                const_map[const_type](targets, driver, maintainOffset=True)
                
                # 重命名为原名称
                new_consts = cmds.listConnections(driver, type='constraint') or []
                for nc in new_consts:
                    if cmds.nodeType(nc) == const_type and nc != const_name:
                        if cmds.objExists(const_name):
                            cmds.delete(const_name)
                        cmds.rename(nc, const_name)
                        break
                
                restored += 1
                print(f"✅ 恢复: {const_name}")
        except Exception as e:
            print(f"❌ 恢复失败: {e}")
    
    cmds.text("constraint_count_text", edit=True, label=f"✅ 已恢复 {restored} 个约束")
    deleted_constraints_history = []
    cmds.button("restore_constraints_btn", edit=True, enable=False)
    print(f"✅ 已恢复 {restored} 个约束")


def create_constraint_tool_ui():
    """创建约束工具UI"""
    window_name = "constraintToolWindow"
    
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    window = cmds.window(window_name, title="约束工具", widthHeight=(320, 250))
    
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAttach=("both", 10))
    
    cmds.text(label="约束管理工具", align="center", font="boldLabelFont")
    cmds.separator(height=8)
    
    cmds.text(label="选择物体后点击下方按钮", align="center")
    cmds.text("constraint_count_text", label="等待操作...", align="center")
    
    cmds.separator(height=8)
    
    # 第一行按钮：选择和删除
    cmds.rowColumnLayout(nc=2, cw=[(1, 145), (2, 145)])
    cmds.button(label="选择当前层级下的所有约束", height=35, backgroundColor=[0.3, 0.5, 0.7],
                command=lambda x: select_constraints())
    cmds.button(label="删除当前层级下的所有约束", height=35, backgroundColor=[0.7, 0.3, 0.3],
                command=lambda x: delete_constraints())
    cmds.setParent("..")
    
    cmds.separator(height=8)
    
    # 第二行：恢复按钮
    cmds.rowColumnLayout(nc=1, cw=[(1, 290)])
    cmds.button("restore_constraints_btn", label="恢复删除的约束", height=35,
                backgroundColor=[0.3, 0.7, 0.3], enable=False,
                command=lambda x: restore_constraints())
    cmds.setParent("..")
    
    cmds.separator(height=8)
    
    # 刷新按钮
    cmds.button(label="刷新状态", height=25,
                command=lambda x: cmds.text("constraint_count_text", edit=True, label="已刷新"))
    
    cmds.showWindow(window)


# 启动UI
create_constraint_tool_ui()