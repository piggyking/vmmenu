# vmmenu
virt-v2v的CLI图形工具，方便连接vSphere/vCenter进行虚拟机的迁移；

./pyv 目录下的request.sh可以自动安装所需的软件包（需联网）；

./main.py 运行主程序；

测试环境：

Fedora26（无法运行在KVM嵌套CPU虚拟化环境中，只能使用物理机）

Centos7（不确认安装脚本中的Python2.7.x是否能正常安装，但是不影响最终使用）

请使用root运行

已知问题：

virt-v2v 版本为1.32.X时，迁移centos6.x系列会发生错误（1.32.x版本通常会在Centos7下直接yum安装，红帽系列亦同）

Fedora26直接yum安装的virt-v2v版本升级到1.37.x，不会有上面的问题

virt-v2v运行的条件中有必须具备CPU虚拟化功能，如果在虚拟机下运行，务必开启CPU嵌套虚拟化

已知Fedora26在VMware vSphere6.1版本下即使开启CPU嵌套虚拟化也无法使用

CentOS没有类似的问题。
