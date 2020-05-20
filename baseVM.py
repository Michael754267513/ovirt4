#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import ovirtsdk4 as sdk
import ovirtsdk4.types as types

class baseCreateVM:

    def __init__(self, url, username, password, CApath):
        try:
            # 连接ovirtM端
            self.connection = sdk.Connection(
                url=url,
                username=username,
                password=password,
                ca_file=CApath,
                # debug=True,
                # log=logging.getLogger(),
            )
        except Exception as ex:
            print("Unexpected error: %s" % ex)

    def statusVM(self,vmname):
        vms_service = self.connection.system_service().vms_service()
        chsum = 0
        while True:
            chsum += 1
            vms = vms_service.list(search='name=%s'% vmname)
            time.sleep(2)
            if chsum >= 300:
                #检查10分钟如果没有创建好返回失败
                break
            if vms != []:
                break
        for vm in vms:
            #获取所有search到的vm的名称和状态
            return vm.name, vm.status

    def checkVM(self,vmname,vmstaus):
        chsum = 0
        res = True
        while True:
            chsum += 1
            vmname, status = self.statusVM(vmname)
            # 判断vm的状态值，UP or DOWN ,DOWN 状态表示虚拟机创建好或者虚拟机关机
            if str(status) == str(vmstaus):
                break
            if chsum >= 300:
                #检查10分钟如果没有创建好返回失败
                res = False
                break
            time.sleep(2)
        return res

    def createVM(self,vmname,cluster,template,group,memory=10,description=None):
        vms_service = self.connection.system_service().vms_service()
        vms = vms_service.list(search='name=%s' % vmname)
        if vms:
            # 根据 虚拟机名称区分 虚拟机是否存在
            return ("%s虚拟机已存在"%vmname)
        vms_service.add(
            types.Vm(
                name=vmname,  # 虚拟机名称
                comment=group,  # 注释，这里用于分组
                description=description,  # 虚拟机的描述
                cluster=types.Cluster(
                    name=cluster,  # 虚拟机的集群环境
                ),
                template=types.Template(
                    name=template,  # 虚拟机集群环境的模板
                ),
                memory=memory * 2 ** 30,  # 内存 memory 单位GB，默认字节算
            )
        )
        self.checkVM(vmname, "down")  # 创建虚拟机，如果状态是down表示虚拟机已经创建好了

    def startVMWithClouldinit(self,vmname,fqdn,address,netmask,gateway,dns_server,dns_search,nicname="eth0"):
        vms_service = self.connection.system_service().vms_service()
        vm = vms_service.list(search='name=%s'%vmname)[0]
        vm_service = vms_service.vm_service(vm.id)
        vm_service.start(
            use_cloud_init=True,
            vm=types.Vm(
                initialization=types.Initialization(
                    # user_name='root',
                    # root_password='redhat123',
                    host_name=fqdn,  # 虚拟机的hostname
                    nic_configurations=[
                        types.NicConfiguration(
                            name=nicname,  # 默认网卡名为eth0 ，如果多网卡指定名称，目前不支持多网卡配置地址
                            on_boot=True,  # 网卡onboot=yes
                            boot_protocol=types.BootProtocol.STATIC,
                            ip=types.Ip(
                                version=types.IpVersion.V4,
                                address=address,  # 虚拟机的ip地址
                                netmask=netmask,  # 虚拟机的地址掩码
                                gateway=gateway   # 虚拟机的网关
                            )
                        )
                    ],
                    dns_servers=dns_server,  # 虚拟机DNS服务器地址
                    dns_search=dns_search,   # 虚拟机dns 查找域
                )
            )
        )
        # self.checkVM(vmname, "up")

    def delVM(self,vmname):
        vms_service = self.connection.system_service().vms_service()
        vms = vms_service.list(search='name=%s' % vmname)[0]
        vm_service = vms_service.vm_service(vms.id)
        vmname, status = self.statusVM(vmname)  # 获取当前需要删除虚拟机的状态
        if str(status) != "down":  # 如果当时虚拟机的状态不是关机状态，是不允许被删除
            self.stopVM(vmname)  # 不是down状态， 关闭虚拟机 状态改为down
            self.checkVM(vmname, "down")  # 检查状态是否是down，循环检查 检查状态为down 停止
        vm_service.remove()  # 状态为down的虚拟机 进行删除操作

    def stopVM(self,vmname):
        vms_service = self.connection.system_service().vms_service()
        vms = vms_service.list(search='name=%s'%vmname)[0]
        vm_service = vms_service.vm_service(vms.id)
        vm_service.stop()  # 关闭虚拟机
        self.checkVM(vmname, "down")  # 检查当前虚拟机的状态是否是down，状态为down结束

    def editVMCPU(self,vmname,core=2,socket=1):
        # 虚拟机的CPU在虚拟机看到的数量lscpu由 core 和 socket 组成
        vms_service = self.connection.system_service().vms_service()
        vm = vms_service.list(search='name=%s' % vmname)[0]
        vm_service = vms_service.vm_service(vm.id)
        vm_service.update(
            types.Vm(
                cpu=types.Cpu(topology=types.CpuTopology(
                    cores=core,     # 更新 虚拟机的 cpu core
                    sockets=socket,), # 更新 虚拟机的cpu socket
                )
            )
        )

    def editVMMEM(self,vmname,memsize):
        vms_service = self.connection.system_service().vms_service()
        vm = vms_service.list(search='name=%s'%vmname)[0]
        vm_service = vms_service.vm_service(vm.id)
        vm_service.update(
            types.Vm(
                memory=memsize * 2 ** 30,  # 更新虚拟机的内存大小
            ),
        )

    def addVMNIC(self,vmname,network,nicname):
        vms_service = self.connection.system_service().vms_service()
        vm = vms_service.list(search='name=%s'%vmname)[0]
        profiles_service = self.connection.system_service().vnic_profiles_service()
        profile_id = None  # network的网卡编号UUID
        network_list = profiles_service.list()
        for profile in network_list:
            if profile.name == network:  # 判断网卡名是否是network传来的名称
                profile_id = profile.id  # 获取network对应网卡名的UUID
                try:
                    nics_service = vms_service.vm_service(vm.id).nics_service()
                    nics_service.add(
                        types.Nic(
                            name=nicname,  # 虚拟机新增网卡
                            description='My network interface',  # 描述
                            vnic_profile=types.VnicProfile(
                            id=profile_id,  # 选择添加网卡关联的nic，这个与ovirt的网络关联，网络关联的是vlanid
                         ),
                        ),
                    )
                    break  # 停止查找
                except:
                    pass

    def addVMDisk(self,vmname,storagedomain,disksize,diskname,disk_desc):
        vms_service = self.connection.system_service().vms_service()
        vm = vms_service.list(search='name=%s'%str(vmname))[0] # 如果search 多个只获取第一个，后面雷同
        disk_attachments_service = vms_service.vm_service(vm.id).disk_attachments_service()
        disk_attachment = disk_attachments_service.add(
            types.DiskAttachment(
                disk=types.Disk(
                    name=diskname,      # 新增磁盘名称
                    description=disk_desc,  # 新增磁盘描述
                    format=types.DiskFormat.COW,  # 新增磁盘类型为COW
                    provisioned_size=disksize * 2 ** 30,  # 新增磁盘大小
                    storage_domains=[
                        types.StorageDomain(
                            name=storagedomain,  # 从那个存储域获取资源
                        ),
                    ],
                ),
                interface=types.DiskInterface.VIRTIO,  # 磁盘接口类型
                bootable=False,
                active=True,  # 是否激活
            ),
        )
        disks_service = self.connection.system_service().disks_service()  # 获取集群 相关磁盘服务
        disk_service = disks_service.disk_service(disk_attachment.disk.id)   # 根据 磁盘相关信息获取当前附加磁盘状态
        while True:
            time.sleep(2)
            disk = disk_service.get()  # 获取磁盘相关信息
            if disk.status == types.DiskStatus.OK:  # 判断磁盘状态是否正常
                break

    def createVM_startVM(self,vmname,memory,hostname,cpu,group,description,vlanid,address,netmask,gateway,dns_server,dns_domain,cluster="HPcluster",template="geedun",nicname="eth0"):
        self.createVM(vmname=vmname,cluster=cluster,template=template,group=group,description=description,memory=memory)
        self.addVMNIC(vmname=vmname,network=vlanid,nicname=nicname)
        self.editVMCPU(vmname=vmname,core=cpu)
        self.startVMWithClouldinit(vmname=vmname,fqdn=hostname,address=address,netmask=netmask,gateway=gateway,dns_server=dns_server,dns_search=dns_domain)
        self.close()

    def close(self):
        self.connection.close()  # 关闭连接
# vm = baseCreateVM(url="https://engine.com.cn/ovirt-engine/api", username="admin@internal",password="!@#ASD$!s2",CApath="/root/test/CA/test.pem")
# vm.createVM_startVM(hostname="aaa",vmname="ui02",memory=8,cpu=8,group="test",description="risk UI",vlanid="ovirtmgmt",address="10.158.100.57",netmask="255.255.255.0",gateway="10.158.100.1",dns_server="10.148.158.1",dns_domain="test.com",cluster="cluster-test",template="template")
# vm.close()
