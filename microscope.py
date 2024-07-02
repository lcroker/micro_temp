import logging
import time
import gc
import psutil
import multiprocessing
from pycromanager import Core, start_headless, stop_headless

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def shutdown_core():
    try:
        core = Core()
        core.reset()
        stop_headless(debug=True)
    except Exception as e:
        logging.error(f"Error during core shutdown: {e}")
    finally:
        logging.info("Core shutdown process completed.")

class Microscope:
    def __init__(self, config_file, app_path="C:\\Program Files\\Micro-Manager-2.0", headless=True):
        self.config_file = config_file
        self.app_path = app_path
        self.headless = headless
        self.core = self.initialize_core()
        
        if self.core is None:
            raise Exception("Failed to initialize Micro-Manager core.")
        
        self.camera = None
        self.stage = None
        self.lamp = None
        self.autofocus = None
        self.java_process = None
        self.initialize_components()

    def initialize_core(self, max_attempts=10, delay=5):
        for attempt in range(1, max_attempts + 1):
            try:
                logging.info(f"Attempt {attempt} to initialize Micro-Manager")
                if self.headless:
                    start_headless(mm_app_path=self.app_path, config_file=self.config_file, debug=True)
                    logging.info("Waiting for ZMQ server to start...")
                    time.sleep(10)  # Wait for the ZMQ server to start properly
                    self.find_java_process()
                
                core = Core()
                if not self.headless:
                    core.load_system_configuration(self.config_file)
                
                logging.info("Micro-Manager core initialized successfully")
                return core
            except Exception as e:
                logging.error(f"Attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error("All attempts to initialize Micro-Manager have failed.")
                    return None

    def initialize_components(self):
        from camera import Camera
        from stage import Stage
        from lamp import Lamp
        
        self.camera = Camera(self.core)
        self.stage = Stage(self.core)
        self.lamp = Lamp(self.core)

    def find_java_process(self):
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'java' in proc.info['name'].lower() and any('micro-manager' in arg.lower() for arg in proc.info['cmdline']):
                self.java_process = proc
                logging.info(f"Found Java process for Micro-Manager: PID {proc.pid}")
                break

    def shutdown(self):
        logging.info("Initiating Micro-Manager shutdown...")
        try:
            # Release resources
            self.camera = None
            self.stage = None
            self.lamp = None
            self.autofocus = None

            # Run the shutdown helper in a separate process
            p = multiprocessing.Process(target=shutdown_core)
            p.start()
            p.join(timeout=10)  # Wait for up to 10 seconds
            
            if p.is_alive():
                logging.warning("Core shutdown process timed out. Terminating...")
                p.terminate()
                p.join()

            # Nullify the core object
            self.core = None
            
            # Force garbage collection
            gc.collect()

            logging.info("Core reference released and garbage collection forced.")

            # If we found a Java process, try to terminate it
            if self.java_process:
                try:
                    self.java_process.terminate()
                    self.java_process.wait(timeout=5)  # Wait up to 5 seconds for the process to terminate
                    logging.info(f"Java process (PID {self.java_process.pid}) terminated.")
                except psutil.NoSuchProcess:
                    logging.info("Java process already terminated.")
                except psutil.TimeoutExpired:
                    logging.warning(f"Timeout while waiting for Java process (PID {self.java_process.pid}) to terminate. Forcing kill.")
                    self.java_process.kill()
                except Exception as e:
                    logging.error(f"Error terminating Java process: {e}")

            logging.info("Micro-Manager shutdown complete.")
        except Exception as e:
            logging.error(f"Unexpected error during shutdown: {e}")

    def __del__(self):
        if hasattr(self, 'core') and self.core is not None:
            self.shutdown()