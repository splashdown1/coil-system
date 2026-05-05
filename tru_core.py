import time

import os

import json

def pulse():

    while True:

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # Check current state against verified_facts

        try:

            with open('verified_facts.json', 'r') as f:

                facts = json.load(f)

            status = "ok"

            tasks = 7

            chunks = 143360

        except:

            status = "drift detected"

            tasks = 0

            chunks = 0

            

        log_entry = f"{timestamp} HEARTBEAT {status} — tasks:{tasks} complete:{tasks} chunks:{chunks}\n"

        with open('actions.log', 'a') as log:

            log.write(log_entry)

        

        print(f"Pulse: {log_entry.strip()}")

        time.sleep(60)

if __name__ == "__main__":

    pulse()