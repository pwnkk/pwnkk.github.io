---
layout: post
title:  "路由器漏洞复现"
categories: pwn
tags: pwn 
excerpt: 路由器漏洞复现
mathjax: true
---

* content
{:toc}

### Overview
看了《揭秘家用路由器0day漏洞挖掘技术》这本书,自己本身也是pwn手，但是没有做过这方面的利用，复现一下其中的二进制洞，补充一下路由器方面的知识。

### 环境准备

1. 工具
    * binwalk : 从github下的新版本
    * [firmware-mod-kit](https://github.com/rampageX/firmware-mod-kit)
    * [gdbserver](https://github.com/rapid7/embedded-tools/tree/master/binaries/gdbserver)

解压固件
binwalk -e 

2. 搭建交叉编译环境

`wget https://buildroot.org/downloads/buildroot-2018.02.1.tar.gz`

`make menuconfig` 配置编译选项
选择mips 小端序
toolchain的kernel header和本机内核版本一致，选中Build cross gdb for the host 

编译完成的路径，加入环境变量
`/home/pwn/tools/Iot/buildroot-2018.02.1/output/host/bin`

后面的分析中又出现了大端序的程序，因此编译了两个版本的工具链。

### 系统模式环境搭建 

搭建出系统环境，就能基本模拟出路由器，可以测试exp了。在ubuntu 16.04 中 模拟出来没有网络。Firmadyne 是个模拟的好工具，但是调试功能有待探索。
使用了 AttifyOS ，它是IOT的工具集成系统，但是它是32位的,不知道是不是只有32位可以。

用户模式可以模拟执行单独的程序，系统模式则尝试模拟出整个路由器。
| 选项 | 说明 |
| ---- | ---- |
| -kernel bzImage | 指定内核镜像  |
| -hda/-hdb file | 指定硬盘镜像|
| -initrd file | RAM 初始化磁盘|
| -nographic | 禁用图形输出 |
| -append cmdline | 内核命令行|

命令格式为`qemu-system-mipsel -kernel vmlinux-3.2.0-4-4kc-malta -hda debian_wheezy_mipsel_standard.qcow2 -append "root=/dev/sda1 console=ttyS0" -nographic `

1. 下载镜像
https://people.debian.org/~aurel32/qemu/mipsel/ 下载 vmlinux-3.2.0-4-4kc-malta 和 debian_wheezy_mipsel_standard.qcow2 
2. 配置网络
配置qemu网络，使qemu虚拟机和宿主机互通
`sudo apt-get install bridge-utils uml-utilities` 

建立桥接网络
编辑 /etc/network/interfaces 
```
iface br0 inet dhcp
  bridge_ports eth0
  bridge_maxwait 0
```
重启网络
```
sudo ifdown eth0
sudo ifup eth0
sudo ifup br0
```
此时会看到br0 抢夺了eth0 的地址
```
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast master br0 state UP group default qlen 1000
    link/ether 00:0c:29:99:3c:67 brd ff:ff:ff:ff:ff:ff
3: virbr0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default
    link/ether 76:ce:72:33:39:72 brd ff:ff:ff:ff:ff:ff
    inet 192.168.122.1/24 brd 192.168.122.255 scope global virbr0
       valid_lft forever preferred_lft forever
5: br0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
    link/ether 00:0c:29:99:3c:67 brd ff:ff:ff:ff:ff:ff
    inet 192.168.74.133/24 brd 192.168.74.255 scope global br0
       valid_lft forever preferred_lft forever
    inet6 fe80::20c:29ff:fe99:3c67/64 scope link
       valid_lft forever preferred_lft forever
```

3. 启动

`sudo qemu-system-mipsel -M malta -kernel vmlinux-3.2.0-4-4kc-malta -hda debian_wheezy_mipsel_standard.qcow2 -append "root=/dev/sda1 console=tty0" -net nic,macaddr=00:16:3e:00:00:01 -net tap -nographic`

启动后就会发现网卡IP和宿主机在同一网段dhcp的，而且有ssh服务

4. 替换文件
安装`sudo apt-get install libguestfs-tools`
`sudo guestmount  -a ./debian_squeeze_mipsel_standard.qcow2 -m /dev/sda1 ./point`

拷贝htdocs , lib , etc
mount 挂载磁盘修改文件后umount 即可

sudo cp -r etc /mnt/point/etc/
sudo cp -r htdocs /mnt/point/
sudo cp ./sbin/httpd /mnt/point/sbin/


修复后报错 

root@debian-mipsel:~# httpd
httpd: can't load library 'libgcc_s.so.1'


#### 修复文件

```
cp ld-uClibc-0.9.28.so ld-uClibc.so.0
cp libuClibc-0.9.28.so libc.so.0
```

报错
`bin/goahead: can't load library 'libnvram.so.0'`
[nvram-faker](https://github.com/zcutlip/nvram-faker)
运行`buildmipsel.sh`,生成了`libnvram-faker.so`


放到linux中解压即可保留下lib中的符号链接
chroot . ./qemu-mipsel-static bin/goahead


### CVE-2018-20056漏洞复现

[固件地址](ftp://ftp2.dlink.com/PRODUCTS/DIR-619L/REVB/DIR-619L_REVB_FIRMWARE_v2.04B04.zip)

```
root@ubuntu:/home/IOT/DIR619/_DIR-619L_v2.04B04.bin.extracted/squashfs-root-0# readelf -h bin/boa
ELF Header:
  Magic:   7f 45 4c 46 01 02 01 00 00 00 00 00 00 00 00 00
  Class:                             ELF32
  Data:                              2's complement, big endian
  Version:                           1 (current)
  OS/ABI:                            UNIX - System V
  ABI Version:                       0
  Type:                              EXEC (Executable file)
  Machine:                           MIPS R3000
  Version:                           0x1
  Entry point address:               0x407520
  Start of program headers:          52 (bytes into file)
  Start of section headers:          0 (bytes into file)
  Flags:                             0x1007, noreorder, pic, cpic, o32, mips1
  Size of this header:               52 (bytes)
  Size of program headers:           32 (bytes)
  Number of program headers:         7
  Size of section headers:           0 (bytes)
  Number of section headers:         0
  Section header string table index: 0
```
程序是big endian 使用qemu-mips-static 

根据报错定位
```
$ chroot . ./qemu-mips-static bin/boa
Initialize AP MIB failed!
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
Segmentation fault (core dumped)
```
使用ghidra逆向显示如下

![](IMG/2019-11-29-router_begin/init.png)

需要劫持apmib_init()函数,编写程序如下

```c
#include <stdio.h>
#include <stdlib.h>
int apmib_init(void){
    return 1;
}
//mips-linux-gcc -Wall -fPIC -shared apmi.c -o apmib-ld.so
```

`chroot . ./qemu-mips-static -E LD_PRELOAD=./apmib-ld.so bin/boa`

随后报错如下 
```
Create chklist file error!
Create chklist file error!
hard ver is
Create f/w version file error!
Create chklist file error!
boa: server version Boa/0.94.14rc21
boa: server built Feb 13 2015 at 17:32:35.
boa: starting server pid=7410, port 80
Unsupported ioctl: cmd=0x89f0
device ioctl:: Function not implemented
```
IDA 远程调试 在_apmib_init 下断点后单步调试


### IDA python查找危险函数

|函数|功能|
|---|---|
|LocByName(funcname) | 通过函数名查找函数地址|
|CodeRefsTo(ea,flow) | 查找目标地址的交叉引用,flow=1 跟随控制流,否则不跟随 |
|Message()  | 输入提示信息 |
|MakeComm() | 设置注释 |
|SetColor(addr,CIC_ITEM,0x0000ff) | 标记颜色 |

```
from idaapi import *
danger_funcs = ["strcpy","sprintf","strncpy"] 

def judgeAduit(addr):
    MakeComm(addr,"### AUDIT HERE ###")
    SetColor(addr,CIC_ITEM,0x0000ff)  #set backgroud to red

def flagCalls(danger_funcs):
    count = 0
    for func in danger_funcs:      
        faddr = LocByName( func )     
        if faddr != BADADDR: 
            # Grab the cross-references to this address         
            cross_refs = CodeRefsTo( faddr, 0 )                       
            for addr in cross_refs:
                count += 1
                Message("%s[%d] calls 0x%08x\n"%(func,count,addr))
                judgeAduit(addr)
                
if __name__ == '__main__':
    print "-------------------------------"
    danger_funcs = ["strcpy","sprintf","strncpy"] 
    flagCalls(danger_funcs)
    print "-------------------------------"
```
从IDA file => script file 打开, 可以减少一些重复工作, 可惜IDA 不能输出mips伪代码 ... 

#### 
### 参考

[mipsrop IDA7.0](https://github.com/Iolop/ida7.0Plugin)
[attifyos](https://github.com/adi0x90/attifyos)
[路由器漏洞分析系列](https://xz.aliyun.com/t/5699)


