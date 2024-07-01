from pycromanager import Core, start_headless, stop_headless

class Controller(Core):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Controller, cls).__new__(cls)
            cls._initialized = False
        return cls._instance

    def __init__(self, config_file:str, app_path:str="C:\\Program Files\\Micro-Manager-2.0", headless:bool=True):
        if self._initialized:
            return
        super().__init__()
        self._app_path = app_path
        self._config_file = config_file
        self.headless = headless
        self._initialize_core()
        self._initialized = True

    def _initialize_core(self):
        if self.headless:
            start_headless(self._app_path, self._config_file, debug=False)
        self.load_system_configuration(self._config_file)

    def __del__(self):
        if self.headless:
            stop_headless()

    @property
    def app_path(self):
        return self._app_path

    @app_path.setter
    def app_path(self, value:str):
        self._app_path = value
        if self.headless:
            stop_headless()
            start_headless(self._app_path, self._config_file, debug=False)
        self.load_system_configuration(self._config_file)

    @property
    def config_file(self):
        return self._config_file

    @config_file.setter
    def config_file(self, value:str):
        self._config_file = value
        if self.headless:
            stop_headless()
            start_headless(self._app_path, self._config_file, debug=False)
        self.load_system_configuration(self._config_file)


# To be used throughout the program
controller = Controller()

__all__ = ['controller']