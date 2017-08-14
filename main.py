#!/usr/bin/python
#encoding=utf-8
'''*******************************************************************************
# Author : Patrick Zheng
# Email : zzcahj@163.com
# Last modified : 2017-07-25 21:16
# Filename : main.py
#*******************************************************************************'''
import sys
import time
import os
import uuid
import ssl
import atexit
import list_vm
import re
import migration_vm
import subprocess

from snack import *
from pyVim import connect
from pyVmomi import vim

def warning_form(screen, title, text, help = None):
#警告窗口
    btn = Button("确定")
    war = GridForm(screen, title, 1, 15)
    war.add(Label(text),0,1)
    war.add(Label(""),0,2)
    war.add(btn, 0, 3)
    war.runOnce(35,10)

def vmware_ip_form(screen, title, text, prompts, allowCancel = 1,
        width = 40, entryWidth = 20, buttons = [ '确定', '取消' ], 
        help = None):
    bb = ButtonBar(screen, buttons);
    t = TextboxReflowed(width, text)
    count = 0
    for n in prompts:
        count = count + 1
    sg = Grid(2, count)
    count = 0
    entryList = []
    for n in prompts:
        if str(n) == '密码：':
          e = Entry(entryWidth, password = 1)
        else :
          e = Entry(entryWidth, password = 0)
        sg.setField(Label(n), 0, count, padding=(0, 0, 1, 0), anchorRight=1)
        sg.setField(e, 1, count, anchorLeft=1)
        count = count + 1
        entryList.append(e)
    g = GridFormHelp(screen, title, help, 1, 3)
    g.add(t, 0, 0, padding = (0, 0, 0, 1))
    g.add(sg, 0, 1, padding = (0, 0, 0, 1))
    g.add(bb, 0, 2, growx = 1)
    result = g.runOnce(20,5)
    entryValues = []
    count = 0
    for n in prompts:
        entryValues.append(entryList[count].value())
        count = count + 1
    return (result, bb.buttonPressed(result), tuple(entryValues))

def checkip(ip):
    return re.match('^(([01]?\d\d?|2[0-4]\d|25[0-5])\.){3}([01]?\d\d?|2[0-4]\d|25[0-5])$',ip)

def quit_form():
    global quit
    buttons = ("是", "否")
    button_bar = ButtonBar(screen, buttons)
    quit_grid = GridForm(screen, "返回登陆界面？" , 20,16)
    quit_grid.add(button_bar,1,3,(10,0,10,0), growx = 1)
    render_quit_form = quit_grid.runOnce(32,8)
    screen.popWindow()
    if render_quit_form == "ESC" or button_bar.buttonPressed(render_quit_form) == "否":
        screen.finish()
        return main_form()
    else:
        screen.finish()
        quit = True
        return

def init_ui():
    global screen
    screen = SnackScreen()
    screen.finish()
    screen = SnackScreen()
    screen.setColor("ROOT", "gray", "blue")
    screen.setColor("ENTRY","black","blue")
    screen.setColor("LABEL","black","yellow")
    screen.setColor("HELPLINE","black","blue")
    screen.setColor("TEXTBOX","black","yellow")

def vm_list_form(host_ip,
                 host_port,
                 host_user,
                 host_pass,
                 current_vm=0):
    vm_list = ''
    vm_list = list_vm.list_vm(host_ip,host_port,host_user,host_pass)
    if vm_list == False:
        warning_form(screen,'确定','VMware主机连接失败')
        return
    vm_list_box = Listbox(height = 15,
                          width = 82,
                          returnExit = 1,
                          showCursor = 0,
                          scroll = 1)
    list_num = 0
    for i in vm_list[0]:
        vm_list_box.append(i,list_num)
        list_num = list_num + 1
    vm_list_box.setCurrent(current_vm)
    button = CompactButton('<<<返回>>>')
    vm_list_form_grid = GridForm(screen, 'VM List', 1, 10)
    vm_list_form_grid.add(Label("{:^18}".format(u'名称')+\
                                '|'+"{:^40}".format(u'操作系统')+\
                                '|'+"{:^11}".format(u'电源状态')
                                ),0,1)
    vm_list_form_grid.add(vm_list_box,0,2)
    vm_list_form_grid.add(Label(''),0,3)
    vm_list_form_grid.add(button,0,4)
    render_vm_list_form = vm_list_form_grid.runOnce(25,3)
    if render_vm_list_form == 'ESC' or 'snack.CompactButton' in \
                              str(render_vm_list_form):
        return
    vm_uuid = vm_list[1]
    vm_summary = vm_list[2]
    vm_host = vm_list[3]
    vm_powerstate = vm_list[4]
    vm_dc = vm_list[5]
    vm_resource_pool = vm_list[6]
    vm_name = vm_list[7]
    select_vm = vm_uuid[vm_list_box.current()]
    select_vm_summary = vm_summary[select_vm]
    select_vm_host = vm_host[vm_list_box.current()].rstrip('\n')
    select_vm_powerstate = vm_powerstate[vm_list_box.current()].rstrip('\n')
    select_vm_dc = vm_dc[vm_list_box.current()].rstrip('\n')
    select_vm_resource_pool = vm_resource_pool[vm_list_box.current()].rstrip('\n')
    select_vm_name = vm_name[vm_list_box.current()].rstrip('\n')
    vm_detail_form(select_vm,
                   select_vm_summary,
                   host_ip,
                   host_port,
                   host_user,
                   host_pass,
                   select_vm_host,
                   select_vm_powerstate,
                   select_vm_dc,
                   select_vm_resource_pool,
                   select_vm_name,
                   current_vm=vm_list_box.current())
    return

def vm_detail_form(select_vm,
                   select_vm_summary,
                   host_ip,
                   host_port,
                   host_user,
                   host_pass,
                   vm_host,
                   vm_powerstate,
                   vm_dc,
                   vm_resource_pool,
                   vm_name,
                   current_vm=0):

    warning_form(screen,'确定','迁移前请确认关闭虚拟机电源且合并快照')
    vm_detail = ''
    for key,val in select_vm_summary.items():
        if type(val) != dict:
            vm_detail = vm_detail + str(key)
            vm_detail = vm_detail + str(val) + '\n'
            continue
        vm_detail =  vm_detail + str(key) + '\n'
        for key_1,val_1 in val.items():
            if type(val_1) != dict:
                vm_detail = vm_detail + str(key_1)
                vm_detail = vm_detail + str(val_1) + '\n'
                continue
            vm_detail =  vm_detail + str(key_1) + '\n'
            for key_2,val_2 in val_1.items():
                if type(val_2) != dict:
                    vm_detail = vm_detail + str(key_2)
                    vm_detail = vm_detail + str(val_2) + '\n'
                    continue
                vm_detail =  vm_detail + str(key_2) + '\n'
                for key_3,val_3 in val_2.items():
                    vm_detail = vm_detail + str(key_3)
                    vm_detail = vm_detail + str(val_3) + '\n'
    vm_detail_form_grid = GridForm(screen, 'VM详细信息及操作', 1, 10)
    vm_detail_form_grid.add(Textbox(70, 15, vm_detail, scroll = 1, wrap = 1), 0, 1)
    vm_detail_list_box = Listbox(height = 4,
                                 width = 26,
                                 returnExit = 1,
                                 showCursor = 0,
                                 border = 1)
    vm_detail_list_box.append("{: ^28}".format('<--迁移虚拟机-->'),0)
    vm_detail_list_box.append("{: ^24}".format('<-返回->'),1)
    vm_detail_form_grid.add(Label(""),0,2)
    vm_detail_form_grid.add(vm_detail_list_box,0,3)
    render_vm_detail_form = vm_detail_form_grid.runOnce(25,3)
    if render_vm_detail_form == 'ESC' or \
                                vm_detail_list_box.current() == 1:
        return vm_list_form(host_ip,
                            host_port,
                            host_user,
                            host_pass,
                            current_vm)
    migration_exist = os.popen('cat ./migration_state').readlines()
    for i in migration_exist:
        if vm_name in i and host_ip in i and vm_host in i:
            warning_form(screen,'确定','虚拟机迁移任务已经存在，请在迁移任务状态中查看')
            return vm_list_form(host_ip,
                                host_port,
                                host_user,
                                host_pass,
                                current_vm)
    if vm_powerstate == 'poweredOff' :
        warning_form(screen,'确定','如虚拟机快照未合并将造成迁移任务挂起')
        migration_folder_name = migration_folder + '/' + host_ip + '_' +\
                                vm_name + '/'
        os.popen('mkdir ' + migration_folder_name + ' -p')
        migration_vm.migration_start(host_user,
                                     password_file,
                                     host_ip,
                                     vm_dc,
                                     vm_resource_pool,
                                     vm_host,
                                     vm_name,
                                     migration_folder_name,
                                     esxi_check)
        warning_form(screen,'确定','任务开始，请至“迁移任务状态”菜单中查看')
        return vm_list_form(host_ip,
                            host_port,
                            host_user,
                            host_pass,
                            current_vm)
    else:
        warning_form(screen,'确定','请确认虚拟机电源已经关闭')
        return vm_list_form(host_ip,
                            host_port,
                            host_user,
                            host_pass,
                            current_vm)

def vm_host_ip_setup():
    global host_ip
    global host_port
    global host_user
    global host_pass
    global password_file
    global esxi_check
    vmware_ip_config = vmware_ip_form(screen,
                                  'VMware主机连接IP设置',
                                  '请配置VMware主机地址信息',
                                  ['主机地址：','端口(默认443)：',
                                   '用户名：','密码：'],
                                  width = 60,
                                  entryWidth = 40,
                                  buttons = ['确认','取消'])
    if vmware_ip_config[1] == '取消':
        warning_form(screen,'确定','配置已取消')
        return
    if not checkip(vmware_ip_config[2][0]) or vmware_ip_config[2][0] == '':
        warning_form(screen,'确定','主机地址不能为空或非ip地址')
        return
    temp_host_ip = str(vmware_ip_config[2][0])
    if vmware_ip_config[2][1] == '':
        temp_host_port = 443
    else:
        try:
            int(vmware_ip_config[2][1])
            if vmware_ip_config[2][1] <= 0 or vmware_ip_config[2][1] > 65535:
                warning_form(screen,'确定','请输入正确的端口地址')
                return
            temp_host_port = vmware_ip_config[2][1]
        except:
            warning_form(screen,'确定','请输入正确的端口地址')
            return
    if vmware_ip_config[2][2] == '':
        warning_form(screen,'确定','用户名不能为空')
        return
    temp_host_user = vmware_ip_config[2][2]
    if vmware_ip_config[2][3] == '':
        warning_form(screen,'确定','密码不能为空')
        return
    temp_host_pass = vmware_ip_config[2][3]
    service_instance = None
    context = None
    if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()
    try:
        service_instance = connect.SmartConnect(host=temp_host_ip,
                                                user=temp_host_user,
                                                pwd=temp_host_pass,
                                                port=temp_host_port,
                                                sslContext=context)
        atexit.register(connect.Disconnect, service_instance)
    except :
        warning_form(screen,'确定','VMware主机连接失败，请检查配置')
        return

    if not service_instance:
        warning_form(screen,'确定','VMware主机连接失败，请检查配置')
        return
    content = service_instance.RetrieveContent()
    if 'ESXi' in content.about.fullName:
        esxi_check = True
    else:
        esxi_check = False
    warning_form(screen,'确定','VMware主机连接成功')
    host_ip = temp_host_ip
    host_port = temp_host_port
    host_user = temp_host_user
    host_pass = temp_host_pass
    password_file = '/tmp/' + str(uuid.uuid1())
    os.system('echo ' + host_pass + ' > ' + password_file)
    return

def vm_migration_state(select_current=0):
    get_migration_state = os.popen('cat ./migration_state').readlines()
    get_migration_log_file = os.popen('cat ./migration_log_file').readlines()
    if get_migration_state == [] or select_current < 0:
        warning_form(screen,'确定','暂时没有任何迁移任务')
        return
    state_list_box = Listbox(height = 15,
                             width = 82,
                             returnExit = 1,
                             showCursor = 0,
                             scroll = 1)
    list_num = 0
    for i in get_migration_state:
        state_list_box.append(i,list_num)
        list_num = list_num + 1
    button = CompactButton('<<<返回>>>')
    state_list_form_grid = GridForm(screen, '迁移状态列表', 1, 10)
    state_list_form_grid.add(Label("{0: ^8}".format(u'进程')+\
                                '|'+"{0: ^20}".format('vCenter地址')+\
                                '|'+"{0: ^23}".format('宿主机地址')+\
                                '|'+"{0: ^17}".format('虚拟机名称')+\
                                '|'+"{0: ^23}".format('任务状态')
                                ),0,1)
    state_list_form_grid.add(state_list_box,0,2)
    state_list_form_grid.add(button,0,3)
    state_list_box.setCurrent(select_current)
    render_state_list_form = state_list_form_grid.run(25,3)
    if render_state_list_form == 'ESC' or 'snack.CompactButton' in \
                                 str(render_state_list_form) :
        return
    else:
        state_controll = Listbox(height = 3,
                                 width = 15,
                                 returnExit = 1,
                                 showCursor = 0)
        state_controll.append('详细日志',0)
        state_controll.append('删除日志',1)
        button_2 = CompactButton('<<返回>>')
        state_controll_grid = GridForm(screen,'<-操作->', 1, 10)
        state_controll_grid.add(state_controll,0,1)
        state_controll_grid.add(button_2,0,2)
        render_state_controll = state_controll_grid.runOnce(40,8)
        if render_state_controll == 'ESC' or 'snack.CompactButton' in \
            str(render_state_controll):
            return vm_migration_state(select_current=state_list_box.current())
        elif state_controll.current() == 0:
            while True:
                state_detail = \
                os.popen('cat %s'%(get_migration_log_file[state_list_box.current()])).read()
                state_detail = state_detail.replace('\r','set_flag\n')
                tmp_path = get_migration_log_file[state_list_box.current()].replace('./migration_log','/tmp')
                tmp_path = tmp_path.replace('\n','')
                state_tmp = open(tmp_path,'w')
                state_tmp.write(state_detail)
                state_tmp.close()
                state_tmp = os.popen('cat %s'%(tmp_path)).readlines()
                start = 0
                for i in state_tmp:
                    if 'set_flag\n' in i:
                        break
                    start = start + 1
                end = start
                for i in state_tmp[start:]:
                    if 'set_flag\n' in i:
                        end = end + 1
                    else:
                        break
                state_detail = ''
                for i in state_tmp[0:start-1]:
                    state_detail = state_detail + i
                for i in state_tmp[end:]:
                    state_detail = state_detail + i.replace('set_flag\n','\n')
                state_detail_form_grid = GridForm(screen, '迁移状态日志', 1, 10)
                button = CompactButton('<<<返回>>>')
                state_detail_form_grid.add(button,0,2)
                state_detail_form_grid.add(Textbox(90, 25,
                                                   state_detail + '\n',
                                                   scroll = 1,
                                                   wrap = 1),
                                                   0,1)
                state_detail_form_grid.setTimer(200)
                render_state_detail_form = state_detail_form_grid.runOnce(25,3)
                if render_state_detail_form == 'ESC' or 'snack.CompactButton' in \
                                             str(render_state_detail_form) :
                    return vm_migration_state(select_current=state_list_box.current())
        else:
            task_id = get_migration_state[state_list_box.current()][0:10]
            task_running = int(os.popen('ps aux | grep %s | wc -l'%(task_id)).read())
            if '未完成' in \
            get_migration_state[state_list_box.current()] \
            or \
            '开始转换' in \
            get_migration_state[state_list_box.current()] \
            or \
            task_running > 2 :
                if '任务完成' not in get_migration_state[state_list_box.current()] \
                or \
                '失败' not in get_migration_state[state_list_box.current()]:
                    warning_form(screen,'确定','不能清除未完成且在运行的任务')
                    return vm_migration_state(select_current=state_list_box.current())
            os.system('rm -f %s'%(get_migration_log_file[state_list_box.current()]))
            del get_migration_state[state_list_box.current()]
            del get_migration_log_file[state_list_box.current()]
            get_migration_state_file = open('./migration_state','w')
            get_migration_log_file_file = open('./migration_log_file','w')
            for i in get_migration_state:
                get_migration_state_file.write(i)
            for i in get_migration_log_file:
                get_migration_log_file_file.write(i)
            get_migration_state_file.close()
            get_migration_log_file_file.close()
            return vm_migration_state(select_current=state_list_box.current()-1)

def main_form():
    global main_select
    init_ui()
    if host_ip == '':
        vm_host_ip_setup()
        return
    list_box = Listbox(height = 15, width = 18, returnExit = 1, showCursor = 0)
    list_box.append("a)虚拟机清单", 1)
    list_box.append("b)VMware地址配置",2)
    list_box.append("c)迁移状态检查",3)
    button = CompactButton('<<<退出>>>')
    list_box.setCurrent(main_select)
    form_name = os.popen('uname -n').read().strip('\n')
    main_form_grid = GridForm(screen, form_name, 1, 10)
    main_form_grid.add(list_box, 0, 1)
    main_form_grid.add(button, 0, 2)
    main_form_grid.add(Label("-----------------"),0,3)
    main_form_grid.add(Label("【PtONE】"),0,4)
    main_form_grid.add(Label("【虚拟机迁移程序】"),0,5)
    main_form_grid.add(Label("--已连接主机--"),0,6)
    main_form_grid.add(Label(host_ip),0,7)
    screen.pushHelpLine("<Version 0.1 alpha> 南京普天通信股份有限公司版权所有...请使用TAB键在选项间切换")
    render_main_form = main_form_grid.run(1,3)
    if render_main_form == 'ESC' or 'snack.CompactButton' in \
                            str(render_main_form) :
        return quit_form()
    if list_box.current() == 1:
        main_select = list_box.current()
        vm_list_form(host_ip,host_port,host_user,host_pass)
        return
    if list_box.current() == 2:
        main_select = list_box.current()
        vm_host_ip_setup()
        return
    if list_box.current() == 3:
        main_select = list_box.current()
        vm_migration_state()
        return

if __name__ == "__main__":
    esxi_check = ''
    host_ip = ''
    host_port = ''
    host_user = ''
    host_pass = ''
    password_file = ''
    main_select = 1
    os.environ['LIBGUESTFS_BACKEND'] = 'direct'
    reload(sys)
    sys.setdefaultencoding(' utf-8 ')
    os.system('mkdir ./migration_log/ -p')
    os.system('touch ./migration_state')
    os.system('touch ./migration_log_file')
    migration_folder = '/mnt/vmmenu_migration'
    while quit != True:
        main_form()
    sys.exit(0)