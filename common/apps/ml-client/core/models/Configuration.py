import os
import pathlib
import core.util as util


class Configuration(object):
    """Stores configuration data for access by other modules."""

    def __init__(self) -> None:
        self.files: dict = None
        self.data: dict = None

    def load(self):
        """Load all config files in custom/config"""
        self.files = {}
        for root, _dirs, files in os.walk("custom/config"):
            for file in files:
                full_path = os.path.join(root, file)
                self.files[pathlib.Path(full_path).stem] = full_path

        self.data = {}
        for key, value in self.files.items():
            # Only import YML files.
            if pathlib.Path(value).suffix == ".yml":
                self.data[key] = util.config.load_yaml(value)
            else:
                print(f"Ommited {key} while loading")


if __name__ == "__main__":
    config = Configuration()
    config.load()
