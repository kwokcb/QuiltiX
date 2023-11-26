import os
import sys
import logging

from Qt.QtWidgets import (  # type: ignore
    QApplication,
    QAction
)

from QuiltiX import quiltix
from QuiltiX.constants import ROOT
import materialxgltf.core as core
import MaterialX as mx

logger = logging.getLogger(__name__)

class GltfQuilitxPlugin():
    def __init__(self, editor):
        self.editor = editor
        self.editor.file_menu.addSeparator()
        gltfMenu = self.editor.file_menu.addMenu("glTF")

        # Export menu item
        export_gltf = QAction("Export to glTF...", self.editor)
        export_gltf.triggered.connect(self.export_gltf_triggered)
        gltfMenu.addAction(export_gltf)

        # Import menu item
        import_gltf = QAction("Import from glTF...", self.editor)
        import_gltf.triggered.connect(self.import_gltf_triggered)
        gltfMenu.addAction(import_gltf)

    def import_gltf_triggered(self):
        '''
        Import a glTF file into the current graph.
        '''
        start_path = self.editor.mx_selection_path
        if not start_path:
            start_path = self.editor.geometry_selection_path

        if not start_path:
            start_path = os.path.join(ROOT, "resources", "materials")

        path = self.editor.request_filepath(
            title="Load glTF file", start_path=start_path, file_filter="glTF files (*.gltf)", mode="open",
        )

        options = core.GLTF2MtlxOptions()
        options['createAssignments'] = False   
        options['addAllInputs'] = False
        gltf2MtlxReader = core.GLTF2MtlxReader()
        gltf2MtlxReader.setOptions(options)
        doc = gltf2MtlxReader.convert(path)
        success = True
        if not doc:
            success  = False
            logger.error('Error converting glTF file to MaterialX file')
        else:
            success , err = doc.validate()
            if not success:
                logger.error(err)
            else:
                # Load material file, stipped of any library references
                # - Q: Should we attempt to replace usage of "channels" with explicit extracts here 
                # as OpenUSD does not handle this properly. TBD.
                # - Note: we must strip out the library references as QuiltiX tries to load them in
                # as includes instea of stripping them out.
                docString = core.Util.writeMaterialXDocString(doc)
                doc = mx.createDocument()
                mx.readFromXmlString(doc, docString)
                
                self.editor.mx_selection_path = path
                self.editor.qx_node_graph.load_graph_from_mx_doc(doc, path) 
    
    def export_gltf_triggered(self):
        '''
        Export the current graph to a glTF file.
        '''
        start_path = self.editor.mx_selection_path
        if not start_path:
            start_path = self.editor.geometry_selection_path

        if not start_path:
            start_path = os.path.join(ROOT, "resources", "materials")

        path = self.editor.request_filepath(
            title="Save glTF file", start_path=start_path, file_filter="glTF files (*.gltf)", mode="save",
        )

        options = core.MTLX2GLTFOptions()

        # File name for baking
        options['bakeFileName'] = path + '_baked.mtlx'
        options['debugOutput'] = True
        gltfGeomFileName = 'D:/Work/materialx/materialxgltf/src/materialxgltf/data/shaderball.gltf'
        options['geometryFile'] = gltfGeomFileName
        options['primsPerMaterial'] = True
        options['writeDefaultInputs'] = True
        
        searchPath = mx.getDefaultDataSearchPath()
        if not mx.FilePath(path).isAbsolute():
            path = os.path.abspath(path)
        searchPath.append(mx.FilePath(path).getParentPath())
        searchPath.append(mx.FilePath.getCurrentPath())
        searchPath.append(mx.FilePath(gltfGeomFileName).getParentPath())
        options['searchPath'] = searchPath
        options['packageBinary'] = True  

        gltf_string = self.convert_graph_to_gltf(options)
        if gltf_string == '{}':
            return

        self.editor.set_current_filepath(path)
        try:
            with open(path, "w") as f:
                f.write(gltf_string)
                logger.info(f"Wrote .gltf file to {path}")

            # Package binary file
            binaryFileName = str(path)
            binaryFileName = binaryFileName.replace('.gltf', '.glb')            
            logger.debug('- Packaging GLB file...')
            mtlx2glTFWriter = core.MTLX2GLTFWriter()
            mtlx2glTFWriter.setOptions(options)
            saved, images, buffers = mtlx2glTFWriter.packageGLTF(path, binaryFileName)
            logger.debug('- Save GLB file:' + binaryFileName + '. Status:' + str(saved))
            for image in images:
                logger.debug('  - Embedded image: ' + image)
            for buffer in buffers:
                logger.debug('  - Embedded buffer: ' + buffer)  
            logger.debug('- Packaging GLB file... finished.')
        except Exception as e:
            logger.error(e)

    def convert_graph_to_gltf(self, options):
        doc = self.editor.qx_node_graph.get_current_mx_graph_doc()

        mtlx2glTFWriter = core.MTLX2GLTFWriter()
        mtlx2glTFWriter.setOptions(options)

        # Need to load in definition libraries to get translation graphs
        stdlib = mx.createDocument()
        searchPath = mx.getDefaultDataSearchPath()
        libraryFolders = []
        libraryFolders.extend(mx.getDefaultDataLibraryFolders())
        mx.loadLibraries(libraryFolders, searchPath, stdlib)
        doc.importLibrary(stdlib)     

        # Perform shader translation if needed
        translatedCount = mtlx2glTFWriter.translateShaders(doc)
        logger.debug('- Translated shaders.' + str(translatedCount))

        # Perform baking if needed
        if translatedCount > 0:
            logger.debug('- Baking start {')
            bakeResolution = 1024
            bakedFileName = options['bakeFileName']
            #if options['bakeResolution']:
            #    bakeResolution = options['bakeResolution']
            mtlx2glTFWriter.bakeTextures(doc, False, bakeResolution, bakeResolution, False, 
                                        False, False, bakedFileName)
            logger.debug('  - Baked textures to: ' + bakedFileName)
            doc, libFiles = core.Util.createMaterialXDoc()
            mx.readFromXmlFile(doc, bakedFileName, options['searchPath'])
            remappedUris = core.Util.makeFilePathsRelative(doc, bakedFileName)
            for uri in remappedUris:
                logger.debug('  - Remapped URI: ' + uri[0] + ' to ' + uri[1])
                core.Util.writeMaterialXDoc(doc, bakedFileName)
            logger.debug('- Baking end.')

        gltfString = mtlx2glTFWriter.convert(doc)

        return gltfString
                    

class GltfQuiltix(quiltix.QuiltiXWindow):
    '''
    QuiltiX window with glTF import/export functionality added
    '''
    def __init__(self, load_style_sheet=True, load_shaderball=True, load_default_graph=True):
        super().__init__(load_style_sheet=True, load_shaderball=True, load_default_graph=True)

        self.plugin = GltfQuilitxPlugin(self)

    
def launch():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    editor = GltfQuiltix()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    launch()
