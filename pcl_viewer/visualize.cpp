#include <pcl/io/ply_io.h>
#include <pcl/visualization/pcl_visualizer.h>
#include <pcl/point_types.h>
#include <pcl/common/common.h>
#include <Eigen/Dense>
#include <filesystem>
#include <iostream>
#include <thread>
#include <chrono>
#include <unordered_set>

namespace fs = std::filesystem;

void applyTransform(pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud) {
    float scale = 0.179523f;
    Eigen::Vector3f translation(-45.2095f, 7.18301f, -54.3561f);

    for (auto& pt : cloud->points) {
        pt.x = pt.x * scale + translation.x();
        pt.y = pt.y * scale + translation.y();
        pt.z = pt.z * scale + translation.z();
    }
}

void updateViewer(pcl::visualization::PCLVisualizer::Ptr viewer,
                  pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud) {
    viewer->removeAllPointClouds();
    viewer->removeAllShapes();

    pcl::visualization::PointCloudColorHandlerRGBField<pcl::PointXYZRGB> rgb(cloud);
    viewer->addPointCloud<pcl::PointXYZRGB>(cloud, rgb, "colored cloud");
    viewer->setPointCloudRenderingProperties(pcl::visualization::PCL_VISUALIZER_POINT_SIZE, 2, "colored cloud");
    viewer->addCoordinateSystem(10.0);

    // Compute bounding box and set camera
    pcl::PointXYZRGB minPt, maxPt;
    pcl::getMinMax3D(*cloud, minPt, maxPt);
    Eigen::Vector3f center((minPt.x + maxPt.x) / 2.0f,
                           (minPt.y + maxPt.y) / 2.0f,
                           (minPt.z + maxPt.z) / 2.0f);

    float max_dim = std::max({maxPt.x - minPt.x, maxPt.y - minPt.y, maxPt.z - minPt.z});
    float distance = max_dim * 2.0f;
    Eigen::Vector3f cam_pos = center + Eigen::Vector3f(0.0f, 0.0f, distance);

    viewer->setCameraPosition(
        cam_pos.x(), cam_pos.y(), cam_pos.z(),
        center.x(), center.y(), center.z(),
        0.0f, 1.0f, 0.0f
    );
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <folder_to_watch>\n";
        return 1;
    }

    std::string watch_folder = argv[1];
    std::unordered_set<std::string> seen_files;

    pcl::visualization::PCLVisualizer::Ptr viewer(new pcl::visualization::PCLVisualizer("3D Viewer"));
    viewer->setBackgroundColor(1.0, 1.0, 1.0);

    std::string last_loaded;

    while (!viewer->wasStopped()) {
        for (const auto& entry : fs::directory_iterator(watch_folder)) {
            if (entry.is_regular_file() && entry.path().extension() == ".ply") {
                std::string path_str = entry.path().string();
                if (seen_files.find(path_str) == seen_files.end()) {
                    seen_files.insert(path_str);
                    std::cout << "New file detected: " << path_str << std::endl;

                    pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZRGB>);
                    if (pcl::io::loadPLYFile<pcl::PointXYZRGB>(path_str, *cloud) >= 0) {
                        applyTransform(cloud);
                        updateViewer(viewer, cloud);
                    } else {
                        std::cerr << "Failed to load " << path_str << std::endl;
                    }

                    break; // load one new file at a time
                }
            }
        }

        viewer->spinOnce(100);
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    return 0;
}

