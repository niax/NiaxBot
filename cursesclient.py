from client.clients import CursesClient

import logging

if __name__ == '__main__':
    file = logging.FileHandler("logs/client.log")
    file.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file.setFormatter(formatter)
    logging.getLogger('').addHandler(file) # Pull the root logger
    logging.getLogger('').setLevel(logging.DEBUG)
    
    client = CursesClient()
    client.run()
