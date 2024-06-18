import os
import importlib
import inspect

class PluginInterface:
    def perform_action(self):
        raise NotImplementedError("Subclasses must implement this method")


class PluginManager:
    def __init__(self):
        self.plugins = []

    def register_plugin(self, plugin):
        if not isinstance(plugin, PluginInterface):
            raise ValueError("Plugin must be an instance of PluginInterface")
        self.plugins.append(plugin)

    def run_all_plugins(self):
        for plugin in self.plugins:
            plugin.perform_action()


# Example plugin
class SamplePlugin(PluginInterface):
    def perform_action(self):
        print("SamplePlugin performing action")


# Usage
if __name__ == "__main__":
    # Create a PluginManager instance
    plugin_manager = PluginManager()

    # Register plugins
    plugin_manager.register_plugin(SamplePlugin())

    # Run all registered plugins
    plugin_manager.run_all_plugins()

class PluginLoader:
    @staticmethod
    def load_plugins(plugin_folder):
        plugins = []

        # List all files in the plugin folder
        files = [f for f in os.listdir(plugin_folder) if f.endswith(".py")]

        for file_name in files:
            # Remove the ".py" extension
            module_name = file_name[:-3]

            try:
                # Import the module dynamically
                module = importlib.import_module(f"{plugin_folder}.{module_name}")

                # Iterate over the items in the module
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    # Check if it's a class and a subclass of PluginInterface
                    if inspect.isclass(item) and issubclass(item, PluginInterface) and item != PluginInterface:
                        # Instantiate and register the plugin
                        plugin_instance = item()
                        plugins.append(plugin_instance)

            except Exception as e:
                print(f"Error loading plugin from {file_name}: {e}")

        return plugins


if __name__ == "__main__":
    # Specify the folder containing the plugin files
    plugin_folder = "plugins"

    # Create a PluginManager instance
    plugin_manager = PluginManager()

    # Load and register plugins from the specified folder
    loaded_plugins = PluginLoader.load_plugins(plugin_folder)
    for plugin in loaded_plugins:
        plugin_manager.register_plugin(plugin)

    # Run all registered plugins
    plugin_manager.run_all_plugins()
