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



### 参考

[路由器漏洞分析系列](https://xz.aliyun.com/t/5699)


