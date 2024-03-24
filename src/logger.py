import logging.handlers
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.joinpath("logs")
Path(LOG_DIR).mkdir(exist_ok=True)


def set_logger():
    file_log = logging.handlers.RotatingFileHandler(
        filename=LOG_DIR / "log.txt",
        mode="a",
        delay=True,
        encoding="utf-8",
        backupCount=10,
        maxBytes=102400,
    )
    file_log.setLevel(logging.ERROR)
    console_out = logging.StreamHandler()
    console_out.setLevel(logging.INFO)
    logging.basicConfig(
        handlers=(file_log, console_out),
        format="[%(asctime)s | %(levelname)s]: %(message)s",
        datefmt="%d.%m.%Y %H:%M:%S",
        level=logging.INFO,
    )
