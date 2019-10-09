---
layout: post
title:  "内核环境搭建及调试"
date:   2019-09-24 13:54:00
categories: pwn
tags: pwn
excerpt: CTF内核题目环境配置
mathjax: true
---

* content
{:toc}

### Overview 
记录下内核编译及模块的编写调试。

### 0x00 环境准备
先编译内核和busybox, 测试系统 ubuntu16.04

1. 编译内核代码

```
wget https://mirrors.edge.kernel.org/pub/linux/kernel/v4.x/linux-4.4.101.tar.gz
tar zxvf linux-4.4.101.tar.gz
apt-get install libncurses5-dev build-essential kernel-package
cd linux-4.4.101
make menuconfig
```

开启选项
Kernel hacking  ==>  Compile-time checks and compiler options  ==> Compile the kernel with frame pointers
                                                               ==>  Compile the kernel with debug info
                ==>  KGDB: kernel debugger  
关闭选项
                ==>  Write protect kernel read-only data structures （取消）

`make && make modules_install && make install`

2. 编译busybox

```
wget https://busybox.net/downloads/busybox-1.29.3.tar.bz2
tar jxvf busybox-1.29.3.tar.bz2
make menuconfig
#开启
#Settings ==>  Build static binary (no shared libs)
#关闭
#Networking Utilities ==>   inetd (18 kb)
make && make install
```
在_install  目录下有编译好的文件

```sh
cd _install
mkdir proc sys dev etc etc/init.d
vim etc/init.d/rcS
chmod +x etc/init.d/rcS
```

rcS内容
```sh
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
/sbin/mdev -s
```
在_install 目录创建文件系统 `find . | cpio -o --format=newc > ../rootfs.img`

qemu加载linux内核和busybox
```
qemu-system-x86_64 -kernel /home/pwn/kernel/linux-4.4.101/arch/x86_64/boot/bzImage -initrd /home/pwn/kernel/busybox-1.29.3/rootfs.img -append "console=ttyS 0 root=/dev/ram rdinit=/sbin/init" -cpu kvm64,+smep,+smap --nographic -gdb tcp::1234
```
退出qemu `ctrl + A 加X` 

### 0x02 编写驱动入门
编写一个驱动和一个c程序和驱动交互
编写hello.c

```
#include <linux/init.h>
#include <linux/module.h>

static int hello_init(void)
{
    printk(KERN_ALERT "Hello world\n");
    return 0;
}

static int hello_exit(void){
    printk(KERN_ALERT "Goodbye kernel");
}
module_init(hello_init);
module_exit(hello_exit);
```

编写makefile
`obj-m := hello.o`
如果有2个文件的话

```
obj-m := module.o
module-objs := file1.o file2.o
```

编译需要指定内核代码树的路径，编译出对应内核的module

```
make -C ~/kernel/linux-4.4.101 M=`pwd` modules
```

编译过后出现hello.ko

安装模块 insmod hello.ko 
insmod: ERROR: could not insert module hello.ko: Invalid module format
显示格式错误，这是因为系统内核和源码的内核版本不一致导致的,进入qemu后安装即可。

尝试在qemu中载入内核
将hello.ko 放到busybox目录下的_install/lib/ 中
etc/init.d/rcS如下

```
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs devtmpfs /dev
#/sbin/mdev -s  为驱动创建文件节点 
insmod /lib/hello.ko
```

创建文件系统

`find . | cpio -o --format=newc > ../rootfs.img`

将rootfs.img 和 bzImage 都放到当前目录下
执行启动脚本run.sh

```
qemu-system-x86_64 -kernel ./bzImage -initrd ./rootfs.img -append "console=ttyS 0 root=/dev/ram rdinit=/sbin/init" -cpu kvm64,+smep,+smap --nographic -gdb tcp::1234
```

### 0x03 调试内核模块
如何给模块中的函数下断点 

* 先从内核机器中读取基地址

```
grep 0 /sys/module/hello/sections/.text 
0xffffffffc0005000
```

* 在宿主机的gdb中载入内核模块,加上基地址

```
gdb-peda$ add-symbol-file /home/pwn/kernel/module_demo/hello/hello.ko 0xffffffffc0005000
add symbol table from file "/home/pwn/kernel/module_demo/hello/hello.ko" at
        .text_addr = 0xffffffffc0005000
Reading symbols from /home/pwn/kernel/module_demo/hello/hello.ko...done.
gdb-peda$ b *hello_init
Breakpoint 1 at 0xffffffffc0005000: file /home/pwn/kernel/module_demo/hello/hello.c, line 5.
```

如果有bss和data段的地址也可以加上

```
add-symbol-file /home/pwn/kernel/module_demo/hello/hello.ko 0xffffffffc0000000 -s .bss bss_addr -s .data data_addr 
```

gdb内核调试问题:

1. 出现reply过长的问题
`set architecture i386:x86-64:intel`

### 参考链接
* [内核环境配置](https://xz.aliyun.com/t/2024)

