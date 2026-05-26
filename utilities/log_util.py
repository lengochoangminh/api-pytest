import logging, allure, os, time


class Logger:
    def __init__(self, logger, file_level=logging.INFO):
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)

        fmt = logging.Formatter(
            "%(asctime)s - %(filename)s:[%(lineno)s] - [%(levelname)s] - %(message)s"
        )

        curr_time = time.strftime("%Y-%m-%d")
        BASE_DIR = os.path.dirname(
            os.path.abspath(__file__)
        )  # Directory where configReader.py is located
        log_dir = os.path.join(BASE_DIR, "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        LOG_PATH = os.path.join(log_dir, "log")  # Navigate to conf.ini

        # self.LogFileName = 'Logs\\log' + curr_time + '.txt'
        self.LogFileName = LOG_PATH + curr_time + ".txt"
        # "a" to append the logs in same file, "w" to generate new logs and delete old one
        fh = logging.FileHandler(self.LogFileName, mode="a", encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(file_level)
        self.logger.addHandler(fh)

    def write_log(self, level, message):

        icon = "✅" if level == "info" else "⚠️ "  # ❌

        with allure.step(f"{icon} - {message}"):
            try:
                print(f"{icon} {message}")
            except UnicodeEncodeError:
                print(f"[{level.upper()}] {message}")

            log_methods = {
                "info": self.logger.info,
                "debug": self.logger.debug,
                "warning": self.logger.warning,
                "error": self.logger.error,
                "critical": self.logger.critical,
            }

            log_fn = log_methods.get(level)
            if log_fn:
                log_fn(message)
            else:
                self.logger.error(f"Invalid log level: {level}. Message: {message}")
