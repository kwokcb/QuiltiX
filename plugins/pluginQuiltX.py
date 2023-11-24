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

class GltfQuiltix(quiltix.QuiltiXWindow):
    def __init__(self, load_style_sheet=True, load_shaderball=True, load_default_graph=True):
        super().__init__(load_style_sheet=True, load_shaderball=True, load_default_graph=True)
        export_gltf = QAction("Export as Gltf...", self)
        export_gltf.triggered.connect(self.export_gtlf_triggered)
        self.file_menu.addAction(export_gltf)

    def export_gtlf_triggered(self):
        start_path = self.mx_selection_path
        if not start_path:
            start_path = self.geometry_selection_path

        if not start_path:
            start_path = os.path.join(ROOT, "resources", "materials")

        path = self.request_filepath(
            title="Save glTF file", start_path=start_path, file_filter="MaterialX files (*.gltf)", mode="save"
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

        self.set_current_filepath(path)
        try:
            with open(path, "w") as f:
                f.write(gltf_string)
                logger.info(f"Wrote .gltf file to {path}")

            binaryFileName = str(path)
            binaryFileName = binaryFileName.replace('.gltf', '.glb')
            print('- Packaging GLB file...')
            mtlx2glTFWriter = core.MTLX2GLTFWriter()
            saved, images, buffers = mtlx2glTFWriter.packageGLTF(path, binaryFileName)
            print('- Save GLB file:' + binaryFileName + '. Status:' + str(saved))
            for image in images:
                print('  - Embedded image: %s' % image)
            for buffer in buffers:
                print('  - Embedded buffer: %s' % buffer)

        except Exception as e:
            logger.error(e)

    def convert_graph_to_gltf(self, options):
        doc = self.qx_node_graph.get_current_mx_graph_doc()

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
        print('- Translated %d shaders.' % translatedCount)

        # Perform baking if needed
        if translatedCount > 0:
            print('- Baking start {')
            bakeResolution = 1024
            bakedFileName = options['bakeFileName']
            #if options['bakeResolution']:
            #    bakeResolution = options['bakeResolution']
            mtlx2glTFWriter.bakeTextures(doc, False, bakeResolution, bakeResolution, False, 
                                        False, False, bakedFileName)
            print('  - Baked textures to: ', bakedFileName)
            doc, libFiles = core.Util.createMaterialXDoc()
            mx.readFromXmlFile(doc, bakedFileName, options['searchPath'])
            remappedUris = core.Util.makeFilePathsRelative(doc, bakedFileName)
            for uri in remappedUris:
                print('  - Remapped URI: %s to %s' % (uri[0], uri[1]))
                core.Util.writeMaterialXDoc(doc, bakedFileName)
            print('- Baking end.')

        gltfString = mtlx2glTFWriter.convert(doc)

        return gltfString
    
def launch():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    editor = GltfQuiltix()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    launch()
