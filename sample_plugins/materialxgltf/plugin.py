'''
@brief Sample plug-in for QuiltiX which adds import, export, and preview functionality for MaterialX in JSON format
'''

import logging
import os

# Optional syntax highlighting if pygments is installed
have_highliting = True
try:
    from pygments import highlight
    from pygments.lexers import JsonLexer
    from pygments.formatters import HtmlFormatter
except ImportError:
    have_highliting = False

from typing import TYPE_CHECKING

from qtpy import QtCore  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QAction,
    QDockWidget,
    QVBoxLayout,
    QTextEdit,
    QWidget 
)
from QuiltiX import constants, qx_plugin
from QuiltiX.constants import ROOT

logger = logging.getLogger(__name__)

# MaterialX and related modules
import MaterialX as mx

haveGLTF = False
try:
    import materialxgltf.core as core
    import materialxgltf
    haveGLTF = True
except ImportError:
    logger.error("materialxgltf module is not installed.")

# Optional syntax highlighting if pygments is installed
have_highliting = True
try:
    from pygments import highlight
    from pygments.lexers import JsonLexer
    from pygments.formatters import HtmlFormatter
except ImportError:
    have_highliting = False

# Use to allow access to resources in the package
import pkg_resources

class GLTFHighlighter:
    def __init__(self):
        self.lexer = JsonLexer()
        # We don't add line numbers since this get's copied with
        # copy-paste.
        self.formatter = HtmlFormatter(linenos=False, style='github-dark')

    def highlight(self, text):
        highlighted_html = highlight(text, self.lexer, self.formatter)
        styles = (
            f"<style>"
            f"{self.formatter.get_style_defs('.highlight')}"
            f"pre {{ line-height: 1.0; margin: 0; }}"
            f"</style>"
        )
        full_html = f"<html><head>{styles}</head><body>{highlighted_html}</body></html>"     
        return full_html

class glTFWidget(QDockWidget):
    '''
    Description: glTF Viewer widget    
    '''
    def __init__(self, parent=None):
        '''
        Description: Sets up a web view and loads in a sample glTF viewer page.
        '''
        super(glTFWidget, self).__init__(parent)
        
        self.setWindowTitle("glTF Viewer")

        self.setFloating(False)
        
        # Create a web view. 
        self.web_view = None # QWebEngineView()        
        #self.web_view.setUrl(QtCore.QUrl('https://materialx.nanmucreative.com/documents/simpleViewer.html'))
                #'https://kwokcb.github.io/web_scene_editor/viewer/room_viewer.html'))
                        
        # e.g. Set to local host if you want to run a local page
        #self.web_view.setUrl(QtCore.QUrl('http://localhost:8000/gltfViewer_simple.html'))

        # Set up the layout
        layout = QVBoxLayout()
        #layout.addWidget(self.web_view)
        
        # Create a central widget to hold the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        
        # Set the central widget of the dock widget
        self.setWidget(central_widget)

class QuiltiX_glTF_serializer():
    '''
    @brief glTF serializer for MaterialX
    '''

    def __init__(self, editor, root) -> None:
        '''
        Initialize the plugin. Adds in:
        - Menu items for loading and saving glTF files
        - Menu items for setting options for glTF export
        - Menu item for showing the current graph as glTF text

        @param editor: The QuiltiX editor
        @param root: The root path of QuitiX        
        '''
        self.editor = editor
        self.root = root
        
        # glTF menu items
        # ----------------------------------------
        # Update 'File' menu
        #########################################
        editor.file_menu.addSeparator()
        gltfMenu1 = self.editor.file_menu.addMenu("glTF")

        # Load menu item
        import_gltf_item = QAction("Load glTF...", editor)
        import_gltf_item.triggered.connect(self.import_gltf_triggered)
        gltfMenu1.addAction(import_gltf_item)

        # Save menu item
        export_gltf_item = QAction("Save glTF...", editor)
        export_gltf_item.triggered.connect(self.export_gltf_triggered)
        gltfMenu1.addAction(export_gltf_item)

        # Show glTF text. Does most of export, except does not write to file
        show_gltf_text = QAction("Show as glTF...", editor)
        show_gltf_text.triggered.connect(self.show_gltf_text_triggered)
        gltfMenu1.addAction(show_gltf_text)

        # Update 'Options' menu
        #########################################
        editor.options_menu.addSeparator()
        gltfMenu2 = editor.options_menu.addMenu("glTF Options")

        self.bake_textures_option = QAction("Always Bake Textures", editor)
        self.bake_textures_option.setCheckable(True)
        self.bake_textures_option.setChecked(False)
        gltfMenu2.addAction(self.bake_textures_option)

        #version = 'materialxgltf version: ' + materialxgltf.__version__
        #version_action = QAction(version, self.editor)
        #version_action.setEnabled(False)
        #gltfMenu.addAction(version_action)

        # Add glTF Viewer
        self.setup_gltf_viewer_doc()

        # Update 'View' menu
        #########################################
        # Add viewer toggle
        self.act_gltf_viewer = QAction("glTF Viewer", editor)
        self.act_gltf_viewer.setCheckable(True)
        self.act_gltf_viewer.toggled.connect(self.on_gltf_viewer_toggled)
        editor.view_menu.addSeparator()
        editor.view_menu.addAction(self.act_gltf_viewer)

        # Override about to show event to update the gltf viewer toggle
        editor.view_menu.aboutToShow.connect(self.custom_on_view_menu_about_to_show)   

    def custom_on_view_menu_about_to_show(self):
        '''
        Custom about to show event for the view menu. Updates the glTF viewer toggle.
        '''
        self.editor.on_view_menu_showing()
        self.act_gltf_viewer.setChecked(self.web_dock_widget.isVisible())

    def on_gltf_viewer_toggled(self, checked) -> None:
        '''
        Toggle the glTF viewer dock widget.
        '''
        self.web_dock_widget.setVisible(checked)
        
    def setup_gltf_viewer_doc(self) -> None:
        '''
        Set up the glTF viewer dock widget.
        '''
        self.web_dock_widget = glTFWidget(self.editor)
        self.editor.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.web_dock_widget)        

    ## Core utilities
    def show_text_box(self, text, title="") -> None:
        '''
        Show a text box with the given text.
        @param text: The text to show
        @param title: The title of the text box. Default is empty string.        
        '''
        te_text = QTextEdit()

        if have_highliting:
            jsonHighlighter = GLTFHighlighter()
            highlighted_html = jsonHighlighter.highlight(text)
            te_text.setHtml(highlighted_html)
        else:
            te_text.setText(text)
        te_text.setReadOnly(True)
        te_text.setParent(self.editor, QtCore.Qt.Window)
        te_text.setWindowTitle(title)
        te_text.resize(1000, 800)
        te_text.show()

    def import_gltf_triggered(self) -> None:
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

        # Setup defaults for glTF import and create the MaterialX document
        # - Do not create assignments
        # - Do not add all inputs
        # - Add extract nodes. Only required for pre 1.39 MaterialX
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
                # Extract out the appropriate data from the original MaterialX document
                docString = core.Util.writeMaterialXDocString(doc)
                doc = mx.createDocument()
                mx.readFromXmlString(doc, docString)

                # Auto ng creation can cause issues for nodes with multiple outputs. Turn off on import
                ng_abstraction = self.editor.act_ng_abstraction.isChecked()
                self.editor.act_ng_abstraction.setChecked(False)  

                self.editor.mx_selection_path = path
                self.editor.qx_node_graph.load_graph_from_mx_doc(doc)
                self.editor.qx_node_graph.mx_file_loaded.emit(path)

                self.editor.act_ng_abstraction.setChecked(ng_abstraction)
    
    def setup_default_export_options(self, path, bakeFileName, embed_geometry=False) -> dict:
        '''
        Set up the default export options for gltf output.
        @param path (str): path to the gltf file
        @param bakeFileName (str): path to the baked file
        @param embed_geometry (bool): whether to embed the geometry in the gltf file. Default is False.
        @return options (dict): Dictionary of options for the conversion
        '''
        options = core.MTLX2GLTFOptions()

        options['debugOutput'] = False
        options['bakeFileName'] = bakeFileName

        # TODO: Expose these options to the user
        if embed_geometry:
            # By default uses the "MaterialX" shader ball provided as part of
            # the materialxgltf package for binary export. 
            gltfGeometryFile = pkg_resources.resource_filename('materialxgltf', 'data/shaderBall.gltf')
            msg = '> Load default geometry: %s' % mx.FilePath(gltfGeometryFile).getBaseName()
            logger.info(msg)        
            options['geometryFile'] = gltfGeometryFile        
        options['primsPerMaterial'] = True
        options['writeDefaultInputs'] = False
        options['translateShaders'] = True
        options['bakeTextures'] = True
        # Always should be set
        options['addExtractNodes'] = True

        searchPath = mx.getDefaultDataSearchPath()
        if not mx.FilePath(path).isAbsolute():
            path = os.path.abspath(path)
        searchPath.append(mx.FilePath(path).getParentPath())
        searchPath.append(mx.FilePath.getCurrentPath())
        if embed_geometry:
            searchPath.append(mx.FilePath(gltfGeometryFile).getParentPath())
        options['searchPath'] = searchPath

        return options

    def export_gltf_triggered(self) -> None:
        '''
        Export the current graph to a glTF file in binary format (glb)
        - Will perform shader translation if needed to glTF
        - Will perform baking if needed
        - Will package to a binary file
        @return: None
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
        bakeFileName = start_path + '_baked.mtlx'
        options = self.setup_default_export_options(path, bakeFileName, embed_geometry=True)
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
   

    def convert_graph_to_gltf(self, options) -> str:
        '''
        Convert the current graph to a glTF document string.
        Will perform:
        - Shader translation if needed (not that only standard surface is supported)
        - Baking if needed. Note that this writes local files.
        - Uses the materialgltf package to perform conversion

        @param options (dict): Dictionary of options for the conversion            
        @return The glTF string.
        '''
        # Disable auto nodegraph creation during
        ng_abstraction = self.editor.act_ng_abstraction.isChecked()
        self.editor.act_ng_abstraction.setChecked(False)  

        doc = self.editor.qx_node_graph.get_current_mx_graph_doc()
        
        self.editor.act_ng_abstraction.setChecked(ng_abstraction)

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

        forceBake = False
        if self.bake_textures_option.isChecked():
            logger.debug('--- Forcing baking of textures')
            forceBake = True

        # Perform baking if needed
        if forceBake or (translatedCount > 0 and options['bakeTextures']):
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
        '''
        Show the current graph as glTF text popup.
        '''
        path = self.editor.mx_selection_path
        if not path:
            path = self.editor.geometry_selection_path
        if not path:
            path = os.path.join(ROOT, "resources", "materials")

        # Setup export options
        bakeFileName = path + '/temp_baked.mtlx'
        options = self.setup_default_export_options(path, bakeFileName, embed_geometry=False)

        logger.debug('Show glTF text triggered. Path:' + path + '. bakeFileName: ' + bakeFileName)

        # Convert and display the text                
        text = self.convert_graph_to_gltf(options)
        self.show_text_box(text, 'glTF Representation')
                    
@qx_plugin.hookimpl
def after_ui_init(editor: "quiltix.QuiltiXWindow"):
    '''
    @brief After UI initialization, add the MaterialX glTF serializer to the editor.
    '''
    logger.debug("Adding MaterialX glTF serializer")
    editor.gltf_serializer = QuiltiX_glTF_serializer(editor, constants.ROOT)

def plugin_name() -> str:
    '''
    @brief Get the name of the plugin.
    @return The name of the plugin.'''
    if haveGLTF:
        return "MaterialX glTF Serializer"
    return ""

def is_valid() -> bool:
    '''
    @brief Check if the plugin is valid. That is the glTF serializer module is installed.
    @return True if the plugin is valid), False otherwise.
    '''
    return haveGLTF