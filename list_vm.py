#!/usr/bin/env pythoni
#encoding=utf-8
# VMware vSphere Python SDK
# Copyright (c) 2008-2015 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Python program for listing the vms on an ESX / vCenter host
"""

from __future__ import print_function

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

import argparse
import atexit
import getpass
import ssl
import sys
reload(sys)
sys.setdefaultencoding(' utf-8 ')

def Get_VM_List(vm, dc, dc_childfolder ,child, depth=1):
    global list_all
    global list_uuid
    global list_path
    global list_hostname
    global vm_summary
    global list_powerstate
    global list_dc
    global list_resource
    global list_vm_name
    """
    Print information for a particular virtual machine or recurse into a folder
    or vApp with depth protection
    """
    maxdepth = 10
    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(vm, 'childEntity'):
        if depth > maxdepth:
            return
        vmList = vm.childEntity
        for c in vmList:
            Get_VM_List(c, dc, dc_childfolder, child, depth+1)
#            temp_list = Get_VM_List(c, dc, depth+1)
#            list_dc.append(dc)
#            list_all = temp_list[0]
#            list_uuid = temp_list[1]
#            list_hostname = temp_list[3]
#            list_powerstate = temp_list[4]
        return
    # if this is a vApp, it likely contains child VMs
    # (vApps can nest vApps, but it is hardly a common usecase, so ignore that)
    if isinstance(vm, vim.VirtualApp):
        vmList = vm.vm
        for c in vmList:
            Get_VM_List(c, dc, dc_childfolder, child, depth+1)
#            temp_list = Get_VM_List(c, dc, depth+1)
#            list_dc.append(dc)
#            list_all = temp_list[0]
#            list_uuid = temp_list[1]
#            list_hostname = temp_list[3]
#            list_powerstate = temp_list[4]
        return
    
    summary = vm.summary
#跳开模板
    test_Template = 0
    for i in vm.disabledMethod:
        if i == 'PowerOffVM_Task' or i == 'PowerOnVM_Task':
            test_Template = test_Template + 1
    if test_Template >= 2:
        return
#匹配host信息则记录
    for childfolder in dc_childfolder:
        if hasattr(child, 'hostFolder'):
            for get_host_name in childfolder.host:
                if vm.runtime.host.name == get_host_name.name:
                    dc_childfolder_name = childfolder.name
                    break

    list_resource.append(dc_childfolder_name)
    list_dc.append(dc)
    list_all.append("{:^20}".format(summary.config.name)+\
#      '\t'+summary.config.vmPathName+\
       '|'+"{:^45}".format(summary.config.guestFullName)+\
       '|'+"{:^12}".format(summary.runtime.powerState))
    list_path.append(summary.config.vmPathName)
    list_uuid.append(summary.config.instanceUuid)
    list_powerstate.append(summary.runtime.powerState)

#获取DataCenter，Host主机名等信息
    list_hostname.append(vm.runtime.host.name)
    list_vm_name.append(summary.config.name)

#开始汇总虚拟机信息
    for device in vm.config.hardware.device:
        if device.backing is None:
            vm_dev_summary = {'label：':device.deviceInfo.label}
            continue
        
        if hasattr(device.backing, 'fileName'):
            backing_dev_summary = {}
            backing_dev = {}
            vm_summary_base = {}
            datastore = device.backing.datastore
            if datastore:
                backing_dev_summary['datastore：'] = datastore.name
                # there may be multiple hosts, the host property
                # is a host mount info type not a host system type
                # but we can navigate to the host system from there
                host_num = 1
                for host_mount in datastore.host:
                    host_system = host_mount.key
                    backing_dev_summary\
                    ['backing dev host name' + str(host_num) + '：'] = host_system.name
                backing_dev_summary['capacity：'] = datastore.summary.capacity
                backing_dev_summary['freeSpace：'] = datastore.summary.freeSpace
                backing_dev_summary['file system：'] = datastore.summary.type,
                backing_dev_summary['url'] = datastore.summary.url
                backing_dev['backing dev summary：'] = backing_dev_summary
            backing_dev['filename：'] = device.backing.fileName
            backing_dev['device ID：'] = device.backing.backingObjectId
            
            vm_dev_summary = {'label：':device.deviceInfo.label,
                              'summary：':device.deviceInfo.summary,
                              'device type：': type(device).__name__,
                              'backing type：': type(device.backing).__name__,
                              'backing dev：':backing_dev}
            
            vm_summary_base['虚拟设备信息：'] = vm_dev_summary
            vm_summary_base['宿主机：'] = vm.runtime.host.name
            vm_summary_base['路径：'] = summary.config.vmPathName
            vm_summary_base['虚拟机名称：'] = summary.config.name

            vm_summary[summary.config.instanceUuid] = vm_summary_base
            
    return(list_all,
           list_uuid,
           vm_summary,
           list_hostname,
           list_powerstate,
           list_dc,
           list_resource,
           list_vm_name)

def list_vm(host='',
             port='',
             user='',
             pwd=''):
    global list_all
    global list_uuid
    global list_path
    global list_hostname
    global vm_summary
    global list_powerstate
    global list_dc
    global list_resource
    global list_vm_name
    
    list_all = []
    list_uuid = []
    list_path = []
    list_hostname = []
    list_powerstate = []
    list_dc = []
    list_resource = []
    list_vm_name = []
    vm_summary = {}
    context = None
    
    if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()
    try:
        log_in = SmartConnect(host=host,
                          user=user,
                          pwd=pwd,
                          port=int(port),
                          sslContext=context)
    except:
        return(False)
    if not log_in:
        return(False)
    atexit.register(Disconnect, log_in)
    content = log_in.RetrieveContent()
    for child in content.rootFolder.childEntity:
        if hasattr(child, 'vmFolder'):
            datacenter = child
            vmFolder = datacenter.vmFolder
            vmList = vmFolder.childEntity
            for vm in vmList:
                dc = child.name
                dc_childfolder = child.hostFolder.childEntity
#                for childfolder in dc_childfolder:
#                    if hasattr(child, 'hostFolder'):
#                        for get_host_name in childfolder.host:
#                            if vm.runtime.host.name == get_host_name.name:
#                                dc_childfolder = childfolder.name
#                                break
                VM_LIST = Get_VM_List(vm,dc,dc_childfolder,child)
    return(VM_LIST)
