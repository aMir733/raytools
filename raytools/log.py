def calc_verb(verbose, quiet, default):
        if quiet:
            return 50
        if not verbose:
            return default
        res = default - verbose * 10
        return 10 if res < 10 else res

def configure_logging(logging, level, logs=()):
        logging.basicConfig(
                level=level,
                format="[%(levelname)s] %(name)s: %(message)s",
                )
        for delta_level, log in logs:
            logging.getLogger(log).setLevel(level + delta_level)