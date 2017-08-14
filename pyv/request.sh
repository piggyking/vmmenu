#!/usr/bin/bash
wget https://fedorapeople.org/groups/virt/virtio-win/virtio-win.repo \
            -O /etc/yum.repos.d/virtio-win.repo
yum install python2 libguestfs.x86_64 virt-v2v virtio-win -y
python2 ./pip-8.1.2/setup.py install
pip2 install pyvim
pip2 install pvmomi
brctl addbr virbr0
