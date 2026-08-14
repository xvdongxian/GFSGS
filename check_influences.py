import maya.cmds as cmds
import maya.api.OpenMaya as om2
import time

def check_skin_weights(threshold=8):
    """
    检查选中模型上蒙皮点受骨骼影响的数量，并高亮显示超过阈值的点。
    优化版本：使用API批量获取权重，大幅提升性能。
    """
    start_time = time.time()
    
    # 获取当前选择的模型
    selected = cmds.ls(selection=True, transforms=True, dag=True)
    meshes = []

    # 获取所有选中的模型及其子网格
    for obj in selected:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True, noIntermediate=True)
        if shapes:
            for shape in shapes:
                if cmds.nodeType(shape) == 'mesh':
                    meshes.append(shape)

    if not meshes:
        cmds.warning("请选择一个或多个带有蒙皮网格的模型。")
        return

    all_vertices_above = []
    total_vertices = 0
    
    # 先统计总顶点数
    cmds.progressWindow(title='检查蒙皮权重', progress=0, isInterruptable=True, 
                       status='正在统计顶点数量...')
    
    for mesh in meshes:
        if cmds.progressWindow(query=True, isCancelled=True):
            cmds.progressWindow(endProgress=True)
            cmds.warning("用户取消了操作。")
            return
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        total_vertices += vertex_count
    
    cmds.progressWindow(endProgress=True)
    
    # 重新创建进度条，这次基于顶点数量
    cmds.progressWindow(title='检查蒙皮权重', progress=0, isInterruptable=True, 
                       status='准备就绪', maxValue=total_vertices)
    
    processed_vertices = 0
    
    try:
        for mesh in meshes:
            # 检查是否被中断
            if cmds.progressWindow(query=True, isCancelled=True):
                cmds.progressWindow(endProgress=True)
                cmds.warning("用户取消了操作。")
                return
            
            # 获取该网格的蒙皮节点
            skin_cluster = None
            hist = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=1)
            for node in hist:
                if cmds.nodeType(node) == 'skinCluster':
                    skin_cluster = node
                    break
            
            if not skin_cluster:
                # 更新进度：没有蒙皮的网格直接跳过
                vertex_count = cmds.polyEvaluate(mesh, vertex=True)
                processed_vertices += vertex_count
                cmds.progressWindow(edit=True, progress=processed_vertices, 
                                  status=f'跳过: {mesh} (无蒙皮)')
                continue
            
            # 获取影响骨骼列表
            influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
            
            # 更新状态
            cmds.progressWindow(edit=True, status=f'正在分析: {mesh}')
            
            # 使用API批量获取权重
            vertices_above = check_weights_api(mesh, skin_cluster, influences, threshold, 
                                               processed_vertices, total_vertices)
            
            if vertices_above:
                all_vertices_above.extend(vertices_above)
            
            # 更新已处理顶点数
            vertex_count = cmds.polyEvaluate(mesh, vertex=True)
            processed_vertices += vertex_count
            cmds.progressWindow(edit=True, progress=processed_vertices)
            
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cmds.progressWindow(endProgress=True)
    
    elapsed_time = time.time() - start_time
    print(f"\n检查完成，耗时: {elapsed_time:.2f} 秒")
    
    # 输出结果
    if all_vertices_above:
        print("\n" + "="*50)
        print(f"找到 {len(all_vertices_above)} 个顶点，其骨骼影响数量超过 {threshold}:")
        
        # 统计信息
        influence_counts = [cnt for _, cnt in all_vertices_above]
        print(f"最大影响数: {max(influence_counts)}")
        print(f"平均影响数: {sum(influence_counts)/len(influence_counts):.1f}")
        
        for vtx, cnt in all_vertices_above[:20]:
            print(f"顶点: {vtx}  |  影响数: {cnt}")
        if len(all_vertices_above) > 20:
            print(f"... 还有 {len(all_vertices_above)-20} 个顶点未显示。")

        # 弹出对话框，询问用户是否选择这些顶点
        result = cmds.confirmDialog(
            title='选择顶点',
            message=f'检测到 {len(all_vertices_above)} 个顶点，骨骼影响数量超过 {threshold}。\n耗时: {elapsed_time:.2f}秒\n\n是否立即选中这些顶点？',
            button=['是', '否'],
            defaultButton='是',
            cancelButton='否',
            dismissString='否'
        )

        if result == '是':
            # 提取所有顶点名称并选中
            vertex_list = [vtx for vtx, _ in all_vertices_above]
            cmds.select(vertex_list, replace=True)
            print(f"已选中 {len(vertex_list)} 个顶点。")
    else:
        cmds.confirmDialog(
            title='检查完成',
            message=f'在选中模型中，没有发现骨骼影响数量超过 {threshold} 的顶点。\n耗时: {elapsed_time:.2f}秒',
            button=['确定']
        )

def check_weights_api(mesh, skin_cluster, influences, threshold, processed_start, total_vertices):
    """
    使用Maya API 2.0批量获取权重，速度最快
    同时报告进度
    """
    try:
        # 获取MObject
        sel = om2.MSelectionList()
        sel.add(mesh)
        mesh_obj = sel.getDependNode(0)
        
        # 获取蒙皮节点对象
        sel.clear()
        sel.add(skin_cluster)
        skin_obj = sel.getDependNode(0)
        skin_fn = om2.MFnSkinCluster(skin_obj)
        
        # 获取顶点数量
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        
        # 构建组件列表
        vertex_components = om2.MFnMesh(mesh_obj).getVertices()
        
        # 批量获取权重
        weights = skin_fn.getWeights(mesh_obj, vertex_components)
        
        # 检查每个顶点的非零权重数量
        vertices_above = []
        
        # 分批处理权重检查，以便更新进度
        batch_size = max(1000, vertex_count // 20)  # 至少分20批
        
        for batch_start in range(0, vertex_count, batch_size):
            batch_end = min(batch_start + batch_size, vertex_count)
            
            # 处理当前批次
            for vtx_idx in range(batch_start, batch_end):
                if vtx_idx < len(weights):
                    weight_list = weights[vtx_idx]
                    influence_count = sum(1 for w in weight_list if w > 0.0001)
                    
                    if influence_count > threshold:
                        vtx_name = f"{mesh}.vtx[{vtx_idx}]"
                        vertices_above.append((vtx_name, influence_count))
            
            # 更新进度条
            current_processed = processed_start + batch_end
            progress_percent = int((current_processed / total_vertices) * 100)
            cmds.progressWindow(edit=True, progress=current_processed,
                              status=f'分析顶点 {current_processed}/{total_vertices} ({progress_percent}%)')
        
        return vertices_above
        
    except Exception as e:
        print(f"API方法失败，回退到传统方法: {e}")
        return check_weights_fallback(mesh, skin_cluster, influences, threshold, 
                                     processed_start, total_vertices)

def check_weights_fallback(mesh, skin_cluster, influences, threshold, processed_start, total_vertices):
    """
    传统方法：逐顶点查询（作为备用）
    带进度更新
    """
    vertices = cmds.ls(cmds.polyListComponentConversion(mesh, toVertex=True), flatten=True)
    vertices_above = []
    vertex_count = len(vertices)
    
    for i, vertex in enumerate(vertices):
        weights = cmds.skinPercent(skin_cluster, vertex, query=True, value=True)
        influence_count = sum(1 for w in weights if w > 0.0001)
        
        if influence_count > threshold:
            vertices_above.append((vertex, influence_count))
        
        # 每处理100个顶点更新一次进度
        if i % 100 == 0:
            current_processed = processed_start + i
            progress_percent = int((current_processed / total_vertices) * 100)
            cmds.progressWindow(edit=True, progress=current_processed,
                              status=f'传统模式: {current_processed}/{total_vertices} ({progress_percent}%)')
    
    return vertices_above

def create_ui():
    """
    创建带有自定义输入框的UI，允许用户输入任意影响数量阈值。
    """
    # 删除已存在的窗口
    if cmds.window('skinWeightCheckerWin', exists=True):
        cmds.deleteUI('skinWeightCheckerWin')

    window = cmds.window('skinWeightCheckerWin', title='蒙皮影响数量检查工具', widthHeight=(400, 180))
    
    # 使用columnLayout作为主布局
    main_layout = cmds.columnLayout(adjustableColumn=True)
    
    # 顶部提示
    cmds.text(label='检查选中网格的蒙皮点，找出被过多骨骼影响的顶点', align='center', height=30)
    cmds.separator(height=10)

    # 使用frameLayout来分组
    cmds.frameLayout(label='阈值设置', collapsable=False, marginWidth=10, marginHeight=10)
    
    # 阈值输入区域
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)], columnOffset=[(1, 'both', 5), (2, 'both', 5)])
    cmds.text(label='骨骼影响数量阈值 (>):', align='right')
    threshold_field = cmds.intField(value=8, minValue=1, maxValue=50, width=140)
    cmds.setParent('..')
    
    cmds.setParent('..')  # 返回到columnLayout
    
    cmds.separator(height=10)
    
    # 按钮区域
    cmds.frameLayout(label='执行检查', collapsable=False, marginWidth=10, marginHeight=10)
    
    cmds.rowLayout(numberOfColumns=1, columnAlign=(1, 'center'))
    cmds.button(label='开始检查', command=lambda x: check_skin_weights(threshold=cmds.intField(threshold_field, query=True, value=True)), 
                height=35, width=200)
    cmds.setParent('..')
    
    cmds.setParent('..')
    
    cmds.separator(height=10)

    # 提示信息
    cmds.text(label='提示: 阈值代表"大于"该数值', align='center', height=25, wordWrap=True)
    cmds.text(label='例如输入4则找出影响数≥5的顶点', align='center', height=20, wordWrap=True)
    cmds.text(label='使用Maya API 2.0加速，支持高面数模型', align='center', height=20, wordWrap=True, backgroundColor=[0.2, 0.2, 0.2])

    cmds.showWindow(window)

# 运行UI
create_ui()