# Handson: Docker Compose with a Real-World Example - Point Cloud Transmission Server

## In this exercise, we'll need computer graphics for point cloud visualization. For the Comnetsemu VM can use your laptop graphics, you need to install Xming X Server in your laptop:

### Download and install Xming X Server for Windows: https://sourceforge.net/projects/xming/

## After installed Xming X Server:
* Restart your laptop if needed
* Open Window Power shell to stop Xming: `Stop-Process -Name Xming -Force`
* Open XLaunch application to start Xming with options: `Multiple windows` -> `Start no client` -> `Clipboard` + `No Access Control`


## 0. SSH to comnetsemu with X11 forwarder
```
vagrant ssh comnetsemu -- -X
vagrant@comnetsemu:~$ export DISPLAY=$(ip route show default | awk '{print $3}'):0.0
vagrant@comnetsemu:~$ xeyes
```
### Notes: if you see a window with eyes open, your Xming connection is successful.


## Preparation

## 1. Clone this repo to your comnetsemu VM
```
vagrant@comnetsemu:~$ git clone https://github.com/binhfdv/pcl_handson_backup.git ~/pcl_handson
```

## 2. Install docker compose:
```
vagrant@comnetsemu:~$ sudo mkdir -p /etc/apt/keyrings
vagrant@comnetsemu:~$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
vagrant@comnetsemu:~$ echo  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu focal stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
vagrant@comnetsemu:~$ sudo apt update && sudo apt install docker-compose-plugin -y
```

## 3. Install Draco encoder and decoder
```
vagrant@comnetsemu:~$ cd pcl_handson/
vagrant@comnetsemu:~/pcl_handson$ sudo apt update && sudo apt install -y wget unzip cmake make g++
vagrant@comnetsemu:~/pcl_handson$ git clone https://github.com/google/draco.git && cd draco
vagrant@comnetsemu:~/pcl_handson/draco$ mkdir build && cd build
vagrant@comnetsemu:~/pcl_handson/draco/build$ cmake ..
vagrant@comnetsemu:~/pcl_handson/draco/build$ make
vagrant@comnetsemu:~/pcl_handson/draco/build$ export PATH=$PATH:/home/vagrant/pcl_handson/draco/build
```
### Notes: after built, run `export PATH=$PATH:/home/vagrant/pcl_handson/draco/build` whenever you find an error `draco_encoder` or `draco_decoder: command not found`

## 4. Build point cloud visualizer
```
vagrant@comnetsemu:~/pcl_handson/draco/build$ sudo apt update && sudo apt install -y libpcl-dev
vagrant@comnetsemu:~/pcl_handson/draco/build$ cd ~/pcl_handson/
vagrant@comnetsemu:~/pcl_handson$ cd pcl_viewer/
vagrant@comnetsemu:~/pcl_handson/pcl_viewer$ mkdir build && cd build
vagrant@comnetsemu:~/pcl_handson/pcl_viewer/build$ cmake ..
vagrant@comnetsemu:~/pcl_handson/pcl_viewer/build$ make
vagrant@comnetsemu:~/pcl_handson/pcl_viewer/build$ export PATH=$PATH:/home/vagrant/pcl_handson/pcl_viewer/build
```
### Notes: after built
* run `export PATH=$PATH:/home/vagrant/pcl_handson/pcl_viewer/build` whenever you find an error `pcl_viewer: command not found`
* run `export DISPLAY=$(ip route show default | awk '{print $3}'):0.0` whenever you see `ERROR: In /build/vtk7-yd0MKW/vtk7-7.1.1+dfsg2/Rendering/OpenGL2/vtkXOpenGLRenderWindow.cxx, line 1497 vtkXOpenGLRenderWindow (0x557d396081c0): bad X server connection. DISPLAY=Aborted (core dumped)`














