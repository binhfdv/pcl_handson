# from fastapi import FastAPI, HTTPException
# from fastapi.responses import Response
# from fastapi.routing import APIRoute
# import os
# import time as T
# import logging
# import redis
# import mimetypes
# import asyncio
# import subprocess
# import threading
# from hypercorn.config import Config
# from hypercorn.asyncio import serve

# # Redis Configuration
# REDIS_HOST = "redis"
# REDIS_PORT = 6379
# MPD_CHANNEL = "mpd_updates"
# MPD_KEY = "mpd:current"  # Redis key for MPD storage

# # Initialize Redis
# redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# class DASHServer():
#     def __init__(self, host:str="127.0.0.1", port:int=5000, media_path:str="./media", cache=None, buffer_size:int=512):
#         self.media_path=media_path

#         self.config=Config()
#         self.config.bind="{}:{}".format(host, port)

#         self.app = FastAPI(
#             routes=[
#                 APIRoute("/media/{name}", self.__media_mpd, methods=["GET"]),
#                 APIRoute("/media/{name}/{representation}/{segment}", self.__media_segment, methods=["GET"]),
#             ]
#         )

#         mimetypes.add_type('pointcloud/ply', '.ply')
#         mimetypes.add_type('pointcloud/drc', '.drc')
#         mimetypes.add_type('pointcloud/mpeg-vpcc', '.vpcc')
#         mimetypes.add_type('pointcloud/mpeg-gpcc', '.gpcc')
#         mimetypes.add_type('application/zip', '.zip')

        
      
#         self.cache = cache
#         self.redis_pubsub = None

#          # Subscribe to Redis Pub/Sub for MPD updates
#         if isinstance(self.cache, redis.Redis):
#             try:
#                 self.redis_pubsub = self.cache.pubsub()
#                 self.redis_pubsub.subscribe("mpd_updates")
#                 logging.info("Subscribed to Redis channel: mpd_updates")

#                 # Run listener in background thread (not async task)
#                 threading.Thread(target=self.listen_for_mpd_updates, daemon=True).start()
            
#             except redis.exceptions.ConnectionError as e:
#                 logging.error(f"Failed to connect to Redis: {e}")



#     def listen_for_mpd_updates(self):
#         """Listens for MPD update messages and appends new frames."""
#         while True:
#             try:
#                 for message in self.redis_pubsub.listen():
#                     if message["type"] == "message":
#                         self.generate_mpd()
#             except redis.exceptions.ConnectionError as e:
#                 logging.error(f"Redis connection lost! Retrying... {e}")
#                 time.sleep(5)

        
#     def generate_mpd(self, name):
#         """Generate MPD file and store it in Redis."""
#         output_dir = os.path.join(self.media_path, name)
#         mpd_path = os.path.join(output_dir, "mpd.xml")
#         base_url = f"http://127.0.0.1:8080/media/{name}/"

#         try:
#             logging.info(f"Generating MPD for {name}...")

#             subprocess.run([
#                 "pointcloudserver", "mpd",
#                 "--pretty",
#                 "--outputFile", mpd_path,
#                 "--framesPerSecond", "30",
#                 "--baseUrl", base_url,
#                 output_dir
#             ], check=True)

#             # Store MPD in Redis
#             with open(mpd_path, "rb") as mpd_file:
#                 self.cache.set(f"mpd:{name}", mpd_file.read())

#             self.cache.publish("mpd_updates", name)
#             logging.info(f"MPD generated & stored in Redis for {name}")

#         except subprocess.CalledProcessError as e:
#             logging.error(f"MPD generation failed: {e}")

    
    


#     async def __media_mpd(self, name):
#         filename=os.path.join(self.media_path, name, "mpd.xml")

#         data=self.load_file(filename)
#         if data is None:
#             raise HTTPException(status_code=404)

#         return Response(content=data, media_type='application/dash+xml')

#     async def __media_segment(self, name, representation, segment):
#         filename=os.path.join(self.media_path, name, representation, segment)

#         data = self.load_file(filename)
#         if data is None:
#             raise HTTPException(status_code=404)

#         # content_type=mimetypes.guess_type(filename, strict=False)[0]
#         content_type = mimetypes.guess_type(filename, strict=False)[0] or "application/octet-stream"
#         if content_type is None:
#             raise HTTPException(status_code=406)

#         return Response(content=data, media_type=content_type)

#     def get_extension(self, path):
#         return os.path.splitext(path)[1]

#     def load_file(self, path):
#         t_start=T.time()

#         data=None
#         if self.cache is not None:
#             data=self.cache.get(path)
#             if isinstance(self.cache, redis.Redis) and data:
#                 logging.debug(f"Cache hit in Redis: {path}")
#                 return data
        
#         if data is None:
#             logging.debug("Cache miss")
#             try:
#                 with open(path, "rb") as file:
#                     data = file.read()
#                     if self.cache is not None:
#                         self.cache.set(path, data)  # Store in cache
#             except FileNotFoundError:
#                 data=None 
#         else:
#             logging.debug("Cache hit")

#         delta=T.time()-t_start
#         logging.debug("Response Time \"{}\" {}ms".format(path, delta))
#         return data

#     def start(self):
#         asyncio.run(serve(self.app, self.config))


# 

# from fastapi import FastAPI, HTTPException
# from fastapi.responses import Response
# from fastapi.routing import APIRoute
# import os
# import time as T
# import logging

# import mimetypes
# import asyncio
# from hypercorn.config import Config
# from hypercorn.asyncio import serve

# class DASHServer():
#     def __init__(self, host:str="127.0.0.1", port:int=5000, media_path:str="./media", cache=None, buffer_size:int=512):
#         self.media_path=media_path

#         self.config=Config()
#         self.config.bind="{}:{}".format(host, port)

#         self.app = FastAPI(
#             routes=[
#                 APIRoute("/media/{name}", self.__media_mpd, methods=["GET"]),
#                 APIRoute("/media/{name}/{representation}/{segment}", self.__media_segment, methods=["GET"]),
#             ]
#         )

#         mimetypes.add_type('pointcloud/ply', '.ply')
#         mimetypes.add_type('pointcloud/drc', '.drc')
#         mimetypes.add_type('pointcloud/mpeg-vpcc', '.vpcc')
#         mimetypes.add_type('pointcloud/mpeg-gpcc', '.gpcc')
#         mimetypes.add_type('application/zip', '.zip')

#         self.cache = None
#         if cache is not None:
#             self.cache = cache


#     async def __media_mpd(self, name):
#         filename=os.path.join(self.media_path, name, "mpd.xml")

#         data=self.load_file(filename)
#         if data is None:
#             raise HTTPException(status_code=404)

#         return Response(content=data, media_type='application/dash+xml')

#     async def __media_segment(self, name, representation, segment):
#         filename=os.path.join(self.media_path, name, representation, segment)

#         data = self.load_file(filename)
#         if data is None:
#             raise HTTPException(status_code=404)

#         content_type=mimetypes.guess_type(filename, strict=False)[0]
#         if content_type is None:
#             raise HTTPException(status_code=406)

#         return Response(content=data, media_type=content_type)

#     def get_extension(self, path):
#         return os.path.splitext(path)[1]

#     def load_file(self, path):
#         t_start=T.time()

#         data=None
#         if self.cache is not None:
#             data=self.cache.get(path)
#         if data is None:
#             logging.debug("Cache miss")
#             try:
#                 file=open(path, 'rb')
#                 data=file.read()
#             except FileNotFoundError:
#                 data=None
            
#             if self.cache is not None:
#                 self.cache.set(path, data)
#         else:
#             logging.debug("Cache hit")

#         delta=T.time()-t_start
#         logging.debug("Response Time \"{}\" {}ms".format(path, delta))
#         return data

#     def start(self):
#         asyncio.run(serve(self.app, self.config))

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.routing import APIRoute
import os
import time as T
import logging
import redis
import mimetypes
import asyncio
import subprocess
import threading
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
MPD_CHANNEL = "mpd_updates"  # Pub/Sub channel for MPD updates
OUTPUT_DIR = "media/foo"
BASE_URL = f"http://127.0.0.1:8080/media/foo/"

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

class DASHServer():
    def __init__(self, host:str="127.0.0.1", port:int=5000, media_path:str="./media", cache=None, buffer_size:int=512):
        self.media_path=media_path
        self.cache = cache

        self.config=Config()
        self.config.bind="{}:{}".format(host, port)

        self.app = FastAPI(
            routes=[
                APIRoute("/media/{name}", self.__media_mpd, methods=["GET"]),
                APIRoute("/media/{name}/{representation}/{segment}", self.__media_segment, methods=["GET"]),
            ]
        )

        mimetypes.add_type('pointcloud/ply', '.ply')
        mimetypes.add_type('pointcloud/drc', '.drc')
        mimetypes.add_type('pointcloud/mpeg-vpcc', '.vpcc')
        mimetypes.add_type('pointcloud/mpeg-gpcc', '.gpcc')
        mimetypes.add_type('application/zip', '.zip')

        # Listen for MPD updates in the background
        threading.Thread(target=self.listen_for_mpd_updates, daemon=True).start()

    def listen_for_mpd_updates(self):
        """
        Listens for messages from `watcher.py` indicating a new DRC file.
        Calls `mpd.py` to update the MPD and stores the MPD path in Redis.
        """
        pubsub = redis_client.pubsub()
        pubsub.subscribe(MPD_CHANNEL)
        logging.info("Listening for MPD updates...")

        for message in pubsub.listen():
            if message["type"] == "message":
                drc_filename = message["data"]
                logging.info(f"Received MPD update request for: {drc_filename}")
                self.update_mpd(drc_filename)
                

    def update_mpd(self, drc_filename):
        """
        Calls `mpd.py` to update MPD, then stores the MPD path in Redis.
        """
        logging.info(f"Updating MPD for new DRC: {drc_filename}")

        try:
            output_dir = os.path.join(OUTPUT_DIR, "mpd.xml")

            logging.info(f"build mpd.xml in {output_dir}")

            subprocess.run([
                "pointcloudserver", "mpd",
                "--pretty",
                "--outputFile", output_dir,
                "--framesPerSecond", "30",
                "--baseUrl", BASE_URL,
                "--drcFilename", drc_filename,
                OUTPUT_DIR], check=True)
           
            # # Store the updated MPD file path in Redis instead of using MPD_KEY
            # redis_client.set(output_dir, output_dir)
            logging.info(f"MPD file path stored in Redis: {output_dir}")

        except subprocess.CalledProcessError as e:
            logging.error(f"MPD update failed: {e}")

    async def __media_mpd(self, name):
        filename=os.path.join(self.media_path, name, "mpd.xml")

        data=self.load_file(filename)
        if data is None:
            raise HTTPException(status_code=404)
        
        # Ensure correct format for HTTP response (decode if necessary)
        if isinstance(data, bytes):  
            data = data.decode("utf-8")  # Convert bytes to string

         # Disable caching in the HTTP response
        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }

        return Response(content=data, media_type='application/dash+xml', headers=headers)

    async def __media_segment(self, name, representation, segment):
        filename=os.path.join(self.media_path, name, representation, segment)

        data = self.load_file(filename)
        if data is None:
            raise HTTPException(status_code=404)

        content_type=mimetypes.guess_type(filename, strict=False)[0]
        if content_type is None:
            raise HTTPException(status_code=406)

        return Response(content=data, media_type=content_type)

    def get_extension(self, path):
        return os.path.splitext(path)[1]

    def load_file(self, path):
        t_start = T.time()

        data = None
        logging.info(f"star to check cache")
        if self.cache is not None:
            #data = self.cache.get(path)  # First, check if MPD is in Redis
            data = redis_client.get(path)
            logging.info(f"Find in Redis: {path}")
            if data:
                logging.info(f"Cache hit in Redis: {path}")
                logging.info(f"MPD Content: \n{data}")
                delta = T.time() - t_start
                logging.debug(f"Response Time \"{path}\" {delta}ms")
                return data  # If found in Redis, return immediately

        # if data is None:
        #     logging.debug("Cache miss, reading from disk.")
        #     try:
        #         with open(path, "rb") as file:
        #             data = file.read()
        #             if self.cache is not None:
        #                 self.cache.set(path, data)  # Store back in Redis
        #     except FileNotFoundError:
        #         data = None

        # delta = T.time() - t_start
        # logging.debug(f"Response Time \"{path}\" {delta}ms")
        # return data

    def start(self):
        asyncio.run(serve(self.app, self.config))