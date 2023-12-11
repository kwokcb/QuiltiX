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
    QWidget 
)

#from PySide2.QtWidgets import QApplication, QWidget
from PySide2.QtWebEngineWidgets import QWebEngineView  # type: ignore

from Qt import QtCore # type: ignore
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

# MaterialX and related modules
import MaterialX as mx

haveJson = False
try:
    import materialxjson.core as jsoncore
    haveJson = True
except ImportError:
    print("materialxjson module is not installed.")

haveGLTF = False
try:
    import materialxgltf.core as core
    import materialxgltf
    haveGLTF = True
except ImportError:
    print("materialxgltf module is not installed.")

import pkg_resources

logger = logging.getLogger(__name__)

class glTFWidget(QDockWidget):
    def __init__(self, parent=None):
        super(glTFWidget, self).__init__(parent)
        
        self.setWindowTitle("glTF Viewer")

        self.setFloating(False)
        
        # Create a web view
        self.web_view = QWebEngineView()        
        self.web_view.setUrl(QtCore.QUrl('https://kwokcb.github.io/MaterialX_Learn/documents/gltfViewer_simple.html'))
        # e.g. Set to local host if you want to run a local page
        #self.web_view.setUrl(QtCore.QUrl('http://localhost:8000/gltfViewer_simple.html'))

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)
        
        # Create a central widget to hold the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        
        # Set the central widget of the dock widget
        self.setWidget(central_widget)

class GltfQuilitxPlugin():
    def __init__(self, editor, haveGLTF, haveJson):
        self.editor = editor

        # Test to disable all plug-ins
        disableAll = False
        if disableAll:
            haveGLTF = False
            haveJson = False

        if not haveGLTF and not haveJson:
            logger.error('Neither materialxjson nor materialxgltf modules are installed. glTF/JSON support will not be available.')
        
        if haveJson:
            # JSON menu items
            # ----------------------------------------
            self.editor.file_menu.addSeparator()
            gltfMenu = self.editor.file_menu.addMenu("JSON")
            # Export JSON item
            export_json = QAction("Save JSON...", self.editor)
            export_json.triggered.connect(self.export_json_triggered)
            gltfMenu.addAction(export_json)

            # Import JSON item
            import_json = QAction("Load JSON...", self.editor)
            import_json.triggered.connect(self.import_json_triggered)
            gltfMenu.addAction(import_json)

            # Show JSON text. Does most of export, except does not write to file
            show_json_text = QAction("Show as JSON...", self.editor)
            show_json_text.triggered.connect(self.show_json_triggered)
            gltfMenu.addAction(show_json_text)

        if haveGLTF:
            # glTF menu items
            # ----------------------------------------
            # Update 'File' menu
            #########################################
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

            version = 'materialxgltf version: ' + materialxgltf.__version__
            version_action = QAction(version, self.editor)
            version_action.setEnabled(False)
            gltfMenu.addAction(version_action)

            # Add glTF Viewer
            self.setup_gltf_viewer_doc()

            # Update 'View' menu
            #########################################
            # Add viewer toggle
            self.act_gltf_viewer = QAction("glTF Viewer", self.editor)
            self.act_gltf_viewer.setCheckable(True)
            self.act_gltf_viewer.toggled.connect(self.on_gltf_viewer_toggled)
            self.editor.view_menu.addSeparator()
            self.editor.view_menu.addAction(self.act_gltf_viewer)

            # Override about to show event to update the gltf viewer toggle
            self.editor.view_menu.aboutToShow.connect(self.custom_on_view_menu_about_to_show) 

    def custom_on_view_menu_about_to_show(self):
        self.editor.on_view_menu_showing()
        self.act_gltf_viewer.setChecked(self.web_dock_widget.isVisible())

    def on_gltf_viewer_toggled(self, checked):
        self.web_dock_widget.setVisible(checked)
        
    def setup_gltf_viewer_doc(self):

        self.web_dock_widget = glTFWidget(self.editor)
        self.editor.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.web_dock_widget)        


    ## Core utilities
    def show_text_box(self, text, title=""):
        '''
        Show a text box with the given text.
        '''
        te_text = QTextEdit()
        te_text.setText(text)
        te_text.setReadOnly(True)
        te_text.setParent(self.editor, QtCore.Qt.Window)
        te_text.setWindowTitle(title)
        te_text.resize(1000, 800)
        te_text.show()

    def show_json_triggered(self):
        '''
        Show the current graph as JSON text.
        '''
        doc = self.editor.qx_node_graph.get_current_mx_graph_doc()

        exporter = jsoncore.MaterialXJson()

        json_result = exporter.documentToJSON(doc)

        # Write JSON to file
        if json_result:
            text = jsoncore.Util.jsonToJSONString(json_result, 2)
            self.show_text_box(text, 'JSON Representation')

    def export_json_triggered(self):
        '''
        Export the current graph to a JSON file.
        '''
        start_path = self.editor.mx_selection_path
        if not start_path:
            start_path = self.editor.geometry_selection_path

        if not start_path:
            start_path = os.path.join(ROOT, "resources", "materials")

        path = self.editor.request_filepath(
            title="Save JSON file", start_path=start_path, file_filter="JSON files (*.json)", mode="save",
        )

        if not path:
            return

        doc = self.editor.qx_node_graph.get_current_mx_graph_doc()

        exporter = jsoncore.MaterialXJson()

        json_result = exporter.documentToJSON(doc)

        # Write JSON to file
        if json_result:
            with open(path, 'w') as outfile:
                jsoncore.Util.writeJson(json_result, path, 2)
                logger.info('Wrote JSON file: ' + path)

        self.editor.set_current_filepath(path)

    def import_json_triggered(self):
        '''
        Import a JSON file into the current graph.
        '''
        start_path = self.editor.mx_selection_path
        if not start_path:
            start_path = self.editor.geometry_selection_path

        if not start_path:
            start_path = os.path.join(ROOT, "resources", "materials")

        path = self.editor.request_filepath(
            title="Load JSON file", start_path=start_path, file_filter="JSON files (*.json)", mode="open",
        )

        if not os.path.exists(path):
            logger.error('Cannot find input file: ' + path)
            return

        doc = jsoncore.Util.jsonFileToXml(path) 
        if doc:
            logger.info('Loaded JSON file: ' + path)
            self.editor.mx_selection_path = path
            self.editor.qx_node_graph.load_graph_from_mx_doc(doc, path)

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
    
    def setup_default_export_options(self, path, bakeFileName, embed_geometry=False):
        '''
        Set up the default export options for the given path.
        '''
        options = core.MTLX2GLTFOptions()

        options['debugOutput'] = False
        options['bakeFileName'] = bakeFileName

        if embed_geometry:
            gltfGeometryFile = pkg_resources.resource_filename('materialxgltf', 'data/shaderBall.gltf')
            print('> Load glTF geometry file: %s' % mx.FilePath(gltfGeometryFile).getBaseName())        
            options['geometryFile'] = gltfGeometryFile        
        options['primsPerMaterial'] = True
        options['writeDefaultInputs'] = False
        options['translateShaders'] = True
        options['bakeTextures'] = True

        searchPath = mx.getDefaultDataSearchPath()
        if not mx.FilePath(path).isAbsolute():
            path = os.path.abspath(path)
        searchPath.append(mx.FilePath(path).getParentPath())
        searchPath.append(mx.FilePath.getCurrentPath())
        if embed_geometry:
            searchPath.append(mx.FilePath(gltfGeometryFile).getParentPath())
        options['searchPath'] = searchPath

        return options

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
        
        # Set up export options
        bakeFileName = path + '_baked.mtlx'
        options = self.setup_default_export_options(path, bakeFileName, embed_geometry=True)
        print('Export options:', options)

        gltf_string = self.convert_graph_to_gltf(options)
        if gltf_string == '{}':
            return

        self.editor.set_current_filepath(path)

        # To be able to view the exported file in the glTF viewer, we need to package to a  binary file
        options['packageBinary'] = True
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
            logger.info('- Save GLB file:' + binaryFileName + '. Status:' + str(saved))
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
            logger.debug('- Translated shaders: ' + str(translatedCount))

        # Perform baking if needed
        if translatedCount > 0 and options['bakeTextures']:
            logger.debug('- Baking start...')
            bakeResolution = 2048
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

        path = self.editor.mx_selection_path
        if not path:
            path = self.editor.geometry_selection_path
        if not path:
            path = os.path.join(ROOT, "resources", "materials")

        # Setup export options
        bakeFileName = path + '/temp_baked.mtlx'
        options = self.setup_default_export_options(path, bakeFileName, embed_geometry=False)
    
        # Convert and display the text
        text = self.convert_graph_to_gltf(options)
        self.show_text_box(text, 'glTF Representation')
                    

class GltfQuiltix(quiltix.QuiltiXWindow):
    '''
    QuiltiX window with plug-in functionality added
    '''
    def __init__(self, load_style_sheet=True, load_shaderball=True, load_default_graph=True):
        super().__init__(load_style_sheet=True, load_shaderball=True, load_default_graph=True)

        self.plugin = GltfQuilitxPlugin(self, haveGLTF, haveJson)

    
def launch():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    editor = GltfQuiltix()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    launch()
