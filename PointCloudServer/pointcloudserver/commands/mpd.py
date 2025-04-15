import xml.etree.ElementTree as ET
from argparse import Namespace

from pointcloudserver.dash.mpd import build_multiple_object_mpd, build_single_object_mpd, get_depth, save_xml, serialize_xml, append_new_frame

import logging
import redis
import threading
import time


# def run(args: Namespace):
#     media_dir=args.mediaDir[0]
#     pretty=args.pretty
#     base_url=args.baseUrl
#     output_file=args.outputFile
#     fps=None
#     if args.framesPerSecond is not None:
#         fps=int(args.framesPerSecond)
#     mpd_type="static"

#     mpd = ET.Element("MPD")
#     mpd.set("type", mpd_type)
#     mpd.set("minBufferTime", str(1.0/float(fps)))

#     mpd_url = ET.SubElement(mpd, "BaseURL")
#     mpd_url.text = base_url

#     depth = get_depth(media_dir)
#     if depth == 2:
#         mpd = build_single_object_mpd(mpd, media_dir, fps)
#     elif depth == 3:
#         mpd = build_multiple_object_mpd(mpd, media_dir, fps)
#     mediaPresentationDuration = len(mpd.findall("Period")) * (1/fps)
#     mpd.set("mediaPresentationDuration", str(mediaPresentationDuration))
#     if output_file is not None:
#         save_xml(mpd, output_file, pretty=pretty)
#     else:
#         print(serialize_xml(mpd, pretty=pretty))

# Redis Configuration
REDIS_HOST = "redis"
REDIS_PORT = 6379
MPD_DISK_QUEUE = "mpd_disk_queue"  # Queue for writing MPD to disk

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

# Thread lock for sequential writes
disk_write_lock = threading.Lock()


def run(args: Namespace):
    """
    Generates or updates the MPD file dynamically using the latest DRC frame.
    """

    media_dir = args.mediaDir[0]
    pretty = args.pretty
    base_url = args.baseUrl
    output_file = args.outputFile
    fps = int(args.framesPerSecond) if args.framesPerSecond else None
    # Get latest frame from Redis
    drc_filename = args.drcFilename  # Get last frame

    # Load previous MPD from Redis if available
    
    mpd_path = redis_client.get(output_file)  # Get the stored MPD path
    if mpd_path:
        try:
            mpd_text = mpd_path.decode("utf-8") if isinstance(mpd_path, bytes) else mpd_path  # Decode from bytes
            mpd = ET.fromstring(mpd_text)  # Parse XML
            logging.info(f"Loaded existing MPD from {mpd_path}.")
        except ET.ParseError:
            logging.error("Failed to parse existing MPD. Creating a new one.")
            mpd = create_new_mpd(base_url, fps)

    else:
        logging.info("No existing MPD found. Creating a new one.")
        mpd = create_new_mpd(base_url, fps)
    
    if drc_filename:
        drc_data = redis_client.get(drc_filename)
        if drc_data:
            drc_size = len(drc_data)
            logging.info(f"Appending new frame {drc_filename} to MPD.")
            mpd = append_new_frame(mpd, drc_filename, drc_size, fps)

            # Save updated MPD to Redis and disk
            updated_mpd_xml = serialize_xml(mpd, pretty=pretty)
            redis_client.set(output_file, updated_mpd_xml)  # Store MPD in Redis
            #redis_client.rpush(MPD_DISK_QUEUE, output_file)  # Add to disk write queue

            logging.info(f"MPD updated and stored in Redis: {output_file}")

            # Start background thread to write MPD to disk
            #threading.Thread(target=write_mpd_to_disk, daemon=True).start()

    # if output_file:
    #     redis_client.rpush(MPD_DISK_QUEUE, serialize_xml(mpd))  # Queue for disk writing
    # else:
    #     print(serialize_xml(mpd, pretty=pretty))

    

def create_new_mpd(base_url, fps):
    """
    Creates a new MPD file if none exists.
    """
    mpd = ET.Element("MPD")
    mpd.set("type", "dynamic")  # Streaming mode
    mpd.set("minBufferTime", str(1.0 / float(fps)))

    mpd_url = ET.SubElement(mpd, "BaseURL")
    mpd_url.text = base_url

    return mpd



def write_mpd_to_disk():
    """
    Writes the latest MPD from Redis to disk asynchronously.
    Ensures non-blocking MPD updates.
    """
    while True:
        try:
            output_path = redis_client.lpop(MPD_DISK_QUEUE)  # Get next MPD path to write
            if output_path:
                with disk_write_lock:
                    mpd_data = redis_client.get(output_path)  # Get MPD XML from Redis
                    if mpd_data:
                        mpd_root = ET.fromstring(mpd_data)  # Convert to XML tree
                        save_xml(mpd_root, output_path, pretty=True)  # Save to disk
                        logging.info(f"MPD successfully written to disk at {output_path}")
        except Exception as e:
            logging.error(f"⚠ Error writing MPD to disk: {e}")

        time.sleep(0.1)  # Prevent high CPU usage
