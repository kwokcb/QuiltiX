import sys
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget, QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView

class WebWidget(QDockWidget):
    def __init__(self, parent=None):
        super(WebWidget, self).__init__(parent)
        
        self.setWindowTitle("Web Widget")
        
        # Create a web view
        self.web_view = QWebEngineView()        
        self.web_view.setUrl(QUrl('https://kwokcb.github.io/MaterialX_Learn/documents/gltfViewer_simple.html'))

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)
        
        # Create a central widget to hold the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        
        # Set the central widget of the dock widget
        self.setWidget(central_widget)

def main():
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    
    # Create the main widget
    main_widget = QWidget()
    main_window.setCentralWidget(main_widget)
    
    # Create a dockable web widget
    web_widget = WebWidget(main_window)
    main_window.addDockWidget(Qt.RightDockWidgetArea, web_widget)
    
    main_window.setGeometry(100, 100, 800, 600)
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
