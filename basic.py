from client.clients import BasicClient

import logging

if __name__ == '__main__':
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console) # Pull the root logger
    logging.getLogger('').setLevel(logging.DEBUG)

    client = BasicClient()
    client.run()

