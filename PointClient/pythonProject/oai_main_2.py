import requests
import xml.etree.ElementTree as ET
import os
import threading
import queue
import subprocess
import logging
import time
import tempfile

############
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import socket
############

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class SourceAddressAdapter(HTTPAdapter):
    def __init__(self, source_address, **kwargs):
        self.source_address = source_address
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            source_address=(self.source_address, 0),  # 0 means OS picks port
            **pool_kwargs
        )

# DASH Server Configuration, replace wiith IP of oaitun_ue1
MPD_URL = "http://12.1.1.100:8080/media/foo"
OUTPUT_DIR = "./downloads"
NUM_DOWNLOAD_THREADS = 2
NUM_DECODE_THREADS = 4
MPD_REFRESH_INTERVAL = 0.033  # Fetch MPD every 500ms
MAX_PROCESSED_FILES = 100  # Keep only last 100 frames
DRACO_DECODER_PATH = "draco_decoder"
PREPARE_SCRIPT = "/decode_draco.sh"

# Queues for parallel processing
download_queue = queue.Queue()
decode_queue = queue.Queue()
processed_files = []  # Stores processed DRC URLs

# Replace with actual IP of oai-ext-dn interface
SOURCE_INTERFACE_IP = "192.168.70.135"

session = requests.Session()
session.mount("http://", SourceAddressAdapter(SOURCE_INTERFACE_IP))
session.mount("https://", SourceAddressAdapter(SOURCE_INTERFACE_IP))


def fetch_mpd():
    """Fetches MPD updates & adds new DRC files to the download queue."""
    while True:
        try:
            # response = requests.get(MPD_URL, timeout=20)
            response = session.get(MPD_URL, timeout=20)
            if response.status_code != 200:
                logging.error(f"Failed to fetch MPD: {response.status_code}")
                time.sleep(MPD_REFRESH_INTERVAL)
                continue

            mpd_xml = response.text
            mpd_root = ET.fromstring(mpd_xml)
            # base_url = mpd_root.find("BaseURL").text.rstrip("/")  # ✅ Ensure no trailing `/`
            base_url = MPD_URL

            for period in mpd_root.findall("Period"):
                for adaptation_set in period.findall("AdaptationSet"):
                    for representation in adaptation_set.findall("Representation"):
                        base_url_element = representation.find("BaseURL")
                        if base_url_element is not None:
                            drc_path = base_url_element.text.lstrip("/")  # ✅ Ensure no leading `/`

                            # ✅ Prevent duplicate BaseURL paths
                            if drc_path.startswith("media/foo/"):
                                drc_path = drc_path.replace("media/foo/", "", 1)  # Remove first occurrence

                            full_url = f"{base_url}/{drc_path}"  # Correct URL

                            if full_url not in processed_files:
                                download_queue.put(full_url)
                                processed_files.append(full_url)

                                # Keep only the last 100 frames
                                if len(processed_files) > MAX_PROCESSED_FILES:
                                    processed_files.pop(0)

            time.sleep(MPD_REFRESH_INTERVAL)  # Fetch next MPD update
        except Exception as e:
            logging.error(f"Error fetching MPD: {e}")
            time.sleep(MPD_REFRESH_INTERVAL)


def download_drc():
    """Streams DRC files directly into memory and passes to the decoder."""
    while True:
        drc_url = download_queue.get()
        if drc_url is None:
            break  # Exit thread

        filename = os.path.basename(drc_url)
        logging.info(f"Streaming {drc_url} into memory...")       

        try:
            # response = requests.get(drc_url, stream=True, timeout=2)
            response = session.get(drc_url, stream=True, timeout=2)
            if response.status_code == 200:
                drc_data = response.content  # Load full DRC file into memory
                logging.info(f"Downloaded {filename} into memory ✅")

                decode_queue.put((filename, drc_data))  # Pass to decoder queue
            else:
                logging.error(f"Failed to download {drc_url} - HTTP {response.status_code}")
        except Exception as e:
            logging.error(f"Download error: {e}")

        download_queue.task_done()


def decode_drc():
    """Decodes DRC files directly from memory using Draco decoder."""
    while True:
        filename, drc_data = decode_queue.get()
        if filename is None:
            break  # Exit thread

        ply_path = os.path.join(OUTPUT_DIR, filename.replace(".drc", ".ply"))
        logging.info(f"Decoding {filename} directly from memory to {ply_path}...")

        try:
            # Write the DRC data into a temporary file for Draco
            with tempfile.NamedTemporaryFile(delete=True) as temp_drc:
                temp_drc.write(drc_data)
                temp_drc.flush()  # Ensure all data is written

                process = subprocess.Popen(
                    [DRACO_DECODER_PATH, "-i", temp_drc.name, "-o", ply_path],  # Use temp file
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                stdout, stderr = process.communicate()

            if process.returncode == 0:
                logging.info(f"Decoded PLY saved to {ply_path} ✅")
            else:
                logging.error(f"Decoding failed for {filename}: {stderr.decode()}")

        except Exception as e:
            logging.error(f"Error decoding {filename}: {e}")

    
        decode_queue.task_done()


def start_threads():
    """Starts all necessary threads for ultra-low latency processing."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Start MPD fetching thread
    threading.Thread(target=fetch_mpd, daemon=True).start()

    # Start download worker threads
    for _ in range(NUM_DOWNLOAD_THREADS):
        threading.Thread(target=download_drc, daemon=True).start()

    # Start decode worker threads
    for _ in range(NUM_DECODE_THREADS):
        threading.Thread(target=decode_drc, daemon=True).start()


if __name__ == "__main__":
    start_threads()

    try:
        while True:
            time.sleep(1)  # Keep main thread alive
    except KeyboardInterrupt:
        logging.info("Shutting down client...")
