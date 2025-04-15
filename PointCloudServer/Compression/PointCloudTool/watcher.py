# #!/usr/bin/env python
# import os
# import time
# import subprocess
# import redis
# import logging
# import threading
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler

# # Logging Configuration
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# # Redis Configuration
# REDIS_HOST = "redis"
# REDIS_PORT = 6379
# REDIS_QUEUE = "ply_processing_queue"
# DRC_BUFFER = "drc_stream_buffer"
# MPD_CHANNEL = "mpd_updates"
# DISK_QUEUE = "drc_disk_queue"
# MAX_REDIS_CACHE = 30

# path = "/media/foo/qp10"

# # Initialize Redis Client
# redis_client = redis.Redis(
#     host=os.getenv("REDIS_HOST", "redis"),  # Host is set via environment variable
#     port=int(os.getenv("REDIS_PORT", 6379)),
#     decode_responses=True
# )

# # Configuration Paths
# INPUT_DIR = "/app/media/ply_input"
# OUTPUT_DIR = "/app/media/foo"
# # SERVER_BASE_URL = "http://127.0.0.1:8080/media/foo/"
# PREPARE_SCRIPT = "/app/Compression/prepare_dash_sequence.sh"

# # Thread Lock for Disk Writing (ensures sequential writes)
# disk_write_lock = threading.Lock()

# def wait_for_complete_file(filepath, timeout=1):
#     """Ensures file is fully written before processing (polling every 1ms)."""
#     start_time = time.time()
#     last_size = -1

#     while time.time() - start_time < timeout:
#         try:
#             current_size = os.path.getsize(filepath)
#         except FileNotFoundError:
#             continue  # File might be temporarily unavailable

#         if current_size > 0 and current_size == last_size:
#             return True  # File is ready

#         last_size = current_size
#         time.sleep(0.001)  # Check every 1ms

#     return False  # Timeout reached


# def encode_ply():
#     """Encodes PLY to DRC and sends data directly to Redis."""
#     while True:
#         try:
#             _, ply_path = redis_client.blpop(REDIS_QUEUE)
#             if not ply_path:
#                 continue  
            
#             ply_path = ply_path.decode("utf-8")  # convert bytes to str
#             if not wait_for_complete_file(ply_path):
#                 logging.warning(f"Skipping incomplete file: {ply_path}")
#                 continue

#             logging.info(f"Encoding {ply_path}...")
#             drc_temp_path = "/tmp/encoded.drc"

#             result = subprocess.run(
#                 [PREPARE_SCRIPT, "-i", INPUT_DIR, "-o", "/tmp", "-p", "10", "-f", "30"],
#                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
#             )

#             if result.returncode == 0:
#                 with open(drc_temp_path, "rb") as drc_file:
#                     drc_data = drc_file.read()


#                 """Store file data and track its key in the latest 100 files list"""
#                 redis_client.set(path, drc_data)  # Store data in Redis

#                 # Push the file path into the list (acts as a queue)
#                 redis_client.lpush("file_list", path)

#                 # Trim the list to keep only the last 100 entries
#                 redis_client.ltrim("file_list", 0, 99)  # Keep only the last 100 elements

#                 # redis_client.rpush(DRC_BUFFER, drc_data)
                
#                 # # Maintain FIFO buffer
#                 # if redis_client.llen(DRC_BUFFER) > MAX_REDIS_CACHE:
#                 #     redis_client.rpush(DISK_QUEUE, redis_client.lpop(DRC_BUFFER))

#                 redis_client.publish(MPD_CHANNEL, "NEW_FRAME")
#                 logging.info(f"Encoded & pushed {ply_path} to Redis")

#             else:
#                 logging.error(f"Encoding failed for {ply_path}\n{result.stderr}")

#         except redis.exceptions.ConnectionError as e:
#             logging.error(f"Redis Connection Error: {e}")
#             time.sleep(1)

#         except Exception as e:
#             logging.error(f"Unexpected error: {e}")

# def save_old_drc_to_disk():
#     """Background thread to offload old DRC files from Redis to disk."""
#     while True:
#         drc_data = redis_client.lpop(DISK_QUEUE)
#         if drc_data:
#             with disk_write_lock:
#                 timestamp = int(time.time())
#                 save_path = os.path.join(OUTPUT_DIR, f"frame_{timestamp}.drc")
#                 with open(save_path, "wb") as f:
#                     f.write(drc_data)
#                 logging.info(f"Offloaded old DRC to {save_path}")

#         time.sleep(0.1)



# class PlyHandler(FileSystemEventHandler):
#     """Detects new PLY files and adds them to the processing queue."""

#     def on_created(self, event):
#         if event.is_directory or not event.src_path.endswith(".ply"):
#             return

#         logging.info(f"New PLY detected: {event.src_path}")
#         # Add to Redis queue for processing
#         # Avoid duplicate pushes
#         if not redis_client.sismember("processed_files", event.src_path):
#             redis_client.rpush(REDIS_QUEUE, event.src_path)
#             redis_client.sadd("processed_files", event.src_path)  # Mark as processed


# if __name__ == "__main__":
#     # Ensure directories exist
#     os.makedirs(INPUT_DIR, exist_ok=True)
#     os.makedirs(OUTPUT_DIR, exist_ok=True)

#     encoder_thread = threading.Thread(target=encode_ply, daemon=True)
#     encoder_thread.start()

#     # saver_thread = threading.Thread(target=save_old_drc_to_disk, daemon=True)
#     # saver_thread.start()

#     # Start the file watcher
#     observer = Observer()
#     event_handler = PlyHandler()
#     observer.schedule(event_handler, INPUT_DIR, recursive=False)
#     observer.start()

#     logging.info("Watching for new PLY files at 30 FPS (real-time)...")

#     try:
#         while True:
#             time.sleep(0.001)  # Non-blocking, ultra-low latency
#     except KeyboardInterrupt:
#         observer.stop()
#         logging.info("Stopping watcher...")

#     observer.join()

#!/usr/bin/env python
import os
import time
import subprocess
import redis
import logging
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Redis Configuration
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_QUEUE = "ply_processing_queue"
MPD_CHANNEL = "mpd_updates"
FILE_LIST = "file_list"  # List of latest DRC file paths
MAX_REDIS_CACHE = 100  # Retain last 100 frames

# Initialize Redis Client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Configuration Paths
INPUT_DIR = "/app/media/ply_input"
OUTPUT_DIR = "media/foo/qp10"
PREPARE_SCRIPT = "/app/Compression/prepare_dash_sequence.sh"


def wait_for_complete_file(filepath, timeout=1):
    """Ensures file is fully written before processing (polling every 1ms)."""
    start_time = time.time()
    last_size = -1

    while time.time() - start_time < timeout:
        try:
            current_size = os.path.getsize(filepath)
        except FileNotFoundError:
            continue  # File might be temporarily unavailable

        if current_size > 0 and current_size == last_size:
            return True  # File is ready

        last_size = current_size
        time.sleep(0.001)  # Check every 1ms

    return False  # Timeout reached


def encode_ply():
    """Encodes PLY to DRC while keeping the original filename."""
    while True:
        try:
            _, ply_path = redis_client.blpop(REDIS_QUEUE)
            if not ply_path:
                continue  
            
            ply_path = ply_path.strip()  # Remove any whitespace
            ply_filename = os.path.basename(ply_path)  # Extract filename
            drc_filename = os.path.splitext(ply_filename)[0] + ".drc"  # Replace .ply with .drc
            
            logging.info(f"Checking file exists: {ply_path}")
            if not os.path.exists(ply_path):
                logging.error(f"PLY file not found: {ply_path}")
                continue

            if not wait_for_complete_file(ply_path):
                logging.warning(f"Skipping incomplete file: {ply_path}")
                continue

            logging.info(f"Encoding {ply_path} -> {drc_filename}...")

            
            # Run compression script (capture binary output)
            result = subprocess.run(
                [PREPARE_SCRIPT, "-i", ply_path, "-p", "10", "-f", "30"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False
            )

            if result.returncode == 0:
                # with open(drc_temp_path, "rb") as drc_file:
                #     drc_data = drc_file.read()
                
                drc_data = result.stdout  # Capture compressed data from stdout
                # Use the original filename as the Redis key
                drc_redis_path = f"{OUTPUT_DIR}/{drc_filename}"

                # Store file data in Redis with original filename
                redis_client.set(drc_redis_path, drc_data)

                # Maintain FIFO order: Push new frame path to list
                redis_client.lpush(FILE_LIST, drc_redis_path)

                # Trim the list to keep only the last MAX_REDIS_CACHE frames
                redis_client.ltrim(FILE_LIST, 0, MAX_REDIS_CACHE - 1)

                # Notify DASH Server to update MPD
                redis_client.publish(MPD_CHANNEL, drc_redis_path)

                logging.info(f"Encoded & pushed {ply_filename} as {drc_filename} to Redis.")

            else:
                logging.error(f"Encoding failed for {ply_path}\n{result.stderr}")

        except redis.exceptions.ConnectionError as e:
            logging.error(f"Redis Connection Error: {e}")
            time.sleep(1)

        except Exception as e:
            logging.error(f"Unexpected error: {e}")


class PlyHandler(FileSystemEventHandler):
    """Detects new PLY files and adds them to the processing queue."""

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".ply"):
            return

        abs_ply_path = os.path.abspath(event.src_path)  # Convert to absolute path
        logging.info(f"New PLY detected: {abs_ply_path}")

        if not redis_client.sismember("processed_files", abs_ply_path):
            redis_client.rpush(REDIS_QUEUE, abs_ply_path)  # Store absolute path
            redis_client.sadd("processed_files", abs_ply_path)
            redis_client.expire("processed_files", 120)  # Expires in 120 sec

if __name__ == "__main__":
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    encoder_thread = threading.Thread(target=encode_ply, daemon=True)
    encoder_thread.start()

    observer = Observer()
    event_handler = PlyHandler()
    observer.schedule(event_handler, INPUT_DIR, recursive=False)
    observer.start()

    logging.info("Watching for new PLY files at 30 FPS (real-time)...")

    try:
        while True:
            time.sleep(0.001)  # Non-blocking, ultra-low latency
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Stopping watcher...")

    observer.join()
