from setuptools import find_packages, setup

package_name = 'vda5050_connector'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='kibeom',
    maintainer_email='kibeom@todo.todo',
    description='VDA 5050 Protocol MQTT-ROS2 Bridge Node',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'bridge_node = vda5050_connector.bridge_node:main'
        ],
    },
)
