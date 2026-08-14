import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import os
import re


# ================= Utility Functions =================
def getDagPath(name):
    sel = om.MSelectionList()
    sel.add(name)
    return sel.getDagPath(0)


def getMObject(name):
    sel = om.MSelectionList()
    sel.add(name)
    return sel.getDependNode(0)


def get_all_meshes_from_selection():
    """
    Recursively get all meshes from selection
    Supports selecting meshes, groups, or mixed selection
    """
    selected = cmds.ls(sl=True, type='transform')
    all_meshes = set()
    
    for obj in selected:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True, type='mesh') or []
        if shapes:
            for shape in shapes:
                transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
                all_meshes.add(transform)
        else:
            descendants = cmds.listRelatives(obj, allDescendents=True, fullPath=True, type='transform') or []
            for descendant in descendants:
                descendant_shapes = cmds.listRelatives(descendant, shapes=True, type='mesh') or []
                if descendant_shapes:
                    all_meshes.add(descendant)
    
    return list(all_meshes)


def check_mesh_has_skin(mesh):
    """Check if mesh has skin cluster"""
    history = cmds.listHistory(mesh) or []
    for node in history:
        if cmds.nodeType(node) == "skinCluster":
            return True
    return False


def get_mesh_display_name(mesh):
    """Get mesh display name with skin indicator"""
    clean_name = sanitize_filename(mesh)
    has_skin = check_mesh_has_skin(mesh)
    if has_skin:
        return f"{clean_name} ✅"
    else:
        return clean_name


def sanitize_filename(name):
    """
    Sanitize filename, remove illegal characters and path hierarchy
    """
    if '|' in name:
        name = name.split('|')[-1]
    
    illegal_chars = r'[<>:"/\\|?*]'
    name = re.sub(illegal_chars, '_', name)
    name = name.strip()
    
    return name


def get_weight_files_from_folder(folder):
    """
    Get all .scw weight files from folder
    Returns dict: {model_name: file_path}
    """
    if not os.path.exists(folder):
        return {}
    
    weight_files = {}
    for file in os.listdir(folder):
        if file.endswith('.scw'):
            model_name = file[:-4]
            file_path = os.path.join(folder, file)
            weight_files[model_name] = file_path
    
    return weight_files


# ================= Core =================
class SkinIO:

    def getSkinCluster(self, mesh):
        history = cmds.listHistory(mesh) or []
        for h in history:
            if cmds.nodeType(h) == "skinCluster":
                return h
        return None

    def getSkinFn(self, skinCluster):
        return oma.MFnSkinCluster(getMObject(skinCluster))

    # ===== Export =====
    def exportWeights(self, mesh, folder):
        sc = self.getSkinCluster(mesh)
        if not sc:
            return f"❌ {mesh} has no skinCluster"

        shapes = cmds.skinCluster(sc, q=True, geometry=True)
        if not shapes:
            return f"❌ {mesh} has no geometry"
        shape = shapes[0]
        
        influences = cmds.skinCluster(sc, q=True, influence=True)

        dag = getDagPath(shape)
        skinFn = self.getSkinFn(sc)

        vtxCount = cmds.polyEvaluate(shape, vertex=True)

        compFn = om.MFnSingleIndexedComponent()
        comp = compFn.create(om.MFn.kMeshVertComponent)
        compFn.addElements(list(range(vtxCount)))

        weights, infCount = skinFn.getWeights(dag, comp)

        if not os.path.exists(folder):
            os.makedirs(folder)

        clean_name = sanitize_filename(mesh)
        filePath = os.path.join(folder, f"{clean_name}.scw")

        with open(filePath, "w") as f:
            f.write(" ".join(influences) + "\n")
            for i in range(vtxCount):
                base = i * infCount
                for j in range(infCount):
                    w = weights[base + j]
                    if w > 0.000001:
                        f.write(f"{i} {j} {w:.10f}\n")

        return f"✅ Exported: {mesh} -> {clean_name}.scw ({vtxCount} verts, {infCount} influences)"

    # ===== Batch Export =====
    def exportWeightsBatch(self, meshes, folder):
        results = []
        success_count = 0
        
        for mesh in meshes:
            result = self.exportWeights(mesh, folder)
            results.append(result)
            if "✅" in result:
                success_count += 1
        
        return results, success_count

    # ===== Import (Single) =====
    def importWeights(self, mesh, filePath):
        if not os.path.exists(filePath):
            return f"❌ File not found: {filePath}"

        with open(filePath, "r") as f:
            fileInfluences = f.readline().strip().split()
            lines = f.readlines()

        sc = self.getSkinCluster(mesh)

        if not sc:
            validJoints = [j for j in fileInfluences if cmds.objExists(j)]
            if not validJoints:
                return f"❌ No valid joints found in file for {mesh}"
            
            cmds.select(clear=True)
            cmds.select(mesh)
            for jnt in validJoints:
                cmds.select(jnt, add=True)
            sc = cmds.skinCluster(tsb=True, omi=False, maximumInfluences=4)[0]

        shapes = cmds.skinCluster(sc, q=True, geometry=True)
        if not shapes:
            return f"❌ {mesh} has no geometry"
        shape = shapes[0]
        
        currentInfluences = cmds.skinCluster(sc, q=True, influence=True)

        dag = getDagPath(shape)
        skinFn = self.getSkinFn(sc)

        vtxCount = cmds.polyEvaluate(shape, vertex=True)
        infCount = len(currentInfluences)

        indexMap = {}
        for i, jnt in enumerate(fileInfluences):
            if jnt in currentInfluences:
                indexMap[i] = currentInfluences.index(jnt)

        missing = set(fileInfluences) - set(currentInfluences)
        if missing:
            om.MGlobal.displayWarning(f"Missing joints for {mesh}: {list(missing)}")

        totalSize = vtxCount * infCount
        weightsArray = om.MDoubleArray(totalSize, 0.0)

        validCount = 0
        for line in lines:
            try:
                parts = line.strip().split()
                if len(parts) != 3:
                    continue
                i, j, w = parts
                i = int(i)
                j = int(j)
                w = float(w)

                if i < vtxCount and j in indexMap:
                    newJ = indexMap[j]
                    weightsArray[i * infCount + newJ] = w
                    validCount += 1
            except:
                continue

        compFn = om.MFnSingleIndexedComponent()
        comp = compFn.create(om.MFn.kMeshVertComponent)
        compFn.addElements(list(range(vtxCount)))

        infIndices = om.MIntArray()
        for i in range(infCount):
            infIndices.append(i)

        skinFn.setWeights(dag, comp, infIndices, weightsArray, normalize=False)

        return f"✅ Imported: {mesh} ({validCount} weights transferred)"

    # ===== Auto Match Import =====
    def importAllMatched(self, folder, meshes):
        """Import all meshes that match weight files by name"""
        weight_files = get_weight_files_from_folder(folder)
        
        if not weight_files:
            return [], 0, f"❌ No .scw files found in {folder}"
        
        results = []
        success_count = 0
        
        for mesh in meshes:
            clean_name = sanitize_filename(mesh)
            if clean_name in weight_files:
                result = self.importWeights(mesh, weight_files[clean_name])
                results.append(result)
                if "✅" in result:
                    success_count += 1
            else:
                results.append(f"⏭️ No weight file: {clean_name}.scw for {mesh}")
        
        return results, success_count, f"Found {len(weight_files)} weight files"
    
    # ===== Manual Order Import =====
    def importBatchByOrder(self, folder, meshes, weight_names):
        """Import weights in order matching selected meshes and weight files"""
        weight_files = get_weight_files_from_folder(folder)
        
        if not weight_files:
            return [], 0, f"❌ No .scw files found in {folder}"
        
        results = []
        success_count = 0
        
        for i in range(min(len(meshes), len(weight_names))):
            mesh = meshes[i]
            weight_name = weight_names[i]
            
            if weight_name in weight_files:
                result = self.importWeights(mesh, weight_files[weight_name])
                results.append(f"[{i+1}] {result}")
                if "✅" in result:
                    success_count += 1
            else:
                results.append(f"[{i+1}] ❌ Weight file not found: {weight_name}.scw")
        
        if len(meshes) > len(weight_names):
            for i in range(len(weight_names), len(meshes)):
                results.append(f"[{i+1}] ⏭️ No weight file for: {meshes[i]}")
        elif len(weight_names) > len(meshes):
            for i in range(len(meshes), len(weight_names)):
                results.append(f"[{i+1}] ⏭️ No mesh for weight: {weight_names[i]}.scw")
        
        return results, success_count, f"Processed {min(len(meshes), len(weight_names))} pairs"


# ================= UI =================
class SkinToolUI:

    def __init__(self):
        self.core = SkinIO()
        self.win = "ProSkinTool"
        self.last_export_folder = ""
        self.last_import_folder = ""
        self.current_weight_files = {}

    def show(self):
        if cmds.window(self.win, exists=True):
            cmds.deleteUI(self.win)

        cmds.window(self.win, title="Pro Skin Tool", widthHeight=(540, 680))
        cmds.columnLayout(adj=True, rowSpacing=5, columnAttach=('both', 5))

        # ===== Export Section =====
        cmds.frameLayout(label="Batch Export", collapsable=True, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adj=True, rowSpacing=3)
        
        self.exportFolder = cmds.textFieldButtonGrp(
            label="Export Folder",
            buttonLabel="Browse",
            bc=self.pickExportFolder,
            columnWidth=[(1, 70), (2, 340)]
        )
        cmds.button(label="Export Selected Meshes", height=28, c=self.exportBatch)
        
        cmds.setParent("..")
        cmds.setParent("..")

        # ===== Import Section =====
        cmds.frameLayout(label="Batch Import", collapsable=True, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adj=True, rowSpacing=3)
        
        # Import path selection
        self.importPathType = cmds.radioButtonGrp(
            label="Import Path",
            numberOfRadioButtons=2,
            labelArray2=['Use Export Folder', 'Select Folder'],
            select=1,
            columnWidth=[(1, 70), (2, 100), (3, 80)]
        )
        
        self.importFolder = cmds.textFieldButtonGrp(
            label="Folder",
            buttonLabel="Browse",
            bc=self.pickImportFolder,
            columnWidth=[(1, 70), (2, 340)],
            enable=False
        )
        
        cmds.text(l="", height=2)
        cmds.separator(style="in", height=5)
        
        # ===== Two Column Layout =====
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 245), (2, 245)], columnOffset=[(1, "both", 3), (2, "both", 3)])
        
        # Left: Weight Files List
        cmds.columnLayout(adj=True, rowSpacing=3)
        cmds.text(label="Weight Files (Ctrl+Click for multi-select):", align="center")
        self.weight_file_list = cmds.textScrollList(height=160, allowMultiSelection=True)
        cmds.button(label="Refresh Weight List", height=25, command=lambda x: self.refresh_weight_list())
        cmds.setParent("..")
        
        # Right: Mesh List
        cmds.columnLayout(adj=True, rowSpacing=3)
        cmds.text(label="Meshes (Ctrl+Click for multi-select):", align="center")
        self.mesh_list = cmds.textScrollList(height=160, allowMultiSelection=True)
        
        # Mesh list buttons
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 120))
        cmds.button(label="Load Selected", height=25, command=lambda x: self.load_meshes_from_selection())
        cmds.button(label="⟳ Refresh", height=25, command=lambda x: self.refresh_mesh_list())
        cmds.setParent("..")
        
        cmds.setParent("..")
        
        cmds.setParent("..")
        
        cmds.text(l="", height=2)
        cmds.separator(style="in", height=5)
        
        # ===== Import Buttons =====
        cmds.text(label="Import Options:", align="left")
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(260, 260))
        cmds.button(label="Auto Match Import", height=35, backgroundColor=[0.3, 0.5, 0.3],
                   command=lambda x: self.import_all_matched())
        cmds.button(label="Manual Order Import", height=35, backgroundColor=[0.4, 0.4, 0.7],
                   command=lambda x: self.import_batch_by_order())
        cmds.setParent("..")
        
        cmds.text(l="", height=3)
        cmds.text(label="Auto Match: Automatically matches weights by mesh name", align="left")
        cmds.text(label="Manual Order: Imports in selection order (1st weight to 1st mesh)", align="left")
        
        cmds.setParent("..")
        cmds.setParent("..")

        # ===== Log =====
        cmds.frameLayout(label="Log", marginWidth=5, marginHeight=5)
        self.logField = cmds.scrollField(editable=False, wordWrap=True, height=100)
        cmds.setParent("..")
        
        cmds.button(label="Clear Log", height=22, c=self.clearLog)

        cmds.showWindow()
        
        cmds.radioButtonGrp(self.importPathType, e=True, cc=self.onImportPathTypeChanged)

    def log(self, msg):
        cmds.scrollField(self.logField, e=True, insertText=msg + "\n")
        print(msg)
    
    def clearLog(self, *_):
        cmds.scrollField(self.logField, e=True, clear=True)

    def pickExportFolder(self, *_):
        p = cmds.fileDialog2(fileMode=3)
        if p:
            self.last_export_folder = p[0]
            cmds.textFieldButtonGrp(self.exportFolder, e=True, text=p[0])

    def pickImportFolder(self, *_):
        p = cmds.fileDialog2(fileMode=3)
        if p:
            self.last_import_folder = p[0]
            cmds.textFieldButtonGrp(self.importFolder, e=True, text=p[0])
            self.refresh_weight_list()
    
    def onImportPathTypeChanged(self, *_):
        import_path_type = cmds.radioButtonGrp(self.importPathType, q=True, select=True)
        if import_path_type == 2:
            cmds.textFieldButtonGrp(self.importFolder, e=True, enable=True)
            if self.last_import_folder:
                cmds.textFieldButtonGrp(self.importFolder, e=True, text=self.last_import_folder)
                self.refresh_weight_list()
        else:
            cmds.textFieldButtonGrp(self.importFolder, e=True, enable=False)
            export_folder = cmds.textFieldButtonGrp(self.exportFolder, q=True, text=True)
            if export_folder:
                cmds.textFieldButtonGrp(self.importFolder, e=True, text=export_folder)
                self.refresh_weight_list()

    def getImportFolder(self):
        import_path_type = cmds.radioButtonGrp(self.importPathType, q=True, select=True)
        if import_path_type == 1:
            folder = cmds.textFieldButtonGrp(self.exportFolder, q=True, text=True)
        else:
            folder = cmds.textFieldButtonGrp(self.importFolder, q=True, text=True)
        return folder

    def refresh_weight_list(self):
        """Refresh weight files list"""
        folder = self.getImportFolder()
        if not folder or not os.path.exists(folder):
            cmds.textScrollList(self.weight_file_list, edit=True, removeAll=True)
            return
        
        self.current_weight_files = get_weight_files_from_folder(folder)
        
        cmds.textScrollList(self.weight_file_list, edit=True, removeAll=True)
        for name in sorted(self.current_weight_files.keys()):
            cmds.textScrollList(self.weight_file_list, edit=True, append=name)
        
        self.log(f"📁 Found {len(self.current_weight_files)} weight files")
    
    def refresh_mesh_list(self):
        """Refresh mesh list (update skin status)"""
        current_items = cmds.textScrollList(self.mesh_list, query=True, allItems=True) or []
        if not current_items:
            self.log("⚠️ Mesh list is empty, please load meshes first")
            return
        
        # Save current selection
        selected_items = cmds.textScrollList(self.mesh_list, query=True, selectItem=True) or []
        
        # Rebuild list
        cmds.textScrollList(self.mesh_list, edit=True, removeAll=True)
        
        for item in current_items:
            # Extract original mesh name (remove ✅)
            clean_name = item.replace(" ✅", "")
            
            # Find mesh in scene
            all_transforms = cmds.ls(type='transform')
            found_mesh = None
            for transform in all_transforms:
                if sanitize_filename(transform) == clean_name:
                    found_mesh = transform
                    break
            
            if found_mesh:
                display_name = get_mesh_display_name(found_mesh)
                cmds.textScrollList(self.mesh_list, edit=True, append=display_name)
                
                # Restore selection
                if item in selected_items:
                    cmds.textScrollList(self.mesh_list, edit=True, selectItem=display_name)
        
        self.log("🔄 Mesh list refreshed, skin status updated")
    
    def load_meshes_from_selection(self):
        """Load meshes from selection"""
        meshes = get_all_meshes_from_selection()
        
        if not meshes:
            self.log("❌ No meshes found in selection, please select meshes or groups")
            return
        
        cmds.textScrollList(self.mesh_list, edit=True, removeAll=True)
        for mesh in sorted(meshes):
            display_name = get_mesh_display_name(mesh)
            cmds.textScrollList(self.mesh_list, edit=True, append=display_name)
        
        # Count skinned meshes
        skinned_count = sum(1 for mesh in meshes if check_mesh_has_skin(mesh))
        self.log(f"📁 Loaded {len(meshes)} meshes from selection ({skinned_count} have skin)")
    
    def import_all_matched(self):
        """Auto match import (by name)"""
        folder = self.getImportFolder()
        if not folder or not os.path.exists(folder):
            self.log("❌ Please select a valid weight folder first")
            return
        
        all_items = cmds.textScrollList(self.mesh_list, query=True, allItems=True) or []
        if not all_items:
            self.log("❌ Mesh list is empty, please load meshes first")
            return
        
        # Extract original mesh names (remove ✅)
        all_meshes = [item.replace(" ✅", "") for item in all_items]
        
        self.log("-" * 50)
        self.log("Auto Match Import (by name)...")
        
        results, success_count, info = self.core.importAllMatched(folder, all_meshes)
        
        self.log(f"📁 {info}")
        for result in results:
            self.log(result)
        
        self.log("-" * 50)
        self.log(f"✅ Import completed: {success_count}/{len(all_meshes)} successful")
        
        # Refresh mesh list after import
        self.refresh_mesh_list()
    
    def import_batch_by_order(self):
        """Manual order import (by selection order)"""
        folder = self.getImportFolder()
        if not folder or not os.path.exists(folder):
            self.log("❌ Please select a valid weight folder first")
            return
        
        # Get selected weight files (in selection order)
        selected_weights = cmds.textScrollList(self.weight_file_list, query=True, selectItem=True)
        if not selected_weights:
            self.log("❌ Please select weight files first (Ctrl+Click for multiple)")
            return
        
        # Get selected meshes (in selection order, extract original names)
        selected_items = cmds.textScrollList(self.mesh_list, query=True, selectItem=True)
        if not selected_items:
            self.log("❌ Please select meshes first (Ctrl+Click for multiple)")
            return
        
        selected_meshes = [item.replace(" ✅", "") for item in selected_items]
        
        self.log("-" * 50)
        self.log("Manual Order Import (by selection order):")
        self.log(f"Selected weights ({len(selected_weights)}): {', '.join(selected_weights)}")
        self.log(f"Selected meshes ({len(selected_meshes)}): {', '.join(selected_meshes)}")
        self.log("-" * 30)
        
        results, success_count, info = self.core.importBatchByOrder(folder, selected_meshes, selected_weights)
        
        self.log(f"📁 {info}")
        for result in results:
            self.log(result)
        
        self.log("-" * 50)
        self.log(f"✅ Import completed: {success_count}/{min(len(selected_meshes), len(selected_weights))} successful")
        
        # Refresh mesh list after import
        self.refresh_mesh_list()

    def exportBatch(self, *_):
        folder = cmds.textFieldButtonGrp(self.exportFolder, q=True, text=True)
        
        if not folder:
            self.log("❌ Select a folder first")
            return
        
        all_meshes = get_all_meshes_from_selection()
        
        if not all_meshes:
            self.log("❌ No meshes found in selection")
            return
        
        self.log(f"📁 Found {len(all_meshes)} meshes to export")
        self.log(f"📁 Exporting to: {folder}")
        self.log("-" * 50)
        
        results, success_count = self.core.exportWeightsBatch(all_meshes, folder)
        
        for result in results:
            self.log(result)
        
        self.log("-" * 50)
        self.log(f"✅ Export completed: {success_count}/{len(all_meshes)} successful")


# ================= Run =================
def run_pro_skin_tool():
    SkinToolUI().show()


if __name__ == "__main__":
    run_pro_skin_tool()