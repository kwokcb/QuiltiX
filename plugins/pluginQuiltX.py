import os
import sys
import logging

from Qt.QtWidgets import (  # type: ignore
    QApplication,
    QAction,
    QDockWidget,
    QTextBrowser,
    QVBoxLayout,
    QTextEdit,    
)

from PySide2.QtWidgets import QApplication, QWidget
from PySide2.QtWebEngineWidgets import QWebEngineView  # type: ignore

from Qt import QtCore, QtGui, QtWidgets  # type: ignore
#from Qt.QtWidgets import (  # type: ignore
#    QAction,
#    QActionGroup,
#    QMenu,
#    QMainWindow,
#    QFileDialog,
#    QApplication,
#    QMessageBox,
#    QDialog,
#    QLabel,
#    QLineEdit,
#    QPushButton,
#    QDialogButtonBox,
#    QGridLayout,
#    QSizePolicy,
#)

from QuiltiX import quiltix
from QuiltiX.constants import ROOT
import materialxgltf.core as core
import MaterialX as mx

import pkg_resources

logger = logging.getLogger(__name__)

class glTFWidget(QDockWidget):
    def __init__(self, parent=None):
        super(glTFWidget, self).__init__(parent)
        
        self.setWindowTitle("glTF Viewer")
        
        # Create a web view
        self.web_view = QWebEngineView()        
        self.web_view.setUrl(QtCore.QUrl('https://kwokcb.github.io/MaterialX_Learn/documents/gltfViewer_simple.html'))

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)
        
        # Create a central widget to hold the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        
        # Set the central widget of the dock widget
        self.setWidget(central_widget)

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

        # Show glTF text. Does most of export, except does not write to file
        show_gltf_text = QAction("Show as glTF...", self.editor)
        show_gltf_text.triggered.connect(self.show_gltf_text_triggered)
        gltfMenu.addAction(show_gltf_text)

        self.setup_gltf_viewer_doc()

    def setup_gltf_viewer_doc(self):

        web_widget = glTFWidget(self.editor)
        self.editor.addDockWidget(QtCore.Qt.RightDockWidgetArea, web_widget)
        

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

        if not os.path.exists(path):
            logger.error('Cannot find input file: ' + path)
            return

        options = core.GLTF2MtlxOptions()
        options['createAssignments'] = False   
        options['addAllInputs'] = False
        options['addExtractNodes'] = True
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
                print('---------------------- MaterialX Document ----------------------')
                print(docString)
                print('Wrote MaterialX document to file: ' + path + '_stripped.mtlx')
                core.Util.writeMaterialXDoc(doc, path + '_stripped.mtlx')
                
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

        if not os.path.exists(path):
            logger.error('Cannot find input file: ' + path)
            return
        
        options = core.MTLX2GLTFOptions()

        # File name for baking
        options['bakeFileName'] = path + '_baked.mtlx'
        options['debugOutput'] = True
        gltfGeometryFile = pkg_resources.resource_filename('materialxgltf', 'data/shaderBall.gltf')
        print('> Load glTF geometry file: %s' % mx.FilePath(gltfGeometryFile).getBaseName())        
        #gltfGeomFileName = 'D:/Work/materialx/materialxgltf/src/materialxgltf/data/shaderball.gltf'
        options['geometryFile'] = gltfGeometryFile
        options['primsPerMaterial'] = True
        options['writeDefaultInputs'] = True
        
        searchPath = mx.getDefaultDataSearchPath()
        if not mx.FilePath(path).isAbsolute():
            path = os.path.abspath(path)
        searchPath.append(mx.FilePath(path).getParentPath())
        searchPath.append(mx.FilePath.getCurrentPath())
        searchPath.append(mx.FilePath(gltfGeometryFile).getParentPath())
        options['searchPath'] = searchPath
        options['packageBinary'] = True  
        options['translateShaders'] = True
        options['bakeTextures'] = True

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
        translatedCount = 0
        if options['translateShaders']:
            translatedCount = mtlx2glTFWriter.translateShaders(doc)
            logger.debug('- Translated shaders.' + str(translatedCount))

        # Perform baking if needed
        if translatedCount > 0 and options['bakeTextures']:
            logger.debug('- Baking start...')
            bakeResolution = 1024
            bakedFileName = options['bakeFileName']
            if options['bakeResolution']:
                bakeResolution = options['bakeResolution']
            mtlx2glTFWriter.bakeTextures(doc, False, bakeResolution, bakeResolution, False, 
                                        False, False, bakedFileName)
            if os.path.exists(bakedFileName):
                logger.debug('  - Baked textures to: ' + bakedFileName)
                doc, libFiles = core.Util.createMaterialXDoc()
                mx.readFromXmlFile(doc, bakedFileName, options['searchPath'])
                remappedUris = core.Util.makeFilePathsRelative(doc, bakedFileName)
                for uri in remappedUris:
                    logger.debug('  - Remapped URI: ' + uri[0] + ' to ' + uri[1])
                    core.Util.writeMaterialXDoc(doc, bakedFileName)
            logger.debug('- ...Baking end.')

        gltfString = mtlx2glTFWriter.convert(doc)
        return gltfString

    def show_gltf_text_triggered(self):

        options = core.MTLX2GLTFOptions()
        options['debugOutput'] = False
        options['primsPerMaterial'] = False
        options['writeDefaultInputs'] = False
        options['translateShaders'] = True
        options['bakeTextures'] = True

        path = self.editor.mx_selection_path
        if not path:
            path = self.editor.geometry_selection_path
        if not path:
            path = os.path.join(ROOT, "resources", "materials")

        searchPath = mx.getDefaultDataSearchPath()
        if not mx.FilePath(path).isAbsolute():
            path = os.path.abspath(path)
        searchPath.append(mx.FilePath(path).getParentPath())
        searchPath.append(mx.FilePath.getCurrentPath())
        # We do not embed the geometry file in the glTF file, so there is no need to add the path to the geometry file
        #searchPath.append(mx.FilePath(gltfGeometryFile).getParentPath())
        options['searchPath'] = searchPath

        options['bakeFileName'] = path + '/_temp_bake.mtlx'

        # Convert and display the text
        text = self.convert_graph_to_gltf(options)
        te_text = QTextEdit()
        te_text.setText(text)
        te_text.setReadOnly(True)
        te_text.setParent(self.editor, QtCore.Qt.Window)
        te_text.setWindowTitle("glTF text preview")
        te_text.resize(1000, 800)
        te_text.show()
                    

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
