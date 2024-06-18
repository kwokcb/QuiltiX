import os
import importlib.util

def load_and_install_plugins(editor, plugin_folder):
    if not os.path.isdir(plugin_folder):
        print(f"Plugin folder {plugin_folder} not found.")
        return
    
    # Get the list of all subfolders in the plugin_folder
    for entry in os.listdir(plugin_folder):
        entry_path = os.path.join(plugin_folder, entry)

        if os.path.isdir(entry_path):
            # Check for the presence of plugin.py in the subfolder
            plugin_file = os.path.join(entry_path, 'plugin.py')
            if os.path.isfile(plugin_file):
                module_name = f"{entry}.plugin"

                # Dynamically import the module
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Check if the module has an installPlugin function
                if hasattr(module, "installPlugin"):
                    # Call the installPlugin function
                    loaded = module.installPlugin()
                    print(f"Installing plugin from {plugin_file}...", loaded)
                else:
                    print(f"No installPlugin function found in {plugin_file}.")
            else:
                print(f"No plugin.py file found in {entry_path}.")
        else:
            print(f"Skipping non-directory entry {entry_path}.")

#if __name__ == "__main__":
#    plugin_folder = "plugins"  # Specify the folder containing plugins
#    editor = None
#    load_and_install_plugins(editor, plugin_folder)
