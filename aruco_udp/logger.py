import logging
import sys

def setup_logger(name="ArUcoUDP"):
    """Initialize standard logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# Singleton-like access for convenience
logger = setup_logger()
village_logger = setup_logger("ArUcoUDP")
